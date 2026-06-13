# Wheeling System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the "Wheeling System" to generate optimal combination tickets based on mathematical guarantees, allowing users to enter a budget of tickets and dynamically matching it to the closest wheeling matrix.

---

### Task 1: Create Wheeling Templates Module

**Files:**
- Create: `modules/wheeling_system.py`
- Create: `tests/test_wheeling_system.py`

**Step 1: Write failing test**
Create `tests/test_wheeling_system.py`:
```python
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
```

**Step 2: Write implementation**
Create `modules/wheeling_system.py`:
- Define `WHEELING_TEMPLATES` containing matrices for `pool_size` 8, 9, 10, 12.
- Implement `get_best_matrix(budget: int)`.
- Implement `apply_matrix(matrix: list, pool: list)`.

**Step 3: Run and commit**
- `pytest tests/test_wheeling_system.py`
- `git add ... && git commit -m "feat: add wheeling templates and core matrix logic"`

---

### Task 2: Backend API Integration

**Files:**
- Modify: `app.py`
- Modify: `tests/test_api_wheeling.py`

**Step 1: Write failing test**
Create `tests/test_api_wheeling.py` that hits `POST /api/simulate/wheeling` with budget=15. Expect successful response containing a summary with `wheeling_info`.

**Step 2: Write implementation**
Modify `app.py`:
- Add `@app.route('/api/simulate/wheeling', methods=['POST'])`.
- Call `_calculate_trend_weights`.
- Pick top `pool_size` numbers based on weights.
- Generate tickets using `apply_matrix`.
- Fill remaining budget using `simulate_single`.
- Append `wheeling_info` string to `summary`.

**Step 3: Run and commit**
- `pytest tests/test_api_wheeling.py`
- `git add ... && git commit -m "feat: add wheeling system API endpoint"`

---

### Task 3: Frontend UI Update

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/app.js`

**Step 1: Update HTML**
- Add radio buttons or toggle for "Mode: Standard / Wheeling System".
- When Wheeling is selected, show an input `<input type="number" id="wheeling-budget" min="4" value="14">`.

**Step 2: Update JS**
- Modify the generate button logic to check the mode.
- If wheeling, call `/api/simulate/wheeling`.
- Display the `wheeling_info` from the response summary in the UI.

**Step 3: Commit**
- `git add ... && git commit -m "feat: add wheeling system UI toggles and budget input"`
