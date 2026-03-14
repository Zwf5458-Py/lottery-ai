import traceback
import urllib.request
import json
from modules.ai_engine import analyze_with_ai
from collections import namedtuple

class FakeResp:
    def read(self):
        return b'{"choices": [{"message": {"content": "{\\"analysis\\": \\"ok\\", \\"confidence\\": \\"\u9ad8\\"}"}}]}'
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def fake_urlopen(req, timeout):
    return FakeResp()

urllib.request.urlopen = fake_urlopen

try:
    from modules.statistics_engine import get_full_analysis
    stats = get_full_analysis('macaujc')
    # Use the exact correct signature
    ai_result = analyze_with_ai(stats, 'macaujc', ['big_small'])
    print("SUCCESS", ai_result)
except Exception as e:
    import traceback
    traceback.print_exc()
