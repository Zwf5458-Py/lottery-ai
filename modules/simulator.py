"""
模拟开奖模块
功能：使用加密级别的强伪随机数生成器进行模拟开奖。
采用 Python secrets 模块，基于操作系统提供的最高质量随机源。

重要说明：模拟结果为纯随机生成，与历史数据无关，不具有任何预测性质。
"""

import random
import secrets
import json
import urllib.request
import ssl
import os
from datetime import datetime
from modules.data_processor import get_db_connection
from modules.logger import get_logger
from modules.constants import get_zodiac_mapping, get_color, RED_NUMS, BLUE_NUMS, GREEN_NUMS, ZODIAC_ORDER
from collections import Counter, defaultdict

logger = get_logger()

# 使用 secrets.SystemRandom 作为加密级随机数生成器
_secure_random = secrets.SystemRandom()

# 默认启用 TLS 证书校验；仅在显式设置 INSECURE_SSL=1 时降级（不建议生产使用）
ssl_context = ssl.create_default_context()
if os.environ.get('INSECURE_SSL', '0') == '1':
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

def can_simulate_today(lottery_type: str = 'macaujc') -> bool:
    """
    检查今天是否已经开奖。加入多数据源容灾机制。
    """
    year = datetime.now().strftime('%Y')
    
    # 定义多数据源列表 (主源 -> 备用源1 -> 备用源2)
    if lottery_type == 'macaujc':
        sources = [
            "https://macaumarksix.com/api/macaujc.com",
            f"https://history.macaumarksix.com/history/macaujc/y/{year}"
        ]
    else:
        sources = [
            f"https://history.macaumarksix.com/history/macaujc2/y/{year}",
            "https://macaumarksix.com/api/macaujc2.com"
        ]

    for api_url in sources:
        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://macaujc.com/'
                }
            )
            with urllib.request.urlopen(req, timeout=8, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            latest_record = None
            if data.get('data') and isinstance(data['data'], list):
                latest_record = data['data'][0]
            elif data.get('data') and isinstance(data['data'], dict):
                latest_record = data['data']
                
            if not latest_record:
                continue # 尝试下一个源
                
            draw_number = str(latest_record.get('expect', ''))
            open_time = latest_record.get('openTime', '')
            draw_date = open_time.split(' ')[0] if open_time else ''
            today_date = datetime.now().strftime('%Y-%m-%d')
            
            # 同步记录到数据库
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from data.fetch_real_data import parse_record
            parsed = parse_record(latest_record)
            
            if parsed and draw_number:
                conn = get_db_connection()
                exists = conn.execute("SELECT 1 FROM lottery_history WHERE lottery_type=? AND draw_number=?", (lottery_type, draw_number)).fetchone()
                if not exists:
                    conn.execute('''
                        INSERT INTO lottery_history
                        (lottery_type, draw_number, draw_date, num1, num2, num3, num4, num5, num6,
                         special_num, wave, zodiac)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (lottery_type,) + parsed)
                    conn.commit()
                conn.close()
                
            if draw_date == today_date:
                return False
            else:
                return True # 数据虽不是今天，但请求成功了
                
        except Exception as e:
            logger.warning(f"数据源 {api_url} 同步最新开奖失败: {e}，尝试切换备用源...")
            continue
            
    logger.error("所有开奖数据源均失效，为了不阻断用户使用，放行模拟。")
    return True


# get_zodiac_mapping 已迁移到 modules/constants.py，此处通过顶部 import 引入


def _build_markov_transition_weights(conn, lottery_type: str, z_map: dict = None, max_periods: int = 0) -> dict:
    """
    基于全量历史数据构建马尔可夫链状态转移矩阵。
    统计相邻两期特码生肖（或一区号码）的转移频次，结合当前最新特码生肖，推算其转移到下一个状态的条件概率权重。
    返回: {zodiac_name/number: weight_float}
    """
    if lottery_type == 'weilitsai':
        # 按时间正序拉取一区 6 正码数字
        if max_periods > 0:
            query = "SELECT num1, num2, num3, num4, num5, num6 FROM (SELECT num1, num2, num3, num4, num5, num6, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT ?) ORDER BY draw_date ASC, draw_number ASC"
            rows = conn.execute(query, (lottery_type, int(max_periods))).fetchall()
        else:
            query = "SELECT num1, num2, num3, num4, num5, num6 FROM (SELECT num1, num2, num3, num4, num5, num6, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC) ORDER BY draw_date ASC, draw_number ASC"
            rows = conn.execute(query, (lottery_type,)).fetchall()
            
        default_weights = {str(n): 1.0 for n in range(1, 39)}
        if not rows or len(rows) < 2:
            return default_weights
            
        # 提取每一期正码号码列表
        import pandas as pd
        draws = []
        for r in rows:
            draw = [int(x) for x in r if pd.notna(x) and 1 <= int(x) <= 38]
            if len(draw) > 0:
                draws.append(draw)
                
        if len(draws) < 2:
            return default_weights
            
        # 构建 38x38 转移矩阵
        transition_matrix = {n1: {n2: 0 for n2 in range(1, 39)} for n1 in range(1, 39)}
        for i in range(len(draws) - 1):
            prev_nums = draws[i]
            curr_nums = draws[i+1]
            for n1 in prev_nums:
                for n2 in curr_nums:
                    transition_matrix[n1][n2] += 1
                    
        # 用最后一期的 6 个号码预测下一期
        last_nums = draws[-1]
        next_freqs = {n2: 0 for n2 in range(1, 39)}
        for n1 in last_nums:
            for n2 in range(1, 39):
                next_freqs[n2] += transition_matrix[n1][n2]
                
        # 拉普拉斯平滑
        alpha_smooth = 1
        smoothed_freqs = {n2: freq + alpha_smooth for n2, freq in next_freqs.items()}
        total_smoothed = sum(smoothed_freqs.values())
        
        weights = {}
        base_prob = 1.0 / 38.0
        for n2, count in smoothed_freqs.items():
            prob = count / total_smoothed if total_smoothed > 0 else base_prob
            w = max(0.5, min(2.5, prob / base_prob))
            weights[str(n2)] = round(w, 3)
            
        # 统计频次
        total_occurrences = {str(n): 0 for n in range(1, 39)}
        for draw in draws:
            for n in draw:
                if str(n) in total_occurrences:
                    total_occurrences[str(n)] += 1
                    
        weights['_occurrences'] = total_occurrences
        weights['max_periods'] = max_periods
        return weights

    # 按时间正序拉取全量或指定期数的特码数字
    if max_periods > 0:
        query = "SELECT special_num FROM (SELECT special_num, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT ?) ORDER BY draw_date ASC, draw_number ASC"
        rows = conn.execute(query, (lottery_type, int(max_periods))).fetchall()
    else:
        query = "SELECT special_num FROM (SELECT special_num, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC) ORDER BY draw_date ASC, draw_number ASC"
        rows = conn.execute(query, (lottery_type,)).fetchall()
    
    zodiac_order = ZODIAC_ORDER
    default_weights = {z: 1.0 for z in zodiac_order}
    if not rows or len(rows) < 2:
        return default_weights
        
    # 初始化转移矩阵
    transition_matrix = {z1: {z2: 0 for z2 in zodiac_order} for z1 in zodiac_order}
    
    # 提取有效的生肖时间序列
    z_seq = []
    for r in rows:
        num = r[0]
        if type(num) is int and 1 <= num <= 49 and num in z_map:
            z_seq.append(z_map[num])
        elif type(num) is str and num.isdigit():
            n = int(num)
            if 1 <= n <= 49 and n in z_map:
                z_seq.append(z_map[n])
                
    if len(z_seq) < 2:
        return default_weights
        
    # 计算转移频次
    for i in range(len(z_seq) - 1):
        z_curr = z_seq[i]
        z_next = z_seq[i+1]
        transition_matrix[z_curr][z_next] += 1
        
    # 获取目前真实的最后一期特码生肖
    last_z = z_seq[-1]
    next_freqs = transition_matrix[last_z]
    
    # 引入拉普拉斯平滑 (Laplace Smoothing) 防止零概率情况
    alpha_smooth = 1
    smoothed_freqs = {z: freq + alpha_smooth for z, freq in next_freqs.items()}
    total_smoothed = sum(smoothed_freqs.values())
    
    # 转为相对权重（基准概率 1/12）
    weights = {}
    base_prob = 1.0 / 12.0
    for z, count in smoothed_freqs.items():
        prob = count / total_smoothed
        # 将生成的概率除以基础概率得到权重，限制在此范围避免过于极端
        w = max(0.5, min(2.5, prob / base_prob))
        weights[z] = round(w, 3)

    # 统计期数内各生肖出现的总次数
    total_occurrences = {z: 0 for z in zodiac_order}
    for z in z_seq:
        if z in total_occurrences:
            total_occurrences[z] += 1
            
    weights['_occurrences'] = total_occurrences
    weights['max_periods'] = max_periods
    return weights

def _build_color_markov_transition_weights(conn, lottery_type: str, max_periods: int = 0) -> dict:
    """
    构建特码波色（红、蓝、绿）的马尔可夫链状态转移权重。
    """
    if max_periods > 0:
        query = "SELECT special_num FROM (SELECT special_num, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT ?) ORDER BY draw_date ASC, draw_number ASC"
        rows = conn.execute(query, (lottery_type, int(max_periods))).fetchall()
    else:
        query = "SELECT special_num FROM (SELECT special_num, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC) ORDER BY draw_date ASC, draw_number ASC"
        rows = conn.execute(query, (lottery_type,)).fetchall()
    
    color_order = ["红波", "蓝波", "绿波"]
    default_weights = {c: 1.0 for c in color_order}
    if not rows or len(rows) < 2:
        return default_weights

    # 初始化 3x3 转移矩阵
    transition_matrix = {c1: {c2: 0 for c2 in color_order} for c1 in color_order}

    # 构建有效的波色序列
    c_seq = []
    for r in rows:
        try:
            num = int(r[0])
            c = get_color(num)  # 来自 modules.constants
            if c and c != '未知':
                c_seq.append(c)
        except:
            pass
            
    if len(c_seq) < 2:
        return default_weights

    # 计算转移频次
    for i in range(len(c_seq) - 1):
        c_curr = c_seq[i]
        c_next = c_seq[i+1]
        transition_matrix[c_curr][c_next] += 1

    last_c = c_seq[-1]
    next_freqs = transition_matrix[last_c]

    # 拉普拉斯平滑
    alpha_smooth = 1
    smoothed_freqs = {c: freq + alpha_smooth for c, freq in next_freqs.items()}
    total_smoothed = sum(smoothed_freqs.values())
    
    # 转为相对权重（基准概率 1/3）
    weights = {}
    base_prob = 1.0 / 3.0
    for c, count in smoothed_freqs.items():
        prob = count / total_smoothed
        w = max(0.5, min(2.5, prob / base_prob))
        weights[c] = round(w, 3)

    # 统计期数内各波色出现的总次数
    total_occurrences = {c: 0 for c in color_order}
    for c in c_seq:
        if c in total_occurrences:
            total_occurrences[c] += 1
            
    weights['_occurrences'] = total_occurrences
    weights['max_periods'] = max_periods

    return weights


def _calculate_trend_weights(lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """内部算法：推导各项趋势防跳和断龙的综合权重"""
    if dimensions is None:
        dimensions = ['big_small', 'odd_even', 'zodiac', 'hot_cold', 'tail']
        
    from modules.config_manager import get_chart_periods
    periods_cfg = get_chart_periods(lottery_type=lottery_type)
    
    conn = get_db_connection()
    
    # 获取最近 30 期计算复杂大小单双模式
    rows_30 = conn.execute(
        "SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT 30",
        (lottery_type,)
    ).fetchall()
    
    # 获取最近 50 期获取生肖概率 (仅统计特码)
    rows_50 = conn.execute(
        "SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT 50",
        (lottery_type,)
    ).fetchall()
    conn.close()
    
    # 额外的 DB 连接用于新维度查询
    conn_extra = get_db_connection()

    def _safe_int(value, default):
        try:
            iv = int(value)
            return iv if iv > 0 else int(default)
        except Exception:
            return int(default)
    
    weight_cfg = {
        'big_weight': 1.0, 'small_weight': 1.0, 
        'odd_weight': 1.0, 'even_weight': 1.0,
        'zodiac_weights': {},
        'hot_cold_weights': {},  # {号码: 权重}
        'tail_weights': {}       # {尾数: 权重}
    }
    
    if rows_30:
        special_nums = [r[0] for r in rows_30]
        consecutive_big, consecutive_small = 0, 0
        consecutive_odd, consecutive_even = 0, 0
        
        # 统计连大连小
        bs_threshold = 5 if lottery_type == 'weilitsai' else 25
        for num in special_nums:
            if num >= bs_threshold:
                if consecutive_small > 0: break
                consecutive_big += 1
            else:
                if consecutive_big > 0: break
                consecutive_small += 1
                
        # 统计连单连双
        for num in special_nums:
            if num % 2 != 0:
                if consecutive_even > 0: break
                consecutive_odd += 1
            else:
                if consecutive_odd > 0: break
                consecutive_even += 1
                
        # ======== 新增：高级折线图模式识别 (1-2-1-2 / 天花板限制) ========
        def _analyze_advanced_pattern(nums, check_func, current_consecutive, opposing_consecutive):
            """
            推演接下来一期顺势/逆势权重。
            nums是倒序排列的(nums[0]为最新期)。
            check_func 用来判别目标属性 (如 True=大, False=小)
            返回: (target_weight_multiplier, opposite_weight_multiplier) -> 对应 current_state 和 反面
            """
            if len(nums) < 10: return 1.0, 1.0
            
            # 1. 提取连续段结构 RLE (Run-Length Encoding)，例如 ["大2", "小1", "大2", "小1"]
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

            # rle[0] 是最近结束的一段（或者正在进行中的一段）。
            # 注意：如果正在连庄，rle[0] 的 count 可能就是 current_consecutive。
            
            last_state = check_func(nums[0]) # 最近一期的状态 (例如 大)
            w_keep = 1.0  # 维持当前状态（继续连庄）的乘数
            w_break = 1.0 # 改变状态（转向）的乘数

            # 规则A1：近20期严格的"天花板壁垒"
            # 比如连续近十几次跳变，从来没有超过2连。而当前已经2连了。
            recent_20_streaks = [x[1] for x in rle[:10]] # 看大概20期的跳段
            if len(recent_20_streaks) >= 4:
                max_streak = max(recent_20_streaks)
                # 假设历史上没有任何超过 2 连的，而当前正处于 2连，则极大概率要断掉(w_break暴增)
                if current_consecutive >= max_streak and max_streak <= 3:
                     # 历史最高就这么多，当前顶满天花板了
                     w_break *= (2.0 + current_consecutive * 1.5)
            
            # 规则A2：均值回归防长龙长线
            if current_consecutive == 3:
                w_break *= 2.5
            elif current_consecutive >= 4:
                w_break *= (4.0 + (current_consecutive - 4) * 2.0)

            # 规则B：重复宏观模式匹配 (比如 1-2-1-2 或 1-1-2-1-1-2)
            # 通过匹配 RLE 数组的前面几项。
            if len(rle) >= 5:
                # 检查 `1-2-1-2` 类型跳动：当前可能是处于跳动的某一环
                # 例如历史是 A1, B2, A1, B2... 此时最新的是 A(假设刚开1个A)。下个极大概率是B(形成B2)
                
                # 提取数字特征
                pattern_counts = [x[1] for x in rle] # 例：[1, 2, 1, 2, 1, 2]
                
                # 简单周期2检测: P0 应该对应 P2, P1 应该对应 P3
                if len(pattern_counts) >= 4:
                    if pattern_counts[1] == pattern_counts[3] and pattern_counts[1] > 0:
                        # 形成周期重复。
                        # 我们处于 rle[0]，正在累积 pattern_counts[0]
                        target_count = pattern_counts[2] # 我们"应该"向这个目标靠拢
                        
                        if current_consecutive < target_count:
                            # 还没达到该有的模式长度，非常可能继续连庄
                            w_keep *= 2.5
                        elif current_consecutive == target_count:
                            # 刚好达到模式长度，非常可能在此断掉，转折
                            w_break *= 3.0
                        elif current_consecutive > target_count:
                            # 已经打破模式，视为失效，正常均值回归叠加
                            w_break *= 1.5
                            
                # 检查 1-1-1 单跳长龙
                if all(c == 1 for c in pattern_counts[1:5]):
                    # 历史单跳了4次！
                    if current_consecutive == 1:
                        # 当前处于新状态第1个，下个应该转为打断单跳(连庄)还是继续单跳？
                        # 用户常有"防跳"心理，即单跳太久必有连。
                        w_keep *= 2.5 # 押注它连庄(防跳)
                    elif current_consecutive >= 2:
                        w_keep *= 1.2
            
            return w_keep, w_break

        if 'big_small' in dimensions:
            bs_threshold = 5 if lottery_type == 'weilitsai' else 25
            last_is_big = special_nums[0] >= bs_threshold if special_nums else False
            w_keep, w_break = _analyze_advanced_pattern(special_nums, lambda n: n >= bs_threshold, consecutive_big if last_is_big else consecutive_small, consecutive_small if last_is_big else consecutive_big)
            
            if last_is_big:
                weight_cfg['big_weight'] = w_keep
                weight_cfg['small_weight'] = w_break
            else:
                weight_cfg['small_weight'] = w_keep
                weight_cfg['big_weight'] = w_break
            
        if 'odd_even' in dimensions:
            last_is_odd = special_nums[0] % 2 != 0 if special_nums else False
            w_keep, w_break = _analyze_advanced_pattern(special_nums, lambda n: n % 2 != 0, consecutive_odd if last_is_odd else consecutive_even, consecutive_even if last_is_odd else consecutive_odd)
            
            if last_is_odd:
                weight_cfg['odd_weight'] = w_keep
                weight_cfg['even_weight'] = w_break
            else:
                weight_cfg['even_weight'] = w_keep
                weight_cfg['odd_weight'] = w_break

    # ====== 修改：马尔可夫链状态转移推演 ======
    if 'markov' in dimensions:
        z_map = get_zodiac_mapping(lottery_type) if lottery_type != 'weilitsai' else None
        markov_p = periods_cfg.get('markov', 0)
        weight_cfg['zodiac_weights'] = _build_markov_transition_weights(conn_extra, lottery_type, z_map, markov_p)

    # ====== 修改：冷热频率完全特码化 ======
    if 'hot_cold' in dimensions:
        hc_p = _safe_int(periods_cfg.get('hot_cold', 100), 100)
        
        if lottery_type == 'weilitsai':
            # === 威力彩第一区 (Zone 1) 冷热与遗漏权重计算 ===
            all_rows_z1 = conn_extra.execute(
                "SELECT num1, num2, num3, num4, num5, num6 FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC",
                (lottery_type,)
            ).fetchall()
            
            rows_hc_z1 = all_rows_z1[:hc_p]
            weight_cfg['hot_cold_weights_z1'] = {}
            if rows_hc_z1:
                num_freq = Counter()
                omissions = {n: len(all_rows_z1) for n in range(1, 39)}
                
                for idx, row in enumerate(all_rows_z1):
                    for n in row:
                        if 1 <= n <= 38:
                            if omissions[n] == len(all_rows_z1):
                                omissions[n] = idx
                                
                for row in rows_hc_z1:
                    for n in row:
                        if 1 <= n <= 38:
                            num_freq[n] += 1
                            
                max_omission = max(omissions.values()) if omissions else 0
                avg_freq = sum(num_freq.values()) / 38 if num_freq else 1
                
                for n in range(1, 39):
                    f = num_freq.get(n, 0)
                    base_w = 1.0
                    if avg_freq > 0:
                        ratio = f / avg_freq
                        if ratio < 0.5:
                            base_w = 1.6
                        elif ratio < 0.8:
                            base_w = 1.3
                        elif ratio > 1.5:
                            base_w = 0.85
                        else:
                            base_w = 1.0 + (ratio - 1) * 0.15
                            
                    if omissions[n] == max_omission and max_omission > 5:
                        bonus_multiplier = 1.0 + (max_omission / hc_p) * 2.5
                        base_w *= bonus_multiplier
                        
                    weight_cfg['hot_cold_weights_z1'][n] = base_w
                    
            # === 威力彩第二区 (Zone 2) 冷热与遗漏权重计算 ===
            all_rows_z2 = conn_extra.execute(
                "SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC",
                (lottery_type,)
            ).fetchall()
            
            rows_hc_z2 = all_rows_z2[:hc_p]
            weight_cfg['hot_cold_weights_z2'] = {}
            if rows_hc_z2:
                num_freq = Counter()
                omissions = {n: len(all_rows_z2) for n in range(1, 9)}
                
                for idx, row in enumerate(all_rows_z2):
                    n = row[0]
                    if 1 <= n <= 8:
                        if omissions[n] == len(all_rows_z2):
                            omissions[n] = idx
                            
                for row in rows_hc_z2:
                    n = row[0]
                    if 1 <= n <= 8:
                        num_freq[n] += 1
                        
                max_omission = max(omissions.values()) if omissions else 0
                avg_freq = sum(num_freq.values()) / 8 if num_freq else 1
                
                for n in range(1, 9):
                    f = num_freq.get(n, 0)
                    base_w = 1.0
                    if avg_freq > 0:
                        ratio = f / avg_freq
                        if ratio < 0.5:
                            base_w = 1.6
                        elif ratio < 0.8:
                            base_w = 1.3
                        elif ratio > 1.5:
                            base_w = 0.85
                        else:
                            base_w = 1.0 + (ratio - 1) * 0.15
                            
                    if omissions[n] == max_omission and max_omission > 5:
                        bonus_multiplier = 1.0 + (max_omission / hc_p) * 2.5
                        base_w *= bonus_multiplier
                        
                    weight_cfg['hot_cold_weights_z2'][n] = base_w
        else:
            # 为了计算真实的极值遗漏，我们需要全量数据（或者至少一个极大的窗口比如 1000 期），而不是被 hc_p 截断的数据
            all_rows = conn_extra.execute(
                "SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC",
                (lottery_type,)
            ).fetchall()
            
            # 频率统计仅限于用户要求的期数 (hc_p)
            rows_hc = all_rows[:hc_p]
            
            if rows_hc:
                num_freq = Counter()
                # 从全量数据中计算每个号码的真实遗漏深度
                omissions = {n: len(all_rows) for n in range(1, 50)}
                
                for idx, row in enumerate(all_rows):
                    n = row[0]
                    if 1 <= n <= 49:
                        if omissions[n] == len(all_rows):
                            omissions[n] = idx
                            
                # 计算期数内的出现频率
                for row in rows_hc:
                    n = row[0]
                    if 1 <= n <= 49:
                        num_freq[n] += 1
                        
                # 找出全场所有号码中的真实最大遗漏
                max_omission = max(omissions.values())
                
                avg_freq = sum(num_freq.values()) / 49 if num_freq else 1
                
                for n in range(1, 50):
                    f = num_freq.get(n, 0)
                    base_w = 1.0
                    
                    # 均    # ====== 新增：深层算法 (连涨拐点, 贝叶斯与 LSTM, 波色极值) 直接调用 engine.py 免得重复写 ======
    active_deep = [k for k in ('bayesian', 'lstm', 'consecutive', 'color') if k in dimensions]
    if lottery_type == 'weilitsai':
        active_deep = [k for k in active_deep if k != 'color']
        
    if active_deep:
        import pandas as pd
        from modules.statistics_engine import bayesian_inference, lstm_simulation, zodiac_momentum_analysis, color_hot_cold_analysis, get_zodiac_mapping as ge_z
        z_map_local = ge_z(lottery_type) if lottery_type != 'weilitsai' else None
        
        if lottery_type == 'weilitsai':
            df_all = pd.read_sql_query(
                "SELECT num1, num2, num3, num4, num5, num6, special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT ?",
                conn_extra,
                params=(lottery_type, 200)
            )
        else:
            df_all = pd.read_sql_query(
                "SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT ?",
                conn_extra,
                params=(lottery_type, 200)
            )
        
        if 'bayesian' in dimensions:
            b_data = bayesian_inference(df_all, z_map_local, periods_cfg.get('bayesian', 100), lottery_type=lottery_type)
            # b_data: [{'zodiac': '鼠', 'posterior': 35.6}, ...] or [{'number': 1, 'posterior': 35.6}, ...]
            max_p = max([d['posterior'] for d in b_data]) if b_data else 1
            if lottery_type == 'weilitsai':
                weight_cfg['bayesian_weights'] = {d['number']: 1.0 + (d['posterior'] / max_p)*0.8 for d in b_data} if max_p > 0 else {}
            else:
                weight_cfg['bayesian_weights'] = {d['zodiac']: 1.0 + (d['posterior'] / max_p)*0.8 for d in b_data} if max_p > 0 else {}
            
        if 'lstm' in dimensions:
            l_data = lstm_simulation(df_all, z_map_local, periods_cfg.get('lstm', 100), lottery_type=lottery_type)
            if lottery_type == 'weilitsai':
                weight_cfg['lstm_weights'] = {d['number']: 0.5 + (d['score']/100)*1.0 for d in l_data}
            else:
                weight_cfg['lstm_weights'] = {d['zodiac']: 0.5 + (d['score']/100)*1.0 for d in l_data}
            
        # 共享 consecutive 的结果，避免对 simulator.py 外暴露过多。
        color_momentum_boosts = None
        
        if 'consecutive' in dimensions:
            c_data = zodiac_momentum_analysis(df_all, z_map_local, lottery_type=lottery_type)
            rev_prob = c_data.get('reversal_probability', 0)
            color_momentum_boosts = c_data.get('color_momentum_boosts', None)
            
            if rev_prob >= 50:
                cw = {}
                target_dir = c_data.get('reversal_target_direction', 'none')
                if lottery_type == 'weilitsai':
                    # 和值反转。若 target_dir == 'down' 则调高小号，若 'up' 则调高大号
                    for n in range(1, 39):
                        if target_dir == 'down' and n <= 19:
                            cw[n] = 1.0 + (rev_prob / 100.0) * 1.5
                        elif target_dir == 'up' and n >= 20:
                            cw[n] = 1.0 + (rev_prob / 100.0) * 1.5
                else:
                    z_order = c_data.get('zodiac_order', [])
                    current_y = c_data.get('current_y', -1)
                    if current_y != -1 and target_dir != 'none':
                        for i, z in enumerate(z_order):
                            if target_dir == 'down' and i < current_y:
                                cw[z] = 1.0 + (rev_prob / 100.0) * 1.5
                            elif target_dir == 'up' and i > current_y:
                                cw[z] = 1.0 + (rev_prob / 100.0) * 1.5
                weight_cfg['consecutive_weights'] = cw

        if 'color' in dimensions and lottery_type != 'weilitsai':
            color_data = color_hot_cold_analysis(df_all, periods_cfg.get('hot_cold', 100))
            # 极端度 0-100 转化为基础权重 (1.0 -> 2.5)
            weight_cfg['color_weights'] = {d['color']: 1.0 + (d['extremity'] / 100.0) * 1.5 for d in color_data}
            
            # ====== 新增：融合来自路单引擎（150期）观测到的模式波色修正 ======
            if color_momentum_boosts:
                if '红' in weight_cfg['color_weights']: 
                    weight_cfg['color_weights']['红'] *= color_momentum_boosts.get('red', 1.0)
                if '蓝' in weight_cfg['color_weights']: 
                    weight_cfg['color_weights']['蓝'] *= color_momentum_boosts.get('blue', 1.0)
                if '绿' in weight_cfg['color_weights']: 
                    weight_cfg['color_weights']['绿'] *= color_momentum_boosts.get('green', 1.0)

    conn_extra.close()
    return weight_cfg


def _weighted_random_number(weights_config: dict, z_map: dict, is_special: bool = False, exclude_nums: set = None, max_num: int = 49, extra_weights_multiplier: dict = None) -> int:
    """结合走势与生肖权重生成单个号码"""
    candidates = list(range(1, max_num + 1))
    if exclude_nums:
        candidates = [n for n in candidates if n not in exclude_nums]
        
    weights = []
    
    for num in candidates:
        w = 1.0
        
        # 仅对特码应用基于特码统计的维度权重
        if is_special:
            # 叠加大小权
            threshold = 5 if max_num == 8 else 25
            if num >= threshold:
                w *= weights_config.get('big_weight', 1.0)
            else:
                w *= weights_config.get('small_weight', 1.0)
                
            # 叠加单双权
            if num % 2 != 0:
                w *= weights_config.get('odd_weight', 1.0)
            else:
                w *= weights_config.get('even_weight', 1.0)
                
            # 叠加生肖权重 (马尔可夫链)
            if max_num != 8:
                z = z_map.get(num)
                if z and z in weights_config.get('zodiac_weights', {}):
                    w *= weights_config['zodiac_weights'][z]
                    
                # 叠加贝叶斯生肖权重
                if z and z in weights_config.get('bayesian_weights', {}):
                    w *= weights_config['bayesian_weights'][z]
                    
                # 叠加 LSTM 生肖权重
                if z and z in weights_config.get('lstm_weights', {}):
                    w *= weights_config['lstm_weights'][z]
                    
                # 叠加路单拐点生肖权重
                if z and z in weights_config.get('consecutive_weights', {}):
                    w *= weights_config['consecutive_weights'][z]
            
            # 叠加尾数权重
            tail = num % 10
            if tail in weights_config.get('tail_weights', {}):
                w *= weights_config['tail_weights'][tail]
                
            # 叠加波色权重
            if max_num != 8 and 'color_weights' in weights_config:
                color = get_color(num)  # 来自 modules.constants
                if color and color != '未知' and color in weights_config['color_weights']:
                    w *= weights_config['color_weights'][color]
                    
        # 威力彩一区正码 (max_num == 38)
        if max_num == 38 and not is_special:
            # 叠加马尔可夫号码权重
            for key in ['zodiac_weights', 'markov_weights']:
                weights_dict = weights_config.get(key, {})
                if num in weights_dict:
                    w *= weights_dict[num]
                elif str(num) in weights_dict:
                    w *= weights_dict[str(num)]
            # 叠加贝叶斯号码权重
            bayes_dict = weights_config.get('bayesian_weights', {})
            if num in bayes_dict:
                w *= bayes_dict[num]
            elif str(num) in bayes_dict:
                w *= bayes_dict[str(num)]
            # 叠加 LSTM 号码权重
            lstm_dict = weights_config.get('lstm_weights', {})
            if num in lstm_dict:
                w *= lstm_dict[num]
            elif str(num) in lstm_dict:
                w *= lstm_dict[str(num)]
            # 叠加路单和值拐点号码权重
            cons_dict = weights_config.get('consecutive_weights', {})
            if num in cons_dict:
                w *= cons_dict[num]
            elif str(num) in cons_dict:
                w *= cons_dict[str(num)]
                
        # 冷热权重
        hc_weights = {}
        if max_num == 38:
            hc_weights = weights_config.get('hot_cold_weights_z1', {})
        elif max_num == 8:
            hc_weights = weights_config.get('hot_cold_weights_z2', {})
        else:
            hc_weights = weights_config.get('hot_cold_weights', {})
            
        if num in hc_weights:
            w *= hc_weights[num]
            
        if extra_weights_multiplier and num in extra_weights_multiplier:
            w *= extra_weights_multiplier[num]
            
        weights.append(w)
        
    return _secure_random.choices(candidates, weights=weights, k=1)[0]


def build_cooccurrence_matrix(df, max_num: int, cols: list) -> dict:
    import numpy as np

    matrix = defaultdict(lambda: defaultdict(int))
    if df.empty or not set(cols).issubset(df.columns):
        return matrix

    arr = df[cols].values.astype(int)
    for row in arr:
        unique_nums = set(row)
        for n1 in unique_nums:
            if n1 < 1 or n1 > max_num:
                continue
            for n2 in unique_nums:
                if n2 < 1 or n2 > max_num or n1 == n2:
                    continue
                matrix[n1][n2] += 1

    return matrix


def simulate_single(lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """
    带智能趋势及多维加权的模拟开奖
    dimensions: 启用的加权维度列表
    """
    import pandas as pd
    from modules.statistics_engine import calculate_omission_thresholds
    from modules.data_processor import load_data, clean_data

    weights_config = _calculate_trend_weights(lottery_type, dimensions)
    z_map = get_zodiac_mapping(lottery_type)
    
    max_regular = 38 if lottery_type == 'weilitsai' else 49
    max_special = 8 if lottery_type == 'weilitsai' else 49

    # Pre-calculate omissions and markov clustering based on history
    df = clean_data(load_data(lottery_type))
    cooccurrence = defaultdict(lambda: defaultdict(int))
    
    if not df.empty:
        # Build Omission Boost
        if lottery_type == 'weilitsai':
            # === 威力彩 Zone 1 (第一区 1-38) 遗漏预警加权 ===
            omissions_z1 = calculate_omission_thresholds(df, lottery_type, zone=1)
            for num, data in omissions_z1.items():
                if data['is_alert']:
                    if 'hot_cold_weights_z1' not in weights_config:
                        weights_config['hot_cold_weights_z1'] = {}
                    weights_config['hot_cold_weights_z1'][num] = weights_config['hot_cold_weights_z1'].get(num, 1.0) * 3.0
            
            # === 威力彩 Zone 2 (第二区 1-8) 遗漏预警加权 ===
            omissions_z2 = calculate_omission_thresholds(df, lottery_type, zone=2)
            for num, data in omissions_z2.items():
                if data['is_alert']:
                    if 'hot_cold_weights_z2' not in weights_config:
                        weights_config['hot_cold_weights_z2'] = {}
                    weights_config['hot_cold_weights_z2'][num] = weights_config['hot_cold_weights_z2'].get(num, 1.0) * 3.0
        else:
            # 六合彩默认遗漏预警加权
            omissions = calculate_omission_thresholds(df, lottery_type, zone=1)
            for num, data in omissions.items():
                if data['is_alert']:
                    if 'hot_cold_weights' not in weights_config:
                        weights_config['hot_cold_weights'] = {}
                    weights_config['hot_cold_weights'][num] = weights_config['hot_cold_weights'].get(num, 1.0) * 3.0
                
        # Build Co-occurrence matrix from recent draws
        df_recent = df.head(500)
        cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']
        cooccurrence = build_cooccurrence_matrix(df_recent, max_regular, cols)

    # === 威力彩高级推算 6 码动态数据池初始化 ===
    hot_pool = set()
    cold_pool = set()
    warm_pool = set()
    has_tri_state = False

    repeat_pool = set()
    neighbor_pool = set()
    has_repeat_neighbor = False

    if lottery_type == 'weilitsai' and not df.empty:
        # 1. 动态冷温热三态池划分 (近100期一区正码频次)
        from collections import Counter
        df_100 = df.head(100)
        freq = Counter()
        for _, row in df_100.iterrows():
            for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
                val = row.get(col)
                if pd.notna(val):
                    freq[int(val)] += 1
        
        all_nums = list(range(1, 39))
        for n in all_nums:
            if n not in freq:
                freq[n] = 0
                
        sorted_by_freq = sorted(all_nums, key=lambda x: freq[x], reverse=True)
        hot_pool = set(sorted_by_freq[:12])   # 出现最多 30% 左右
        cold_pool = set(sorted_by_freq[26:])  # 出现最少 30% 左右
        warm_pool = set(sorted_by_freq[12:26]) # 中间 40%
        has_tri_state = True

        # 2. 上期重庄号/斜连邻号分析
        last_row = df.iloc[0]
        last_nums = []
        for col in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6']:
            val = last_row.get(col)
            if pd.notna(val):
                last_nums.append(int(val))
        if len(last_nums) == 6:
            repeat_pool = set(last_nums)
            for n in last_nums:
                for delta in [-1, 1]:
                    neighbor_num = n + delta
                    if 1 <= neighbor_num <= 38 and neighbor_num not in repeat_pool:
                        neighbor_pool.add(neighbor_num)
            has_repeat_neighbor = True

    attempts = 0
    max_attempts = 100
    
    while attempts < max_attempts:
        numbers_set = set()
        attempts += 1
        
        # 1. Pick Core Number (对邻号应用 1.5 倍倾向加权)
        initial_multiplier = {}
        if has_repeat_neighbor:
            for n_num in neighbor_pool:
                initial_multiplier[n_num] = 1.5
                
        core_num = _weighted_random_number(weights_config, z_map, is_special=False, exclude_nums=numbers_set, max_num=max_regular, extra_weights_multiplier=initial_multiplier)
        numbers_set.add(core_num)
        
        # 2. Build clustering multiplier based on core number
        cluster_multiplier = {}
        if core_num in cooccurrence:
            for n2, count in cooccurrence[core_num].items():
                if count > 0:
                    cluster_multiplier[n2] = 1.0 + (count * 0.5) # Boost related numbers
                    
        # 合并邻近号加权因子
        if has_repeat_neighbor:
            for n_num in neighbor_pool:
                cluster_multiplier[n_num] = cluster_multiplier.get(n_num, 1.0) * 1.5
                
        # 3. Pick remaining numbers
        while len(numbers_set) < 6:
            num = _weighted_random_number(weights_config, z_map, is_special=False, exclude_nums=numbers_set, max_num=max_regular, extra_weights_multiplier=cluster_multiplier)
            numbers_set.add(num)
            
        # 4. Multi-dimensional constraints check
        odds = sum(1 for x in numbers_set if x % 2 != 0)
        sorted_numbers = sorted(list(numbers_set))
        
        if lottery_type == 'weilitsai':
            bigs = sum(1 for x in sorted_numbers if x >= 19)
            
            # 基础奇偶与大小比过滤 (始终生效)
            if odds not in [2, 3, 4] or bigs not in [2, 3, 4]:
                continue
                
            # AC值计算
            diffs = set()
            for i in range(len(sorted_numbers)):
                for j in range(i + 1, len(sorted_numbers)):
                    diffs.add(abs(sorted_numbers[i] - sorted_numbers[j]))
            ac_value = len(diffs) - 5
            
            # 和值计算
            sum_value = sum(sorted_numbers)
            
            # 阶段三兜底：尝试次数 >= 70 次，放过所有其它高级约束以保证 100% 成功率
            if attempts >= 70:
                break
                
            # 阶段二兜底：尝试 40 - 70 次，加开 AC值 & 和值校验
            if attempts >= 40:
                if ac_value >= 4 and 85 <= sum_value <= 145:
                    break
                continue
                
            # 阶段一严格过滤：尝试次数 < 40 次，必须通过 AC值、和值、冷温热、重邻号全校验
            if ac_value < 4 or not (85 <= sum_value <= 145):
                continue
                
            # 动态冷温热三态分布校验
            if has_tri_state:
                hot_cnt = sum(1 for x in sorted_numbers if x in hot_pool)
                warm_cnt = sum(1 for x in sorted_numbers if x in warm_pool)
                cold_cnt = sum(1 for x in sorted_numbers if x in cold_pool)
                if not (2 <= hot_cnt <= 3 and 2 <= warm_cnt <= 3 and 0 <= cold_cnt <= 2):
                    continue
                    
            # 重号与斜连邻号分布校验
            if has_repeat_neighbor:
                repeat_cnt = sum(1 for x in sorted_numbers if x in repeat_pool)
                neighbor_cnt = sum(1 for x in sorted_numbers if x in neighbor_pool)
                if not (0 <= repeat_cnt <= 2 and 1 <= neighbor_cnt <= 3):
                    continue
                    
            break
        else:
            if odds in [2, 3, 4]:
                break # Valid ratio for Mark Six
            
    numbers = sorted(list(numbers_set))
    
    exclude_special = numbers_set if lottery_type != 'weilitsai' else None
    
    # 特码应用全部图表与趋势权重，并排除已抽出的正码
    special_num = _weighted_random_number(weights_config, z_map, is_special=True, exclude_nums=exclude_special, max_num=max_special)
    
    return {
        'numbers': numbers,
        'zodiacs': [z_map.get(n, '') for n in numbers] if lottery_type != 'weilitsai' else [],
        'special_num': special_num,
        'special_zodiac': z_map.get(special_num, '') if lottery_type != 'weilitsai' else ''
    }


def simulate_batch(count: int = 10, lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """
    批量模拟多期智能开奖
    dimensions: 启用的加权维度列表
    """
    count = min(count, 1000)
    count = max(count, 1)
    
    draws = []
    
    for _ in range(count):
        # We now reuse the intelligent simulate_single to benefit from constraints & clustering
        result = simulate_single(lottery_type, dimensions)
        draws.append(result)

        
    # 统计分析
    all_numbers = []
    special_nums = []
    special_zodiacs = []
    
    odd_count = 0
    even_count = 0
    big_count = 0
    small_count = 0
    
    for draw in draws:
        all_numbers.extend(draw['numbers'])
        special_nums.append(draw['special_num'])
        special_zodiacs.append(draw['special_zodiac'])
        
        # 统计大小单双
        if draw['special_num'] % 2 != 0:
            odd_count += 1
        else:
            even_count += 1
        
        sp_bs = 5 if lottery_type == 'weilitsai' else 25
        if draw['special_num'] >= sp_bs:
            big_count += 1
        else:
            small_count += 1
            
    number_counts = Counter(all_numbers)
    special_counts = Counter(special_nums)
    zodiac_counts = Counter(special_zodiacs)
    
    summary = {
        'total_draws': count,
        'hot_numbers': [num for num, _ in number_counts.most_common(5)],
        'cold_numbers': [num for num, _ in number_counts.most_common()[-5:]],
        'odd_even_ratio': f"{odd_count}:{even_count}",
        'big_small_ratio': f"{big_count}:{small_count}",
        'hot_special_zodiacs': [z for z, _ in zodiac_counts.most_common(3)]
    }
    
    return {
        'draws': draws,
        'summary': summary
    }
