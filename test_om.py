import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.statistics_engine import hot_cold_numbers

try:
    print("Testing hot_cold_numbers with periods=90")
    result = hot_cold_numbers(top_n=10, df=None, periods=90)
    print("HOT:")
    for item in result['hot']: print(item)
    print("COLD:")
    for item in result['cold']: print(item)
except Exception as e:
    import traceback
    traceback.print_exc()
