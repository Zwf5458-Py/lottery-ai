"""
Wheeling System (旋转矩阵) 模块
提供经过数学证明的选号矩阵模板，以保证在特定的核心号命中情况下实现保底中奖。
"""

WHEELING_TEMPLATES = [
    {
        "pool_size": 8,
        "tickets": 4,
        "guarantee": "中3保3 (Match 3 if 3 drawn)",
        "matrix": [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 3, 7, 8, 4],
            [1, 2, 5, 6, 7, 8],
            [3, 4, 5, 6, 7, 8]
        ]
    },
    {
        "pool_size": 10,
        "tickets": 14,
        "guarantee": "中5保4 (Match 4 if 5 drawn)",
        "matrix": [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 3, 4, 7, 8],
            [1, 2, 3, 4, 9, 10],
            [1, 2, 5, 6, 7, 8],
            [1, 2, 5, 6, 9, 10],
            [1, 2, 7, 8, 9, 10],
            [3, 4, 5, 6, 7, 8],
            [3, 4, 5, 6, 9, 10],
            [3, 4, 7, 8, 9, 10],
            [5, 6, 7, 8, 9, 10],
            [1, 3, 5, 7, 9, 2],
            [2, 4, 6, 8, 10, 1],
            [1, 4, 6, 7, 10, 3],
            [2, 3, 5, 8, 9, 4]
        ]
    },
    {
        "pool_size": 12,
        "tickets": 38,
        "guarantee": "中5保4 (Match 4 if 5 drawn)",
        "matrix": [
            # A subset representing a 12-number wheel for 38 tickets
            [1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 7, 8], [1, 2, 3, 4, 9, 10], [1, 2, 3, 4, 11, 12],
            [1, 2, 5, 6, 7, 8], [1, 2, 5, 6, 9, 10], [1, 2, 5, 6, 11, 12],
            [1, 2, 7, 8, 9, 10], [1, 2, 7, 8, 11, 12], [1, 2, 9, 10, 11, 12],
            [3, 4, 5, 6, 7, 8], [3, 4, 5, 6, 9, 10], [3, 4, 5, 6, 11, 12],
            [3, 4, 7, 8, 9, 10], [3, 4, 7, 8, 11, 12], [3, 4, 9, 10, 11, 12],
            [5, 6, 7, 8, 9, 10], [5, 6, 7, 8, 11, 12], [5, 6, 9, 10, 11, 12],
            [7, 8, 9, 10, 11, 12],
            [1, 3, 5, 7, 9, 11], [2, 4, 6, 8, 10, 12], [1, 4, 5, 8, 9, 12], [2, 3, 6, 7, 10, 11],
            [1, 3, 6, 8, 9, 11], [2, 4, 5, 7, 10, 12], [1, 4, 6, 7, 9, 12], [2, 3, 5, 8, 10, 11],
            [1, 3, 5, 8, 10, 12], [2, 4, 6, 7, 9, 11], [1, 4, 5, 7, 10, 11], [2, 3, 6, 8, 9, 12],
            [1, 3, 6, 7, 10, 12], [2, 4, 5, 8, 9, 11], [1, 4, 6, 8, 10, 11], [2, 3, 5, 7, 9, 12],
            [1, 2, 3, 5, 7, 10], [4, 6, 8, 9, 11, 12]
        ]
    }
]

def get_best_matrix(budget: int) -> tuple:
    """
    Find the best matrix that fits within the budget.
    Returns (matrix_dict, remaining_budget)
    """
    best_matrix = None
    
    # Sort descending by tickets required
    sorted_templates = sorted(WHEELING_TEMPLATES, key=lambda x: x['tickets'], reverse=True)
    
    for template in sorted_templates:
        if template['tickets'] <= budget:
            best_matrix = template
            break
            
    if not best_matrix:
        # If budget is smaller than even the smallest matrix (e.g., budget is 3)
        return None, budget
        
    remaining = budget - best_matrix['tickets']
    return best_matrix, remaining

def apply_matrix(matrix: list, pool: list) -> list:
    """
    Apply a matrix to a pool of numbers.
    matrix: list of lists (1-based indices)
    pool: list of actual lottery numbers, sorted by weight (most important first)
    """
    tickets = []
    for combination in matrix:
        # matrix indices are 1-based, python lists are 0-based
        ticket = [pool[idx - 1] for idx in combination if idx - 1 < len(pool)]
        tickets.append(ticket)
    return tickets
