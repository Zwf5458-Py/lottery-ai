"""
AI 分析引擎
功能：集成 Google Gemini API，基于多维统计数据进行智能分析。
维度过滤：只将用户勾选的加权维度数据送入 Prompt，避免无关分析。
"""

import json
import os

# Gemini API Key — 从配置中心读取，环境变量优先
def _get_ai_config():
    from modules.config_manager import get_ai_config
    return get_ai_config()


def analyze_with_ai(stats_summary: dict, lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """
    使用 Gemini AI 分析统计数据并给出推荐号码
    
    参数:
        stats_summary: 统计引擎的全部分析结果
        lottery_type: 彩种
        dimensions: 用户勾选的加权维度列表
    返回:
        {'numbers': [6个正码], 'special_num': 特码, 'analysis': '分析理由', 'success': bool}
    """
    if dimensions is None:
        dimensions = ['big_small', 'odd_even', 'hot_cold', 'tail', 'zodiac']
    
    try:
        from google import genai
        
        ai_cfg = _get_ai_config()
        api_key = os.environ.get('GEMINI_API_KEY') or ai_cfg.get('api_key', '')
        model_name = ai_cfg.get('model', 'gemini-2.5-pro')
        
        if not api_key:
            raise ValueError("未配置 API Key，请在设置面板中填写")
        
        client = genai.Client(api_key=api_key)
        
        # 构建结构化 Prompt（仅包含勾选的维度）
        prompt = _build_analysis_prompt(stats_summary, lottery_type, dimensions)
        
        # 尝试生成综合多模态大屏图表附件（含大小/单双/贝叶斯/马尔可夫/生肖路单）
        contents = [prompt]
        try:
            from modules.chart_generator import generate_comprehensive_dashboard_bytes
            from modules.data_processor import get_db_connection
            from modules.statistics_engine import get_zodiac_mapping
            import pandas as pd
            
            # 读取历史数据给 chart generator
            conn = get_db_connection()
            df = pd.read_sql_query(f"SELECT draw_number, special_num FROM lottery_history WHERE lottery_type='{lottery_type}' ORDER BY draw_date DESC, draw_number DESC LIMIT 300", conn)
            conn.close()
            z_map = get_zodiac_mapping(lottery_type)
            
            # 根据用户勾选的维度动态生成图片（只显示勾选的维度图表）
            img_bytes = generate_comprehensive_dashboard_bytes(stats_summary, df, z_map, dimensions)
            if img_bytes:
                from google.genai import types
                contents = [
                    types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                    prompt
                ]
        except Exception as e:
            print(f"生成或附加包含图片的 Prompt 失败: {e}")
            pass
        
        print(f"💡 正在发送带有多模态图表的推测请求给 Gemini ({model_name})...")
        import time
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={
                        'response_mime_type': 'application/json',
                        'temperature': 0.7,
                    }
                )
                break  # 成功则跳出循环
            except Exception as e:
                err_msg = str(e).lower()
                # 判断是否是 503 或资源不足的高并发错误
                if '503' in err_msg or 'high deman' in err_msg or 'unavailable' in err_msg or 'resource' in err_msg:
                    if attempt < max_retries:
                        print(f"⚠️ {model_name} 接口繁忙 (503/High Demand)，正在进行重试和降级 ({attempt+1}/{max_retries})...")
                        time.sleep(2)
                        # 如果是较新的实验模型出现高并发，降级到最稳定的 2.5-pro 或者 flash
                        if '3.1' in model_name or '3.0' in model_name or 'preview' in model_name or 'exp' in model_name:
                            print("🔄 自动降级到更稳定的 gemini-2.5-pro 模型...")
                            model_name = 'gemini-2.5-pro'
                        continue
                raise e # 非重试错误直接抛出
        
        # 解析 AI 返回
        result = json.loads(response.text)
        
        # 校验号码范围
        numbers = [int(n) for n in result.get('numbers', [])]
        special = int(result.get('special_num', 1))
        numbers = [max(1, min(49, n)) for n in numbers][:6]
        special = max(1, min(49, special))
        
        # 确保正码不重复
        seen = set()
        unique_numbers = []
        for n in numbers:
            if n not in seen:
                seen.add(n)
                unique_numbers.append(n)
        while len(unique_numbers) < 6:
            for i in range(1, 50):
                if i not in seen:
                    unique_numbers.append(i)
                    seen.add(i)
                    break
        
        return {
            'success': True,
            'numbers': sorted(unique_numbers[:6]),
            'special_num': special,
            'analysis': result.get('analysis', 'AI 分析完成'),
            'confidence': result.get('confidence', '中等')
        }
        
    except ImportError:
        return _fallback_result('google-genai 库未安装，已降级为传统加权模式')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _fallback_result(f'AI 分析异常 ({type(e).__name__}: {str(e)[:100]})，已降级为传统加权模式')


def analyze_zodiac_with_ai(stats_summary: dict, lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """
    使用 Gemini AI 专门推算下期特码的生肖（不推算具体号码）
    返回: {'success': bool, 'zodiac_predictions': [...], 'analysis': str, 'confidence': str}
    """
    if dimensions is None:
        dimensions = ['markov', 'consecutive', 'bayesian', 'lstm']
    
    try:
        from google import genai
        
        ai_cfg = _get_ai_config()
        api_key = os.environ.get('GEMINI_API_KEY') or ai_cfg.get('api_key', '')
        model_name = ai_cfg.get('model', 'gemini-2.5-pro')
        
        if not api_key:
            raise ValueError("未配置 API Key，请在设置面板中填写")
        
        client = genai.Client(api_key=api_key)
        
        # 构建生肖专属 Prompt
        prompt = _build_zodiac_prompt(stats_summary, lottery_type, dimensions)
        
        # 尝试生成综合多模态大屏图表附件（含大小/单双/贝叶斯/马尔可夫/生肖路单）
        contents = [prompt]
        try:
            from modules.chart_generator import generate_comprehensive_dashboard_bytes
            from modules.data_processor import get_db_connection
            from modules.statistics_engine import get_zodiac_mapping
            import pandas as pd
            
            # 读取历史数据给 chart generator
            conn = get_db_connection()
            df = pd.read_sql_query(f"SELECT draw_number, special_num FROM lottery_history WHERE lottery_type='{lottery_type}' ORDER BY draw_date DESC, draw_number DESC LIMIT 300", conn)
            conn.close()
            z_map = get_zodiac_mapping(lottery_type)
            
            # 根据用户勾选的维度动态生成图片（只显示勾选的维度图表）
            img_bytes = generate_comprehensive_dashboard_bytes(stats_summary, df, z_map, dimensions)
            if img_bytes:
                from google.genai import types
                contents = [
                    types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                    prompt
                ]
        except Exception as e:
            print(f"生成或附加包含图片的 Prompt 失败: {e}")
            pass
        
        print(f"💡 正在发送带有多模态图表的推测请求给 Gemini ({model_name})...")
        import time
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={
                        'response_mime_type': 'application/json',
                        'temperature': 0.7,
                    }
                )
                break
            except Exception as e:
                err_msg = str(e).lower()
                if '503' in err_msg or 'high deman' in err_msg or 'unavailable' in err_msg or 'resource' in err_msg:
                    if attempt < max_retries:
                        print(f"⚠️ {model_name} 接口繁忙 (503/High Demand)，正在进行重试和降级 ({attempt+1}/{max_retries})...")
                        time.sleep(2)
                        if '3.1' in model_name or '3.0' in model_name or 'preview' in model_name or 'exp' in model_name:
                            print("🔄 自动降级到更稳定的 gemini-2.5-pro 模型...")
                            model_name = 'gemini-2.5-pro'
                        continue
                raise e
        
        result = json.loads(response.text)
        
        # 校验生肖有效性
        valid_zodiacs = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
        predictions = result.get('zodiac_predictions', [])
        valid_predictions = [p for p in predictions if p.get('zodiac') in valid_zodiacs]
        
        return {
            'success': True,
            'zodiac_predictions': valid_predictions[:5],
            'analysis': result.get('analysis', 'AI 生肖推算完成'),
            'confidence': result.get('confidence', '中等')
        }
        
    except ImportError:
        return _fallback_zodiac('google-genai 库未安装')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _fallback_zodiac(f'AI 分析异常 ({type(e).__name__}: {str(e)[:100]})')


def _build_zodiac_prompt(stats: dict, lottery_type: str, dimensions: list) -> str:
    """构建生肖专属推算 Prompt"""
    type_name = '新澳门六合彩' if lottery_type == 'macaujc2' else '澳门六合彩'
    
    # 收集所有生肖相关的维度数据
    sections = []
    
    # 基础生肖走势数据（永远提供）
    try:
        zs = stats.get('zodiac_stats', {})
        if isinstance(zs, dict) and 'draws' in zs:
            draws = zs.get('draws', [])[-100:]  # 扩大为最近100期
            zodiac_order = zs.get('zodiac_order', [])
            z_lines = []
            for d in draws:
                z_name = zodiac_order[d['zodiac_idx']] if d['zodiac_idx'] < len(zodiac_order) else '?'
                z_lines.append(f"{d['draw_number']}: {d['num']}号({z_name})")
            if z_lines:
                sections.append(f"### 🐾 最近100期特码生肖路单\n" + '\n'.join(z_lines))
    except:
        pass
    
    # 马尔可夫链
    if 'markov' in dimensions:
        try:
            markov = stats.get('markov', {})
            weights = markov.get('weights', {})
            zodiac_names = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
            z_weights = {k: v for k, v in dict(weights).items() if k in zodiac_names}
            if z_weights:
                sorted_z = sorted(z_weights.items(), key=lambda x: x[1], reverse=True)
                top_5 = [f"{z}(跃迁权重{w:.2f})" for z, w in sorted_z[:5]]
                sections.append(f"### 🕸️ 马尔可夫链跃迁概率\n最可能跃迁的前5名: {', '.join(top_5)}")
        except:
            pass
    
    # 路单连涨防跌
    if 'consecutive' in dimensions:
        try:
            cons = stats.get('consecutive', {})
            trend = cons.get('current_trend', 'none')
            count = cons.get('consecutive_count', 0)
            rev_prob = cons.get('reversal_probability', 0)
            target_dir = cons.get('reversal_target_direction', 'none')
            
            if count > 0 and trend != 'flat' and trend != 'none':
                # 状态描述
                if trend == 'jump':
                    dir_chi = "单跳交替(涨跌反复横跳)"
                    target_chi = "打破交替规律(即连庄)"
                else:
                    dir_chi = "向上爬升(开出排位越来越高的生肖)" if trend == 'up' else "向下探底(开出排位越来越低的生肖)"
                    target_chi = "向下回调(应优选图表Y轴排位靠下的生肖，即靠近鼠/牛方向)" if target_dir == 'down' else "向上反弹(应优选图表Y轴排位靠上的生肖，即靠近猪/狗方向)"
                
                # 提取潜在的目标生肖
                z_order = cons.get('zodiac_order', [])
                current_y = cons.get('current_y', -1)
                target_zodiacs = []
                if z_order and current_y != -1:
                    if target_dir == 'down':
                        target_zodiacs = z_order[:current_y]  # 排位比当前低的
                    elif target_dir == 'up':
                        target_zodiacs = z_order[current_y+1:] # 排位比当前高的
                        
                # 针对 jump 模式，目标可能不是按范围取，而是顺应当前步的上或下。
                # 比如上一步是 up，目标是继续 up。这里就直接给比当前高的。
                
                tz_str = f"重点关注反转目标生肖: {', '.join(target_zodiacs)} (注：Y轴排序由下至上为: {', '.join(z_order)})" if target_zodiacs else ""
                
                desc = (
                    f"当前生肖排位路单已连续【{count}】期呈现【{dir_chi}】。\n"
                    f"根据极限回归，下期发生【{target_chi}】的独立概率高达 {rev_prob}%。\n"
                    f"{tz_str}"
                )
                sections.append(f"### 📈 生肖排位路单拐点信号(动量防跳体系)\n{desc}")
        except:
            pass
    
    # 贝叶斯
    if 'bayesian' in dimensions:
        try:
            bayesian = stats.get('bayesian', [])
            if bayesian:
                top_3 = bayesian[:3]
                desc = [
                    f"【{item['zodiac']}】后验权重:{item['posterior']} "
                    f"(当前已连续遗漏 {item['omission']} 期，其实际历史最大连续遗漏为 {item.get('max_omission', '?')} 期，历史平均遗漏 {item.get('avg_omission', '?')} 期)"
                    for item in top_3
                ]
                sections.append(f"### ⚖️ 贝叶斯极值反弹排名\n{chr(10).join(desc)}")
        except:
            pass
    
    # LSTM
    if 'lstm' in dimensions:
        try:
            lstm = stats.get('lstm', [])
            if lstm:
                top_3 = lstm[:3]
                desc = [f"{item['zodiac']}(拟合得分:{item['score']} | 信号:【{item['signal']}】)" for item in top_3]
                sections.append(f"### 🧠 LSTM 时序信号\n{chr(10).join(desc)}")
        except:
            pass
    
    # 最近N期原始特码及生肖序列
    raw_nums = ''
    try:
        from modules.config_manager import get_chart_periods
        from modules.data_processor import get_db_connection
        from modules.statistics_engine import get_zodiac_mapping
        
        z_map = get_zodiac_mapping(lottery_type)
        ai_raw_p = get_chart_periods().get('ai_raw_data', 300)
        conn = get_db_connection()
        rows = conn.execute(
            f"SELECT draw_number, special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT {ai_raw_p}",
            (lottery_type,)
        ).fetchall()
        conn.close()
        if rows:
            rows = list(reversed(rows))
            def _get_color(num):
                red = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
                blue = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
                green = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}
                if num in red: return '红波'
                if num in blue: return '蓝波'
                if num in green: return '绿波'
                return '未知'
            raw_nums = ' → '.join([f"{r[1]}号({_get_color(int(r[1]))}-{z_map.get(int(r[1]), '?')})" for r in rows])
    except:
        pass
    
    data_block = '\n\n'.join(sections)
    
    # 获取严格的生肖映射字典字符串，强制告诉AI
    zmap_text = "【重要系统设定：当前年份2026马年，1-49生肖精确映射】：\n"
    for zname in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']:
        nums = [k for k, v in z_map.items() if v == zname]
        zmap_text += f"{zname}: {nums}；"
    
    prompt = f"""你是一位精通概率论和统计学的生肖命理分析大师。现在请你根据以下"{type_name}"的全部历史走势数据，专门推算下一期特码最可能开出的【生肖】。

⚠️ 核心任务：只推算生肖，不需要推算具体号码。
12 生肖为：鼠、牛、虎、兔、龙、蛇、马、羊、猴、鸡、狗、猪

{zmap_text}

## 最近 {len(rows) if 'rows' in dir() and rows else 300} 期原始特码序列
{raw_nums}

## 多维生肖分析数据

{data_block}

## 推算要求
1. 🛑 极其严格的维度约束：你【必须且只能】分析我提供给你的维度数据。如果某个维度（如单双、大小、冷热）没有在上方的数据区块中出现，你【绝对禁止】在分析中自己凭空捏造或提及。拒绝任何维度的发散和幻觉！
2. 综合以上所有提供的数据，给出你认为下期特码最可能开出的 **前3名生肖**，按概率从高到低排列。
3. 每个生肖给出你的推算理由（30字以内）和一个你估计的概率百分比。
4. 必须在理由中明确体现：路单连涨防跌信号、马尔可夫链跃迁、贝叶斯遗漏反弹、LSTM趋势等数据的直接影响。
5. 🎨 深度观察【色波规律】：请务必仔细观察原始特码序列中的波色跳跃规律（如连续多期蓝波后跳红波）、波色长龙，以及长期遗漏后的反弹概率，并将其作为推理的核心依据之一。
6. 📖 深度长篇推理（建议 800-1500 字）：请不要惜字如金！请极尽详细地阐述你的整个推理传导过程。你需要把每个选用维度（路单防跌、马尔可夫链、波色规律等），特别是图像视觉上的波段涨跌和形态规律，如何影响你的判断、不同指标之间如何互相印证或推翻的过程详尽地写清楚。让整个推算过程像一篇严密且精彩的“破案报告”！
7. 📊 视觉超能力释放：我已在附件中提供了一张近期的【特码生肖走势折线图】。请你发挥视觉模型的多模态超能力，自己用眼睛观察图表中的图形结构（比如头肩顶、双底、波峰波谷的三重对称等），把肉眼看到的周期规律叠加进最终结论中。

请严格以如下 JSON 格式回复：
{{
    "zodiac_predictions": [
        {{"zodiac": "生肖名", "probability": "概率%", "reason": "推算理由"}},
        {{"zodiac": "生肖名", "probability": "概率%", "reason": "推算理由"}},
        {{"zodiac": "生肖名", "probability": "概率%", "reason": "推算理由"}}
    ],
    "analysis": "你的综合推理分析文字",
    "confidence": "高/中/低"
}}"""
    
    return prompt


def _fallback_zodiac(reason: str) -> dict:
    """生肖推算失败的降级返回"""
    return {
        'success': False,
        'zodiac_predictions': [],
        'analysis': reason,
        'confidence': '无'
    }


def _build_analysis_prompt(stats: dict, lottery_type: str, dimensions: list) -> str:
    """
    构建发送给 Gemini 的分析 Prompt。
    只包含用户勾选的维度数据，避免 AI 分析未选维度。
    新增最近 10 期特码明细，让 AI 能精确判断连续走势。
    """
    
    type_name = '新澳门六合彩' if lottery_type == 'macaujc2' else '澳门六合彩'
    dim_names = {
        'big_small': '大小走势',
        'odd_even': '单双走势',
        'hot_cold': '冷热频率',
        'tail': '尾数分布',
        'zodiac': '生肖权重',
        'color': '波色推测'
    }
    active_dims_text = '、'.join([dim_names.get(d, d) for d in dimensions])
    
    # ====== 最近10期特码走势明细（只在勾选大小或单双时才给AI看） ======
    recent_detail = ''
    raw_special_nums = ''  # 最近N期原始特码序列
    try:
        if 'big_small' in dimensions or 'odd_even' in dimensions:
            oe = stats.get('odd_even', {})
            bs = stats.get('big_small', {})
            oe_labels = oe.get('labels', [])
            oe_values = oe.get('values', [])
            bs_values = bs.get('values', [])
            
            # 取最后 20 期走势明细
            n = min(20, len(oe_labels))
            if n > 0:
                lines = []
                for i in range(n):
                    idx = len(oe_labels) - n + i
                    period = oe_labels[idx] if idx < len(oe_labels) else '?'
                    oe_v = oe_values[idx] if idx < len(oe_values) else 0
                    bs_v = bs_values[idx] if idx < len(bs_values) else 0
                    oe_tag = f"奇(连{oe_v})" if oe_v > 0 else f"双(连{abs(oe_v)})"
                    bs_tag = f"大(连{bs_v})" if bs_v > 0 else f"小(连{abs(bs_v)})"
                    lines.append(f"  {period}: {oe_tag}, {bs_tag}")
                recent_detail = f"## 最近 {n} 期特码走势明细\n" + '\n'.join(lines)
        
        # 提取最近N期原始特码数字（用于AI自主观察），默认300期
        from modules.config_manager import get_chart_periods
        ai_raw_p = get_chart_periods().get('ai_raw_data', 300)
        special_freq = stats.get('special_frequency', {})
        # 从数据库直接获取最近N期原始特码
        from modules.data_processor import get_db_connection
        conn = get_db_connection()
        rows = conn.execute(
            f"SELECT draw_number, special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT {ai_raw_p}",
            (lottery_type,)
        ).fetchall()
        conn.close()
        if rows:
            # 时间正序（旧到新）
            rows = list(reversed(rows))
            def _get_color(num):
                red = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
                blue = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
                green = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}
                if num in red: return '红波'
                if num in blue: return '蓝波'
                if num in green: return '绿波'
                return '未知'
            raw_special_nums = ' → '.join([f"{r[1]}号({_get_color(int(r[1]))})" for r in rows])
    except:
        recent_detail = recent_detail or '暂无明细'
        raw_special_nums = '暂无'
    
    # ====== 按维度构建对应数据段 ======
    sections = []
    
    if 'big_small' in dimensions:
        try:
            bs = stats.get('big_small', {})
            total_big = bs.get('total_big', '?')
            total_small = bs.get('total_small', '?')
            vals = bs.get('values', [])
            jumps = bs.get('current_jumps', 0)
            last5 = vals[-5:] if vals else []
            
            # 检测当前连续趋势或单跳交替
            if jumps >= 3:
                trend = f"当前处于高频单跳交替中(已连续交替{jumps}次)，存在极大止跳(连庄)可能"
            elif last5:
                last_v = last5[-1]
                trend = f"当前连续{abs(last_v)}期{'大' if last_v > 0 else '小'}"
            else:
                trend = '无走势数据'
                
            sections.append(f"""### 📊 大小走势（特码，≥25为大，<25为小）
- 近100期统计: 大号 {total_big} 期 | 小号 {total_small} 期
- 最近5期K线值: {last5}
- ⚠️ {trend}""")
        except:
            sections.append("### 📊 大小走势\n暂无数据")
    
    if 'odd_even' in dimensions:
        try:
            oe = stats.get('odd_even', {})
            total_odd = oe.get('total_odd', '?')
            total_even = oe.get('total_even', '?')
            vals = oe.get('values', [])
            jumps = oe.get('current_jumps', 0)
            last5 = vals[-5:] if vals else []
            
            # 检测当前连续趋势或单跳交替
            if jumps >= 3:
                trend = f"当前处于高频单跳交替中(已连续交替{jumps}次)，存在极大止跳(连庄)可能"
            elif last5:
                last_v = last5[-1]
                trend = f"当前连续{abs(last_v)}期{'单(奇数)' if last_v > 0 else '双(偶数)'}"
            else:
                trend = '无走势数据'
                
            sections.append(f"""### 🔢 单双走势（特码）
- 近100期统计: 单(奇) {total_odd} 期 | 双(偶) {total_even} 期
- 最近5期K线值: {last5}
- ⚠️ {trend}""")
        except:
            sections.append("### 🔢 单双走势\n暂无数据")
    
    if 'hot_cold' in dimensions:
        try:
            hot_cold = stats.get('hot_cold', {})
            hot_list = hot_cold.get('hot', [])[:8]
            cold_list = hot_cold.get('cold', [])[:8]
            # hot_cold_numbers 返回格式: [{'number': n, 'count': c}, ...]
            hot_str = ', '.join([f"{h['number']}号({h['count']}次)" for h in hot_list]) if hot_list else '暂无'
            cold_str = ', '.join([f"{c['number']}号({c['count']}次)" for c in cold_list]) if cold_list else '暂无'
            sections.append(f"""### 🔥 冷热频率（特码）
- 最热号码: {hot_str}
- 最冷号码: {cold_str}""")
            # 特码频率
            special_freq = stats.get('special_frequency', {})
            top_sp = sorted(special_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            sp_str = ', '.join([f'{k}号({v}次)' for k, v in top_sp]) if top_sp else '暂无'
            sections.append(f"### 特码频率 TOP10\n{sp_str}")
        except:
            sections.append("### 🔥 冷热频率\n暂无数据")

    if 'color' in dimensions:
        try:
            color_data = stats.get('color_hot_cold', [])
            if color_data:
                desc = []
                for c in color_data:
                    hint = c.get('rebound_hint', '')
                    desc.append(f"【{c['color']}】当前遗漏 {c['current_gap']} 期 (平均遗漏 {c['avg_gap']} 期)。基于几何分布累积概率(CDF)，其遗漏极端度达到 {c['extremity']}%，状态：{hint}")
                sections.append(f"### 🎨 波色冷热与极值反弹推测\n{chr(10).join(desc)}")
        except:
            sections.append("### 🎨 波色推测\n暂无数据")
    
    if 'tail' in dimensions:
        try:
            tail = stats.get('tail_numbers', {})
            tail_str = json.dumps(tail, ensure_ascii=False) if tail else '暂无'
            sections.append(f"### 🎯 尾数分布\n{tail_str}")
        except:
            sections.append("### 🎯 尾数分布\n暂无数据")
    
    # --- 生肖权重与走势 (结合最近 5 期真实开奖分布) ---
    if 'zodiac' in dimensions:
        zodiac_text = "未收集到足够数据"
        z_lines = []
        try:
            # 获取最近5期生肖直观数据
            zs = stats.get('zodiac_stats', {})
            if isinstance(zs, dict) and 'draws' in zs:
                draws = zs.get('draws', [])[-5:]
                zodiac_order = zs.get('zodiac_order', [])
                for d in draws:
                    z_name = zodiac_order[d['zodiac_idx']] if d['zodiac_idx'] < len(zodiac_order) else '?'
                    z_lines.append(f"{d['draw_number']}: {d['num']}号({z_name})")
            recent_z_str = '\n'.join(z_lines) if z_lines else '暂无'
            zodiac_text = f"【最近5期生肖真实走势】:\n{recent_z_str}"
            sections.append(f"### 🐾 基础生肖频率走势\n{zodiac_text}")
        except:
            sections.append("### 🐾 基础生肖频率走势\n暂无数据")

    if 'markov' in dimensions:
        try:
            # 提取马尔可夫链跃迁权重
            weight_cfg = stats.get('markov', {}).get('weights', {})
            markov_str = "暂无"
            if weight_cfg:
                # 过滤出 12 生肖名称及其权重
                zodiac_names = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
                z_weights = {k: v for k, v in dict(weight_cfg).items() if k in zodiac_names}
                
                is_sig = weight_cfg.get('_is_significant', True)
                chi_val = weight_cfg.get('_chi_square_val', 0)
                
                sorted_z = sorted(z_weights.items(), key=lambda x: x[1], reverse=True)
                top_3 = [f"{z}(权重{w:.2f})" for z, w in sorted_z[:3]]
                bottom_3 = [f"{z}(权重{w:.2f})" for z, w in sorted_z[-3:]]
                
                sig_text = f"【显著有效】卡方检验(Chi-Square)显示转移规律明显，远超随机噪音(x²={chi_val})。" if is_sig else f"【噪音警告】卡方检验不显著(x²={chi_val} < 临界值19.675)，历史无明确偏移方向，预测权重已向均值(1.0)收缩，建议勿强信此条规律。"
                
                markov_str = (
                    f"基于全量特码数据的马尔可夫链(Markov Chain)状态转移推演：\n"
                    f" - {sig_text}\n"
                    f" - 最极高概率跃迁目标：{', '.join(top_3)} (指向上期开出后，下期最容易转向的生肖)\n"
                    f" - 最小概率跃迁目标（建议规避）：{', '.join(bottom_3)}\n"
                    f"   [说明：此模型已滤除纯噪音，请重点参考高权重生肖]"
                )
            sections.append(f"### 🕸️ 马尔可夫链生肖转移推演\n{markov_str}")
        except:
            sections.append("### 🕸️ 马尔可夫链生肖转移推演\n暂无数据")

    if 'consecutive' in dimensions:
        try:
            cons = stats.get('consecutive', {})
            trend = cons.get('current_trend', 'none')
            count = cons.get('consecutive_count', 0)
            rev_prob = cons.get('reversal_probability', 0)
            target_dir = cons.get('reversal_target_direction', 'none')
            
            if count > 0 and trend != 'none' and trend != 'flat':
                dir_chi = "向上爬升" if trend == 'up' else "向下探底"
                target_chi = "向下回调(选取排位低于当期的生肖)" if target_dir == 'down' else "向上反弹(选取排位高于当期的生肖)"
                
                desc = (
                    f"- 当期状态：在生肖Y坐标排序(鼠低->猪高)中已连续【{count}】期【{dir_chi}】。\n"
                    f"- 动量反转预警：根据极限回归模型，下期发生图表【{target_chi}】的独立概率高达 {rev_prob}%。\n"
                    f"  [AI行动指南：利用此概率干预生肖选择。若反转概率>70%，务必顺应反转方向选取对应的生肖。注：Y轴排序由下至上为: 鼠, 牛, 虎, 兔, 龙, 蛇, 马, 羊, 猴, 鸡, 狗, 猪]"
                )
                sections.append(f"### 📈 生肖路单拐点预判(连涨防跌体系)\n{desc}")
            else:
                sections.append("### 📈 生肖路单拐点预判\n- 当前走势平稳或处于横盘，暂无明显连涨/连跌反转的信号。")
        except:
            sections.append("### 📈 生肖路单拐点预判\n暂无数据")

    if 'bayesian' in dimensions:
        try:
            bayesian = stats.get('bayesian', [])
            if bayesian:
                top_3 = bayesian[:3]
                desc_list = [f"{item['zodiac']}(后验权重:{item['posterior']} | 当前已连续遗漏:{item['omission']}期)" for item in top_3]
                sections.append(f"### ⚖️ 贝叶斯推断(极端反弹捕捉)\n最有可能触底爆发反弹的前3名生肖:\n{chr(10).join(desc_list)}")
            else:
                sections.append("### ⚖️ 贝叶斯推断\n无法推算反弹指数")
        except:
            sections.append("### ⚖️ 贝叶斯推断\n暂无数据")

    if 'lstm' in dimensions:
        try:
            lstm = stats.get('lstm', [])
            if lstm:
                top_3 = lstm[:3]
                desc_list = [f"{item['zodiac']}(动态拟合得分:{item['score']} | AI信号判决:【{item['signal']}】)" for item in top_3]
                sections.append(f"### 🧠 LSTM 时间走势拟合(深层非线性)\n得分最高具备强势突破趋势的前3名生肖:\n{chr(10).join(desc_list)}")
            else:
                sections.append("### 🧠 LSTM 时间走势拟合\n网络未形成明显信号")
        except:
            sections.append("### 🧠 LSTM 时间走势拟合\n暂无数据")
    
    data_block = '\n\n'.join(sections)
    
    # 获取严格的生肖映射字典字符串，强制告诉AI
    from modules.statistics_engine import get_zodiac_mapping
    z_map2 = get_zodiac_mapping(lottery_type)
    zmap_text = "【重要系统设定：当前年份2026马年，1-49生肖精确映射】：\n"
    for zname in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']:
        nums = [k for k, v in z_map2.items() if v == zname]
        zmap_text += f"{zname}: {nums}；"
    
    # ====== 组合最终 Prompt ======
    recent_detail_block = f"{recent_detail}" if recent_detail else ""
    prompt = f"""你是一位资深的彩票统计分析专家。请根据以下"{type_name}"的历史统计数据进行分析。

{zmap_text}

⚠️ 重要约束：
1. 用户勾选了以下加权维度进行分析：【{active_dims_text}】。禁止提及或使用未选择的维度。
2. 极其重要：以下所有统计数据全部【仅针对特码】统计，因此你必须将所有已选维度的数据全部用于推荐【特码】。
3. 推荐【正码】（6个）时，采用均衡分布策略即可，不要用特码的统计数据来选正码。
4. 特码选取必须严格基于已选维度的数据做出有据可依的推荐，千万不要发散到未选的走势分析上。
5. 当你提到号码对应的生肖时，绝对！绝对！绝对要参照上方提供的【系统设定：1-49生肖精确映射】，切勿使用你内置的过期生肖知识。

## 最近 300 期原始特码序列（从旧到新，请自行发现隐藏规律）
{raw_special_nums}

{recent_detail_block}

## 已选维度统计数据

{data_block}

## 分析要求
1. 🛑 极其严格的维度约束：你【必须且只能】分析我提供给你的维度数据。如果用户没有勾选某个维度（比如没有提供大小、单双或冷热数据），你【绝对禁止】在分析中自己凭空捏造、猜测或补充该维度的分析。不要产生“幻觉”！
2. 根据选定的各个维度相互印证，综合锁定最可能跃迁的特码区间。
3. 🔍 自主发现：请仔细观察上方原始特码序列，尝试发现我未定义的隐藏规律，例如：
   - 号码间隔/跳跃规律（相邻两期差值是否有周期性）
   - 🎨 波色跳跃与遗漏规律（例如：连续开出蓝波后打断跳红波，或某波色遗漏10期以上极易反弹）
   - 某些号码是否有固定回头周期（如每隔N期重复出现）
   - 区间偏好（连续多期集中在某个十位段）
   将你发现的任何额外规律融入推荐理由中。
4. 📊 多模态视觉超能力：我已在附件中提供了一张近期的【特码生肖走势折线图点阵图】。请你发挥视觉大模型的多模态能力，观察图表中的连线波动（比如是否存在头肩顶、波峰波谷的三重对称、大级别M头等技术图形），把这种图形周期叠加进最终号码选取结论中。
5. 正码6个，特码1个，范围均为 1-49，正码不可重复，但特码可与正码相同。
6. 📖 深度长篇推理（建议 800-1500 字）：请不要惜字如金！请写出一篇详细深入的分析推理长文，详细拆解推理的每个环节：哪些是基于已选维度的推断、规律的共振互补，哪些是你自主发现或通过视觉图表看出的多模态图形规律。让过程推演成为一篇极具说服力的分析报告。

请严格以如下 JSON 格式回复：
{{
    "numbers": [正码1, 正码2, 正码3, 正码4, 正码5, 正码6],
    "special_num": 特码,
    "analysis": "你的分析理由（分别说明正码和特码的逻辑，只讨论所选维度）",
    "confidence": "高/中/低"
}}"""
    
    return prompt


def _fallback_result(reason: str) -> dict:
    """AI 不可用时的降级返回"""
    return {
        'success': False,
        'numbers': [],
        'special_num': 0,
        'analysis': reason,
        'confidence': '无'
    }
