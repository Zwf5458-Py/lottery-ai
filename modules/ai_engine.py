"""
AI 分析引擎 (重构瘦身版)
功能：集成 Google Gemini API，基于多维统计数据进行智能分析。
负责统一的路由分发与调用调度。
"""

from modules.prompts.weilitsai import _build_weilitsai_analysis_prompt
from modules.prompts.macau import _build_macau_analysis_prompt, _build_zodiac_prompt
from modules.ai_client import call_ai_api, call_zodiac_ai_api

def analyze_with_ai(stats_summary: dict, lottery_type: str = 'macaujc', dimensions: list = None, pool: list = None, special_num: int = None) -> dict:
    if dimensions is None:
        dimensions = ['big_small', 'odd_even', 'hot_cold', 'tail', 'zodiac']
        
    is_wheeling = (pool is not None and len(pool) > 6)
    
    # 1. 获取选定号码与底层权重
    if is_wheeling:
        pre_sel_nums = sorted(pool)
        pre_sel_special = special_num if special_num is not None else 1
        from modules.simulator import _calculate_trend_weights
        system_weights = _calculate_trend_weights(lottery_type, dimensions)
    else:
        from modules.simulator import simulate_single
        sys_res = simulate_single(lottery_type, dimensions)
        pre_sel_nums = sorted(sys_res.get('numbers', []))
        pre_sel_special = sys_res.get('special_num', 1)
        system_weights = sys_res.get('_weights', {})
        
    # 2. 路由并生成对应彩种专属 Prompt
    if lottery_type == 'weilitsai':
        prompt = _build_weilitsai_analysis_prompt(stats_summary, dimensions, pre_sel_nums, pre_sel_special, system_weights, is_wheeling=is_wheeling)
    else:
        prompt = _build_macau_analysis_prompt(stats_summary, lottery_type, dimensions, pre_sel_nums, pre_sel_special, system_weights, is_wheeling=is_wheeling)
        
    # 3. 调用通讯层发送并返回结果
    return call_ai_api(prompt, stats_summary, lottery_type, dimensions, pre_sel_nums, pre_sel_special, is_wheeling=is_wheeling)


def analyze_zodiac_with_ai(stats_summary: dict, lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    if dimensions is None:
        dimensions = ['zodiac_trend']
        
    # 路由新澳生肖专属预测 Prompt
    prompt = _build_zodiac_prompt(stats_summary, lottery_type, dimensions)
    
    # 调用通讯层并返回生肖专属格式
    return call_zodiac_ai_api(prompt, stats_summary, lottery_type, dimensions)


def analyze_with_ai_stream(stats_summary: dict, lottery_type: str = 'macaujc', dimensions: list = None, pool: list = None, special_num: int = None):
    if dimensions is None:
        dimensions = ['big_small', 'odd_even', 'hot_cold', 'tail', 'zodiac']
        
    is_wheeling = (pool is not None and len(pool) > 6)
    
    if is_wheeling:
        pre_sel_nums = sorted(pool)
        pre_sel_special = special_num if special_num is not None else 1
        from modules.simulator import _calculate_trend_weights
        system_weights = _calculate_trend_weights(lottery_type, dimensions)
    else:
        from modules.simulator import simulate_single
        sys_res = simulate_single(lottery_type, dimensions)
        pre_sel_nums = sorted(sys_res.get('numbers', []))
        pre_sel_special = sys_res.get('special_num', 1)
        system_weights = sys_res.get('_weights', {})
        
    if lottery_type == 'weilitsai':
        prompt = _build_weilitsai_analysis_prompt(stats_summary, dimensions, pre_sel_nums, pre_sel_special, system_weights, is_wheeling=is_wheeling)
    else:
        prompt = _build_macau_analysis_prompt(stats_summary, lottery_type, dimensions, pre_sel_nums, pre_sel_special, system_weights, is_wheeling=is_wheeling)
        
    from modules.ai_client import call_ai_api_stream
    for item in call_ai_api_stream(prompt, stats_summary, lottery_type, dimensions, pre_sel_nums, pre_sel_special, is_wheeling=is_wheeling):
        yield item
