# tests/test_ai_engine.py
from modules.ai_engine import _build_analysis_prompt

def test_build_prompt_weilitsai():
    prompt = _build_analysis_prompt(
        lottery_type='weilitsai',
        stats={'z1': 'data', 'z2': 'data', 'chart_periods': {}, 'markov': {'target_num': 8, 'target_color': '', 'target_zodiac': ''}, 'number_frequency': {}, 'odd_even': {'values': [], 'labels': [], 'current_jumps': 0}, 'big_small': {'values': [], 'labels': [], 'current_jumps': 0}, 'hot_cold': {'hot': [], 'cold': []}, 'special_frequency': {}, 'lstm': [], 'bayesian': [], 'five_elements': {'poisson': {'items': []}, 'chi_square': {'items': []}}, 'consecutive': {'current_trend': 'none', 'consecutive_count': 0, 'reversal_probability': 0}, 'color_hot_cold': []},
        dimensions=['hot_cold'],
        pre_sel_nums=[1,2,3,4,5,6],
        pre_sel_special=8
    )
    assert '威力彩' in prompt
    assert '第一區' in prompt
    assert '第二區' in prompt
    assert '生肖' not in prompt
    assert '波色' not in prompt

