import pytest
from modules.ai_engine import _build_analysis_prompt

def test_build_prompt_weilitsai():
    prompt = _build_analysis_prompt(
        stats={},
        lottery_type='weilitsai',
        dimensions=[],
        pre_sel_nums=[1,2,3,4,5,6],
        pre_sel_special=8
    )
    assert '威力彩' in prompt
    assert '第一區' in prompt
    assert '第二區' in prompt
    assert '生肖' not in prompt
    assert '波色' not in prompt
