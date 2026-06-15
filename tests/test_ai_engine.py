import pytest
from modules.prompts.weilitsai import _build_weilitsai_analysis_prompt

def test_build_prompt_weilitsai():
    prompt = _build_weilitsai_analysis_prompt(
        stats={},
        dimensions=[],
        pre_sel_nums=[1,2,3,4,5,6],
        pre_sel_special=8
    )
    assert '威力彩' in prompt
    assert '第一區' in prompt
    assert '第二區' in prompt
    assert '生肖' not in prompt
    assert '波色' not in prompt


def test_build_prompt_weilitsai_markov():
    stats = {
        'markov': {
            'weights': {
                '13': 1.8,
                '38': 2.2,
                '_is_significant': True,
                '_chi_square_val': 15.5
            }
        }
    }
    prompt = _build_weilitsai_analysis_prompt(
        stats=stats,
        dimensions=['markov'],
        pre_sel_nums=[1,2,3,4,5,6],
        pre_sel_special=8
    )
    assert '马尔可夫链第一區号码跃迁推演' in prompt
    assert '基于第一區号码全量数据的马尔可夫链状态转移' in prompt
    assert '38号(跃迁权重 2.20)' in prompt
    assert '13号(跃迁权重 1.80)' in prompt
