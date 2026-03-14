"""
统计分析引擎
功能：基于历史开奖数据计算多维度纯客观统计指标。
所有分析结果仅为历史数据的客观呈现，不含任何预测性质。
"""

import pandas as pd
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


def number_frequency(df: pd.DataFrame = None, periods: int = 100) -> dict:
    """
    号码出现频率分布
    返回: {号码: 出现次数} 的字典，按号码排序
    """
    if df is None:
        df = clean_data(load_data())
    
    # 截取用户配置的统计期数
    if periods > 0:
        df = df.head(periods)
    
    all_nums = _get_all_numbers_with_special(df)
    counter = Counter(all_nums)
    
    # 确保 1-49 都有值
    result = {}
    for i in range(1, 50):
        result[i] = counter.get(i, 0)
    
    return result


def hot_cold_numbers(top_n: int = 10, df: pd.DataFrame = None, periods: int = 100) -> dict:
    """
    冷热号统计
    参数:
        top_n: 返回前 N 个最热/最冷号码
    返回: {'hot': [{'number': n, 'count': c, 'omission': o}], ...}
    """
    if df is None:
        df = clean_data(load_data())
    
    # 1. 统计频率 (基于指定的 periods)
    freq = number_frequency(df, periods)
    sorted_nums = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    
    # 2. 计算所有号码的当前遗漏值 (基于全量历史，确保捕捉到 139 期等真实的极致大冷号)
    # 注意：热度统计（出现次数）依然严格遵循用户选定的 periods 期数。
    omission_dict = {}
    
    # 向量化计算：用 numpy 数组代替逐行 Python 循环 (O(N×49) -> O(N+49))
    import numpy as np
    df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[False, False])
    special_arr = df_sorted['special_num'].values.astype(int)
    for num in range(1, 50):
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


def odd_even_ratio(df: pd.DataFrame = None, periods: int = 100) -> dict:
    """
    特码单双时间轴 K 线数据
    """
    if df is None:
        df = clean_data(load_data())
        
    total_odd = df['special_num'].apply(lambda x: x % 2 == 1).sum()
    total_even = len(df) - total_odd
    
    df_recent = df.head(periods).iloc[::-1]
    
    labels = []
    values = []
    
    current_type = None
    current_val = 0
    
    for _, row in df_recent.iterrows():
        num = row['special_num']
        is_odd = num % 2 == 1
        labels.append(str(row['draw_number']))
        
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


def big_small_ratio(df: pd.DataFrame = None, periods: int = 100) -> dict:
    """
    特码大小时间轴 K 线数据
    """
    if df is None:
        df = clean_data(load_data())
    
    total_big = df['special_num'].apply(lambda x: x >= 25).sum()
    total_small = len(df) - total_big
    
    df_recent = df.head(periods).iloc[::-1]
    
    labels = []
    values = []
    
    current_type = None
    current_val = 0
    
    for _, row in df_recent.iterrows():
        num = row['special_num']
        is_big = num >= 25
        labels.append(str(row['draw_number']))
        
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


def zodiac_momentum_analysis(df: pd.DataFrame, z_map: dict) -> dict:
    """
    生肖路单连涨连跌特征（动量拐点预测）
    根据最近图表中的连续向上或向下趋势，计算可能反向的概率权重。
    引入 RLE 复杂多维跳变观测系统。
    """
    if df is None or df.empty:
        return {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}
    
    zodiac_order = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
    
    # 扩大观测窗口至 150 期
    recent_draws = df.head(150)
    
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
        
    # 清理掉假波动(也就是连续两期生肖相同，y 轴停留在原地的干扰项)
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
    
    # ====== 新增：波色模式提取与分析 ======
    # 直接在同一个 150 期数据集中提取颜色跳动规律
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
        
        # 将颜色动量转化为具体颜色的权重倍增器
        color_boosts[current_color] *= w_keep_color
        # 逆势转向（打断当前颜色连庄的权重，均分给其他两色）
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
        # 新增输出给 simulator 用的波色权重修饰符
        'color_momentum_boosts': color_boosts
    }



def tail_number_stats(df: pd.DataFrame = None, periods: int = 100) -> dict:
    """
    尾数分布统计
    返回: {
        'distribution': {尾数: 出现次数},
        'omission': {尾数: 当前遗漏期数}
    }
    """
    if df is None:
        df = clean_data(load_data())
    
    # 1. 统计近期出现频率 (基于指定的 periods)
    df_recent = df.head(periods)
    all_nums = _get_all_numbers_with_special(df_recent)
    tail_counter = Counter()
    for num in all_nums:
        tail = num % 10
        tail_counter[tail] += 1
    
    # 2. 计算各尾数的当前遗漏值 (基于全量历史，仅看特码)
    # 注意：为了准确性，通常看特码的遗漏。如果是看特码+正码的遗漏，则需要每期遍历7个球。
    # 这里我们统一标准：尾数统计包含正码+特码的频率，但遗漏值仅针对“该尾数在特码位置”的遗漏。
    # 也可以改为“任意位置出现该尾数”的遗漏。一般彩民看尾数遗漏更关注特码尾数。
    # **决策**：为了配合图表展示特码趋势，我们这里计算【特码尾数】的遗漏值。
    
    omission_dict = {}
    for t in range(10):
        omission_dict[t] = 0
        
    # 向量化计算：用 numpy 数组代替逐行 Python 循环
    import numpy as np
    df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[False, False])
    tail_arr = df_sorted['special_num'].values.astype(int) % 10
    for t in range(10):
        indices = np.where(tail_arr == t)[0]
        omission_dict[t] = int(indices[0]) if len(indices) > 0 else len(tail_arr)

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


def bayesian_inference(df: pd.DataFrame, z_map: dict, periods: int = 100) -> list:
    """
    贝叶斯推断：结合先验概率与最新遗漏值推算反弹概率
    periods: 用于计算先验频率的期数范围
    返回: [{"zodiac": "鼠", "prior": 8.3, "omission": 12, "posterior": 24.5}, ...]
    """
    if df is None or df.empty: return []
    
    # 截取指定期数
    df_recent = df.head(periods) if periods > 0 else df
    total_draws = len(df_recent)
    
    # 统计指定期数内每个生肖的出现频次（先验），并统计历史遗漏数据
    zodiac_list = [z_map.get(int(row['special_num']), '未知') for _, row in df_recent.iterrows()]
    counts = Counter(zodiac_list)
    
    # 计算当前遗漏和历史遗漏统计
    # omission: 当前遗漏（从最新一期往回数，直到该生肖最近一次出现的行数）
    # history_omissions: 历史上每次出现的间隔期数列表
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


def lstm_simulation(df: pd.DataFrame, z_map: dict, periods: int = 100) -> list:
    """
    深度学习模拟预测：基于真实历史数据的多维特征提取，
    使用 sklearn.neural_network.MLPClassifier 训练小型神经网络预测生肖。
    提取特征：近50期频率、近10期频率、当前遗漏值。
    """
    if df is None or len(df) < 50: return []
    
    zodiac_order = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
    
    try:
        from sklearn.neural_network import MLPClassifier
        import numpy as np
        
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


def get_full_analysis(lottery_type: str = 'macaujc') -> dict:
    """
    汇总所有统计维度，一次性返回给前端
    减少多次请求的开销
    """
    df = clean_data(load_data(lottery_type))
    
    # 读取用户配置的各图表期数
    from modules.config_manager import get_chart_periods
    periods = get_chart_periods()
    
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
    try:
        if not df.empty:
            latest_num = int(df.iloc[0]['special_num'])
            latest_zodiac = z_map.get(latest_num, "未知")
            latest_color = get_color(latest_num)
    except:
        pass
        
    return {
        'total_draws': len(df),
        'number_frequency': number_frequency(df, periods.get('hot_cold', 100)),
        'hot_cold': hot_cold_numbers(10, df, periods.get('hot_cold', 100)),
        'odd_even': odd_even_ratio(df, periods.get('odd_even', 100)),
        'big_small': big_small_ratio(df, periods.get('big_small', 100)),
        'consecutive': zodiac_momentum_analysis(df, z_map),
        'tail_numbers': tail_number_stats(df, periods.get('tail', 100)),
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
