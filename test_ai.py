import traceback
from modules.ai_engine import analyze_with_ai
from modules.statistics_engine import get_full_analysis

lottery_type = 'macaujc'
dimensions = ['big_small', 'odd_even']

stats = get_full_analysis(lottery_type)
try:
    ai_result = analyze_with_ai(stats, lottery_type, dimensions)
    print("SUCCESS", ai_result)
except Exception as e:
    traceback.print_exc()
