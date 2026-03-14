import sys
sys.path.insert(0, '.')
from modules.simulator import _calculate_trend_weights

weights = _calculate_trend_weights('macaujc2', ['zodiac'])
print("=== 生肖马尔可夫链权重分布 ===")
for zodiac, weight in sorted(weights['zodiac_weights'].items(), key=lambda x: x[1], reverse=True):
    print(f"{zodiac}: {weight}")
