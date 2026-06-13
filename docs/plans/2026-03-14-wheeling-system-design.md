# Wheeling System (旋转矩阵) Design Plan

## Overview
Implement a "Wheeling System" to generate multiple optimal tickets based on AI predictions. This system will use predefined mathematically proven combinatorial templates. When a user inputs a budget (number of tickets), the system will automatically find the largest wheeling matrix that fits the budget, use the top-weighted AI numbers to fill the matrix, and generate the remaining tickets using the standard AI simulation algorithm.

## Section 1: Data Structure & Matrix Definition
- Create a new module: `modules/wheeling_system.py`
- Define `WHEELING_TEMPLATES` with the following structure:
  ```python
  WHEELING_TEMPLATES = [
      {
          "pool_size": 8,
          "tickets": 4,
          "guarantee": "3/3", # Guarantees a match of 3 if 3 drawn numbers are in the pool
          "matrix": [
              [1, 2, 3, 4, 5, 6],
              [1, 2, 3, 4, 7, 8],
              ...
          ]
      },
      # Add templates for 9, 10, 12 numbers etc.
  ]
  ```
- **Matching Logic**: Given a budget `N`, find the template with the largest `tickets` where `tickets <= N`. The remaining `N - tickets` will be generated using the standard `simulate_single`.

## Section 2: AI Core Number Selection & API
- Extract AI weights using `_calculate_trend_weights`.
- Sort numbers by weight to find the Top K numbers (where K is the `pool_size` of the chosen template).
- Map the Top K numbers to the matrix indices (1 to K). Ensure the highest weighted numbers are mapped to the most frequent positions in the matrix.
- Special Number (Zone 2): Generate standard weighted random special numbers for each generated ticket.
- **API Endpoint**: 
  - `POST /api/simulate/wheeling`
  - Parameters: `count` (budget), `lottery_type`, `dimensions`
  - Returns identical JSON structure to standard `/api/simulate` but includes a `wheeling_info` string in the summary (e.g., "Used 10-number matrix (4/5 guarantee) for 14 tickets, + 6 standard AI tickets").

## Section 3: Frontend Integration
- Modify `index.html` and `app.js` in the simulation section.
- Add a mode toggle: "Standard" vs "Wheeling System".
- When "Wheeling System" is selected, show a number input field for "Budget (Tickets)", min 4.
- Update the API call to point to `/api/simulate/wheeling` when the toggle is active.
- Display the `wheeling_info` string in the UI summary area after generation.

## Implementation Steps
1. Create `modules/wheeling_system.py` with the matrices and core generator function.
2. Add tests for the wheeling system generator.
3. Update `app.py` with the new `/api/simulate/wheeling` endpoint.
4. Update frontend (`index.html`, `app.js`) to support the new UI and endpoint.