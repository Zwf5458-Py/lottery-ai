import pytest
from modules.wheeling_system import get_best_matrix, apply_matrix

def test_get_best_matrix():
    matrix, remaining = get_best_matrix(20)
    assert matrix['tickets'] <= 20
    assert remaining == 20 - matrix['tickets']
    assert len(matrix['matrix']) == matrix['tickets']
    
def test_apply_matrix():
    matrix = [[1, 2, 3], [1, 4, 5]]
    pool = [10, 20, 30, 40, 50]
    result = apply_matrix(matrix, pool)
    assert result[0] == [10, 20, 30]
    assert result[1] == [10, 40, 50]
