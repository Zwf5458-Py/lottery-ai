# Algorithm Refinement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine the existing prediction simulator by implementing advanced Data Science/Lottery algorithms: Maximum Omission Hit/Skip thresholding, Odd/Even normal distribution filtering, and Markov Co-occurrence clustering.

**Architecture:** 
1. **Omission Hit/Skip**: Calculate historical max omission per number. If current omission >= 80% of max, apply an `extreme_omission_boost` to the simulator weights.
2. **Markov Co-occurrence**: Calculate a 38x38 (or 49x49) co-occurrence matrix (how often number A appears with number B in the same draw). 
3. **Simulator Logic Update**: Modify `simulate_single`. Pick 1 core number using base weights + omission boost. Pick the remaining numbers heavily weighted by the co-occurrence matrix of the core number.
4. **Odd/Even Constraint**: After 6 numbers are chosen, validate the odd/even ratio. Reject if it is 6:0, 0:6, 5:1, or 1:5. Loop until a valid 3:3, 2:4, or 4:2 combination is found.

**Tech Stack:** Python, Pandas, Numpy

---

### Task 1: Historical Max Omission Calculation

**Files:**
- Modify: `modules/statistics_engine.py`
- Modify: `tests/test_statistics.py`

**Step 1: Write the failing test**

```python
# tests/test_statistics.py
from modules.statistics_engine import calculate_omission_thresholds
import pandas as pd

def test_calculate_omission_thresholds():
    # Mock data where 1 appears in draw 1 and 10 (omission 8), then current draw is 18 (omission 8)
    df = pd.DataFrame({
        'draw_date': pd.date_range(start='1/1/2023', periods=18),
        'draw_number': range(1, 19),
        'n1': [1] + [2]*8 + [1] + [2]*8,
        'n2': [3]*18, 'n3': [4]*18, 'n4': [5]*18, 'n5': [6]*18, 'n6': [7]*18,
        'special': [8]*18
    })
    
    thresholds = calculate_omission_thresholds(df, lottery_type='weilitsai', zone=1)
    
    assert 1 in thresholds
    assert thresholds[1]['max_omission'] == 8
    assert thresholds[1]['current_omission'] == 8
    assert thresholds[1]['is_alert'] is True # 8 >= 8 * 0.8
    assert thresholds[2]['is_alert'] is False # 2 appears always, omission 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_statistics.py::test_calculate_omission_thresholds -v`
Expected: FAIL with "ImportError: cannot import name 'calculate_omission_thresholds'"

**Step 3: Write minimal implementation**

```python
# modules/statistics_engine.py
def calculate_omission_thresholds(df: pd.DataFrame, lottery_type: str = 'macaujc', zone: int = 1) -> dict:
    """Calculate current and max historical omission for each number, and flag if >= 80%"""
    import numpy as np
    
    if lottery_type == 'weilitsai':
        max_num = 38 if zone == 1 else 8
        cols = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6'] if zone == 1 else ['special']
    else:
        max_num = 49
        cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'special_num'] if zone == 1 else ['special_num']
        
    df_sorted = df.sort_values(by=['draw_date', 'draw_number'], ascending=[True, True])
    arr = df_sorted[cols].values.astype(int) if set(cols).issubset(df_sorted.columns) else np.array([])
    
    thresholds = {}
    for num in range(1, max_num + 1):
        if arr.size == 0:
            thresholds[num] = {'max_omission': 0, 'current_omission': 0, 'is_alert': False}
            continue
            
        # Find all indices where number appeared
        hits = np.where((arr == num).any(axis=1))[0]
        if len(hits) == 0:
            omission = len(arr)
            max_omi = len(arr)
        else:
            # Calculate gaps between hits
            # First gap is from start to first hit: hits[0]
            # subsequent gaps: hits[i] - hits[i-1] - 1
            # Current omission: len(arr) - 1 - hits[-1]
            gaps = [hits[0]]
            for i in range(1, len(hits)):
                gaps.append(hits[i] - hits[i-1] - 1)
            current_omi = len(arr) - 1 - hits[-1]
            gaps.append(current_omi)
            
            max_omi = max(gaps) if gaps else 0
            omission = current_omi
            
        thresholds[num] = {
            'max_omission': int(max_omi),
            'current_omission': int(omission),
            'is_alert': int(omission) >= int(max_omi * 0.8) and int(max_omi) > 5 # ignore very small max omissions
        }
        
    return thresholds
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_statistics.py::test_calculate_omission_thresholds -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/statistics_engine.py tests/test_statistics.py
git commit -m "feat: implement historical max omission and hit/skip alert threshold"
```

---

### Task 2: Build Markov Co-occurrence Matrix

**Files:**
- Modify: `modules/simulator.py`
- Modify: `tests/test_simulator.py`

**Step 1: Write the failing test**

```python
# tests/test_simulator.py
from modules.simulator import build_cooccurrence_matrix
import pandas as pd

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
    
    # 1 appears with 2, 3, 4, 5, 6 in draw 1, and 3, 4, 5, 6, 7 in draw 3
    # So 1 appears with 3 twice.
    assert matrix[1][3] == 2
    # 2 appears with 1 once
    assert matrix[2][1] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulator.py::test_build_cooccurrence_matrix -v`
Expected: FAIL with "ImportError: cannot import name 'build_cooccurrence_matrix'"

**Step 3: Write minimal implementation**

```python
# modules/simulator.py
def build_cooccurrence_matrix(df, max_num: int, cols: list) -> dict:
    import numpy as np
    from collections import defaultdict
    
    matrix = defaultdict(lambda: defaultdict(int))
    if df.empty or not set(cols).issubset(df.columns):
        return matrix
        
    arr = df[cols].values.astype(int)
    for row in arr:
        unique_nums = set(row)
        for n1 in unique_nums:
            if n1 < 1 or n1 > max_num: continue
            for n2 in unique_nums:
                if n2 < 1 or n2 > max_num or n1 == n2: continue
                matrix[n1][n2] += 1
                
    return matrix
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulator.py::test_build_cooccurrence_matrix -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/simulator.py tests/test_simulator.py
git commit -m "feat: implement markov co-occurrence matrix building"
```

---

### Task 3: Refine Simulator with Clustering, Omission Boost, and Odd/Even Constraint

**Files:**
- Modify: `modules/simulator.py`
- Modify: `tests/test_simulator.py`

**Step 1: Write the failing test**

```python
# tests/test_simulator.py
from modules.simulator import simulate_single

def test_simulate_single_constraints_and_clustering(monkeypatch):
    import pandas as pd
    
    # Mock data to provide enough history for omission and matrix
    df = pd.DataFrame({
        'draw_date': pd.date_range(start='1/1/2023', periods=10),
        'draw_number': range(1, 11),
        'lottery_type': ['weilitsai'] * 10,
        'n1': [1]*10, 'n2': [2]*10, 'n3': [3]*10, 'n4': [4]*10, 'n5': [5]*10, 'n6': [6]*10,
        'special': [8]*10
    })
    
    monkeypatch.setattr('modules.data_processor.load_data', lambda t: df)
    
    # Run multiple simulations to ensure odd/even constraints hold
    for _ in range(10):
        res = simulate_single(lottery_type='weilitsai')
        odds = sum(1 for x in res['numbers'] if x % 2 != 0)
        evens = 6 - odds
        # Valid ratios: 3:3, 2:4, 4:2 => odds must be 2, 3, or 4
        assert odds in [2, 3, 4]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulator.py::test_simulate_single_constraints_and_clustering -v`
Expected: FAIL because current `simulate_single` doesn't enforce 3:3, 2:4, or 4:2 ratio.

**Step 3: Write minimal implementation**

Modify `simulate_single` in `modules/simulator.py`:
1. Use `calculate_omission_thresholds` to get `is_alert`. Give alert numbers a `x3.0` boost in `weights_config`.
2. Build `cooccurrence_matrix` from `df_recent` (e.g. last 500 draws).
3. Implement `while True` loop up to 100 max attempts.
4. Inside loop, pick `core_num` based on `weights_config`.
5. For the remaining 5 numbers, merge `weights_config` with `cooccurrence_matrix[core_num]` (e.g., multiplier) to heavily favor clustered numbers. Pick them.
6. Verify Odd/Even ratio. If `odds in [2, 3, 4]`, break and accept.
7. Repeat similar logic for regular Mark Six (`lottery_type != 'weilitsai'`).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulator.py::test_simulate_single_constraints_and_clustering -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/simulator.py tests/test_simulator.py
git commit -m "feat: enforce odd-even normal distribution and markov clustering in simulator"
```
