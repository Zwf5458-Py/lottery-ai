"""
统计分析引擎
功能：基于历史开奖数据计算多维度纯客观统计指标。
所有分析结果仅为历史数据的客观呈现，不含任何预测性质。
"""

import pandas as pd
import numpy as np
import math
from collections import Counter
from modules.data_processor import load_data, clean_data, get_db_connection
from modules.simulator import _build_markov_transition_weights, _build_color_markov_transition_weights
from modules.constants import get_zodiac_mapping, get_color, RED_NUMS, BLUE_NUMS, GREEN_NUMS, ZODIAC_ORDER, NUM_TO_ZODIAC_IDX, ZODIAC_NUMS


FIVE_ELEMENTS_MAP = {
    '金': {6, 7, 20, 21, 28, 29, 36, 37, 44, 45},
    '木': {1, 8, 9, 16, 17, 30, 31, 38, 39, 46, 47},
    '水': {4, 5, 12, 13, 26, 27, 34, 35, 48, 49},
    '火': {2, 3, 10, 11, 18, 19, 32, 33, 40, 41},
    '土': {14, 15, 22, 23, 24, 25, 42, 43},
}


def _get_five_element(num: int) -> str:
    for name, nums in FIVE_ELEMENTS_MAP.items():
        if int(num) in nums:
            return name
    return '未知'


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


def five_elements_analysis(df: pd.DataFrame = None, periods: int = 100) -> dict:
    """五行监控面板：卡方偏差、状态关联、泊松遗漏极限。"""
    if df is None:
        df = clean_data(load_data())

    if periods > 0:
        df_recent = df.head(periods).copy()
    else:
        df_recent = df.copy()

    recent_specials = [int(x) for x in df_recent['special_num'].tolist()]
    full_specials = [int(x) for x in df['special_num'].tolist()]
    recent_elements = [_get_five_element(n) for n in recent_specials]
    full_elements = [_get_five_element(n) for n in full_specials]
    total = len(recent_elements)

    expected_probs = {k: len(v) / 49.0 for k, v in FIVE_ELEMENTS_MAP.items()}
    counts = Counter(recent_elements)
    chi_items = []
    chi_square = 0.0
    for name in FIVE_ELEMENTS_MAP.keys():
        observed = counts.get(name, 0)
        expected = total * expected_probs[name]
        deviation = observed - expected
        chi_square += ((deviation ** 2) / expected) if expected > 0 else 0.0
        chi_items.append({
            'element': name,
            'observed': observed,
            'expected': round(expected, 2),
            'deviation': round(deviation, 2),
            'ratio': round((observed / expected) if expected else 0, 3)
        })
    p_value = _chi_square_p_value(chi_square, 4)

    transitions = Counter()
    prev_counts = Counter()
    for i in range(1, len(full_elements)):
        prev_el = full_elements[i]
        curr_el = full_elements[i - 1]
        if prev_el == '未知' or curr_el == '未知':
            continue
        transitions[(prev_el, curr_el)] += 1
        prev_counts[prev_el] += 1

    ordered_elements = list(FIVE_ELEMENTS_MAP.keys())
    association_rules = []
    total_transitions = sum(transitions.values()) or 1
    transition_matrix = []
    for (prev_el, curr_el), cnt in transitions.items():
        support = cnt / total_transitions
        confidence = cnt / prev_counts[prev_el] if prev_counts[prev_el] else 0
        lift = confidence / expected_probs.get(curr_el, 1)
        association_rules.append({
            'from': prev_el,
            'to': curr_el,
            'count': cnt,
            'support': round(support * 100, 2),
            'confidence': round(confidence * 100, 2),
            'lift': round(lift, 2)
        })
    association_rules.sort(key=lambda x: (x['confidence'], x['support'], x['lift']), reverse=True)

    for row_el in ordered_elements:
        row_items = []
        row_total = prev_counts.get(row_el, 0)
        for col_el in ordered_elements:
            cnt = transitions.get((row_el, col_el), 0)
            confidence = (cnt / row_total * 100) if row_total else 0
            row_items.append({
                'to': col_el,
                'count': cnt,
                'confidence': round(confidence, 2)
            })
        transition_matrix.append({'from': row_el, 'items': row_items})

    omission_stats = []
    horizon = 10
    for name in FIVE_ELEMENTS_MAP.keys():
        lam = horizon * expected_probs[name]
        current_gap = 0
        for el in full_elements:
            if el == name:
                break
            current_gap += 1
        if lam > 0:
            no_show_prob = math.exp(-lam)
            cdf_gap = math.exp(-expected_probs[name] * current_gap)
        else:
            no_show_prob = 1.0
            cdf_gap = 1.0
        omission_stats.append({
            'element': name,
            'lambda_10': round(lam, 3),
            'current_gap': current_gap,
            'p0_next_10': round(no_show_prob * 100, 2),
            'gap_tail_prob': round(cdf_gap * 100, 3),
            'extreme': cdf_gap <= 0.01,
            'hint': '⚠️ 接近均值回归拐点' if cdf_gap <= 0.01 else ('📈 值得关注' if cdf_gap <= 0.05 else '✅ 正常波动')
        })
    omission_stats.sort(key=lambda x: x['gap_tail_prob'])

    number_balls = {
        name: sorted(list(nums))
        for name, nums in FIVE_ELEMENTS_MAP.items()
    }

    strongest = max(chi_items, key=lambda x: abs(x['deviation'])) if chi_items else None
    return {
        'periods': total,
        'chi_square': {
            'stat': round(chi_square, 3),
            'p_value': round(p_value, 4),
            'significant': p_value < 0.05,
            'items': chi_items,
            'headline': f"{strongest['element']}偏差最明显" if strongest else '样本不足'
        },
        'apriori': {
            'rules': association_rules[:8],
            'matrix': transition_matrix,
            'headline': f"{association_rules[0]['from']}→{association_rules[0]['to']} 置信度最高" if association_rules else '样本不足'
        },
        'poisson': {
            'items': omission_stats,
            'headline': f"{omission_stats[0]['element']}遗漏最极端" if omission_stats else '样本不足'
        },
        'number_balls': number_balls
    }


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
        
    if lottery_type == 'weilitsai':
        target_col = 'special_num' if zone == 2 else 'num1' # just fallback to num1 if zone 1 is forced, though usually zone 2 is used
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
            
    # 计算当前单跳次数（从最近一期往回看，A-B-A-B交替）
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


def zodiac_momentum_analysis(df: pd.DataFrame, z_map: dict = None, lottery_type: str = 'macaujc') -> dict:
    """
    生肖路单连涨连跌特征（动量拐点预测） / 威力彩一区正码和值动量拐点分析
    根据最近图表中的连续向上或向下趋势，计算可能反向的概率权重。
    引入 RLE 复杂多维跳变观测系统。
    """
    if df is None or df.empty:
        return {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}
    
    zodiac_order = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
    recent_draws = df.head(150)
    
    if lottery_type == 'weilitsai':
        # 威力彩：统计 1 区 6 个正码的和值变化走势
        y_values = []
        for _, row in recent_draws.iterrows():
            try:
                draw_sum = sum(int(row[col]) for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row[col]))
                y_values.append(draw_sum)
            except:
                continue
        y_values.reverse()
        
        if len(y_values) < 2:
            return {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}
            
        trends = []
        for i in range(1, len(y_values)):
            diff = y_values[i] - y_values[i-1]
            if diff > 0: trends.append('up')
            elif diff < 0: trends.append('down')
            else: trends.append('flat')
            
        trends = [t for t in trends if t != 'flat']
        if not trends:
            return {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}
            
        rev_trends = list(reversed(trends))
        current_trend = rev_trends[0]
        consecutive_count = 0
        for t in rev_trends:
            if t == current_trend:
                consecutive_count += 1
            else:
                break
                
        def _analyze_sum_pattern(trends_arr):
            if len(trends_arr) < 5: return 1.0, 1.0
            rle = []
            curr_val = trends_arr[0]
            count = 1
            for i in range(1, len(trends_arr)):
                val = trends_arr[i]
                if val == curr_val:
                    count += 1
                else:
                    rle.append((curr_val, count))
                    curr_val = val
                    count = 1
            rle.append((curr_val, count))
            
            w_keep = 1.0
            w_break = 1.0
            c_count = rle[0][1]
            
            # 均值回归防长龙
            if c_count == 3:
                w_break *= 2.5
            elif c_count >= 4:
                w_break *= (4.0 + (c_count - 4) * 2.0)
                
            return w_keep, w_break
            
        w_keep_sum, w_break_sum = _analyze_sum_pattern(rev_trends)
        total_w = w_keep_sum + w_break_sum
        if total_w == 0: total_w = 1
        rev_prob = (w_break_sum / total_w) * 100
        
        reversal_target = 'down' if current_trend == 'up' else 'up'
        
        return {
            'current_trend': current_trend,
            'consecutive_count': consecutive_count,
            'reversal_probability': rev_prob,
            'reversal_target_direction': reversal_target,
            'current_y': y_values[-1] if y_values else -1,
            'last_step': current_trend,
            'color_momentum_boosts': {'red': 1.0, 'blue': 1.0, 'green': 1.0}
        }

    y_values = []
    for _, row in recent_draws.iterrows():
        try:
            num = int(row['special_num'])
            z = z_map.get(num, '未知')
            y_val = zodiac_order.index(z) if z in zodiac_order else -1
            if y_val != -1:
                y_values.append(y_val)
        except:
            continue
            
    # 从老到最新
    y_values.reverse()
    
    if len(y_values) < 2:
        return {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}
        
    trends = []
    for i in range(1, len(y_values)):
        diff = y_values[i] - y_values[i-1]
        if diff > 0: trends.append('up')
        elif diff < 0: trends.append('down')
        else: trends.append('flat')
        
    # 清理掉假波动
    trends = [t for t in trends if t != 'flat']
    if not trends:
        return {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}
        
    # 反转数组，最新的在最前面 index 0
    rev_trends = list(reversed(trends))
    
    current_trend = rev_trends[0]
    consecutive_count = 0
    for t in rev_trends:
        if t == current_trend:
            consecutive_count += 1
        else:
            break
            
    # ------ 高级 RLE 模式识别开始 ------
    def _analyze_zodiac_pattern(trends_arr):
        if len(trends_arr) < 5: return 1.0, 1.0
        
        rle = []
        curr_val = trends_arr[0]
        count = 1
        for i in range(1, len(trends_arr)):
            val = trends_arr[i]
            if val == curr_val:
                count += 1
            else:
                rle.append((curr_val, count))
                curr_val = val
                count = 1
        rle.append((curr_val, count))

        w_keep = 1.0
        w_break = 1.0
        c_count = rle[0][1]

        # 规则A1：天花板限制 (近30次方向突变中寻找)
        recent_streaks = [x[1] for x in rle[:30]]
        if len(recent_streaks) >= 4:
            max_streak = max(recent_streaks)
            if c_count >= max_streak and max_streak <= 3:
                 w_break *= (2.0 + c_count * 1.5)
        
        # 规则A2：均值回归防长龙
        if c_count == 3:
            w_break *= 2.5
        elif c_count >= 4:
            w_break *= (4.0 + (c_count - 4) * 2.0)

        # 规则B：重复宏观模式匹配
        if len(rle) >= 5:
            pattern_counts = [x[1] for x in rle]
            if len(pattern_counts) >= 4:
                # 类似 1-2-1-2 震荡跟随
                if pattern_counts[1] == pattern_counts[3] and pattern_counts[1] > 0:
                    target_count = pattern_counts[2]
                    if c_count < target_count:
                        w_keep *= 2.5
                    elif c_count == target_count:
                        w_break *= 3.0
                    elif c_count > target_count:
                        w_break *= 1.5
                        
            # 单跳防跳跟随
            if all(c == 1 for c in pattern_counts[1:5]):
                if c_count == 1:
                    w_keep *= 3.5 # 押注它连庄(防跳)
                elif c_count >= 2:
                    w_keep *= 1.2
                    
        return w_keep, w_break

    # 这里的 w_keep_zodiac 代表"顺势", 即下期继续 current_trend
    # w_break_zodiac 代表"逆势转向", 即下期相反方向
    w_keep_zodiac, w_break_zodiac = _analyze_zodiac_pattern(rev_trends)
    
    total_w_z = w_keep_zodiac + w_break_zodiac
    if total_w_z == 0: total_w_z = 1
    rev_prob = (w_break_zodiac / total_w_z) * 100
    
    reversal_target = 'down' if current_trend == 'up' else 'up'
    
    # ------ 波色模式提取与分析 ------
    color_seq = []
    red_set = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
    blue_set = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
    green_set = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}
    
    for _, row in recent_draws.iterrows():
        try:
            num = int(row['special_num'])
            if num in red_set: color_seq.append('red')
            elif num in blue_set: color_seq.append('blue')
            elif num in green_set: color_seq.append('green')
        except:
            continue
            
    color_seq.reverse() # 变成最老在左边，最新在右边
    rev_color_seq = list(reversed(color_seq)) # 最新的在 index 0
    
    color_boosts = {'red': 1.0, 'blue': 1.0, 'green': 1.0}
    
    if len(rev_color_seq) > 5:
        w_keep_color, w_break_color = _analyze_zodiac_pattern(rev_color_seq)
        current_color = rev_color_seq[0]
        
        color_boosts[current_color] *= w_keep_color
        break_boost = w_break_color / 2.0
        for c in ['red', 'blue', 'green']:
            if c != current_color:
                color_boosts[c] *= break_boost
                
    return {
        'current_trend': current_trend,
        'consecutive_count': consecutive_count,
        'reversal_probability': rev_prob,
        'reversal_target_direction': reversal_target,
        'current_y': y_values[-1] if y_values else -1,
        'last_step': current_trend,
        'zodiac_order': zodiac_order,
        'color_momentum_boosts': color_boosts
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


def zodiac_frequency(df: pd.DataFrame = None, periods: int = 200) -> dict:
    """
    特码生肖走势数据 (路单格式)
    """
    if df is None:
        df = clean_data(load_data())
        
    zodiac_order = ZODIAC_ORDER
    num_to_zodiac_idx = NUM_TO_ZODIAC_IDX
    
    df_recent = df.head(periods).iloc[::-1]
    
    draws = []
    for _, row in df_recent.iterrows():
        special_num = int(row['special_num'])
        if 1 <= special_num <= 49 and special_num in num_to_zodiac_idx:
            draws.append({
                'draw_number': str(row['draw_number']),
                'num': special_num,
                'zodiac_idx': num_to_zodiac_idx[special_num]
            })
                    
    return {
        'draws': draws,
        'zodiac_order': zodiac_order
    }


def special_number_frequency(df: pd.DataFrame = None) -> dict:
    """
    特码出现频率统计
    返回: {号码: 出现次数} 的字典
    """
    if df is None:
        df = clean_data(load_data())
    
    counter = Counter(df['special_num'].tolist())
    
    result = {}
    for i in range(1, 50):
        result[i] = counter.get(i, 0)
    
    return result


def bayesian_inference(df: pd.DataFrame, z_map: dict = None, periods: int = 100, lottery_type: str = 'macaujc') -> list:
    """
    贝叶斯推断：结合先验概率与最新遗漏值推算反弹概率
    periods: 用于计算先验频率的期数范围
    返回: [{"zodiac": "鼠", "prior": 8.3, "omission": 12, "posterior": 24.5}, ...]
    """
    if df is None or df.empty: return []
    
    # 截取指定期数
    df_recent = df.head(periods) if periods > 0 else df
    total_draws = len(df_recent)
    
    if lottery_type == 'weilitsai':
        # 统计指定期数内一区 1-38 每个号码的出现频次（先验），并统计历史遗漏数据
        num_list = []
        for _, row in df_recent.iterrows():
            for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                val = row.get(col)
                if pd.notna(val):
                    num_list.append(int(val))
        counts = Counter(num_list)
        
        omission = {}
        history_omissions = {n: [] for n in range(1, 39)}
        
        for n in range(1, 39):
            last_seen_pos = -1
            for pos, (_, row) in enumerate(df.iterrows()):
                draw_nums = [row.get(col) for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']]
                if n in draw_nums or str(n) in draw_nums or float(n) in draw_nums:
                    if last_seen_pos == -1:
                        omission[n] = pos
                    else:
                        gap = pos - last_seen_pos - 1
                        if gap >= 0:
                            history_omissions[n].append(gap)
                    last_seen_pos = pos
                    
            if last_seen_pos == -1:
                omission[n] = len(df)
                
        results = []
        for n in range(1, 39):
            c = counts.get(n, 0)
            p_prior = c / (total_draws * 6) if total_draws > 0 else 1/38
            omi = omission.get(n, 0)
            
            h_omis = history_omissions.get(n, [])
            max_omi = max(h_omis) if h_omis else (total_draws / 38 * 18)
            avg_omi = (sum(h_omis) / len(h_omis)) if h_omis else (total_draws / 38 * 6)
            
            approaching_ratio = omi / max(max_omi, 1)
            boost_factor = (1 + approaching_ratio) ** 2.5
            posterior_score = p_prior * boost_factor * 100
            
            breaking_record = omi > max_omi
            
            results.append({
                'number': n,
                'prior': round(p_prior * 100, 1),
                'omission': omi,
                'max_omission': int(max_omi),
                'avg_omission': round(avg_omi, 1),
                'posterior': round(posterior_score, 1),
                'breaking_record': breaking_record
            })
            
        results.sort(key=lambda x: x['posterior'], reverse=True)
        return results

    # 统计指定期数内每个生肖的出现频次（先验），并统计历史遗漏数据
    zodiac_list = [z_map.get(int(row['special_num']), '未知') for _, row in df_recent.iterrows()]
    counts = Counter(zodiac_list)
    
    # 计算当前遗漏和历史遗漏统计
    omission = {}
    history_omissions = {z: [] for z in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']}
    
    for z in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']:
        last_seen_pos = -1  # 行位置计数器（不是 DataFrame index）
        
        # df 默认是从新到旧排序，用 enumerate 确保取到的是行位置而非原始 index
        for pos, (_, row) in enumerate(df.iterrows()):
            curr_z = z_map.get(int(row['special_num']), '未知')
            if curr_z == z:
                if last_seen_pos == -1:  # 这是最近一次出现
                    omission[z] = pos
                else:
                    # 距离上一次出现的间隔期数
                    gap = pos - last_seen_pos - 1
                    if gap >= 0:
                        history_omissions[z].append(gap)
                last_seen_pos = pos
                
        # 如果循环结束都没有发现，当前遗漏就是全表长度
        if last_seen_pos == -1:
            omission[z] = len(df)
            
    # 计算推断后验概率权重
    results = []
    for z in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']:
        c = counts.get(z, 0)
        p_prior = c / total_draws if total_draws > 0 else 1/12  # 历史基础概率
        omi = omission.get(z, 0)
        
        # 计算该生肖特有的历史极值
        h_omis = history_omissions.get(z, [])
        max_omi = max(h_omis) if h_omis else (total_draws / 12 * 3) # 如果没出过，假设一个极值
        avg_omi = (sum(h_omis) / len(h_omis)) if h_omis else (total_draws / 12)
        
        # 贝叶斯后验公式：先验概率 × 遗漏反弹因子
        # 反弹因子现在的核心是：当前遗漏逼近甚至超过历史最大遗漏时，随时可能爆发
        # 逼近度 ratio
        approaching_ratio = omi / max(max_omi, 1)
        # 指数级放大接近极值的生肖
        boost_factor = (1 + approaching_ratio) ** 2.5 
        posterior_score = p_prior * boost_factor * 100
        
        # 刷新历史记录判定
        breaking_record = omi > max_omi
        
        results.append({
            'zodiac': z,
            'prior': round(p_prior * 100, 1),
            'omission': omi,
            'max_omission': int(max_omi),
            'avg_omission': round(avg_omi, 1),
            'posterior': round(posterior_score, 1),
            'breaking_record': breaking_record
        })
        
    # 按后验概率从高到低排序
    results.sort(key=lambda x: x['posterior'], reverse=True)
    return results


def lstm_simulation(df: pd.DataFrame, z_map: dict = None, periods: int = 100, lottery_type: str = 'macaujc') -> list:
    """
    深度学习模拟预测：基于真实历史数据的多维特征提取，
    使用 sklearn.neural_network.MLPClassifier 训练小型神经网络预测。
    """
    if df is None or len(df) < 50: return []
    
    if lottery_type == 'weilitsai':
        try:
            from sklearn.neural_network import MLPClassifier
            
            df_rev = df.iloc[::-1].reset_index(drop=True)
            draws_seq = []
            for _, row in df_rev.iterrows():
                draw_nums = []
                for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                    val = row.get(col)
                    if pd.notna(val):
                        draw_nums.append(int(val))
                draws_seq.append(draw_nums)
                
            train_seq = draws_seq[-500:]
            if len(train_seq) < 60:
                raise ValueError("Data too short")
                
            X = []
            y = []
            
            for i in range(50, len(train_seq)):
                target_draw = train_seq[i]
                window_50 = [num for sub in train_seq[i-50:i] for num in sub]
                window_10 = [num for sub in train_seq[i-10:i] for num in sub]
                
                omi_dict = {n: 50 for n in range(1, 39)}
                for step in range(i-1, i-51, -1):
                    for num in train_seq[step]:
                        if num in omi_dict and omi_dict[num] == 50:
                            omi_dict[num] = i - 1 - step
                            
                count_50 = Counter(window_50)
                count_10 = Counter(window_10)
                
                for n in range(1, 39):
                    f_50 = count_50[n]
                    f_10 = count_10[n]
                    omi = omi_dict[n]
                    X.append([f_50, f_10, omi])
                    y.append(1 if n in target_draw else 0)
                    
            clf = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=200, random_state=42)
            if len(X) > 0 and sum(y) > 0:
                clf.fit(X, y)
            else:
                raise ValueError("Invalid target distribution")
                
            current_50 = [num for sub in train_seq[-50:] for num in sub]
            current_10 = [num for sub in train_seq[-10:] for num in sub]
            
            omi_dict = {n: 50 for n in range(1, 39)}
            for step in range(len(train_seq)-1, len(train_seq)-51, -1):
                for num in train_seq[step]:
                    if num in omi_dict and omi_dict[num] == 50:
                        omi_dict[num] = len(train_seq) - 1 - step
                        
            c_50 = Counter(current_50)
            c_10 = Counter(current_10)
            
            X_pred = []
            for n in range(1, 39):
                X_pred.append([c_50[n], c_10[n], omi_dict[n]])
                
            probs = clf.predict_proba(X_pred)[:, 1] if hasattr(clf, 'classes_') else np.zeros(38)
            
            max_p = max(probs)
            min_p = min(probs)
            if max_p == min_p:
                scores = [50 for _ in range(1, 39)]
            else:
                scores = [5 + 90 * (p - min_p) / (max_p - min_p) for p in probs]
                
            results = []
            for idx, n in enumerate(range(1, 39)):
                score = scores[idx]
                if score >= 75: signal = "强势突破"
                elif score >= 55: signal = "震荡上行"
                elif score <= 25: signal = "深度回调"
                else: signal = "横盘整理"
                
                results.append({
                    'number': n,
                    'score': round(score, 1),
                    'signal': signal
                })
                
            results.sort(key=lambda x: x['score'], reverse=True)
            return results
            
        except Exception as e:
            df_recent = df.head(periods) if periods > 0 else df
            total = len(df_recent)
            
            num_list = []
            for _, row in df_recent.iterrows():
                for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                    val = row.get(col)
                    if pd.notna(val):
                        num_list.append(int(val))
            counts = Counter(num_list)
            avg_count = (total * 6) / 38.0 if total > 0 else 1
            
            short_window = min(20, total)
            short_list = []
            for _, row in df_recent.head(short_window).iterrows():
                for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                    val = row.get(col)
                    if pd.notna(val):
                        short_list.append(int(val))
            short_counts = Counter(short_list)
            short_avg = (short_window * 6) / 38.0
            
            omission = {}
            for n in range(1, 39):
                omi = 0
                for _, row in df.iterrows():
                    draw_nums = [row.get(col) for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']]
                    if n in draw_nums or str(n) in draw_nums or float(n) in draw_nums:
                        break
                    omi += 1
                omission[n] = omi
            max_omi = max(omission.values()) if omission else 1
            
            results = []
            for n in range(1, 39):
                freq = counts.get(n, 0)
                short_freq = short_counts.get(n, 0)
                omi = omission.get(n, 0)
                
                freq_score = min(35, (freq / avg_count) * 17.5) if avg_count > 0 else 17.5
                momentum_score = min(30, (short_freq / short_avg) * 15) if short_avg > 0 else 15
                omission_score = min(35, (omi / max(max_omi, 1)) * 35)
                
                score = freq_score + momentum_score + omission_score
                score = max(5, min(95, score))
                
                if score >= 75: signal = "强势突破"
                elif score >= 55: signal = "震荡上行"
                elif score <= 25: signal = "深度回调"
                else: signal = "横盘整理"
                    
                results.append({
                    'number': n,
                    'score': round(score, 1),
                    'signal': signal
                })
                
            results.sort(key=lambda x: x['score'], reverse=True)
            return results

    zodiac_order = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
    
    try:
        from sklearn.neural_network import MLPClassifier
        
        # DataFrame 是从新到旧的，我们需要正序进行时序训练
        df_rev = df.iloc[::-1].reset_index(drop=True)
        z_seq = [z_map.get(int(x), '未知') for x in df_rev['special_num']]
        
        # 取最近最多 500 期进行训练保证速度
        train_seq = z_seq[-500:]
        if len(train_seq) < 60:
            raise ValueError("Data too short")
            
        X = []
        y = []
        
        # 构造训练集
        for i in range(50, len(train_seq)):
            target_z = train_seq[i]
            window_50 = train_seq[i-50:i]
            window_10 = train_seq[i-10:i]
            
            # 计算截点处的遗漏值
            omi_dict = {z: 50 for z in zodiac_order}
            for step in range(i-1, i-51, -1):
                z = train_seq[step]
                if z in omi_dict and omi_dict[z] == 50:
                    omi_dict[z] = i - 1 - step
                    
            count_50 = Counter(window_50)
            count_10 = Counter(window_10)
            
            for z in zodiac_order:
                f_50 = count_50[z]
                f_10 = count_10[z]
                omi = omi_dict[z]
                X.append([f_50, f_10, omi])
                y.append(1 if z == target_z else 0)
                
        clf = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=200, random_state=42)
        if len(X) > 0 and sum(y) > 0:
            clf.fit(X, y)
        else:
            raise ValueError("Invalid target distribution")
            
        # 预测当前情况
        current_50 = train_seq[-50:]
        current_10 = train_seq[-10:]
        
        omi_dict = {z: 50 for z in zodiac_order}
        for step in range(len(train_seq)-1, len(train_seq)-51, -1):
            z = train_seq[step]
            if z in omi_dict and omi_dict[z] == 50:
                omi_dict[z] = len(train_seq) - 1 - step
                
        c_50 = Counter(current_50)
        c_10 = Counter(current_10)
        
        X_pred = []
        for z in zodiac_order:
            X_pred.append([c_50[z], c_10[z], omi_dict[z]])
            
        probs = clf.predict_proba(X_pred)[:, 1] if hasattr(clf, 'classes_') else np.zeros(12)
        
        # 归一化为 5-95 的评分
        max_p = max(probs)
        min_p = min(probs)
        if max_p == min_p:
            scores = [50 for _ in zodiac_order]
        else:
            scores = [5 + 90 * (p - min_p) / (max_p - min_p) for p in probs]
            
        results = []
        for idx, z in enumerate(zodiac_order):
            score = scores[idx]
            if score >= 75: signal = "强势突破"
            elif score >= 55: signal = "震荡上行"
            elif score <= 25: signal = "深度回调"
            else: signal = "横盘整理"
            
            results.append({
                'zodiac': z,
                'score': round(score, 1),
                'signal': signal
            })
            
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    except Exception as e:
        # 降级：如果缺少 sklearn 或数据不足，使用基础启发式
        df_recent = df.head(periods) if periods > 0 else df
        total = len(df_recent)
        zodiac_list = [z_map.get(int(row['special_num']), '未知') for _, row in df_recent.iterrows()]
        
        counts = Counter(zodiac_list)
        avg_count = total / 12.0 if total > 0 else 1
        
        short_window = min(20, total)
        short_counts = Counter(zodiac_list[:short_window])
        short_avg = short_window / 12.0
        
        omission = {}
        for z in zodiac_order:
            omi = 0
            for _, row in df.iterrows():
                if z_map.get(int(row['special_num']), '未知') == z: break
                omi += 1
            omission[z] = omi
        max_omi = max(omission.values()) if omission else 1
        
        results = []
        for z in zodiac_order:
            freq = counts.get(z, 0)
            short_freq = short_counts.get(z, 0)
            omi = omission.get(z, 0)
            
            freq_score = min(35, (freq / avg_count) * 17.5) if avg_count > 0 else 17.5
            momentum_score = min(30, (short_freq / short_avg) * 15) if short_avg > 0 else 15
            omission_score = min(35, (omi / max(max_omi, 1)) * 35)
            
            score = freq_score + momentum_score + omission_score
            score = max(5, min(95, score))
            
            if score >= 75: signal = "强势突破"
            elif score >= 55: signal = "震荡上行"
            elif score <= 25: signal = "深度回调"
            else: signal = "横盘整理"
                
            results.append({
                'zodiac': z,
                'score': round(score, 1),
                'signal': signal
            })
            
        results.sort(key=lambda x: x['score'], reverse=True)
        return results


def color_hot_cold_analysis(df: pd.DataFrame, periods: int = 100) -> dict:
    """
    波色冷热极限推测：基于几何分布 (Geometric Distribution) 与遗漏分析。
    计算红、蓝、绿三色的出现频次、当前遗漏期数和几何分布反弹概率。
    """
    # 波色集合和 get_color 已通过顶部从 constants.py 导入

    # 截取指定期数
    subset = df.head(periods) if periods > 0 else df
    total = len(subset)

    # 统计频次
    freq = {'红波': 0, '蓝波': 0, '绿波': 0}
    for _, row in subset.iterrows():
        c = get_color(row['special_num'])
        if c:
            freq[c] += 1

    # 计算当前遗漏值（从最新一期开始，连续多少期未出现该波色）
    gap = {'红波': 0, '蓝波': 0, '绿波': 0}
    found = {'红波': False, '蓝波': False, '绿波': False}
    for _, row in df.iterrows():
        c = get_color(row['special_num'])
        if c is None:
            continue
        if not found[c]:
            found[c] = True
        for color_name in gap:
            if not found[color_name]:
                gap[color_name] += 1
        if all(found.values()):
            break

    result = []
    for color_name in ['红波', '蓝波', '绿波']:
        count = freq[color_name]
        p = count / total if total > 0 else 1/3  # 经验概率
        if p <= 0: p = 0.001
        if p >= 1: p = 0.999
        k = gap[color_name]  # 当前遗漏期数

        # 几何分布 P(X=k) = (1-p)^{k-1} * p
        import math
        pmf = ((1 - p) ** max(0, k)) * p if k >= 0 else p
        # 累积分布 CDF: P(X <= k) = 1 - (1-p)^k
        cdf = 1 - ((1 - p) ** max(1, k + 1)) if k >= 0 else 0
        # 反弹概率：已经连续 k 期未出现，下一期出现的条件概率仍为 p
        # 但“极端程度”用 CDF 衡量：CDF 越高，说明遗漏已超过歷史中该波色平均间隔的概率
        extremity = round(cdf * 100, 1)  # 百分制极端度

        # 历史平均遗漏 (1/p - 1)
        avg_gap = round(1 / p - 1, 1) if p > 0 else 999

        result.append({
            'color': color_name,
            'count': count,
            'total': total,
            'probability': round(p * 100, 2),  # 百分比
            'current_gap': k,
            'avg_gap': avg_gap,
            'pmf': round(pmf * 100, 3),  # 几何分布 PMF %
            'cdf': round(cdf * 100, 2),  # CDF %
            'extremity': extremity,  # 极端程度 0~100
            'rebound_hint': '🔥 极热反弹' if extremity >= 85 else ('⚠️ 偏高遗漏' if extremity >= 60 else '✅ 正常范围')
        })

    # 按极端度降序
    result.sort(key=lambda x: x['extremity'], reverse=True)
    return result


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


def get_full_analysis(lottery_type: str = 'macaujc') -> dict:
    """
    汇总所有统计维度，一次性返回给前端
    减少多次请求的开销
    """
    df = clean_data(load_data(lottery_type))
    
    # 读取用户配置的各图表期数
    from modules.config_manager import get_chart_periods
    periods = get_chart_periods(lottery_type=lottery_type)
    
    # 获取马尔可夫链转移推演权重
    conn = get_db_connection()
    z_map = get_zodiac_mapping(lottery_type)
    markov_weights = _build_markov_transition_weights(conn, lottery_type, z_map, max_periods=periods.get('markov', 0))
    color_weights = _build_color_markov_transition_weights(conn, lottery_type, max_periods=periods.get('markov', 0))
    conn.close()
    
    # 红蓝绿波色判断
    # get_color 已通过顶部从 constants.py 导入
    
    # 找出最新一期的生肖和数字作为雷达图的中心点展示依据
    latest_zodiac = "未知"
    latest_num = "??"
    latest_color = "未知"
    latest_numbers = []
    try:
        if not df.empty:
            if 'num1' in df.columns:
                latest_numbers = [int(df.iloc[0][col]) for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']]
            if lottery_type == 'weilitsai':
                latest_num = int(df.iloc[0]['special_num']) if 'special_num' in df.columns else "??"
            else:
                latest_num = int(df.iloc[0]['special_num'])
                latest_zodiac = z_map.get(latest_num, "未知")
                latest_color = get_color(latest_num)
    except:
        pass
        
    if lottery_type == 'weilitsai':
        # === 威力彩 1 区 6 码下期推算预测概率计算 ===
        from collections import Counter
        base_weights = {n: 1.0 for n in range(1, 39)}
        num_freq = Counter()
        omissions = {n: len(df) for n in range(1, 39)}
        
        for idx, row in df.iterrows():
            draw_nums = [row.get(c) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']]
            for n in draw_nums:
                if pd.notna(n) and 1 <= int(n) <= 38:
                    n_int = int(n)
                    if omissions[n_int] == len(df):
                        omissions[n_int] = idx
                        
        for _, row in df.head(100).iterrows():
            draw_nums = [row.get(c) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']]
            for n in draw_nums:
                if pd.notna(n) and 1 <= int(n) <= 38:
                    num_freq[int(n)] += 1
                    
        avg_freq = sum(num_freq.values()) / 38 if num_freq else 1
        max_omission = max(omissions.values()) if omissions else 0
        
        for n in range(1, 39):
            f = num_freq.get(n, 0)
            w = 1.0
            if avg_freq > 0:
                ratio = f / avg_freq
                if ratio < 0.5:
                    w = 1.6
                elif ratio < 0.8:
                    w = 1.3
                elif ratio > 1.5:
                    w = 0.85
                else:
                    w = 1.0 + (ratio - 1) * 0.15
                    
            if omissions[n] == max_omission and max_omission > 5:
                w *= (1.0 + (max_omission / 100.0) * 2.5)
            base_weights[n] = w
            
        alerts = calculate_omission_thresholds(df, lottery_type, zone=1)
        for n, alert_data in alerts.items():
            if alert_data.get('is_alert') and n in base_weights:
                base_weights[n] *= 3.0
                
        last_nums = []
        repeat_nums = set()
        if not df.empty:
            last_row = df.iloc[0]
            for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                val = last_row.get(col)
                if pd.notna(val):
                    last_nums.append(int(val))
            repeat_nums = set(last_nums)
            for n in last_nums:
                for delta in [-1, 1]:
                    neighbor_num = n + delta
                    if 1 <= neighbor_num <= 38 and neighbor_num not in repeat_nums and neighbor_num in base_weights:
                        base_weights[neighbor_num] *= 1.5
                        
        total_w = sum(base_weights.values())
        prob_list = []
        for n in range(1, 39):
            prob = (base_weights[n] / total_w) * 100 if total_w > 0 else 0
            prob_list.append({
                'number': n,
                'probability': round(prob, 2),
                'weight': round(base_weights[n], 2),
                'is_alert': alerts.get(n, {}).get('is_alert', False),
                'is_neighbor': any(abs(n - ln) == 1 and n not in repeat_nums for ln in last_nums) if not df.empty else False
            })
            
        predict_probabilities_z1 = sorted(prob_list, key=lambda x: x['probability'], reverse=True)

        return {
            'total_draws': len(df),
            'latest_num': latest_num,
            'latest_numbers': latest_numbers,
            'predict_probabilities_z1': predict_probabilities_z1,
            'number_frequency_z1': number_frequency(df, periods.get('hot_cold', 100), lottery_type, zone=1),
            'number_frequency_z2': number_frequency(df, periods.get('hot_cold', 100), lottery_type, zone=2),
            'hot_cold_z1': hot_cold_numbers(10, df, periods.get('hot_cold', 100), lottery_type, zone=1),
            'hot_cold_z2': hot_cold_numbers(10, df, periods.get('hot_cold', 100), lottery_type, zone=2),
            'odd_even_z1': odd_even_ratio(df, periods.get('odd_even', 100), lottery_type, zone=1),
            'odd_even_z2': odd_even_ratio(df, periods.get('odd_even', 100), lottery_type, zone=2),
            'big_small_z1': big_small_ratio(df, periods.get('big_small', 100), lottery_type, zone=1),
            'big_small_z2': big_small_ratio(df, periods.get('big_small', 100), lottery_type, zone=2),
            'tail_numbers_z1': tail_number_stats(df, periods.get('tail', 100), lottery_type, zone=1),
            'tail_numbers_z2': tail_number_stats(df, periods.get('tail', 100), lottery_type, zone=2),
            'consecutive': zodiac_momentum_analysis(df, None, lottery_type='weilitsai'),
            'markov': {
                'target_num': latest_num,
                'target_zodiac': '',
                'target_color': '',
                'weights': markov_weights,
                'color_weights': {}
            },
            'bayesian': bayesian_inference(df, None, periods.get('bayesian', 100), lottery_type='weilitsai'),
            'lstm': lstm_simulation(df, None, periods.get('lstm', 100), lottery_type='weilitsai'),
            'chart_periods': periods
        }
        
    return {
        'total_draws': len(df),
        'latest_num': latest_num,
        'latest_numbers': latest_numbers,
        'number_frequency': number_frequency(df, periods.get('hot_cold', 100), lottery_type),
        'hot_cold': hot_cold_numbers(10, df, periods.get('hot_cold', 100), lottery_type),
        'odd_even': odd_even_ratio(df, periods.get('odd_even', 100), lottery_type),
        'big_small': big_small_ratio(df, periods.get('big_small', 100), lottery_type),
        'consecutive': zodiac_momentum_analysis(df, z_map),
        'tail_numbers': tail_number_stats(df, periods.get('tail', 100), lottery_type),
        'special_frequency': special_number_frequency(df),
        'zodiac_stats': zodiac_frequency(df, periods.get('zodiac_trend', 200)),
        'markov': {
            'target_num': latest_num,
            'target_zodiac': latest_zodiac,
            'target_color': latest_color,
            'weights': markov_weights,
            'color_weights': color_weights
        },
        'five_elements': five_elements_analysis(df, periods.get('hot_cold', 100)),
        'bayesian': bayesian_inference(df, z_map, periods.get('bayesian', 100)),
        'lstm': lstm_simulation(df, z_map, periods.get('lstm', 100)),
        'color_hot_cold': color_hot_cold_analysis(df, periods.get('hot_cold', 100)),
        'chart_periods': periods
    }
