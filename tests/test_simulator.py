import pytest
import pandas as pd
from modules.simulator import simulate_single, build_cooccurrence_matrix

def test_simulate_weilitsai(monkeypatch):
    monkeypatch.setattr('modules.data_processor.load_data', lambda t: pd.DataFrame())
    
    result = simulate_single(lottery_type='weilitsai')
    
    assert len(result['numbers']) == 6
    assert all(1 <= n <= 38 for n in result['numbers'])
    assert len(set(result['numbers'])) == 6
    assert 1 <= result['special_num'] <= 8


def test_build_cooccurrence_matrix():
    df = pd.DataFrame({
        'n1': [1, 2, 1],
        'n2': [2, 3, 3],
        'n3': [3, 4, 4],
        'n4': [4, 5, 5],
        'n5': [5, 6, 6],
        'n6': [6, 7, 7]
    })
    
    matrix = build_cooccurrence_matrix(df, max_num=7, cols=['n1', 'n2', 'n3', 'n4', 'n5', 'n6'])
    
    assert matrix[1][3] == 2
    assert matrix[2][1] == 1
