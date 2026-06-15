import pandas as pd
from collections import Counter
import math

def _analyze_three_region_distribution(df: pd.DataFrame, periods: int = 100) -> dict:
    if df.empty:
        return {'distribution': {}, 'trend': [], 'next_pred': "2:2:2", 'region_status': {}}
    df_recent = df.head(periods)
    
    patterns = []
    r1_history, r2_history, r3_history = [], [], []
    
    for _, row in df_recent.iterrows():
        nums = []
        for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
            v = row.get(c)
            if pd.notna(v) and 1 <= int(v) <= 38:
                nums.append(int(v))
        
        r1 = sum(1 for x in nums if 1 <= x <= 13)
        r2 = sum(1 for x in nums if 14 <= x <= 25)
        r3 = sum(1 for x in nums if 26 <= x <= 38)
        
        patterns.append(f"{r1}:{r2}:{r3}")
        r1_history.append(r1)
        r2_history.append(r2)
        r3_history.append(r3)
        
    dist = dict(Counter(patterns))
    
    exp_r1, exp_r2, exp_r3 = 2.053, 1.895, 2.053
    
    recent_len = min(10, len(df_recent))
    avg_r1 = sum(r1_history[:recent_len]) / recent_len if recent_len > 0 else exp_r1
    avg_r2 = sum(r2_history[:recent_len]) / recent_len if recent_len > 0 else exp_r2
    avg_r3 = sum(r3_history[:recent_len]) / recent_len if recent_len > 0 else exp_r3
    
    dev_r1 = avg_r1 - exp_r1
    dev_r2 = avg_r2 - exp_r2
    dev_r3 = avg_r3 - exp_r3
    
    pred_r1 = max(0.0, exp_r1 - dev_r1 * 0.5)
    pred_r2 = max(0.0, exp_r2 - dev_r2 * 0.5)
    pred_r3 = max(0.0, exp_r3 - dev_r3 * 0.5)
    
    total_pred = pred_r1 + pred_r2 + pred_r3
    if total_pred > 0:
        pred_r1_int = round((pred_r1 / total_pred) * 6)
        pred_r2_int = round((pred_r2 / total_pred) * 6)
        pred_r3_int = 6 - pred_r1_int - pred_r2_int
        if pred_r3_int < 0:
            pred_r2_int += pred_r3_int
            pred_r3_int = 0
    else:
        pred_r1_int, pred_r2_int, pred_r3_int = 2, 2, 2
        
    next_pred = f"{pred_r1_int}:{pred_r2_int}:{pred_r3_int}"
    
    trend_data = []
    for i in reversed(range(min(20, len(df_recent)))):
        trend_data.append({
            'issue': str(df_recent.index[i]),
            'r1': r1_history[i],
            'r2': r2_history[i],
            'r3': r3_history[i]
        })
        
    return {
        'distribution': dist,
        'trend': trend_data,
        'next_pred': next_pred,
        'region_status': {
            'r1': {'avg': round(avg_r1, 2), 'trend': '走热' if dev_r1 > 0.2 else ('走冷' if dev_r1 < -0.2 else '平稳')},
            'r2': {'avg': round(avg_r2, 2), 'trend': '走热' if dev_r2 > 0.2 else ('走冷' if dev_r2 < -0.2 else '平稳')},
            'r3': {'avg': round(avg_r3, 2), 'trend': '走热' if dev_r3 > 0.2 else ('走冷' if dev_r3 < -0.2 else '平稳')}
        }
    }


def _analyze_repeats_and_tails(df: pd.DataFrame, periods: int = 100) -> dict:
    if df.empty or len(df) < 2:
        return {'repeats_dist': {}, 'poisson_probs': {}, 'tails_dist': {}, 'next_repeat_pred': 0, 'next_tails_pred': 1, 'mean_repeats': 0, 'mean_tails': 0}
        
    df_recent = df.head(periods)
    
    repeat_counts = []
    for i in range(len(df_recent) - 1):
        row_curr = df_recent.iloc[i]
        row_prev = df_recent.iloc[i+1]
        
        nums_curr = set(int(row_curr.get(c)) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row_curr.get(c)))
        nums_prev = set(int(row_prev.get(c)) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row_prev.get(c)))
        
        repeat_counts.append(len(nums_curr & nums_prev))
        
    repeats_dist = dict(Counter(repeat_counts))
    mean_repeats = sum(repeat_counts) / len(repeat_counts) if repeat_counts else 0.95
    
    poisson_probs = {}
    for k in range(5):
        try:
            prob = (math.pow(mean_repeats, k) * math.exp(-mean_repeats)) / math.factorial(k)
        except:
            prob = 0
        poisson_probs[str(k)] = round(prob * 100, 2)
        
    next_repeat_pred = int(max(poisson_probs, key=poisson_probs.get)) if poisson_probs else 0
    
    tails_group_counts = []
    for _, row in df_recent.iterrows():
        nums = [int(row.get(c)) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row.get(c))]
        tails = [n % 10 for n in nums]
        t_counter = Counter(tails)
        groups = sum(1 for t, count in t_counter.items() if count >= 2)
        tails_group_counts.append(groups)
        
    tails_dist = dict(Counter(tails_group_counts))
    mean_tails = sum(tails_group_counts) / len(tails_group_counts) if tails_group_counts else 1.0
    next_tails_pred = int(Counter(tails_group_counts).most_common(1)[0][0]) if tails_group_counts else 1
    
    return {
        'repeats_dist': repeats_dist,
        'poisson_probs': poisson_probs,
        'next_repeat_pred': next_repeat_pred,
        'tails_dist': tails_dist,
        'next_tails_pred': next_tails_pred,
        'mean_repeats': round(mean_repeats, 2),
        'mean_tails': round(mean_tails, 2)
    }


def _analyze_range_span(df: pd.DataFrame, periods: int = 100) -> dict:
    if df.empty:
        return {'distribution': {}, 'trend': [], 'next_pred_span': 31, 'mean_span': 31, 'suggested_range': [28, 34]}
        
    df_recent = df.head(periods)
    spans = []
    
    for _, row in df_recent.iterrows():
        nums = [int(row.get(c)) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row.get(c))]
        if nums:
            spans.append(max(nums) - min(nums))
            
    dist = dict(Counter(spans))
    
    trend_data = []
    for i in reversed(range(min(20, len(spans)))):
        trend_data.append(spans[i])
        
    mean_span = sum(spans) / len(spans) if spans else 31.0
    
    recent_len = min(10, len(spans))
    recent_avg_span = sum(spans[:recent_len]) / recent_len if recent_len > 0 else mean_span
    dev_span = recent_avg_span - mean_span
    
    pred_span = mean_span - dev_span * 0.4
    pred_span = max(5, min(37, pred_span))
    
    return {
        'distribution': dist,
        'trend': trend_data,
        'mean_span': round(mean_span, 2),
        'next_pred_span': round(pred_span, 1),
        'suggested_range': [max(5, int(pred_span - 3)), min(37, int(pred_span + 3))]
    }


def _analyze_arithmetic_complexity(df: pd.DataFrame, periods: int = 100) -> dict:
    if df.empty:
        return {'distribution': {}, 'ac_probs': {}, 'trend': [], 'next_pred_ac': 9, 'high_prob_ac_range': [7, 8, 9, 10]}
        
    df_recent = df.head(periods)
    ac_values = []
    
    for _, row in df_recent.iterrows():
        nums = [int(row.get(c)) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row.get(c))]
        if len(nums) == 6:
            diffs = set()
            for i in range(6):
                for j in range(i+1, 6):
                    diffs.add(abs(nums[i] - nums[j]))
            ac = len(diffs) - 5
            ac_values.append(ac)
            
    dist = dict(Counter(ac_values))
    
    trend_data = []
    for i in reversed(range(min(20, len(ac_values)))):
        trend_data.append(ac_values[i])
        
    most_common_ac = Counter(ac_values).most_common(1)[0][0] if ac_values else 9
    
    ac_probs = {}
    total = len(ac_values)
    if total > 0:
        for ac, count in dist.items():
            ac_probs[str(ac)] = round((count / total) * 100, 2)
        
    return {
        'distribution': dist,
        'ac_probs': ac_probs,
        'trend': trend_data,
        'next_pred_ac': most_common_ac,
        'high_prob_ac_range': [7, 8, 9, 10]
    }


def _analyze_prime_composite_ratio(df: pd.DataFrame, periods: int = 100) -> dict:
    if df.empty:
        return {'distribution': {}, 'next_pred': "2:4", 'mean_primes': 1.89}
        
    primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}
    df_recent = df.head(periods)
    
    ratios = []
    prime_counts = []
    
    for _, row in df_recent.iterrows():
        nums = [int(row.get(c)) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row.get(c))]
        if nums:
            p_cnt = sum(1 for x in nums if x in primes)
            c_cnt = len(nums) - p_cnt
            ratios.append(f"{p_cnt}:{c_cnt}")
            prime_counts.append(p_cnt)
            
    dist = dict(Counter(ratios))
    
    recent_len = min(10, len(prime_counts))
    avg_primes = sum(prime_counts[:recent_len]) / recent_len if recent_len > 0 else 2.0
    
    exp_primes = 1.89
    dev_primes = avg_primes - exp_primes
    pred_primes = exp_primes - dev_primes * 0.4
    pred_primes_round = max(0, min(6, round(pred_primes)))
    
    next_pred = f"{pred_primes_round}:{6 - pred_primes_round}"
    
    return {
        'distribution': dist,
        'next_pred': next_pred,
        'mean_primes': round(sum(prime_counts)/len(prime_counts), 2) if prime_counts else 1.89
    }


def _analyze_mean_deviation_regression(df: pd.DataFrame, periods: int = 100) -> dict:
    if df.empty:
        return {'deviations': [], 'cumulative_deviations': [], 'next_pred_mean': 19.5, 'next_pred_sum': 117, 'recent_dev_trend': '围绕期望平稳震荡'}
        
    df_recent = df.head(periods)
    deviations = []
    cum_dev = 0
    cumulative_deviations = []
    
    for _, row in reversed(list(df_recent.iterrows())):
        nums = [int(row.get(c)) for c in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6'] if pd.notna(row.get(c))]
        if len(nums) == 6:
            m = sum(nums) / 6.0
            dev = m - 19.5
            cum_dev += dev
            deviations.append(dev)
            cumulative_deviations.append(cum_dev)
            
    recent_count = 20
    trend_deviations = deviations[-recent_count:] if len(deviations) >= recent_count else deviations
    trend_cumulative = cumulative_deviations[-recent_count:] if len(cumulative_deviations) >= recent_count else cumulative_deviations
    
    recent_len = min(5, len(deviations))
    recent_devs = deviations[-recent_len:] if deviations else [0]
    avg_recent_dev = sum(recent_devs) / recent_len if recent_len > 0 else 0
    
    alpha = 0.6
    pred_dev = -avg_recent_dev * alpha
    pred_mean = 19.5 + pred_dev
    pred_mean = max(3.5, min(35.5, pred_mean))
    pred_sum = round(pred_mean * 6)
    
    if avg_recent_dev > 2:
        trend_str = '大号区强势偏离'
    elif avg_recent_dev < -2:
        trend_str = '小号区弱势偏离'
    else:
        trend_str = '围绕期望平稳震荡'
        
    return {
        'deviations': [round(d, 2) for d in trend_deviations],
        'cumulative_deviations': [round(cd, 2) for cd in trend_cumulative],
        'next_pred_mean': round(pred_mean, 2),
        'next_pred_sum': pred_sum,
        'recent_dev_trend': trend_str
    }
