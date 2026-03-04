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
from datetime import datetime
from modules.data_processor import get_db_connection
from modules.logger import get_logger
from collections import Counter

logger = get_logger()

# 使用 secrets.SystemRandom 作为加密级随机数生成器
_secure_random = secrets.SystemRandom()

# 创建不验证证书的 SSL 上下文（解决部分环境 SSL 握手失败问题）
ssl_context = ssl.create_default_context()
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


def get_zodiac_mapping(lottery_type: str = 'macaujc') -> dict:
    """
    2026年（马年）1-49 号码 -> 生肖 映射字典
    直接硬编码，不依赖数据库的 zodiac 文本字段（避免繁简体不匹配）
    返回: {number(int): zodiac(str)}
    """
    zodiac_nums = {
        "马": [1, 13, 25, 37, 49],
        "蛇": [2, 14, 26, 38],
        "龙": [3, 15, 27, 39],
        "兔": [4, 16, 28, 40],
        "虎": [5, 17, 29, 41],
        "牛": [6, 18, 30, 42],
        "鼠": [7, 19, 31, 43],
        "猪": [8, 20, 32, 44],
        "狗": [9, 21, 33, 45],
        "鸡": [10, 22, 34, 46],
        "猴": [11, 23, 35, 47],
        "羊": [12, 24, 36, 48],
    }
    mapping = {}
    for zodiac_name, nums in zodiac_nums.items():
        for n in nums:
            mapping[n] = zodiac_name
    return mapping


def _build_markov_transition_weights(conn, lottery_type: str, z_map: dict, max_periods: int = 0) -> dict:
    """
    基于全量历史数据构建马尔可夫链状态转移矩阵。
    统计相邻两期特码生肖的转移频次，结合当前最新特码生肖，推算其转移到下一个生肖的条件概率权重。
    返回: {zodiac_name: weight_float}
    """
    # 按时间正序拉取全量或指定期数的特码数字
    limit_clause = f"LIMIT {max_periods}" if max_periods > 0 else ""
    query = f"SELECT special_num FROM (SELECT special_num, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC {limit_clause}) ORDER BY draw_date ASC, draw_number ASC"
    
    rows = conn.execute(query, (lottery_type,)).fetchall()
    
    zodiac_order = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
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
    limit_clause = f"LIMIT {max_periods}" if max_periods > 0 else ""
    query = f"SELECT special_num FROM (SELECT special_num, draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC {limit_clause}) ORDER BY draw_date ASC, draw_number ASC"
    rows = conn.execute(query, (lottery_type,)).fetchall()
    
    color_order = ["红波", "蓝波", "绿波"]
    default_weights = {c: 1.0 for c in color_order}
    if not rows or len(rows) < 2:
        return default_weights

    # 红蓝绿波色判断
    def get_color(num):
        red = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
        blue = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
        green = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}
        if num in red: return "红波"
        if num in blue: return "蓝波"
        if num in green: return "绿波"
        return None

    # 初始化 3x3 转移矩阵
    transition_matrix = {c1: {c2: 0 for c2 in color_order} for c1 in color_order}

    # 构建有效的波色序列
    c_seq = []
    for r in rows:
        try:
            num = int(r[0])
            c = get_color(num)
            if c:
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
    periods_cfg = get_chart_periods()
    
    conn = get_db_connection()
    
    # 获取最近 10 期计算大小单双长龙
    rows_10 = conn.execute(
        "SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT 10",
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
    
    weight_cfg = {
        'big_weight': 1.0, 'small_weight': 1.0, 
        'odd_weight': 1.0, 'even_weight': 1.0,
        'zodiac_weights': {},
        'hot_cold_weights': {},  # {号码: 权重}
        'tail_weights': {}       # {尾数: 权重}
    }
    
    if rows_10:
        special_nums = [r[0] for r in rows_10]
        consecutive_big, consecutive_small = 0, 0
        consecutive_odd, consecutive_even = 0, 0
        
        # 统计连大连小
        for num in special_nums:
            if num >= 25:
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
                
        # ======== 新增：识别交替单跳 (大-小-大-小 或 单-双-单-双) ========
        def _get_alternating_jumps(nums, check_func):
            """计算单跳(一十一负)的连续次数。check_func返回bool"""
            jumps = 0
            if len(nums) < 2: return 0
            
            # 从最近一期往前看，必须是 A-B-A-B 形式才算单跳
            current_state = check_func(nums[0])
            for i in range(1, len(nums)):
                prev_state = check_func(nums[i])
                if current_state != prev_state:
                    jumps += 1
                    current_state = prev_state
                else:
                    # 只要出现连庄（非交替），单跳就此断掉
                    break
            return jumps
            
        bs_jumps = _get_alternating_jumps(special_nums, lambda n: n >= 25)
        oe_jumps = _get_alternating_jumps(special_nums, lambda n: n % 2 != 0)
                
        # 均值回归策略（强化版）：连出补偿与单跳防跳补偿
        def _get_regression_weight(consecutive_count, is_alternating_jump=False, jumps_count=0):
            # 基础连出断龙补偿
            weight = 1.0
            if consecutive_count <= 2:
                weight = 1.0 + (consecutive_count * 0.2)
            elif consecutive_count == 3:
                weight = 2.5
            elif consecutive_count >= 4:
                weight = 4.0 + (consecutive_count - 4) * 1.5
                
            # 若处于高频单跳状态（例如：大小大大，已经跳了3次或以上）
            # 则"防跳"权重猛增（即押注它会连庄，打断交替）
            if is_alternating_jump and jumps_count >= 3:
                # jumps_count 越大，越倾向于它停止跳。
                # 由于这是应用在"上期开出属性"上的方法：
                # 假设上期大，如果防跳，那这期必定也是大（连庄打断）。
                # 所以我们给予上期同样属性一个成倍放大的权重。
                return weight + (jumps_count * 1.0)
                
            return weight
                
        if 'big_small' in dimensions:
            last_is_big = special_nums[0] >= 25 if special_nums else False
            # 对于【大】的权重：
            # 若长龙连小，大应该爆发；若正在单跳且前一期是【大】，大也应该爆发（防跳即连庄）。
            weight_cfg['big_weight'] = _get_regression_weight(consecutive_small, last_is_big, bs_jumps)
            weight_cfg['small_weight'] = _get_regression_weight(consecutive_big, not last_is_big, bs_jumps)
            
        if 'odd_even' in dimensions:
            last_is_odd = special_nums[0] % 2 != 0 if special_nums else False
            weight_cfg['odd_weight'] = _get_regression_weight(consecutive_even, last_is_odd, oe_jumps)
            weight_cfg['even_weight'] = _get_regression_weight(consecutive_odd, not last_is_odd, oe_jumps)

    # ====== 修改：生肖马尔可夫链状态转移推演 ======
    if 'markov' in dimensions:
        z_map = get_zodiac_mapping(lottery_type)
        markov_p = periods_cfg.get('markov', 0)
        weight_cfg['zodiac_weights'] = _build_markov_transition_weights(conn_extra, lottery_type, z_map, markov_p)

    # ====== 修改：冷热频率完全特码化 ======
    if 'hot_cold' in dimensions:
        hc_p = periods_cfg.get('hot_cold', 100)
        rows_hc = conn_extra.execute(
            f"SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT {hc_p}",
            (lottery_type,)
        ).fetchall()
        if rows_hc:
            num_freq = Counter()
            for row in rows_hc:
                n = row[0]
                if 1 <= n <= 49:
                    num_freq[n] += 1
            avg_freq = sum(num_freq.values()) / 49 if num_freq else 1
            for n in range(1, 50):
                f = num_freq.get(n, 0)
                # 均值回归：冷号加权，热号轻微加权
                if avg_freq > 0:
                    ratio = f / avg_freq
                    if ratio < 0.5:
                        weight_cfg['hot_cold_weights'][n] = 1.6  # 极冷号大幅提权
                    elif ratio < 0.8:
                        weight_cfg['hot_cold_weights'][n] = 1.3  # 冷号适度提权
                    elif ratio > 1.5:
                        weight_cfg['hot_cold_weights'][n] = 0.85 # 极热号轻微降权
                    else:
                        weight_cfg['hot_cold_weights'][n] = 1.0 + (ratio - 1) * 0.15

    # ====== 新增：尾数分布加权 ======
    if 'tail' in dimensions:
        tail_p = periods_cfg.get('tail', 50)
        rows_tail = conn_extra.execute(
            f"SELECT special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT {tail_p}",
            (lottery_type,)
        ).fetchall()
        if rows_tail:
            tail_freq = Counter()
            for r in rows_tail:
                tail_freq[r[0] % 10] += 1
            avg_tail = sum(tail_freq.values()) / 10 if tail_freq else 1
            for tail in range(10):
                f = tail_freq.get(tail, 0)
                if avg_tail > 0:
                    ratio = f / avg_tail
                    if ratio < 0.6:
                        weight_cfg['tail_weights'][tail] = 1.4
                    elif ratio > 1.4:
                        weight_cfg['tail_weights'][tail] = 0.85
                    else:
                        weight_cfg['tail_weights'][tail] = 1.0

    # ====== 新增：深层算法 (连涨拐点, 贝叶斯与 LSTM, 波色极值) 直接调用 engine.py 免得重复写 ======
    if any(k in dimensions for k in ('bayesian', 'lstm', 'consecutive', 'color')):
        import pandas as pd
        from modules.statistics_engine import bayesian_inference, lstm_simulation, zodiac_momentum_analysis, color_hot_cold_analysis, get_zodiac_mapping as ge_z
        z_map_local = ge_z(lottery_type)
        df_all = pd.read_sql_query(f"SELECT special_num FROM lottery_history WHERE lottery_type='{lottery_type}' ORDER BY draw_date DESC, draw_number DESC LIMIT 200", conn_extra)
        
        if 'bayesian' in dimensions:
            b_data = bayesian_inference(df_all, z_map_local, periods_cfg.get('bayesian', 100))
            # b_data: [{'zodiac': '鼠', 'posterior': 35.6}, ...]
            # 取极大值归一化，基础权重为1.0
            max_p = max([d['posterior'] for d in b_data]) if b_data else 1
            weight_cfg['bayesian_weights'] = {d['zodiac']: 1.0 + (d['posterior'] / max_p)*0.8 for d in b_data} if max_p > 0 else {}
            
        if 'lstm' in dimensions:
            l_data = lstm_simulation(df_all, z_map_local, periods_cfg.get('lstm', 100))
            # score 0-100
            weight_cfg['lstm_weights'] = {d['zodiac']: 0.5 + (d['score']/100)*1.0 for d in l_data}
            
        if 'consecutive' in dimensions:
            c_data = zodiac_momentum_analysis(df_all, z_map_local)
            rev_prob = c_data.get('reversal_probability', 0)
            if rev_prob >= 50:
                cw = {}
                target_dir = c_data.get('reversal_target_direction', 'none')
                z_order = c_data.get('zodiac_order', [])
                current_y = c_data.get('current_y', -1)
                if current_y != -1 and target_dir != 'none':
                    for i, z in enumerate(z_order):
                        if target_dir == 'down' and i < current_y:
                            cw[z] = 1.0 + (rev_prob / 100.0) * 1.5
                        elif target_dir == 'up' and i > current_y:
                            cw[z] = 1.0 + (rev_prob / 100.0) * 1.5
                weight_cfg['consecutive_weights'] = cw

        if 'color' in dimensions:
            color_data = color_hot_cold_analysis(df_all, periods_cfg.get('hot_cold', 100))
            # 极端度 0-100 转化为权重 (1.0 -> 2.5)
            weight_cfg['color_weights'] = {d['color']: 1.0 + (d['extremity'] / 100.0) * 1.5 for d in color_data}

    conn_extra.close()
    return weight_cfg


def _weighted_random_number(weights_config: dict, z_map: dict, is_special: bool = False) -> int:
    """结合走势与生肖权重生成单个号码（1-49）"""
    candidates = list(range(1, 50))
    weights = []
    
    for num in candidates:
        w = 1.0
        
        # 仅对特码应用基于特码统计的维度权重
        if is_special:
            # 叠加大小权
            if num >= 25:
                w *= weights_config.get('big_weight', 1.0)
            else:
                w *= weights_config.get('small_weight', 1.0)
                
            # 叠加单双权
            if num % 2 != 0:
                w *= weights_config.get('odd_weight', 1.0)
            else:
                w *= weights_config.get('even_weight', 1.0)
                
            # 叠加生肖权重 (马尔可夫链)
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
            if 'color_weights' in weights_config:
                color = None
                red = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
                blue = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
                green = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}
                if num in red: color = '红波'
                elif num in blue: color = '蓝波'
                elif num in green: color = '绿波'
                if color and color in weights_config['color_weights']:
                    w *= weights_config['color_weights'][color]
                
        # 冷热权重（现在变为仅针对特码有效）
        if is_special and num in weights_config.get('hot_cold_weights', {}):
            w *= weights_config['hot_cold_weights'][num]
            
        weights.append(w)
        
    return _secure_random.choices(candidates, weights=weights, k=1)[0]


def simulate_single(lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """
    带智能趋势及多维加权的模拟开奖
    dimensions: 启用的加权维度列表
    """
    weights_config = _calculate_trend_weights(lottery_type, dimensions)
    z_map = get_zodiac_mapping(lottery_type)
    
    numbers_set = set()
    while len(numbers_set) < 6:
        # 正码不仅应用冷热权重，还要确保不重复（在实际开奖中，同一期正码不重复）
        num = _weighted_random_number(weights_config, z_map, is_special=False)
        numbers_set.add(num)
        
    numbers = sorted(list(numbers_set))
    # 特码应用全部维度权重
    special_num = _weighted_random_number(weights_config, z_map, is_special=True)
    
    return {
        'numbers': numbers,
        'zodiacs': [z_map[n] for n in numbers],
        'special_num': special_num,
        'special_zodiac': z_map[special_num]
    }


def simulate_batch(count: int = 10, lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """
    批量模拟多期智能开奖
    dimensions: 启用的加权维度列表
    """
    count = min(count, 1000)
    count = max(count, 1)
    
    draws = []
    
    weights_config = _calculate_trend_weights(lottery_type, dimensions)
    z_map = get_zodiac_mapping(lottery_type)
    
    for _ in range(count):
        numbers_set = set()
        while len(numbers_set) < 6:
            numbers_set.add(_weighted_random_number(weights_config, z_map, is_special=False))
            
        numbers = sorted(list(numbers_set))
        special_num = _weighted_random_number(weights_config, z_map, is_special=True)
        
        draws.append({
            'numbers': numbers,
            'zodiacs': [z_map[n] for n in numbers],
            'special_num': special_num,
            'special_zodiac': z_map[special_num]
        })
        
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
        
        if draw['special_num'] >= 25:
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
