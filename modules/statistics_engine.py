import pandas as pd
import numpy as np
import math
from collections import Counter
from modules.data_processor import load_data, clean_data, get_db_connection
from modules.simulator import _build_markov_transition_weights, _build_color_markov_transition_weights
from modules.constants import get_zodiac_mapping, get_color, RED_NUMS, BLUE_NUMS, GREEN_NUMS, ZODIAC_ORDER, NUM_TO_ZODIAC_IDX, ZODIAC_NUMS

# ==========================================
# 统计引擎统一路由网关 (Facade Pattern)
# 将底层计算按板块物理隔离到 modules/stats 目录下
# 外部模块仍可直接从本文件安全导入以下方法
# ==========================================

from modules.stats.common import (
    number_frequency, hot_cold_numbers, odd_even_ratio, 
    big_small_ratio, tail_number_stats, calculate_omission_thresholds,
    _get_all_numbers, _get_all_numbers_with_special
)
from modules.stats.macau import (
    five_elements_analysis, zodiac_momentum_analysis, 
    zodiac_frequency, special_number_frequency, color_hot_cold_analysis
)
from modules.stats.weilitsai import (
    bayesian_inference, lstm_simulation, zone_1_exclusive_prediction
)
from modules.high_order_statistics import (
    _analyze_three_region_distribution, _analyze_repeats_and_tails, 
    _analyze_range_span, _analyze_arithmetic_complexity, 
    _analyze_prime_composite_ratio, _analyze_mean_deviation_regression
)

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
            'zone1_exclusive': zone_1_exclusive_prediction(df, periods.get('z1_exclusive', 100)),
            'three_region': _analyze_three_region_distribution(df, periods.get('three_region', 50)),
            'repeats_tails': _analyze_repeats_and_tails(df, periods.get('poisson_tail', 50)),
            'range_span': _analyze_range_span(df, periods.get('range_distribution', 50)),
            'ac_value': _analyze_arithmetic_complexity(df, periods.get('ac_value', 50)),
            'prime_composite': _analyze_prime_composite_ratio(df, periods.get('three_region', 50)),
            'mean_regression': _analyze_mean_deviation_regression(df, periods.get('range_distribution', 50)),
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
        'three_region': _analyze_three_region_distribution(df, periods.get('three_region', 50)),
        'repeats_tails': _analyze_repeats_and_tails(df, periods.get('poisson_tail', 50)),
        'range_span': _analyze_range_span(df, periods.get('range_distribution', 50)),
        'ac_value': _analyze_arithmetic_complexity(df, periods.get('ac_value', 50)),
        'prime_composite': _analyze_prime_composite_ratio(df, periods.get('three_region', 50)),
        'mean_regression': _analyze_mean_deviation_regression(df, periods.get('range_distribution', 50)),
        'chart_periods': periods
    }
