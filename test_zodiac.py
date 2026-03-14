import math

def _analyze_advanced_pattern(nums, check_func, current_consecutive, opposing_consecutive):
    if len(nums) < 10: return 1.0, 1.0
    
    rle = []
    curr_val = check_func(nums[0])
    count = 1
    for i in range(1, len(nums)):
        val = check_func(nums[i])
        if val == curr_val:
            count += 1
        else:
            rle.append((curr_val, count))
            curr_val = val
            count = 1
    rle.append((curr_val, count))
    
    w_keep = 1.0
    w_break = 1.0

    recent_20_streaks = [x[1] for x in rle[:10]]
    if len(recent_20_streaks) >= 4:
        max_streak = max(recent_20_streaks)
        if current_consecutive >= max_streak and max_streak <= 3:
             w_break *= (2.0 + current_consecutive * 1.5)
    
    if current_consecutive == 3:
        w_break *= 2.5
    elif current_consecutive >= 4:
        w_break *= (4.0 + (current_consecutive - 4) * 2.0)

    if len(rle) >= 5:
        pattern_counts = [x[1] for x in rle]
        if len(pattern_counts) >= 4:
            if pattern_counts[1] == pattern_counts[3] and pattern_counts[1] > 0:
                target_count = pattern_counts[2]
                if current_consecutive < target_count:
                    w_keep *= 2.5
                elif current_consecutive == target_count:
                    w_break *= 3.0
                elif current_consecutive > target_count:
                    w_break *= 1.5
                    
        if all(c == 1 for c in pattern_counts[1:5]):
            if current_consecutive == 1:
                w_keep *= 2.5
            elif current_consecutive >= 2:
                w_keep *= 1.2
                
    return w_keep, w_break

def test_zodiac_momentum():
    # 模拟从老到新的 y 坐标序列
    # y 坐标：鼠0, 牛1, 虎2, 兔3, 龙4, 蛇5, 马6, 羊7, 猴8, 鸡9, 狗10, 猪11
    y_values = [
        3, 8, 2,  # 涨, 跌
        6, 1,     # 涨, 跌
        10, 5,    # 涨, 跌 (此时形成规律 单跳)
    ]
    
    # 构建趋势序列 ('up' or 'down')
    trends = []
    for i in range(1, len(y_values)):
        diff = y_values[i] - y_values[i-1]
        if diff > 0: trends.append('up')
        elif diff < 0: trends.append('down')
        else: trends.append('flat')
        
    trends = [t for t in trends if t != 'flat']
    
    # 按照 _analyze_advanced_pattern 需要的格式：最新的在索引0
    trends.reverse() 
    print("反转后的趋势 (左侧最新):", trends)
    
    current_trend = trends[0]
    consecutive_count = 0
    for t in trends:
        if t == current_trend:
            consecutive_count += 1
        else:
            break
            
    print(f"当前趋势: {current_trend}, 连续: {consecutive_count}次")
    
    # 把 up 判断为 True
    w_keep, w_break = _analyze_advanced_pattern(trends, lambda x: x == 'up', consecutive_count, 0)
    
    print(f"w_keep (顺势: 接着{current_trend}): {w_keep:.2f}")
    print(f"w_break (逆势: 改为{'up' if current_trend == 'down' else 'down'}): {w_break:.2f}")
    
    # 将乘子转换为 0-100 的 reversal_probability 概率
    # 基线: w_keep=1, w_break=1 代表 50% 转向概率
    # 如果 w_break > w_keep, 转折概念 > 50%
    # prob = (w_break / (w_keep + w_break)) * 100
    prob = (w_break / (w_keep + w_break)) * 100
    print(f"计算出的反转概率 (reversal_probability): {prob:.1f}%")

test_zodiac_momentum()
