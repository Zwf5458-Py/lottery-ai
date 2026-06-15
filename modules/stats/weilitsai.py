from modules.simulator import _build_markov_transition_weights, _build_color_markov_transition_weights
from modules.constants import get_zodiac_mapping, get_color, RED_NUMS, BLUE_NUMS, GREEN_NUMS, ZODIAC_ORDER, NUM_TO_ZODIAC_IDX, ZODIAC_NUMS
from modules.data_processor import load_data, clean_data, get_db_connection
import pandas as pd
import numpy as np
import datetime
from collections import Counter
from modules.constants import get_zodiac_mapping
from modules.stats.common import _normal_sf, _chi_square_p_value

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



def zone_1_exclusive_prediction(df: pd.DataFrame, periods: int = 100) -> dict:
    """
    威力彩 1 区专属分析算法 (1-38号)：结合频率与关联规则 (Association Rules)
    """
    if df.empty:
        return {'predicted_numbers': [], 'details': []}
        
    df_recent = df.head(periods)
    from collections import defaultdict
    freq = defaultdict(int)
    co_occur = defaultdict(lambda: defaultdict(int))
    
    for _, row in df_recent.iterrows():
        nums = []
        for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
            v = row.get(c)
            if pd.notna(v) and 1 <= int(v) <= 38:
                nums.append(int(v))
        for n in nums:
            freq[n] += 1
            for m in nums:
                if n != m:
                    co_occur[n][m] += 1

    last_nums = []
    if not df.empty:
        for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
            v = df.iloc[0].get(c)
            if pd.notna(v) and 1 <= int(v) <= 38:
                last_nums.append(int(v))
    
    scores = {}
    for n in range(1, 39):
        score = freq[n] * 1.0
        for ln in last_nums:
            score += co_occur[n][ln] * 0.5
        scores[n] = score
        
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    predicted_numbers = [item[0] for item in sorted_scores[:6]]
    
    return {
        'predicted_numbers': predicted_numbers,
        'details': [{'number': n, 'score': round(s, 2)} for n, s in sorted_scores[:12]]
    }


