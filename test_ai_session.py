import sys
import logging
from app import app
from flask import session

logging.basicConfig(level=logging.DEBUG)

with app.test_request_context('/api/simulate', method='POST', json={
    'type': 'macaujc',
    'mode': 'ai',
    'dimensions': ['big_small', 'odd_even'],
    'count': 1
}):
    session['user_id'] = 1
    session['role'] = 'admin'
    res = app.full_dispatch_request()
    print("RESPONSE BODY:", res.get_data(as_text=True))
