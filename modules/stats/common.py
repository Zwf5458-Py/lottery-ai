from modules.constants import get_zodiac_mapping, get_color, RED_NUMS, BLUE_NUMS, GREEN_NUMS, ZODIAC_ORDER, NUM_TO_ZODIAC_IDX, ZODIAC_NUMS
import pandas as pd
import math
import numpy as np
from modules.data_processor import load_data, clean_data

from collections import Counter

def _normal_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _chi_square_p_value(chi2: float, dfree: int) -> float:
    if dfree <= 0:
        return 1.0
    if chi2 <= 0:
        return 1.0
    # Wilson-Hilferty approximation
    a = 2.0 / (9.0 * dfree)
    z = ((chi2 / dfree) ** (1.0 / 3.0) - (1.0 - a)) / math.sqrt(a)
    return max(0.0, min(1.0, _normal_sf(z)))



def _get_all_numbers(df: pd.DataFrame) -> list:
    """提取所有正码（不含特码），返回扁平化列表"""
    number_cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']
    all_nums = []
    for col in number_cols:
        all_nums.extend(df[col].tolist())
    return all_nums


def _get_all_numbers_with_special(df: pd.DataFrame) -> list:
    """提取特码（忽略正码）作为全局统计的基础"""
    return df['special_num'].tolist()


def number_frequency(df: pd.DataFrame = None, periods: int = 100, lottery_type: str = 'macaujc', zone: int = 1) -> dict:
    """
    号码出现频率分布
    返回: {号码: 出现次数} 的字典，按号码排序
    """
    if df is None:
        df = clean_data(load_data(lottery_type))
    
    # 截取用户配置的统计期数
    if periods > 0:
        df = df.head(periods)
    
    if lottery_type == 'weilitsai':
        if zone == 1:
            all_nums = []
            for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                if col in df.columns:
                    all_nums.extend(df[col].tolist())
            max_num = 38
        else:
            all_nums = df['special_num'].tolist() if 'special_num' in df.columns else []
            max_num = 8
    else:
        all_nums = _get_all_numbers_with_special(df)
        max_num = 49

    counter = Counter(all_nums)
    
    result = {}
    for i in range(1, max_num + 1):
        result[i] = counter.get(i, 0)
    
    return result


def hot_cold_numbers(top_n: int = 10, df: pd.DataFrame = None, periods: int = 100, lottery_type: str = 'macaujc', zone: int = 1) -> dict:
    """
    冷热号统计
    参数:
        top_n: 返回前 N 个最热/最冷号码
    返回: {'hot': [{'number': n, 'count': c, 'omission': o}], ...}
    """
    if df is None:
        df = clean_data(load_data(lottery_type))
    
    # 1. 统计频率 (基于指定的 periods)
    freq = number_frequency(df, periods, lottery_type, zone)
    sorted_nums = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    
    # 2. 计算所有号码的当前遗漏值 (基于全量历史，确保捕捉到 139 期等真实的极致大冷号)
    # 注意：热度统计（出现次数）依然严格遵循用户选定的 periods 期数。
    omission_dict = {}
    
    # 向量化计算：用 numpy 数组代替逐行 Python 循环 (O(N×49) -> O(N+49))
    df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[False, False])
    
    if lottery_type == 'weilitsai':
        if zone == 1:
            max_num = 38
            # Compute omission for all n1-n6 columns
            # It's a bit complex vectorization, fallback to rows if needed or use pandas
            # Let's vectorize across n1-n6
            # Get the matrix of n1-n6
            if not df_sorted.empty and 'num1' in df_sorted.columns:
                arr = df_sorted[['num1', 'num2', 'num3', 'num4', 'num5', 'num6']].values.astype(int)
            else:
                arr = np.array([])
            
            for num in range(1, max_num + 1):
                if arr.size > 0:
                    indices = np.where((arr == num).any(axis=1))[0]
                    omission_dict[num] = int(indices[0]) if len(indices) > 0 else len(arr)
                else:
                    omission_dict[num] = 0
        else:
            max_num = 8
            special_arr = df_sorted['special_num'].values.astype(int) if 'special_num' in df_sorted.columns else np.array([])
            for num in range(1, max_num + 1):
                if special_arr.size > 0:
                    indices = np.where(special_arr == num)[0]
                    omission_dict[num] = int(indices[0]) if len(indices) > 0 else len(special_arr)
                else:
                    omission_dict[num] = 0
    else:
        max_num = 49
        special_arr = df_sorted['special_num'].values.astype(int)
        for num in range(1, max_num + 1):
            indices = np.where(special_arr == num)[0]
            omission_dict[num] = int(indices[0]) if len(indices) > 0 else len(special_arr)
        
    hot_list = []
    for n, c in sorted_nums[:top_n]:
        hot_list.append({'number': n, 'count': c, 'omission': omission_dict.get(n, 0)})
        
    cold_list = []
    for n, c in sorted_nums[-top_n:]:
        cold_list.append({'number': n, 'count': c, 'omission': omission_dict.get(n, 0)})
        
    return {
        'hot': hot_list,
        'cold': cold_list
    }



def odd_even_ratio(df: pd.DataFrame = None, periods: int = 100, lottery_type: str = 'macaujc', zone: int = 2) -> dict:
    """
    特码单双时间轴 K 线数据
    """
    if df is None:
        df = clean_data(load_data(lottery_type))
        
    if lottery_type == 'weilitsai' and zone == 1:
        # 威力彩 1 区 6 个正码球的单双比走势统计
        cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']
        total_odd = 0
        for col in cols:
            if col in df.columns:
                total_odd += df[col].apply(lambda x: x % 2 == 1).sum()
        total_even = (len(df) * 6) - total_odd
        
        df_recent = df.head(periods).iloc[::-1]
        labels = []
        values = []
        current_type = None
        current_val = 0
        
        for _, row in df_recent.iterrows():
            draw_nums = [row.get(c) for c in cols]
            odd_count = sum(1 for n in draw_nums if pd.notna(n) and int(n) % 2 == 1)
            is_odd = odd_count >= 3
            labels.append(str(row.get('draw_number', '')))
            
            if is_odd:
                if current_type == '奇':
                    current_val += 1
                else:
                    current_type = '奇'
                    current_val = 1
                values.append(current_val)
            else:
                if current_type == '偶':
                    current_val -= 1
                else:
                    current_type = '偶'
                    current_val = -1
                values.append(current_val)
        
        current_jumps = 0
        if values:
            current_state = values[-1] > 0
            for i in range(len(values) - 2, -1, -1):
                prev_state = values[i] > 0
                if current_state != prev_state:
                    current_jumps += 1
                    current_state = prev_state
                else:
                    break
                    
        return {
            'labels': labels,
            'values': values,
            'total_odd': int(total_odd),
            'total_even': int(total_even),
            'current_jumps': int(current_jumps)
        }

    # 非威力彩一区的情况（例如威力彩二区，或者六合彩特码等）
    if lottery_type == 'weilitsai':
        target_col = 'special_num' if zone == 2 else 'num1'
    else:
        target_col = 'special_num'

    if target_col not in df.columns:
        return {'labels': [], 'values': [], 'total_odd': 0, 'total_even': 0, 'current_jumps': 0}

    total_odd = df[target_col].apply(lambda x: x % 2 == 1).sum()
    total_even = len(df) - total_odd
    
    df_recent = df.head(periods).iloc[::-1]
    
    labels = []
    values = []
    
    current_type = None
    current_val = 0
    
    for _, row in df_recent.iterrows():
        num = row[target_col]
        is_odd = num % 2 == 1
        labels.append(str(row['draw_issue'] if 'draw_issue' in row else row.get('draw_number', '')))
        
        if is_odd:
            if current_type == '奇':
                current_val += 1
            else:
                current_type = '奇'
                current_val = 1
            values.append(current_val)
        else:
            if current_type == '偶':
                current_val -= 1
            else:
                current_type = '偶'
                current_val = -1
            values.append(current_val)
            
    # 计算奇偶当前单跳次数
    def _get_alternating_jumps(vals):
        if len(vals) < 2: return 0
        jumps = 0
        current_state = vals[0] > 0
        for i in range(1, len(vals)):
            prev_state = vals[i] > 0
            if current_state != prev_state:
                jumps += 1
                current_state = prev_state
            else:
                break
        return jumps
        
    current_jumps = _get_alternating_jumps(list(reversed(values)))

    return {
        'labels': labels,
        'values': values,
        'total_odd': int(total_odd),
        'total_even': int(total_even),
        'current_jumps': current_jumps
    }
def big_small_ratio(df: pd.DataFrame = None, periods: int = 100, lottery_type: str = 'macaujc', zone: int = 2) -> dict:
    """
    特码大小时间轴 K 线数据
    """
    if df is None:
        df = clean_data(load_data(lottery_type))
    
    if lottery_type == 'weilitsai' and zone == 1:
        # 威力彩 1 区 6 个正码球的大小比走势统计
        cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']
        total_big = 0
        for col in cols:
            total_big += df[col].apply(lambda x: x >= 20).sum()
        total_small = (len(df) * 6) - total_big
        
        df_recent = df.head(periods).iloc[::-1]
        labels = []
        values = []
        current_type = None
        current_val = 0
        
        for _, row in df_recent.iterrows():
            draw_nums = [row.get(c) for c in cols]
            big_count = sum(1 for n in draw_nums if pd.notna(n) and int(n) >= 20)
            is_big = big_count >= 3
            labels.append(str(row.get('draw_number', '')))
            
            if is_big:
                if current_type == '大':
                    current_val += 1
                else:
                    current_type = '大'
                    current_val = 1
                values.append(current_val)
            else:
                if current_type == '小':
                    current_val -= 1
                else:
                    current_type = '小'
                    current_val = -1
                values.append(current_val)
        
        current_jumps = 0
        if values:
            current_state = values[-1] > 0
            for i in range(len(values) - 2, -1, -1):
                prev_state = values[i] > 0
                if current_state != prev_state:
                    current_jumps += 1
                    current_state = prev_state
                else:
                    break
                    
        return {
            'labels': labels,
            'values': values,
            'total_big': int(total_big),
            'total_small': int(total_small),
            'current_jumps': int(current_jumps)
        }

    if lottery_type == 'weilitsai':
        target_col = 'special_num' if zone == 2 else 'num1'
        threshold = 5 if zone == 2 else 20
    else:
        target_col = 'special_num'
        threshold = 25

    if target_col not in df.columns:
        return {'labels': [], 'values': [], 'total_big': 0, 'total_small': 0, 'current_jumps': 0}
        
    total_big = df[target_col].apply(lambda x: x >= threshold).sum()
    total_small = len(df) - total_big
    
    df_recent = df.head(periods).iloc[::-1]
    
    labels = []
    values = []
    
    current_type = None
    current_val = 0
    
    for _, row in df_recent.iterrows():
        num = row[target_col]
        is_big = num >= threshold
        labels.append(str(row['draw_issue'] if 'draw_issue' in row else row.get('draw_number', '')))
        
        if is_big:
            if current_type == '大':
                current_val += 1
            else:
                current_type = '大'
                current_val = 1
            values.append(current_val)
        else:
            if current_type == '小':
                current_val -= 1
            else:
                current_type = '小'
                current_val = -1
            values.append(current_val)
            
    # 计算大小当前单跳次数
    def _get_alternating_jumps(vals):
        if len(vals) < 2: return 0
        jumps = 0
        current_state = vals[0] > 0
        for i in range(1, len(vals)):
            prev_state = vals[i] > 0
            if current_state != prev_state:
                jumps += 1
                current_state = prev_state
            else:
                break
        return jumps
        
    current_jumps = _get_alternating_jumps(list(reversed(values)))

    return {
        'labels': labels,
        'values': values,
        'total_big': int(total_big),
        'total_small': int(total_small),
        'current_jumps': current_jumps
    }



def tail_number_stats(df: pd.DataFrame = None, periods: int = 100, lottery_type: str = 'macaujc', zone: int = 1) -> dict:
    """
    尾数分布统计
    返回: {
        'distribution': {尾数: 出现次数},
        'omission': {尾数: 当前遗漏期数}
    }
    """
    if df is None:
        df = clean_data(load_data(lottery_type))
        
    # 1. 统计近期出现频率 (基于指定的 periods)
    df_recent = df.head(periods)
    
    if lottery_type == 'weilitsai':
        if zone == 1:
            all_nums = []
            for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                if col in df_recent.columns:
                    all_nums.extend(df_recent[col].tolist())
            special_arr = df[['num1', 'num2', 'num3', 'num4', 'num5', 'num6']].values.astype(int) if 'num1' in df.columns else np.array([])
        else:
            all_nums = df_recent['special_num'].tolist() if 'special_num' in df_recent.columns else []
            special_arr = df['special_num'].values.astype(int) if 'special_num' in df.columns else np.array([])
    else:
        all_nums = _get_all_numbers_with_special(df_recent)
        special_arr = df['special_num'].values.astype(int) if 'special_num' in df.columns else np.array([])
        
    tail_counter = Counter()
    for num in all_nums:
        tail = num % 10
        tail_counter[tail] += 1
    
    omission_dict = {}
    for t in range(10):
        omission_dict[t] = 0
        
    df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[False, False])
    if lottery_type == 'weilitsai' and zone == 1:
        if 'num1' in df_sorted.columns:
            arr = df_sorted[['num1', 'num2', 'num3', 'num4', 'num5', 'num6']].values.astype(int)
            for t in range(10):
                if arr.size > 0:
                    indices = np.where((arr % 10 == t).any(axis=1))[0]
                    omission_dict[t] = int(indices[0]) if len(indices) > 0 else len(arr)
                else:
                    omission_dict[t] = 0
    else:
        if lottery_type == 'weilitsai':
            tail_arr = df_sorted['special_num'].values.astype(int) % 10 if 'special_num' in df_sorted.columns else np.array([])
        else:
            tail_arr = df_sorted['special_num'].values.astype(int) % 10 if 'special_num' in df_sorted.columns else np.array([])
        for t in range(10):
            if tail_arr.size > 0:
                indices = np.where(tail_arr == t)[0]
                omission_dict[t] = int(indices[0]) if len(indices) > 0 else len(tail_arr)
            else:
                omission_dict[t] = 0

    # 结果封装
    distribution = {}
    for i in range(10):
        distribution[i] = tail_counter.get(i, 0)
        
    return {
        'distribution': distribution,
        'omission': omission_dict
    }



def calculate_omission_thresholds(df: pd.DataFrame, lottery_type: str = 'macaujc', zone: int = 1) -> dict:
    if lottery_type == 'weilitsai':
        max_num = 38 if zone == 1 else 8
        cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if zone == 1 else ['special_num']
    else:
        max_num = 49
        cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'special_num'] if zone == 1 else ['special_num']

    df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[True, True])
    arr = df_sorted[cols].values.astype(int) if set(cols).issubset(df_sorted.columns) else np.array([])

    thresholds = {}
    for num in range(1, max_num + 1):
        if arr.size == 0:
            thresholds[num] = {'max_omission': 0, 'current_omission': 0, 'is_alert': False}
            continue

        hits = np.where((arr == num).any(axis=1))[0]
        if len(hits) == 0:
            omission = len(arr)
            max_omi = len(arr)
        else:
            gaps = [hits[0]]
            for i in range(1, len(hits)):
                gaps.append(hits[i] - hits[i - 1] - 1)
            current_omi = len(arr) - 1 - hits[-1]
            gaps.append(current_omi)

            max_omi = max(gaps) if gaps else 0
            omission = current_omi

        thresholds[num] = {
            'max_omission': int(max_omi),
            'current_omission': int(omission),
            'is_alert': int(omission) >= int(max_omi * 0.8) and int(max_omi) > 5
        }

    return thresholds

