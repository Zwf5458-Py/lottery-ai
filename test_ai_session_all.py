import sys
import logging
from app import app
from flask import session

logging.basicConfig(level=logging.DEBUG)

with app.test_request_context('/api/simulate', method='POST', json={
    'type': 'macaujc',
    'mode': 'ai',
    'dimensions': ['big_small', 'odd_even', 'hot_cold', 'tail', 'color', 'markov', 'consecutive', 'bayesian', 'lstm'],
    'count': 1
}):
    session['user_id'] = 1
    session['role'] = 'admin'
    try:
        res = app.full_dispatch_request()
        print("RESPONSE BODY:", res.get_data(as_text=True))
    except Exception as e:
        import traceback
        traceback.print_exc()
