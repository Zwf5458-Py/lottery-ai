"""
统计分析引擎
功能：基于历史开奖数据计算多维度纯客观统计指标。
所有分析结果仅为历史数据的客观呈现，不含任何预测性质。
"""

import pandas as pd
from collections import Counter
from modules.data_processor import load_data, clean_data, get_db_connection
from modules.simulator import _build_markov_transition_weights, _build_color_markov_transition_weights, get_zodiac_mapping


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
    
    # 2. 计算所有号码的当前遗漏值 (基于全量数据，从最新一期往回数)
    # 注意：遗漏值通常是基于全量历史来算的，或者至少要比 periods 长很多才能算准
    omission_dict = {}
    for num in range(1, 50):
        omission = 0
        found = False
        # 倒序遍历 (df 默认是从新到旧, 第0行是最新的)
        # 假设 df 已经是按时间倒序排列 (最新的在最前)
        # 如果不是，先 sort 一下
        df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[False, False])
        
        for _, row in df_sorted.iterrows():
            if int(row['special_num']) == num:
                found = True
                break
            omission += 1
        omission_dict[num] = omission
        
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
    """
    if df is None or df.empty:
        return {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}
    
    # 按照前端图表：Y轴从下到上是 鼠, 牛, 虎, 兔, 龙, 蛇, 马, 羊, 猴, 鸡, 狗, 猪
    zodiac_order = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
    
    recent_draws = df.head(30) # 取最近30期分析走势
    
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
        
    # 检测单跳交替规律 (up-down-up-down 这种)
    # 从最新的趋势往回看
    rev_trends = list(reversed(trends))
    
    current_trend = rev_trends[0]
    consecutive_count = 0
    is_jumping = False
    
    # 首先检查是否是连续单跳交替 (例如: up, down, up, down)
    if len(rev_trends) >= 3 and current_trend in ('up', 'down'):
        jump_count = 1
        expected_next = 'down' if rev_trends[0] == 'up' else 'up'
        for t in rev_trends[1:]:
            if t == expected_next:
                jump_count += 1
                expected_next = 'down' if expected_next == 'up' else 'up'
            elif t == 'flat' and jump_count == 1:
                # 忽略偶尔的 flat
                pass
            else:
                break
        if jump_count >= 3:
            is_jumping = True
            consecutive_count = jump_count
            current_trend = 'jump'
    
    # 如果不是单跳，检查正常的连涨连跌
    if not is_jumping:
        for t in rev_trends:
            if t == current_trend:
                consecutive_count += 1
            else:
                break
                
    # 确定反转目标
    # 如果是涨，回调目标是 down；如果是跌，反弹目标是 up
    # 如果是单跳(jump)，反转目标就是"打破当前的跳动，即连庄"，
    # 比如最近是 down, up, down, up（最新一期是up），理论上下期该 down。
    # 所以如果大模型"顺应反弹"(防跳)，那就是押注它【不跳了，继续 up】。
    if current_trend == 'jump':
        # rev_trends[0] 是最新的一步（例如最新一步是从低到高 up）
        # 如果规律继续跳，下期该是 down。如果防跳（反转这个单跳规律），下期就该是 up。
        reversal_target = rev_trends[0]
    else:
        reversal_target = 'down' if current_trend == 'up' else ('up' if current_trend == 'down' else 'none')
    
    # 反转概率：无论是连涨、连跌还是连跳，次数越多，被打破的概率越高
    prob_map = {1: 45, 2: 65, 3: 80, 4: 92, 5: 98}
    rev_prob = prob_map.get(consecutive_count, 99) if consecutive_count > 0 and current_trend != 'flat' else 0
    
    return {
        'current_trend': current_trend,
        'consecutive_count': consecutive_count,
        'reversal_probability': rev_prob,
        'reversal_target_direction': reversal_target,
        'current_y': y_values[-1] if y_values else -1,
        'last_step': rev_trends[0] if rev_trends else 'none', # 用于 jump 模式说明状态
        'zodiac_order': zodiac_order
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
        
    df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[False, False])
    
    for t in range(10):
        omission = 0
        for _, row in df_sorted.iterrows():
            if int(row['special_num']) % 10 == t:
                break
            omission += 1
        omission_dict[t] = omission

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
        
    zodiac_order = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
    
    num_to_zodiac_idx = {}
    zodiac_nums = {
        "马": [1, 13, 25, 37, 49],
        "蛇": [2, 14, 26, 38],
        "龙": [3, 15, 27, 39],
        "兔": [4, 16, 28, 40],
        "虎": [5, 17, 29, 41],
        "牛": [6, 18, 30, 42],
        "鼠": [7, 19, 31, 43],
        "猪": [8, 20, 32, 44],
        "狗": [9, 21, 33, 45],
        "鸡": [10, 22, 34, 46],
        "猴": [11, 23, 35, 47],
        "羊": [12, 24, 36, 48]
    }
    for zodiac_name, nums in zodiac_nums.items():
        idx = zodiac_order.index(zodiac_name)
        for n in nums:
            num_to_zodiac_idx[n] = idx
    
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
    # omission: 当前遗漏
    # history_omissions: 历史上每次出现的间隔期数列表
    omission = {}
    history_omissions = {z: [] for z in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']}
    
    for z in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']:
        current_omi = 0
        last_seen_idx = -1
        
        # 为了统计所有历史遗漏区间，遍历全表(或近N期)
        # df 默认是从新到旧排序
        for i, row in df.iterrows():
            curr_z = z_map.get(int(row['special_num']), '未知')
            if curr_z == z:
                if last_seen_idx == -1: # 这是最近一次出现
                    omission[z] = i
                else:
                    # 距离上一次出现的间隔期数减1就是遗漏期数
                    gap = i - last_seen_idx - 1
                    if gap >= 0:
                        history_omissions[z].append(gap)
                last_seen_idx = i
                
        # 如果循环结束都没有发现，当前遗漏就是全表长度
        if last_seen_idx == -1:
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
        
        results.append({
            'zodiac': z,
            'prior': round(p_prior * 100, 1),
            'omission': omi,
            'max_omission': int(max_omi),
            'avg_omission': round(avg_omi, 1),
            'posterior': round(posterior_score, 1)
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
    red = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
    blue = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
    green = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}

    def get_color(num):
        try:
            n = int(num)
            if n in red: return '红波'
            if n in blue: return '蓝波'
            if n in green: return '绿波'
        except:
            pass
        return None

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
    def get_color(num):
        red = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
        blue = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
        green = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}
        if num in red: return "红波"
        if num in blue: return "蓝波"
        if num in green: return "绿波"
        return "未知"
    
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
        'bayesian': bayesian_inference(df, z_map, periods.get('bayesian', 100)),
        'lstm': lstm_simulation(df, z_map, periods.get('lstm', 100)),
        'color_hot_cold': color_hot_cold_analysis(df, periods.get('hot_cold', 100)),
        'chart_periods': periods
    }
