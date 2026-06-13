# Taiwan Weilitsai (威力彩) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate Taiwan Weilitsai (威力彩) into the existing lottery system, including a scraper for historical data and adapted prediction algorithms for its dual-zone (38-choose-6 + 8-choose-1) format.

**Architecture:** 
1. **Data Layer**: Create a Python scraper using `requests` and `BeautifulSoup` to fetch historical data from Taiwan Lottery, storing it in the existing `lottery_history` SQLite table with `lottery_type='weilitsai'`.
2. **Logic Layer**: Modify `modules/statistics_engine.py` and `modules/simulator.py` to support `lottery_type` routing. For `weilitsai`, run statistics independently for Zone 1 (n1-n6, 1-38) and Zone 2 (special, 1-8).
3. **AI Layer**: Add a specific prompt template for Weilitsai in `modules/ai_engine.py` that ignores Zodiac/Color logic and focuses on the dual-zone rules.
4. **UI Layer**: Add a lottery type toggle in the frontend, hide Mark Six specific charts when Weilitsai is selected, and adapt the AI output display.

**Tech Stack:** Python, Flask, Pandas, SQLite, BeautifulSoup, HTML/JS/CSS

---

### Task 1: Create Data Scraper for Weilitsai

**Files:**
- Create: `data/fetch_weilitsai_data.py`
- Test: `tests/test_fetch_weilitsai.py` (optional for scraper, but let's do a basic structure test)

**Step 1: Write the failing test**

```python
# tests/test_fetch_weilitsai.py
import pytest
from unittest.mock import patch, MagicMock
from data.fetch_weilitsai_data import parse_html_to_records

def test_parse_html_to_records():
    # Mock HTML structure mimicking Taiwan Lottery
    html = '''
    <table>
        <tr>
            <td>113000001</td>
            <td>113/01/01</td>
            <td>01</td><td>02</td><td>03</td><td>04</td><td>05</td><td>06</td>
            <td>07</td>
        </tr>
    </table>
    '''
    records = parse_html_to_records(html)
    assert len(records) == 1
    assert records[0]['draw_issue'] == '113000001'
    assert records[0]['n1'] == 1
    assert records[0]['special'] == 7
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetch_weilitsai.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'data.fetch_weilitsai_data'"

**Step 3: Write minimal implementation**

```python
# data/fetch_weilitsai_data.py
from bs4 import BeautifulSoup

def parse_html_to_records(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []
    # Simplified parsing logic for the test
    tables = soup.find_all('table')
    if not tables: return []
    for tr in tables[0].find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 9:
            record = {
                'lottery_type': 'weilitsai',
                'draw_issue': tds[0].text.strip(),
                'draw_date': tds[1].text.strip(), # Needs real conversion in actual impl
                'n1': int(tds[2].text.strip()),
                'n2': int(tds[3].text.strip()),
                'n3': int(tds[4].text.strip()),
                'n4': int(tds[5].text.strip()),
                'n5': int(tds[6].text.strip()),
                'n6': int(tds[7].text.strip()),
                'special': int(tds[8].text.strip())
            }
            records.append(record)
    return records
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetch_weilitsai.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_fetch_weilitsai.py data/fetch_weilitsai_data.py
git commit -m "feat: add basic html parsing for weilitsai data"
```

---

### Task 2: Adapt Statistics Engine for Dual-Zone

**Files:**
- Modify: `modules/statistics_engine.py`
- Modify: `tests/test_statistics.py`

**Step 1: Write the failing test**

```python
# In tests/test_statistics.py, add:
def test_number_frequency_weilitsai():
    from modules.statistics_engine import number_frequency
    import pandas as pd
    
    # Mock dataframe with weilitsai data
    df = pd.DataFrame({
        'lottery_type': ['weilitsai', 'weilitsai'],
        'n1': [1, 2], 'n2': [2, 3], 'n3': [3, 4], 
        'n4': [4, 5], 'n5': [5, 6], 'n6': [6, 7],
        'special': [1, 8]
    })
    
    # Test Zone 1
    freq_z1 = number_frequency(df=df, lottery_type='weilitsai', zone=1)
    assert 1 in freq_z1 and 7 in freq_z1
    assert 8 not in freq_z1 # Special number shouldn't be here
    
    # Test Zone 2
    freq_z2 = number_frequency(df=df, lottery_type='weilitsai', zone=2)
    assert 1 in freq_z2 and 8 in freq_z2
    assert 2 not in freq_z2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_statistics.py::test_number_frequency_weilitsai -v`
Expected: FAIL due to unexpected keyword arguments `lottery_type` and `zone`

**Step 3: Write minimal implementation**

Modify `number_frequency` and helper functions in `modules/statistics_engine.py` to accept `lottery_type` and `zone`. 
If `lottery_type == 'weilitsai'`:
- `zone == 1`: extract from `n1` to `n6`
- `zone == 2`: extract from `special`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_statistics.py::test_number_frequency_weilitsai -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/statistics_engine.py tests/test_statistics.py
git commit -m "feat: adapt number frequency stats for weilitsai zones"
```

*(Repeat similar process for Hot/Cold, Odd/Even, Big/Small in Task 2.5)*

---

### Task 3: Adapt Simulator for 38-choose-6 + 8-choose-1

**Files:**
- Modify: `modules/simulator.py`
- Modify: `tests/test_simulator.py` (Create if not exists)

**Step 1: Write the failing test**

```python
# tests/test_simulator.py
from modules.simulator import simulate_next_draw

def test_simulate_weilitsai(monkeypatch):
    # Mock data loading
    monkeypatch.setattr('modules.data_processor.load_data', lambda t: pd.DataFrame())
    
    result = simulate_next_draw(lottery_type='weilitsai')
    
    assert len(result['regular_numbers']) == 6
    assert all(1 <= n <= 38 for n in result['regular_numbers'])
    assert len(set(result['regular_numbers'])) == 6 # Unique
    assert 1 <= result['special_number'] <= 8
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulator.py::test_simulate_weilitsai -v`
Expected: FAIL because simulator assumes Mark Six (1-49) and logic

**Step 3: Write minimal implementation**

Modify `simulate_next_draw` in `modules/simulator.py` to branch on `lottery_type`. For `weilitsai`, adjust the candidate pools (1-38 for regular, 1-8 for special) and selection logic.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulator.py::test_simulate_weilitsai -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/simulator.py tests/test_simulator.py
git commit -m "feat: adapt simulator for weilitsai rules"
```

---

### Task 4: AI Prompt Engineering for Weilitsai

**Files:**
- Modify: `modules/ai_engine.py`
- Modify: `tests/test_ai_engine.py`

**Step 1: Write the failing test**

```python
# tests/test_ai_engine.py
from modules.ai_engine import build_prompt

def test_build_prompt_weilitsai():
    prompt = build_prompt(
        lottery_type='weilitsai',
        stats_data={'z1': 'data', 'z2': 'data'},
        simulated_nums={'regular_numbers': [1,2,3,4,5,6], 'special_number': 8}
    )
    assert '威力彩' in prompt
    assert '第一區' in prompt
    assert '第二區' in prompt
    assert '生肖' not in prompt
    assert '波色' not in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_engine.py::test_build_prompt_weilitsai -v`
Expected: FAIL because `build_prompt` doesn't handle `lottery_type` properly or hardcodes Mark Six logic.

**Step 3: Write minimal implementation**

Modify `build_prompt` to accept `lottery_type` and use a different base template if `lottery_type == 'weilitsai'`. Ensure the new template explicitly mentions the two zones and excludes Zodiac/Color references.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_engine.py::test_build_prompt_weilitsai -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/ai_engine.py tests/test_ai_engine.py
git commit -m "feat: add specific ai prompt template for weilitsai"
```

---

### Task 5: Backend API Routing

**Files:**
- Modify: `blueprints/api.py`
- Test: Modify existing API tests or add `tests/test_api_weilitsai.py`

Update endpoints like `/api/statistics` and `/api/simulate` to accept `?lottery_type=weilitsai`. Validate that the correct stats and simulations are returned.

---

### Task 6: Frontend UI Adaptation

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/app.js`

Add a switcher (HTML Select or Radio Buttons) in the UI state for `currentLotteryType` (default: `macaujc`). 
Update AJAX calls in `app.js` to append `&lottery_type=` to requests.
Conditionally hide Zodiac/Color chart containers when `weilitsai` is selected.
Update the AI Report display layout to show "第一區 (Zone 1)" and "第二區 (Zone 2)".
