import pytest
import pandas as pd
from modules.simulator import simulate_single

def test_simulate_weilitsai(monkeypatch):
    # Mock data loading
    monkeypatch.setattr('modules.data_processor.load_data', lambda t: pd.DataFrame())
    
    result = simulate_single(lottery_type='weilitsai')
    
    assert len(result['numbers']) == 6
    assert all(1 <= n <= 38 for n in result['numbers'])
    assert len(set(result['numbers'])) == 6 # Unique
    assert 1 <= result['special_num'] <= 8
