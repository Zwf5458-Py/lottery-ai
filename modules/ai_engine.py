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


def _resolve_api_config():
    """解析 AI 平台配置，返回 (platform, api_key, model_name, base_url)"""
    # 确保 .env 环境变量已加载（防止被后台启动时遗漏）
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except ImportError:
        pass
    
    ai_cfg = _get_ai_config()
    platform = ai_cfg.get('platform', 'local').lower()
    model_name = ai_cfg.get('model', 'gpt-5.4')
    
    # 优先从该平台专有的 provider 配置中读取 key、base_url 和 format
    providers = ai_cfg.get('providers', {})
    provider_cfg = providers.get(platform, {}) if isinstance(providers, dict) else {}
    
    api_key = provider_cfg.get('api_key') if isinstance(provider_cfg, dict) else None
    base_url = provider_cfg.get('api_base') if isinstance(provider_cfg, dict) else None
    api_format = provider_cfg.get('format', '').strip().lower() if isinstance(provider_cfg, dict) else ''
    
    # 如果没读到，则降级使用旧的全局字段 (向前兼容)
    if not api_key:
        api_key = ai_cfg.get('api_key', '')
    if not base_url:
        base_url = ai_cfg.get('base_url') or ai_cfg.get('api_base', 'http://127.0.0.1:8317/v1')
    
    is_openai_compatible = False
    if api_format == 'openai':
        is_openai_compatible = True
    elif api_format == 'google':
        is_openai_compatible = False
    else:
        # 如果没有明确的 format 字段，通过 platform 名字进行猜测
        if platform in ('local', 'openai', 'deepseek', 'qwen', 'glm', 'minimax', 'nvidia', 'cpamc'):
            is_openai_compatible = True
        elif platform == 'google':
            is_openai_compatible = False
        else:
            # 对于其他未知自定义平台，默认为 OpenAI 兼容格式
            is_openai_compatible = True

    if is_openai_compatible:
        # 只有在 base_url 为空时，才尝试读取环境变量
        if not base_url:
            base_url = os.environ.get('LOCAL_AI_BASE') or os.environ.get('HOST_GATEWAY_URL') or 'http://127.0.0.1:8317/v1'
        if not api_key:
            api_key = os.environ.get('LOCAL_AI_API_KEY', '')
        # 最后保险：如果环境变量仍为空，手动从 .env 文件读取
        if not api_key or not base_url:
            try:
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
                if os.path.exists(env_path):
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if '=' in line and not line.startswith('#'):
                                k, v = line.split('=', 1)
                                k, v = k.strip(), v.strip()
                                if k == 'LOCAL_AI_API_KEY' and not api_key:
                                    api_key = v
                                elif k == 'LOCAL_AI_BASE' and not base_url:
                                    base_url = v
                                elif k == 'HOST_GATEWAY_URL' and not base_url:
                                    base_url = v
            except Exception:
                pass
                
        # === 针对 Nvidia NIM 的特殊适配 ===
        # 如果平台选了 nvidia，或者 key 是 nvapi- 开头，强制使用 Nvidia 的官方 Base URL
        if platform == 'nvidia' or (api_key and api_key.startswith('nvapi-')):
            base_url = 'https://integrate.api.nvidia.com/v1'
            platform = 'openai' # Nvidia 接口完全兼容 OpenAI SDK
            
        print(f"🔧 AI 路由: platform={platform}, model={model_name}, base_url={base_url}, key_len={len(api_key) if api_key else 0}")
        return platform, api_key, model_name, base_url
    else:
        # Google Gemini
        if not api_key:
            api_key = os.environ.get('GEMINI_API_KEY', '')
        print(f"🔧 AI 路由: platform=google, model={model_name}, key_len={len(api_key) if api_key else 0}")
        return 'google', api_key, model_name, None


def _resolve_backup_api_config(backup_index: int):
    """解析备用平台配置（backup_index 为 1 或 2），返回 (platform, api_key, model_name, base_url)"""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except ImportError:
        pass
    
    ai_cfg = _get_ai_config()
    platform = ai_cfg.get(f'backup_platform_{backup_index}', '').strip().lower()
    model_name = ai_cfg.get(f'backup_model_{backup_index}', '').strip()
    
    if not platform or not model_name:
        return None, None, None, None
        
    # 优先从该平台专有的 provider 配置中读取 key、base_url 和 format
    providers = ai_cfg.get('providers', {})
    provider_cfg = providers.get(platform, {}) if isinstance(providers, dict) else {}
    
    api_key = provider_cfg.get('api_key') if isinstance(provider_cfg, dict) else None
    base_url = provider_cfg.get('api_base') if isinstance(provider_cfg, dict) else None
    api_format = provider_cfg.get('format', '').strip().lower() if isinstance(provider_cfg, dict) else ''
    
    # 如果没读到，则降级使用旧的全局字段 (向前兼容)
    if not api_key:
        api_key = ai_cfg.get('api_key', '')
    if not base_url:
        base_url = ai_cfg.get('base_url') or ai_cfg.get('api_base', 'http://127.0.0.1:8317/v1')
        
    is_openai_compatible = False
    if api_format == 'openai':
        is_openai_compatible = True
    elif api_format == 'google':
        is_openai_compatible = False
    else:
        # 如果没有明确的 format 字段，通过 platform 名字进行猜测
        if platform in ('local', 'openai', 'deepseek', 'qwen', 'glm', 'minimax', 'nvidia', 'cpamc'):
            is_openai_compatible = True
        elif platform == 'google':
            is_openai_compatible = False
        else:
            # 对于其他未知自定义平台，默认为 OpenAI 兼容格式
            is_openai_compatible = True

    if is_openai_compatible:
        # 只有在 base_url 为空时，才尝试读取环境变量
        if not base_url:
            base_url = os.environ.get('LOCAL_AI_BASE') or os.environ.get('HOST_GATEWAY_URL') or 'http://127.0.0.1:8317/v1'
        if not api_key:
            api_key = os.environ.get('LOCAL_AI_API_KEY', '')
            
        if platform == 'nvidia' or (api_key and api_key.startswith('nvapi-')):
            base_url = 'https://integrate.api.nvidia.com/v1'
            platform = 'openai'
            
        return platform, api_key, model_name, base_url
    else:
        # Google Gemini
        if not api_key:
            api_key = os.environ.get('GEMINI_API_KEY', '')
        return 'google', api_key, model_name, None


def _check_same_platform_tip(model_chain: list) -> str:
    """检查模型链是否都属于同一个平台/自建网关，并返回相应的提示信息"""
    if not model_chain:
        return ""
    platforms = list(set([m['platform'].lower() for m in model_chain if m.get('platform')]))
    
    # 提取 base_url 的主机名或域名，用于判断是否为同一个自建网关
    domains = []
    for m in model_chain:
        base = m.get('base_url')
        if base and isinstance(base, str):
            from urllib.parse import urlparse
            try:
                netloc = urlparse(base).netloc
                if netloc:
                    domains.append(netloc)
            except:
                pass
    domains = list(set(domains))
    
    is_same = False
    if len(platforms) <= 1:
        is_same = True
    elif len(domains) == 1:
        is_same = True
        
    if is_same:
        platform_name = platforms[0] if platforms else "当前"
        if platform_name == 'google':
            platform_disp = "Google Gemini"
        elif platform_name == 'openai':
            platform_disp = "OpenAI"
        else:
            platform_disp = platform_name.upper()
            
        if domains:
            platform_disp += f" (网关: {domains[0]})"
            
        return f"\n\n【高可用提示】：系统检测到您当前配置的主模型与所有备用模型均使用同一个平台/网关({platform_disp})。如果该平台因网络或代理问题极其不稳定，建议您在“系统设置”中更换为其他稳定的官方公共平台模型（例如直接使用官方 Google Gemini、OpenAI 或 DeepSeek 官方直接接口）以保证服务的绝对稳定性。"
    return ""


def _call_openai_compatible(prompt: str, api_key: str, model_name: str, base_url: str) -> dict:
    """通过 OpenAI 兼容接口调用本地或第三方模型"""
    import requests
    
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Connection': 'close',
    }
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    
    payload = {
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': '你是一位资深的彩票走势分析专家与系统推理报告撰写者。请严格按照用户要求的 JSON 格式输出。'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
    }
    
    # Nvidia NIM 对 max_tokens 参数极其敏感（尤其是类似 z-ai/glm 系列），
    # 强制指定可能导致连接无限期挂起直至超时被掐断，因此对 Nvidia 接口屏蔽该参数
    if 'integrate.api.nvidia.com' not in base_url:
        payload['max_tokens'] = 4096

    
    print(f"💡 正在发送推测请求给本地模型 ({model_name}) @ {base_url}...")
    
    import time
    max_retries = 2
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            # Nvidia 接口某些模型推理极慢，放宽到 180 秒
            timeout_cfg = 180 if 'integrate.api.nvidia.com' in base_url else 120
            
            # 容错容灾：如果之前发生过连接异常，重试时强制直连，防止本地脏代理变量污染私有网关
            proxies_cfg = None
            if attempt > 0 and last_err and isinstance(last_err, requests.exceptions.ConnectionError):
                print(f"⚠️ {model_name} 监测到连接异常，重试时强制启用免代理直连...")
                proxies_cfg = {"http": None, "https": None}
                
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout_cfg, proxies=proxies_cfg)
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            
            # 防御空响应
            if not content or not content.strip():
                raise ValueError(f"模型 {model_name} 返回了空内容，该模型可能不存在或不可用。请检查模型名称是否正确。（提示：Nvidia NIM 平台必须使用带厂商前缀的模型名，如 meta/llama-3.1-70b-instruct）")
            
            # 尝试解析 JSON（可能被 ```json ... ``` 包裹）
            content = content.strip()
            if content.startswith('```'):
                # 去除 markdown 代码块
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)
            # 预处理：修复模型 JSON 中可能出现的非标准键名（如 *key* 变体）
            import re as _re
            content = _re.sub(r'"[\s*]*([a-zA-Z_][a-zA-Z0-9_]*)[\s*]*"(\s*:)', r'"\1"\2', content)
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # 模型未返回 JSON，但返回了文字 -> 将原始文字作为分析文本
                print(f"⚠️ 模型 {model_name} 未返回标准 JSON，尝试提取文字作为分析内容")
                result = {
                    "analysis": content[:3000],
                    "confidence": "低（模型未按格式回复）"
                }
            
            # 规范化键名（去除残余的 * 等装饰字符）
            if isinstance(result, dict):
                cleaned = {}
                for k, v in result.items():
                    clean_key = k.strip().strip('*').strip()
                    cleaned[clean_key] = v
                result = cleaned
            
            return result
        except requests.exceptions.HTTPError as he:
            err_content = "未知错误"
            try:
                err_content = he.response.text
            except:
                pass
            last_err = Exception(f"HTTP {he.response.status_code}: {err_content}")
            err_msg = str(last_err).lower()
            if '503' in err_msg or '502' in err_msg or 'timeout' in err_msg or 'connection' in err_msg:
                if attempt < max_retries:
                    print(f"⚠️ API接口异常，重试中 ({attempt+1}/{max_retries})...")
                    time.sleep(2)
                    continue
            raise last_err
        except Exception as e:
            last_err = e
            err_msg = str(e).lower()
            if '503' in err_msg or '502' in err_msg or 'timeout' in err_msg or 'connection' in err_msg:
                if attempt < max_retries:
                    print(f"⚠️ 本地模型接口异常，重试中 ({attempt+1}/{max_retries})...")
                    time.sleep(2)
                    continue
            raise e
    raise last_err


def _call_gemini(prompt: str, api_key: str, model_name: str, stats_summary: dict, lottery_type: str, dimensions: list) -> dict:
    """通过 Google Gemini SDK 调用"""
    from google import genai
    
    client = genai.Client(api_key=api_key)
    
    contents = [prompt]
    try:
        from modules.chart_generator import generate_comprehensive_dashboard_bytes
        from modules.data_processor import get_db_connection
        from modules.statistics_engine import get_zodiac_mapping
        import pandas as pd
        
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT draw_number, special_num FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT 300", conn, params=(lottery_type,))
        conn.close()
        z_map = get_zodiac_mapping(lottery_type)
        
        img_bytes = generate_comprehensive_dashboard_bytes(stats_summary, df, z_map, dimensions)
        if img_bytes:
            from google.genai import types
            contents = [
                types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                prompt
            ]
    except Exception as e:
        print(f"生成或附加包含图片的 Prompt 失败: {e}")
    
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
                    print(f"⚠️ {model_name} 接口繁忙，重试中 ({attempt+1}/{max_retries})...")
                    time.sleep(2)
                    continue
            raise e
    
    return json.loads(response.text)


def analyze_with_ai(stats_summary: dict, lottery_type: str = 'macaujc', dimensions: list = None, pool: list = None, special_num: int = None) -> dict:
    if dimensions is None:
        dimensions = ['big_small', 'odd_even', 'hot_cold', 'tail', 'zodiac']
        
    is_wheeling = (pool is not None and len(pool) > 6)
    
    try:
        # 1. 获取选定号码与底层权重
        if is_wheeling:
            pre_sel_nums = sorted(pool)
            pre_sel_special = special_num if special_num is not None else 1
            # 动态计算图表加权系数
            from modules.simulator import _calculate_trend_weights
            system_weights = _calculate_trend_weights(lottery_type, dimensions)
        else:
            from modules.simulator import simulate_single
            sys_res = simulate_single(lottery_type, dimensions)
            pre_sel_nums = sorted(sys_res.get('numbers', []))
            pre_sel_special = sys_res.get('special_num', 1)
            system_weights = sys_res.get('_weights', {})
        
        prompt = _build_analysis_prompt(stats_summary, lottery_type, dimensions, pre_sel_nums, pre_sel_special, system_weights, is_wheeling=is_wheeling)
        
        # 2. 解析主模型配置
        platform, api_key, model_name, base_url = _resolve_api_config()
        
        # 3. 构造大模型调用链
        model_chain = [
            {"name": "主模型", "platform": platform, "api_key": api_key, "model_name": model_name, "base_url": base_url}
        ]
        
        # 备用模型 1 (对应备用模型 2)
        bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
        if bp1 and bm1:
            model_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
            
        # 备用模型 2 (对应备用模型 3)
        bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
        if bp2 and bm2:
            model_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
            
        result = None
        last_exception = None
        called_model_label = "主模型"
        called_model_name = model_name
        
        for m_info in model_chain:
            try:
                # 针对本地或第三方的调试打印
                key_len = len(m_info['api_key']) if m_info['api_key'] else 0
                print(f"🤖 正在尝试通过 {m_info['name']} ({m_info['model_name']} @ {m_info['platform']}, key_len={key_len}) 进行预测...")
                
                if not m_info['api_key'] and m_info['platform'] == 'google':
                    raise ValueError("未配置 Gemini API Key，请在设置面板中填写")
                
                if m_info['platform'] == 'google':
                    result = _call_gemini(prompt, m_info['api_key'], m_info['model_name'], stats_summary, lottery_type, dimensions)
                else:
                    result = _call_openai_compatible(prompt, m_info['api_key'], m_info['model_name'], m_info['base_url'])
                
                if result and result.get('analysis'):
                    called_model_label = m_info['name']
                    called_model_name = m_info['model_name']
                    break
            except Exception as e:
                print(f"❌ {m_info['name']} ({m_info['model_name']}) 尝试调用失败: {e}")
                last_exception = e
                continue
                
        if not result:
            if last_exception:
                raise last_exception
            else:
                raise ValueError("未配置可用模型或所有配置模型尝试均失败")
        
        # ====== 无视AI瞎猜，强制返回系统底层的推算号码 ======
        numbers = sorted(pre_sel_nums)
        special = pre_sel_special
        if len(numbers) < 6:
            seen = set(numbers)
            max_val = 39 if lottery_type == 'weilitsai' else 50
            for i in range(1, max_val):
                if len(numbers) >= 6: break
                if i not in seen:
                    numbers.append(i)
                    seen.add(i)
        
        analysis_text = result.get('analysis', 'AI 分析完成')
        if called_model_label != "主模型":
            analysis_text = f"【系统提示：由于主模型服务响应失败，系统已自动启用 {called_model_label} ({called_model_name}) 完成此次预测。】\n\n" + analysis_text
            
        return {
            'success': True,
            'numbers': pre_sel_nums if is_wheeling else sorted(numbers[:6]),
            'special_num': special,
            'analysis': analysis_text,
            'confidence': result.get('confidence', '高')
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # 安全地获取 model_chain
        m_chain = locals().get('model_chain', [])
        if not m_chain:
            try:
                p, k, mn, bu = _resolve_api_config()
                m_chain = [{"name": "主模型", "platform": p, "api_key": k, "model_name": mn, "base_url": bu}]
                bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
                if bp1 and bm1:
                    m_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
                bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
                if bp2 and bm2:
                    m_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
            except:
                pass
                
        tip = _check_same_platform_tip(m_chain)
        return _fallback_result(f'AI 分析异常 ({type(e).__name__}: {str(e)[:100]}){tip}，已降级为传统加权模式')


def analyze_zodiac_with_ai(stats_summary: dict, lottery_type: str = 'macaujc', dimensions: list = None) -> dict:
    """
    使用 AI 专门推算下期特码的生肖（不推算具体号码）
    返回: {'success': bool, 'zodiac_predictions': [...], 'analysis': str, 'confidence': str}
    """
    if dimensions is None:
        dimensions = ['markov', 'consecutive', 'bayesian', 'lstm']
    
    try:
        # 1. 构建生肖专属 Prompt
        prompt = _build_zodiac_prompt(stats_summary, lottery_type, dimensions)
        
        # 2. 解析主模型配置
        platform, api_key, model_name, base_url = _resolve_api_config()
        
        # 3. 构造大模型调用链
        model_chain = [
            {"name": "主模型", "platform": platform, "api_key": api_key, "model_name": model_name, "base_url": base_url}
        ]
        
        # 备用模型 1 (对应备用模型 2)
        bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
        if bp1 and bm1:
            model_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
            
        # 备用模型 2 (对应备用模型 3)
        bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
        if bp2 and bm2:
            model_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
            
        result = None
        last_exception = None
        called_model_label = "主模型"
        called_model_name = model_name
        
        for m_info in model_chain:
            try:
                key_len = len(m_info['api_key']) if m_info['api_key'] else 0
                print(f"🤖 正在尝试通过 {m_info['name']} 生肖推算 ({m_info['model_name']} @ {m_info['platform']}, key_len={key_len})...")
                
                if not m_info['api_key'] and m_info['platform'] == 'google':
                    raise ValueError("未配置 Gemini API Key，请在设置面板中填写")
                
                if m_info['platform'] == 'google':
                    result = _call_gemini(prompt, m_info['api_key'], m_info['model_name'], stats_summary, lottery_type, dimensions)
                else:
                    result = _call_openai_compatible(prompt, m_info['api_key'], m_info['model_name'], m_info['base_url'])
                
                if result and (result.get('zodiac_predictions') or result.get('analysis')):
                    called_model_label = m_info['name']
                    called_model_name = m_info['model_name']
                    break
            except Exception as e:
                print(f"❌ {m_info['name']} 生肖推算 ({m_info['model_name']}) 尝试调用失败: {e}")
                last_exception = e
                continue
                
        if not result:
            if last_exception:
                raise last_exception
            else:
                raise ValueError("未配置可用模型或所有配置模型尝试均失败")
        
        # 校验生肖有效性
        valid_zodiacs = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
        predictions = result.get('zodiac_predictions', [])
        valid_predictions = [p for p in predictions if p.get('zodiac') in valid_zodiacs]
        
        analysis_text = result.get('analysis', 'AI 生肖推算完成')
        if called_model_label != "主模型":
            analysis_text = f"【系统提示：由于主模型服务响应失败，系统已自动启用 {called_model_label} ({called_model_name}) 完成此次生肖推算。】\n\n" + analysis_text
            
        return {
            'success': True,
            'zodiac_predictions': valid_predictions[:5],
            'analysis': analysis_text,
            'confidence': result.get('confidence', '中等')
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # 安全地获取 model_chain
        m_chain = locals().get('model_chain', [])
        if not m_chain:
            try:
                p, k, mn, bu = _resolve_api_config()
                m_chain = [{"name": "主模型", "platform": p, "api_key": k, "model_name": mn, "base_url": bu}]
                bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
                if bp1 and bm1:
                    m_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
                bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
                if bp2 and bm2:
                    m_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
            except:
                pass
                
        tip = _check_same_platform_tip(m_chain)
        return _fallback_zodiac(f'AI 分析异常 ({type(e).__name__}: {str(e)[:100]}){tip}')


def _build_common_dimensions(stats: dict, dimensions: list) -> list:
    sections = []
    if 'big_small' in dimensions:
        try:
            bs = stats.get('big_small', {})
            total_big = bs.get('total_big', '?')
            total_small = bs.get('total_small', '?')
            vals = bs.get('values', [])
            jumps = bs.get('current_jumps', 0)
            last5 = vals[-5:] if vals else []
            
            trend_str = ""
            if jumps >= 3:
                trend_str = f"当前处于高频单跳震荡中(已连续上下交替{jumps}次)，比如呈现 1-1-1 锯齿状，随时可能发生止跳连庄！"
            elif last5:
                last_v = last5[-1]
                v_abs = abs(last_v)
                v_label = '大' if last_v > 0 else '小'
                if v_abs >= 13:
                    trend_str = f"🚨 **【极度危险】**：当前已连续{v_abs}期{v_label}！根据近2000期历史统计，最大连庄极值为13期左右，当前已完全触达或突破该理论天花板极限，下一期具有**极其强烈的断龙(反转)均值回归预期**！"
                elif v_abs >= 8:
                    trend_str = f"⚠️ **高危长龙盘**：当前已连续{v_abs}期{v_label}，已进入后半段长龙深水区（历史极限突破13期的极少见），强烈建议密切防范断龙或选择顺势末期观望。"
                else:
                    trend_str = f"当前连续{v_abs}期{v_label}。历史统计表明超过5连后断龙概率会逐期剧增（硬极限在13期）。注意动态止盈。"
            else:
                trend_str = "无走势数据"
                
            ceiling_warning = ""
            last30 = vals[-30:] if len(vals) >= 30 else vals
            if len(last30) >= 10:
                for direction, label in [(1, '大'), (-1, '小')]:
                    consecutive_segments = []
                    for v in last30:
                        if (v > 0) == (direction > 0):
                            consecutive_segments.append(abs(v))
                    if len(consecutive_segments) >= 5:
                        recent_segs = consecutive_segments[-8:]
                        if len(recent_segs) >= 5:
                            recent_max = max(recent_segs)
                            if recent_max <= 2 and len(recent_segs) >= 5:
                                ceiling_warning += (
                                    f"\n⚠️ **近期形态天花板规律（双向解读）**：「{label}」方向在最近{len(recent_segs)}次出现中，连续次数始终未突破{recent_max}（每次最多连{recent_max}就转向）。\n"
                                    f"  ❶ 防守解读：近期{label}号处于弱势交替状态，形成天花板压制，短期难以形成长龙。\n"
                                    f"  ❷ 进攻解读（均值回归）：连续{len(recent_segs)}次都被压制在{recent_max}连以内，这是一种**极端统计压缩**状态。根据均值回归原理，长期被抑制的连庄潜力正在累积蓄能——一旦{label}方向再次出现，**极有可能打破天花板突破{recent_max+1}连甚至更多**！\n"
                                    f"  📌 AI需同时评估上述两种可能性，并在分析中明确表态倾向哪一种。"
                                )
                            elif recent_max <= 3 and all(s <= 3 for s in recent_segs) and len(recent_segs) >= 6:
                                ceiling_warning += (
                                    f"\n📊 **连续压制信号（双向解读）**：「{label}」方向最近{len(recent_segs)}次出现中最大连续仅为{recent_max}。\n"
                                    f"  ❶ 压制仍在延续，短期内可能继续维持{recent_max}连以内的交替节奏。\n"
                                    f"  ❷ 但如此长期的压制本身就是异常信号，随时可能因蓄能爆发打破{recent_max}连天花板。"
                                )
                
            sections.append(f"### 📊 特码大小走势图表分析（≥25为大，<25为小）\n- 近100期统计: 大 {total_big} 期 | 小 {total_small} 期\n- 最近K线值(正为大，负为小): {last5}\n- 📉 走势规律警告: {trend_str}{ceiling_warning}\n  (AI需观察长龙极限压力（最大历史极值13期）以及近期规律中的天花板壁垒结构)")
        except:
            sections.append("### 📊 特码大小走势图表分析\n暂无数据")
    
    if 'odd_even' in dimensions:
        try:
            oe = stats.get('odd_even', {})
            total_odd = oe.get('total_odd', '?')
            total_even = oe.get('total_even', '?')
            vals = oe.get('values', [])
            jumps = oe.get('current_jumps', 0)
            last5 = vals[-5:] if vals else []
            
            trend_str = ""
            if jumps >= 3:
                trend_str = f"当前处于高频单跳震荡中(已连续上下交替{jumps}次)，比如呈现 1-1-1 锯齿状，随时可能发生止跳连庄！"
            elif last5:
                last_v = last5[-1]
                v_abs = abs(last_v)
                v_label = '单' if last_v > 0 else '双'
                if v_abs >= 13:
                    trend_str = f"🚨 **【极度危险】**：当前已连续{v_abs}期{v_label}！根据近2000期历史宏观统计，单双最大连庄极值约为13期，当前已触及并挑战该理论硬极限天花板，具备**碾压级的断龙反转势能**！"
                elif v_abs >= 8:
                    trend_str = f"⚠️ **高危长龙盘**：当前已连续{v_abs}期{v_label}进入长龙深水区（历史极限罕见突破13期），均值回归的向心力正在急剧增强，极可能随时断龙。"
                else:
                    trend_str = f"当前连续{v_abs}期{v_label}。历史统计表明连龙超过50%分水岭后断崖概率增加（最大理论极限在13期）。"
            else:
                trend_str = "无走势数据"
                
            ceiling_warning = ""
            last30 = vals[-30:] if len(vals) >= 30 else vals
            if len(last30) >= 10:
                for direction, label in [(1, '单'), (-1, '双')]:
                    consecutive_segments = []
                    for v in last30:
                        if (v > 0) == (direction > 0):
                            consecutive_segments.append(abs(v))
                    if len(consecutive_segments) >= 5:
                        recent_segs = consecutive_segments[-8:]
                        if len(recent_segs) >= 5:
                            recent_max = max(recent_segs)
                            if recent_max <= 2 and len(recent_segs) >= 5:
                                ceiling_warning += (
                                    f"\n⚠️ **近期形态天花板规律（双向解读）**：「{label}」方向在最近{len(recent_segs)}次出现中，连续次数始终未突破{recent_max}。\n"
                                    f"  ❶ 防守解读：近期{label}号处于弱势交替状态，形成天花板压制。\n"
                                    f"  ❷ 进攻解读（均值回归）：连续{len(recent_segs)}次被压制在{recent_max}连以内是**极端统计压缩**，正在累积蓄能——一旦{label}方向再次出现，**极有可能打破天花板突破{recent_max+1}连甚至更多**！\n"
                                    f"  📌 AI需同时评估两种可能性并明确表态。"
                                )
                            elif recent_max <= 3 and all(s <= 3 for s in recent_segs) and len(recent_segs) >= 6:
                                ceiling_warning += (
                                    f"\n📊 **连续压制信号（双向解读）**：「{label}」方向最近{len(recent_segs)}次出现中最大连续仅为{recent_max}。\n"
                                    f"  ❶ 压制延续中，短期内可能继续维持{recent_max}连以内的交替节奏。\n"
                                    f"  ❷ 长期压制本身是异常信号，随时可能蓄能爆发打破{recent_max}连天花板。"
                                )
                
            sections.append(f"### 🔢 特码单双走势图表分析\n- 近100期统计: 单 {total_odd} 期 | 双 {total_even} 期\n- 最近K线值(正为单，负为双): {last5}\n- 📉 走势规律警告: {trend_str}{ceiling_warning}\n  (AI需高度重视逼近历史极值（13期）带来的断龙势能，以及近期局部的天花板壁垒)")
        except:
            sections.append("### 🔢 特码单双走势图表分析\n暂无数据")
    
    if 'hot_cold' in dimensions:
        try:
            hot_cold = stats.get('hot_cold', {})
            hot_list = hot_cold.get('hot', [])[:8]
            cold_list = hot_cold.get('cold', [])[:8]
            hot_str = ', '.join([f"{h['number']}号({h['count']}次)" for h in hot_list]) if hot_list else '暂无'
            cold_str = ', '.join([f"{c['number']}号({c['count']}次)" for c in cold_list]) if cold_list else '暂无'
            sections.append(f"### 🔥 特码冷热频率（近100期）\n- 热号区间: {hot_str}\n- 冷号区间(关注极寒回补): {cold_str}")
        except:
            sections.append("### 🔥 特码冷热频率\n暂无数据")

    if 'color' in dimensions:
        try:
            color_data = stats.get('color_hot_cold', [])
            if color_data:
                desc = []
                for c in color_data:
                    hint = c.get('rebound_hint', '')
                    desc.append(f"- 【{c['color']}】当前遗漏 {c['current_gap']} 期 (平均遗漏 {c['avg_gap']} 期)。基于几何分布累积概率(CDF)，其遗漏极端度达到 {c['extremity']}%，状态：{hint}")
                sections.append(f"### 🎨 波色冷热与极值反弹推测\n{chr(10).join(desc)}\n(注意：红波、蓝波、绿波在盘面上通常具有互补修复属性)")
        except:
            sections.append("### 🎨 波色推测\n暂无数据")
    
    if 'tail' in dimensions:
        try:
            tail_raw = stats.get('tail_numbers', {})
            # tail_number_stats 返回 {'distribution': {...}, 'omission': {...}}
            if isinstance(tail_raw, dict) and 'distribution' in tail_raw:
                tail = tail_raw.get('distribution', {})
                tail_omi = tail_raw.get('omission', {})
            else:
                tail = tail_raw
                tail_omi = {}
                
            if tail:
                tail_lines = []
                total_draws = sum(tail.values())
                avg_draws = total_draws / 10 if total_draws > 0 else 0
                for t_num in range(10):
                    count = tail.get(t_num, tail.get(str(t_num), 0))
                    omi = tail_omi.get(t_num, tail_omi.get(str(t_num), 0))
                    
                    omi_mark = f"，当前已连续遗漏 {omi} 期！" if omi >= 15 else (f"，当前遗漏 {omi} 期" if omi > 0 else "")
                    
                    if avg_draws > 0:
                        diff = count - avg_draws
                        diff_pct = (diff / avg_draws) * 100
                        if count <= max(1, avg_draws * 0.3) or count <= 2 or omi >= 20:
                            mark = "⚠️ 极度冷门或超长遗漏 (强烈回补信号)"
                        elif diff_pct <= -30:
                            mark = "❄️ 偏冷"
                        elif diff_pct >= 50:
                            mark = "🔥 极热"
                        elif diff_pct >= 20:
                            mark = "🌡️ 偏热"
                        else:
                            mark = "均值附近"
                        tail_lines.append(f"-尾数【{t_num}】: 近期出现 {count}次 ({diff_pct:+.1f}%) -> {mark}{omi_mark}")
                t_str = '\n'.join(tail_lines)
                sections.append(f"### 🎯 尾数分布与遗漏监控\n{t_str}\n（AI必须关注带有'极大遗漏'或'强烈回补信号'的尾数，比如当前连续遗漏超过20期的尾号，这类尾数极易在近期发生均值回归爆冷出号！）")
            else:
                sections.append("### 🎯 尾数分布\n暂无数据")
        except:
            sections.append("### 🎯 尾数分布\n暂无数据")
    
    return sections


def _build_zodiac_prompt(stats: dict, lottery_type: str, dimensions: list) -> str:
    """构建生肖专属推算 Prompt"""
    type_name = '新澳门六合彩' if lottery_type == 'macaujc2' else '澳门六合彩'
    
    # 收集所有生肖相关的维度数据
    sections = []
    
    # 补充所有通用维度的数据（大小、单双、波色等）
    sections.extend(_build_common_dimensions(stats, dimensions))
    
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
    
    # ========== 多维路单规则分析（颜色连续、生肖连庄、涨跌交替模式） ==========
    try:
        zs = stats.get('zodiac_stats', {})
        if isinstance(zs, dict) and 'draws' in zs:
            draws_full = zs.get('draws', [])[-50:]  # 最近50期用于规则分析
            zodiac_order = zs.get('zodiac_order', [])
            
            if len(draws_full) >= 10:
                red_set = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
                blue_set = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
                green_set = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}
                
                def _get_color(n):
                    if n in red_set: return '红'
                    if n in blue_set: return '蓝'
                    if n in green_set: return '绿'
                    return '?'
                
                # 提取序列
                z_seq = []  # 生肖名序列
                c_seq = []  # 颜色序列
                y_seq = []  # Y轴位置序列
                for d in draws_full:
                    z_name = zodiac_order[d['zodiac_idx']] if d['zodiac_idx'] < len(zodiac_order) else '?'
                    z_seq.append(z_name)
                    c_seq.append(_get_color(int(d['num'])))
                    y_seq.append(d['zodiac_idx'])
                
                multi_rules = []
                
                # --- 规则1：颜色连续（最近N期的波色连庄） ---
                if c_seq:
                    curr_color = c_seq[-1]
                    color_streak = 0
                    for c in reversed(c_seq):
                        if c == curr_color:
                            color_streak += 1
                        else:
                            break
                    color_map = {'红': '红波', '蓝': '蓝波', '绿': '绿波'}
                    if color_streak >= 3:
                        multi_rules.append(f"🎨 【波色连庄】最近连续{color_streak}期开出{color_map.get(curr_color, curr_color)}！波色长龙持续中，需重点关注是否即将断龙转色。")
                    elif color_streak >= 2:
                        multi_rules.append(f"🎨 【波色连续】最近连续{color_streak}期{color_map.get(curr_color, curr_color)}，短期波色趋势形成中。")
                
                # --- 规则2：生肖连庄（同一生肖连续出现） ---
                if z_seq:
                    curr_z = z_seq[-1]
                    z_streak = 0
                    for z in reversed(z_seq):
                        if z == curr_z:
                            z_streak += 1
                        else:
                            break
                    if z_streak >= 2:
                        multi_rules.append(f"🐾 【生肖连庄】{curr_z}连续出现{z_streak}期！历史上连庄超过3期非常罕见，需评估是否即将转肖。")
                
                # --- 规则3：涨跌交替模式分析（如121212、112112等） ---
                if len(y_seq) >= 6:
                    # 计算涨跌序列
                    ud_seq = []
                    for i in range(1, len(y_seq)):
                        diff = y_seq[i] - y_seq[i-1]
                        if diff > 0: ud_seq.append('U')
                        elif diff < 0: ud_seq.append('D')
                        else: ud_seq.append('=')
                    
                    # 去掉平（=）
                    ud_clean = [x for x in ud_seq if x != '=']
                    
                    if len(ud_clean) >= 6:
                        # 检测完美交替 UDUDUD...
                        tail6 = ud_clean[-6:]
                        is_alternating = all(tail6[i] != tail6[i+1] for i in range(len(tail6)-1))
                        if is_alternating:
                            alt_count = 0
                            for i in range(len(ud_clean)-1, 0, -1):
                                if ud_clean[i] != ud_clean[i-1]:
                                    alt_count += 1
                                else:
                                    break
                            multi_rules.append(f"🔄 【完美交替模式】最近{alt_count+1}步呈现涨跌交替(UDUDUD...)，单跳锯齿形态明显！根据大小走势规则，连续交替超过5步后随时可能止跳连庄。")
                        
                        # 检测分组交替 如 112112、221221
                        tail8 = ud_clean[-8:] if len(ud_clean) >= 8 else ud_clean[-6:]
                        # RLE
                        rle = []
                        curr = tail8[0]
                        cnt = 1
                        for j in range(1, len(tail8)):
                            if tail8[j] == curr:
                                cnt += 1
                            else:
                                rle.append(cnt)
                                curr = tail8[j]
                                cnt = 1
                        rle.append(cnt)
                        
                        if len(rle) >= 4:
                            # 检测节奏重复 如 [1,1,2,1,1,2] 或 [2,1,2,1]
                            for period in [2, 3]:
                                if len(rle) >= period * 2:
                                    pattern = rle[:period]
                                    is_repeating = True
                                    for k in range(period, min(len(rle), period * 3)):
                                        if rle[k] != pattern[k % period]:
                                            is_repeating = False
                                            break
                                    if is_repeating:
                                        pattern_str = '-'.join(str(x) for x in pattern)
                                        multi_rules.append(f"📊 【节奏模式】涨跌步长呈现周期性重复模式（{pattern_str}循环），下一步可参考模式预测走向。")
                                        break
                
                if multi_rules:
                    sections.append(f"### 🔍 路单多维规则信号\n" + "\n".join(multi_rules))
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
                        
                tz_str = f"重点关注反转目标生肖: {', '.join(target_zodiacs)} (注：Y轴排序由下至上为: {', '.join(z_order)})" if target_zodiacs else ""
                
                # 关键逻辑：用户提出连续次数达到 2 次即应视为第 3 期强力预警，因此阈值降为 < 2
                if count < 2:
                    desc = (
                        f"当前生肖排位路单刚形成【{count}】期【{dir_chi}】方向，动量极弱，暂不建议作为判断依据。"
                    )
                else:
                    target_chi = "向下回调(应优选图表Y轴排位靠下的生肖)" if target_dir == 'down' else "向上反弹(应优选图表Y轴排位靠上的生肖)"
                    desc = (
                        f"当前生肖排位路单已连续【{count}】期呈现【{dir_chi}】（加上即将摇奖的这期即实质已形成 {count+1} 连形态）。\n"
                        f"📊 【最新图表规律触发】：从历史图表上看路单生肖排位单边运动极限约在5期，通常达到3连极其容易发生掉头反转！\n"
                        f"当前处于强烈的掉头落点反转预期区间，下期发生【{target_chi}】的独立概率极高（{rev_prob:.1f}%）。\n"
                        f"{tz_str}"
                    )
                sections.append(f"### 📈 生肖排位路单拐点图表信号(动量防跳体系)\n{desc}")
        except:
            pass
    
    if 'bayesian' in dimensions:
        try:
            bayesian = stats.get('bayesian', [])
            if bayesian:
                desc = []
                for item in bayesian:
                    record_flag = ""
                    if item.get('breaking_record', False):
                        record_flag = f" \U0001f6a8\U0001f6a8\u3010\u7a81\u7834\u5386\u53f2\u6781\u503c\uff01\u5f53\u524d{item['omission']}\u671f\u9057\u6f0f\u5df2\u5237\u65b0\u8be5\u751f\u8096\u5386\u53f2\u6700\u5927\u9057\u6f0f\u8bb0\u5f55{item.get('max_omission', '?')}\u671f\uff0c\u5c5e\u4e8e\u6570\u636e\u7ea7\u522b\u7684\u6781\u7aef\u5f02\u5e38\u4fe1\u53f7\uff0c\u5fc5\u987b\u9ad8\u5ea6\u91cd\u89c6\u53cd\u5f39\uff01\u3011"
                    elif item['omission'] >= item.get('max_omission', 999) * 0.8:
                        record_flag = f" \u26a0\ufe0f\u3010\u5df2\u63a5\u8fd1\u5386\u53f2\u6781\u503c{item.get('max_omission', '?')}\u671f\u768480%\u8b66\u6212\u7ebf\u3011"
                    desc.append(
                        f"\u3010{item['zodiac']}\u3011\u540e\u9a8c\u6743\u91cd:{item['posterior']} "
                        f"(\u5f53\u524d\u5df2\u8fde\u7eed\u9057\u6f0f {item['omission']} \u671f / \u5386\u53f2\u6700\u5927\u9057\u6f0f {item.get('max_omission', '?')} \u671f / \u5e73\u5747\u9057\u6f0f {item.get('avg_omission', '?')} \u671f){record_flag}"
                    )
                sections.append(f"### \u2696\ufe0f \u8d1d\u53f6\u65af\u6781\u503c\u53cd\u5f39\u6392\u540d\uff08\u5168\u90e812\u751f\u8096\uff0c\u6309\u540e\u9a8c\u6982\u7387\u964d\u5e8f\uff09\n{chr(10).join(desc)}")
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
        ai_raw_p = get_chart_periods(lottery_type=lottery_type).get('ai_raw_data', 300)
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
1. 🛑 极其严格的维度约束：你【必须且只能】分析我提供给你的维度数据。如果某个维度（如单双、大小、冷热）没有在上方的数据区块中出现，你【绝对禁止】在分析中自己凭空捏造或提及。如果上方出现了大小、单双、尾数、冷热等非生肖维度的数据，请你必须将其作为跨维度交叉印证的依据（例如：大号偏多则大概率开出分布在大号区间的生肖），并把这些推导依据写入最终的分析描述中。拒绝凭空捏造毫无依据的数据！
2. 综合以上所有提供的数据，给出你认为下期特码最可能开出的 **前3名生肖**，按概率从高到低排列。
3. 每个生肖给出你的推算理由（30字以内）和一个你估计的概率百分比。
4. 你的分析必须且仅必须覆盖上方数据区块中实际出现的全部维度，逐一说明其对你判断的影响。不要提及未在数据中出现的维度名称（例如：如果上方没有波色数据块，就不要分析波色）。
5. 特别关注贝叶斯遗漏中带有突破历史极值或接近历史极值标记的生肖，这类生肖正处于统计学意义上的极端反弹临界区域，必须在分析中重点讨论其爆发概率。
6. 📖 深度长篇推理（建议 800-1500 字）：请极尽详细地阐述推理过程。把上方每个提供的维度如何影响你的判断、不同指标如何互相印证或推翻写清楚。
7. 📊 结合图表视角的多模态深度融合：虽然你现在接收的是结构化数值，但你必须表现出极其擅长“看图说话”的多模态图形分析能力。请把提供给你的近期走势数字看作各种图表的坐标轨迹，用类似“从近期图表的折线来看、本期图表走势线显示、结合大小和生肖等柱状图多维联动来看”的图表化专业视角，重点将【大小图表】、【单双趋势】、【路单连线】及【尾数冷热分布】这几大核心维度的图形特征综合共振，挖掘深层的三重对称或锯齿状反转模式，写出具有画面感的实战肉眼结论！

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


def _build_analysis_prompt(stats: dict, lottery_type: str, dimensions: list, pre_sel_nums: list = None, pre_sel_special: int = 1, system_weights: dict = None, is_wheeling: bool = False) -> str:
    if lottery_type == 'weilitsai':
        sections = []
        if 'big_small' in dimensions:
            try:
                bs_z1 = stats.get('big_small_z1', {})
                bs_z2 = stats.get('big_small_z2', {})
                b1 = bs_z1.get('total_big', '?')
                s1 = bs_z1.get('total_small', '?')
                vals_1 = bs_z1.get('values', [])
                last5_1 = vals_1[-5:] if vals_1 else []
                b2 = bs_z2.get('total_big', '?')
                s2 = bs_z2.get('total_small', '?')
                vals_2 = bs_z2.get('values', [])
                last5_2 = vals_2[-5:] if vals_2 else []
                desc = (
                    f"- **第一區 (1-38，20及以上为大，19及以下为小)**: 近100期大 {b1} 次 | 小 {s1} 次，最近5期K线值(正大负小): {last5_1}\n"
                    f"- **第二區 (1-8，5及以上为大，4及以下为小)**: 近100期大 {b2} 次 | 小 {s2} 次，最近5期K线值(正大负小): {last5_2}"
                )
                sections.append(f"### 📊 威力彩两區大小走势图表分析\n{desc}")
            except:
                sections.append("### 📊 威力彩两區大小走势图表分析\n暂无数据")

        if 'odd_even' in dimensions:
            try:
                oe_z1 = stats.get('odd_even_z1', {})
                oe_z2 = stats.get('odd_even_z2', {})
                o1 = oe_z1.get('total_odd', '?')
                e1 = oe_z1.get('total_even', '?')
                vals_1 = oe_z1.get('values', [])
                last5_1 = vals_1[-5:] if vals_1 else []
                o2 = oe_z2.get('total_odd', '?')
                e2 = oe_z2.get('total_even', '?')
                vals_2 = oe_z2.get('values', [])
                last5_2 = vals_2[-5:] if vals_2 else []
                desc = (
                    f"- **第一區**: 近100期单 {o1} 次 | 双 {e1} 次，最近5期K线值(正单负双): {last5_1}\n"
                    f"- **第二區**: 近100期单 {o2} 次 | 双 {e2} 次，最近5期K线值(正单负双): {last5_2}"
                )
                sections.append(f"### 🎲 威力彩两區单双走势图表分析\n{desc}")
            except:
                sections.append("### 🎲 威力彩两區单双走势图表分析\n暂无数据")

        if 'hot_cold' in dimensions:
            try:
                hc_z1 = stats.get('hot_cold_z1', {})
                hc_z2 = stats.get('hot_cold_z2', {})
                hot_1 = hc_z1.get('hot', [])
                cold_1 = hc_z1.get('cold', [])
                hot_2 = hc_z2.get('hot', [])
                cold_2 = hc_z2.get('cold', [])
                def _fmt_hc(lst):
                    return ', '.join([f"{item['number']}号(出现{item['count']}次/遗漏{item['omission']}期)" for item in lst])
                desc = (
                    f"- **第一區 (1-38)**:\n"
                    f"  - 热门号码: {_fmt_hc(hot_1)}\n"
                    f"  - 冷门号码: {_fmt_hc(cold_1)}\n"
                    f"- **第二區 (1-8)**:\n"
                    f"  - 热门号码: {_fmt_hc(hot_2)}\n"
                    f"  - 冷门号码: {_fmt_hc(cold_2)}"
                )
                sections.append(f"### ❄️🔥 号码冷热频率与遗漏统计\n{desc}")
            except:
                sections.append("### ❄️🔥 号码冷热频率与遗漏统计\n暂无数据")

        if 'tail' in dimensions:
            try:
                t_z1 = stats.get('tail_numbers_z1', {})
                t_z2 = stats.get('tail_numbers_z2', {})
                dist_1 = t_z1.get('distribution', {})
                omi_1 = t_z1.get('omission', {})
                dist_2 = t_z2.get('distribution', {})
                omi_2 = t_z2.get('omission', {})
                def _fmt_tail(dist, omi):
                    lines = []
                    for t in range(10):
                        lines.append(f"尾数 {t}(出现 {dist.get(t, 0)} 次/遗漏 {omi.get(t, 0)} 期)")
                    return ', '.join(lines)
                desc = (
                    f"- **第一區 (Zone 1) 尾数**: {_fmt_tail(dist_1, omi_1)}\n"
                    f"- **第二區 (Zone 2) 尾数**: {_fmt_tail(dist_2, omi_2)}"
                )
                sections.append(f"### 🔢 号码尾数分布统计\n{desc}")
            except:
                sections.append("### 🔢 号码尾数分布统计\n暂无数据")

        if 'markov' in dimensions:
            try:
                weight_cfg = stats.get('markov', {}).get('weights', {})
                markov_str = "暂无"
                if weight_cfg:
                    z_weights = {int(k): v for k, v in dict(weight_cfg).items() if str(k).isdigit() and 1 <= int(k) <= 8}
                    is_sig = weight_cfg.get('_is_significant', True)
                    chi_val = weight_cfg.get('_chi_square_val', 0)
                    sorted_z = sorted(z_weights.items(), key=lambda x: x[1], reverse=True)
                    top_3 = [f"{num}号(跃迁权重 {w:.2f})" for num, w in sorted_z[:3]]
                    bottom_3 = [f"{num}号(跃迁权重 {w:.2f})" for num, w in sorted_z[-3:]]
                    sig_text = f"【显著有效】卡方检验验证(x²={chi_val})。" if is_sig else f"【噪音警告】卡方检验不显著(x²={chi_val} < 14.0671)。"
                    markov_str = (
                        f"基于第二區特别号全量数据的马尔可夫链状态转移：\n - {sig_text}\n"
                        f" - 极高概率跃迁目标：{', '.join(top_3)}\n"
                        f" - 最小概率跃迁目标：{', '.join(bottom_3)}"
                    )
                sections.append(f"### 🕸️ 马尔可夫链第二區特别号跃迁推演\n{markov_str}")
            except:
                sections.append("### 🕸️ 马尔可夫链第二區特别号跃迁推演\n暂无数据")

        if 'consecutive' in dimensions:
            try:
                cons = stats.get('consecutive', {})
                trend = cons.get('current_trend', 'none')
                count = cons.get('consecutive_count', 0)
                rev_prob = cons.get('reversal_probability', 0)
                target_dir = cons.get('reversal_target_direction', 'none')
                curr_y = cons.get('current_y', -1)
                if count > 0 and trend != 'none' and trend != 'flat':
                    dir_chi = "向上攀升" if trend == 'up' else "向下探底"
                    target_chi = "向下回调" if target_dir == 'down' else "向上反弹"
                    desc = (
                        f"- 当期图表状态：第一區 6 码正码和值折线处于【{dir_chi}】趋势中，已连续走势【{count}】期。\n"
                        f"- 当前最新正码和值为: {curr_y}\n"
                        f"- 动量反转预警：基于 RLE 连涨防跌变跳动能，系统推算在当前极限连庄形态下，下一期和值**{target_chi}**的概率为 {rev_prob}%。"
                    )
                    sections.append(f"### 📈 第一區正码和值动量路单拐点预判\n{desc}")
                else:
                    sections.append("### 📈 第一區正码和值动量路单拐点预判\n- 当前正码和值折线波动平稳，暂无连涨连跌拐点。")
            except:
                sections.append("### 📈 第一區正码和值动量路单拐点预判\n暂无数据")

        if 'bayesian' in dimensions:
            try:
                bayesian = stats.get('bayesian', [])
                if bayesian:
                    desc_list = []
                    for item in bayesian[:5]:
                        record_flag = ""
                        if item.get('breaking_record', False):
                            record_flag = " 🚨突破历史极限！"
                        elif item['omission'] >= item.get('max_omission', 999) * 0.8:
                            record_flag = " ⚠️接近极限遗漏值"
                        desc_list.append(f"  - {item['number']}号(后验概率:{item['posterior']} | 遗漏:{item['omission']}期 / 历史极限:{item.get('max_omission','?')}期){record_flag}")
                    sections.append(f"### ⚖️ 贝叶斯推断一区反弹概率 Top 5\n" + '\n'.join(desc_list))
                else:
                    sections.append("### ⚖️ 贝叶斯推断\n无法推算反弹指数")
            except:
                sections.append("### ⚖️ 贝叶斯推断\n暂无数据")

        if 'lstm' in dimensions:
            try:
                lstm = stats.get('lstm', [])
                if lstm:
                    top_5 = lstm[:5]
                    desc_list = [f"  - {item['number']}号(神经网络评分:{item['score']} | AI信号判决:【{item['signal']}】)" for item in top_5]
                    sections.append(f"### 🧠 MLP 神经网络拟合得分 Top 5 (一区号码)\n" + '\n'.join(desc_list))
                else:
                    sections.append("### 🧠 MLP 神经网络拟合得分\n网络未形成明显信号")
            except:
                sections.append("### 🧠 MLP 神经网络拟合得分\n暂无数据")

        data_block = '\n\n'.join(sections)
        recent_detail = ''
        try:
            if 'big_small' in dimensions or 'odd_even' in dimensions:
                oe_z1 = stats.get('odd_even_z1', {})
                bs_z1 = stats.get('big_small_z1', {})
                oe_z2 = stats.get('odd_even_z2', {})
                bs_z2 = stats.get('big_small_z2', {})
                oe_labels = oe_z1.get('labels', [])
                oe_values_z1 = oe_z1.get('values', [])
                bs_values_z1 = bs_z1.get('values', [])
                oe_values_z2 = oe_z2.get('values', [])
                bs_values_z2 = bs_z2.get('values', [])
                n = min(15, len(oe_labels))
                if n > 0:
                    lines = []
                    for i in range(n):
                        idx = len(oe_labels) - n + i
                        period = oe_labels[idx] if idx < len(oe_labels) else '?'
                        oe_v1 = oe_values_z1[idx] if idx < len(oe_values_z1) else 0
                        bs_v1 = bs_values_z1[idx] if idx < len(bs_values_z1) else 0
                        oe_tag1 = f"奇(连{oe_v1})" if oe_v1 > 0 else f"双(连{abs(oe_v1)})"
                        bs_tag1 = f"大(连{bs_v1})" if bs_v1 > 0 else f"小(连{abs(bs_v1)})"
                        oe_v2 = oe_values_z2[idx] if idx < len(oe_values_z2) else 0
                        bs_v2 = bs_values_z2[idx] if idx < len(bs_values_z2) else 0
                        oe_tag2 = f"奇(连{oe_v2})" if oe_v2 > 0 else f"双(连{abs(oe_v2)})"
                        bs_tag2 = f"大(连{bs_v2})" if bs_v2 > 0 else f"小(连{abs(bs_v2)})"
                        lines.append(f"  {period}期: [第一區] {oe_tag1}, {bs_tag1} | [第二區] {oe_tag2}, {bs_tag2}")
                    recent_detail = f"## 最近 {n} 期第一區与第二區走势 K 线跳变明细\n" + '\n'.join(lines)
        except:
            recent_detail = '暂无明细'

        raw_draw_nums_str = "暂无"
        try:
            from modules.config_manager import get_chart_periods
            ai_raw_p = min(50, get_chart_periods(lottery_type='weilitsai').get('ai_raw_data', 300))
            from modules.data_processor import get_db_connection
            conn = get_db_connection()
            rows = conn.execute(
                f"SELECT draw_number, num1, num2, num3, num4, num5, num6, special_num FROM lottery_history WHERE lottery_type='weilitsai' ORDER BY draw_date DESC, draw_number DESC LIMIT {ai_raw_p}",
            ).fetchall()
            conn.close()
            if rows:
                rows = list(reversed(rows))
                raw_draw_nums_str = '\n'.join([
                    f"  {r[0]}期: 一区({r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[6]}) | 二区({r[7]})" for r in rows
                ])
        except:
            raw_draw_nums_str = '暂无'

        weights_info = ""
        if system_weights:
            weight_lines = []
            if 'big_small' in dimensions:
                _big_w = system_weights.get('big_weight', 1.0)
                _small_w = system_weights.get('small_weight', 1.0)
                weight_lines.append(f"- 大号权重: {_big_w:.2f}，小号权重: {_small_w:.2f}")
            if 'odd_even' in dimensions:
                _odd_w = system_weights.get('odd_weight', 1.0)
                _even_w = system_weights.get('even_weight', 1.0)
                weight_lines.append(f"- 单号权重: {_odd_w:.2f}，双号权重: {_even_w:.2f}")
            if 'hot_cold' in dimensions:
                hc_w_z1 = system_weights.get('hot_cold_weights_z1', {})
                hc_w_z2 = system_weights.get('hot_cold_weights_z2', {})
                z1_w_list = [f"{num}号({w:.2f})" for num, w in hc_w_z1.items() if w != 1.0] if isinstance(hc_w_z1, dict) else []
                z2_w_list = [f"{num}号({w:.2f})" for num, w in hc_w_z2.items() if w != 1.0] if isinstance(hc_w_z2, dict) else []
                if z1_w_list:
                    weight_lines.append(f"- 第一區底层冷热/遗漏加权: {', '.join(z1_w_list)}")
                if z2_w_list:
                    weight_lines.append(f"- 第二區底层冷热/遗漏加权: {', '.join(z2_w_list)}")
            if weight_lines:
                weights_info = "\n## 底层图表算法赋予的核心权重系数参考（数值>1代表看好，<1代表看衰）：\n" + "\n".join(weight_lines) + "\n"

        dim_names = {
            'big_small': '大小走势',
            'odd_even': '单双走势',
            'hot_cold': '冷热频率',
            'tail': '尾数分布',
            'markov': '马尔可夫',
            'consecutive': '正码和值动量拐点',
            'bayesian': '贝叶斯',
            'lstm': 'MLP神经网络'
        }
        active_dims_text = '、'.join([dim_names.get(d, d) for d in dimensions])

        report_parts = [
            "1. **宏观盘面与走势图景**：结合最近走势 and 已选维度的开奖信号概述，阐述威力彩 Zone 1 与 Zone 2 的总体盘面特征。",
            f"2. **加权维度逐项剖析**：必须针对本次勾选的【所有 {len(dimensions)} 个独立维度（{active_dims_text}）】逐一分段进行说明。请深入研判第一區 1-38 与第二區 1-8 的数据异同，严密扣合概率与走势规律。",
        ]
        if weights_info:
            report_parts.append("3. **算法底层加权解码**：结合上述各个维度的剖析，带入底层设定的各个权重系数，解释系统是如何利用权重抑制次要矛盾、放大主要趋势的。")
            
        if is_wheeling:
            report_parts.append(f"4. **旋转矩阵包牌共振与最后定胆**：阐述为什么本期底层数学模型筛选出的【{len(pre_sel_nums)}码精选码池】{pre_sel_nums} 在组合概率上具有巨大优势，并合理推演选择第二區特别号 {pre_sel_special} 的合理性；同时说明使用旋转矩阵（中5保4）进行包牌对冲，是如何将资金利用率和中奖概率期望最大化的。")
        else:
            report_parts.append(f"4. **双区多维共振与最后定胆**：论证在多重算法约束和指标下产生的合力，是如何完美指向第二區特别号码 {pre_sel_special} 与第一區号码组合 {pre_sel_nums} 这个推算解的。通过大量的概率均值回归、连庄断龙、极限遗漏反弹进行论证。")
            
        report_structure = "\n\n".join(report_parts)

        active_algos = []
        if 'big_small' in dimensions or 'odd_even' in dimensions: active_algos.append('大小单双防连跳')
        if 'markov' in dimensions: active_algos.append('马尔可夫转移')
        if 'bayesian' in dimensions: active_algos.append('贝叶斯反弹')
        if 'lstm' in dimensions: active_algos.append('MLP神经网络')
        if 'hot_cold' in dimensions: active_algos.append('冷热遗漏')
        if 'tail' in dimensions: active_algos.append('尾数分布')
        algo_desc = '、'.join(active_algos) if active_algos else '统计算法'

        if is_wheeling:
            prompt_nums_str = f"👉 **本期底层算法最终敲定的【第一區旋转矩阵 {len(pre_sel_nums)}码精选码池】：{pre_sel_nums}**"
            target_lock_str = f"1. 目标锁定：你最后的分析结论【必须、无可争议地】指向第一區这 {len(pre_sel_nums)} 个精选码池号码 {pre_sel_nums} 和 second 區特别号 {pre_sel_special}。所有的概率推理、数学模型均须围绕这些码池号码展开，论证其作为旋转矩阵输入的概率优势与保底中奖的合理性。"
        else:
            prompt_nums_str = f"👉 **本期底层算法最终敲定的【第一區号码组合】：{pre_sel_nums}**"
            target_lock_str = f"1. 目标锁定：你最后的分析结论【必须、无可争议地】指向第一區号码组合 {pre_sel_nums} 和 second 區特别号 {pre_sel_special}。所有的概率推理、数学模型推算均须收敛于此，论证其合理性与概率优势。"

        prompt = f"""你是一位资深的彩票走势分析专家与系统推理报告撰写者。

【系统高度机密指令】：底层的工业级统计算法（含{algo_desc}等）已经高度结合了图表规则，**精准计算并选定了本期的号码**。
你的唯一任务是：作为系统的“首席分析师”，根据下方的【历史走势数据】与【底层权重系数】，写一篇严丝合缝、极具逻辑说服力的长篇图表规则报告，向用户解释**底层数学模型基于图表为什么推算出了这组号码**，从而彻底消除你的逻辑幻觉，完美匹配图表。

【注意】：台湾威力彩(威力彩)由两个区组成，开奖规则与六合彩截然不同：
第一區 (Zone 1): 从 1-38 中随机摇出 6 个号码 (正码)
第二區 (Zone 2): 从 1-8 中随机摇出 1 个号码 (特别号)
请绝对不要提及任何生相动物（如鼠、牛等）、球色波段（如红、蓝、绿等颜色波段）、五行属性等其他彩票玩法的特有术语！

{prompt_nums_str}
👉 **本期底层算法最终敲定的【第二區特别号】：{pre_sel_special}**

⚠️ 绝不妥协的纪律要求：
{target_lock_str}
2. 🚫 严格维度隔离：用户本次只勾选了【{active_dims_text}】这些维度。你的分析报告中**只允许引用和讨论这些维度的数据**。绝对禁止提及、引用或编造任何未勾选维度的数据或概念。
3. ✨ 深度关注图像反转与图表多模态综合：你必须假装你正盯着几张实时更新的【数据走势图表】。请用“从大小单双折线图、和值连涨防跌曲线、冷热遗漏分布图来看”等典型的图表视觉描述手法，把【大小】、【单双】、【尾数】和【正码和值动量】这几个图表维度的特征联合研判！提取它们在“图表轨迹”上的共振图形缩影（如双向探顶、和值极限回踩等），向用户论证均值回归规律必然爆发的原因。
4. 杜绝对数据的数值幻觉：你在分析中引用的任何数据百分比，**必须**从下方的《已选维度统计数据》中提取！如果数据里没提，绝对不要自己编造具体数字。

## 最近 50 期原始 【中奖号码】 序列（从旧到新，供你挖掘第一區和值与第二區特别号的隐藏走势规律）：
{raw_draw_nums_str}

{recent_detail}

## 已选维度统计数据与底层推算中间变量
{data_block}
{weights_info}

## 分析撰写结构要求（参考字数 800 - 1500 字）
请按以下模块化结构撰写这篇极品分析报告（格式自行美化，可使用加粗等）：
{report_structure}

请严格以如下 JSON 格式回复（将你的长篇推算报告置于 analysis 字段，号码原样回传）：
{{
    "numbers": {pre_sel_nums},
    "special_num": {pre_sel_special},
    "analysis": "你的严密推算报告...",
    "confidence": "高"
}}"""
        return prompt

    type_name = '新澳门六合彩' if lottery_type == 'macaujc2' else '澳门六合彩'
    dim_names = {
        'big_small': '大小走势',
        'odd_even': '单双走势',
        'hot_cold': '冷热频率',
        'tail': '尾数分布',
        'zodiac': '生肖权重',
        'color': '波色推测',
        'markov': '马尔可夫',
        'consecutive': '路单连涨防跌',
        'bayesian': '贝叶斯',
        'lstm': 'LSTM'
    }
    active_dims_text = '、'.join([dim_names.get(d, d) for d in dimensions])
    
    recent_detail = ''
    raw_special_nums = ''
    try:
        if 'big_small' in dimensions or 'odd_even' in dimensions:
            oe = stats.get('odd_even', {})
            bs = stats.get('big_small', {})
            oe_labels = oe.get('labels', [])
            oe_values = oe.get('values', [])
            bs_values = bs.get('values', [])
            
            # 取最后 15 期走势明细（既能观察连续规律又不至于给模型过大压力）
            n = min(15, len(oe_labels))
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
        
        from modules.config_manager import get_chart_periods
        # 生肖预测无需三百期宏观冷热记录，取近 50 期以节约 Token
        ai_raw_p = min(50, get_chart_periods(lottery_type=lottery_type).get('ai_raw_data', 300))
        from modules.data_processor import get_db_connection
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
            raw_special_nums = ' → '.join([f"{r[1]}号({_get_color(int(r[1]))})" for r in rows])
    except:
        recent_detail = recent_detail or '暂无明细'
        raw_special_nums = '暂无'
    
    sections = []
    
    sections.extend(_build_common_dimensions(stats, dimensions))
    if 'zodiac' in dimensions:
        zodiac_text = "未收集到足够数据"
        z_lines = []
        try:
            zs = stats.get('zodiac_stats', {})
            if isinstance(zs, dict) and 'draws' in zs:
                draws = zs.get('draws', [])
                zodiac_order = zs.get('zodiac_order', [])
                recent_draws = draws[-30:]
                for d in recent_draws:
                    z_name = zodiac_order[d['zodiac_idx']] if d['zodiac_idx'] < len(zodiac_order) else '?'
                    z_lines.append(f"{d['draw_number']}: {d['num']}号({z_name})")
                recent_z_str = '\n'.join(z_lines) if z_lines else '暂无'
                zodiac_freq = {}
                for d in draws:
                    z_name = zodiac_order[d['zodiac_idx']] if d['zodiac_idx'] < len(zodiac_order) else '?'
                    zodiac_freq[z_name] = zodiac_freq.get(z_name, 0) + 1
                total_z_draws = len(draws)
                avg_z = total_z_draws / 12 if total_z_draws > 0 else 0
                freq_list = []
                for z, count in zodiac_freq.items():
                    diff_pct = ((count - avg_z) / avg_z) * 100 if avg_z > 0 else 0
                    mark = "🔥热" if diff_pct > 30 else ("❄️冷" if diff_pct < -30 else "平")
                    freq_list.append((z, count, diff_pct, mark))
                freq_list.sort(key=lambda x: x[1], reverse=True)
                freq_str = ', '.join([f"{z}({c}次 {mark})" for z, c, _, mark in freq_list])
                trend_pattern = "分析走势..."
                if len(recent_draws) >= 5:
                    y_vals = [d['zodiac_idx'] for d in recent_draws[-5:]]
                    if all(y_vals[i] <= y_vals[i-1] for i in range(1, len(y_vals))) and y_vals[0] != y_vals[-1]:
                        trend_pattern = "📈 近5期生肖Y轴呈上升趋势，关注可能见顶回落"
                    elif all(y_vals[i] >= y_vals[i-1] for i in range(1, len(y_vals))) and y_vals[0] != y_vals[-1]:
                        trend_pattern = "📉 近5期生肖Y轴呈下降趋势，关注反弹上行信号"
                    else:
                        trend_pattern = "🔀 近5期生肖走势无明显单向规律"
                zodiac_text = f"【最近30期特码生肖路单】：\n{recent_z_str}\n\n【生肖频率分布】（近{total_z_draws}期，均值={avg_z:.1f}次）：\n{freq_str}\n\n【走势模式】：{trend_pattern}"
            sections.append(f"### 🐾 特码生肖路单深度分析\n{zodiac_text}")
        except:
            sections.append("### 🐾 特码生肖路单深度分析\n暂无数据")

    if 'markov' in dimensions:
        try:
            weight_cfg = stats.get('markov', {}).get('weights', {})
            markov_str = "暂无"
            if weight_cfg:
                zodiac_names = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
                z_weights = {k: v for k, v in dict(weight_cfg).items() if k in zodiac_names}
                is_sig = weight_cfg.get('_is_significant', True)
                chi_val = weight_cfg.get('_chi_square_val', 0)
                sorted_z = sorted(z_weights.items(), key=lambda x: x[1], reverse=True)
                top_3 = [f"{z}(权重{w:.2f})" for z, w in sorted_z[:3]]
                bottom_3 = [f"{z}(权重{w:.2f})" for z, w in sorted_z[-3:]]
                sig_text = f"【显著有效】卡方检验验证(x²={chi_val})。" if is_sig else f"【噪音警告】卡方检验不显著(x²={chi_val} < 19.675)。"
                markov_str = (
                    f"基于全量特码数据的马尔可夫链状态转移：\n - {sig_text}\n"
                    f" - 极高概率跃迁目标：{', '.join(top_3)}\n"
                    f" - 最小概率跃迁目标：{', '.join(bottom_3)}"
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
                if count < 2:
                    desc = (
                        f"- 当期图表状态：生肖Y坐标路单中仅连续【{count}】期【{dir_chi}】。\n"
                        f"- 动量预警：当前路单图表处于弱信号横盘区间，暂未形成单边图表趋势，不建议作为图表研判核心依据。"
                    )
                else:
                    desc = (
                        f"- 当期图表状态：生肖Y坐标路单折线已连续单边【{count}】期【{dir_chi}】（实质等同 {count+1} 连形态）。\n"
                        f"- 动量反转预警：从图表规律看极端单边连续一般在3连左右发生掉头（历史极限5连）。当前图表已满足甚至突破掉头条件，极限回归图表【{target_chi}】落点反弹概率高达 {rev_prob}%。"
                    )
                sections.append(f"### 📈 生肖路单拐点预判(图表连涨防跌体系)\n{desc}")
            else:
                sections.append("### 📈 生肖路单拐点预判\n- 当前处于横盘，暂无明显连涨/连跌反转。")
        except:
            sections.append("### 📈 生肖路单拐点预判\n暂无数据")

    if 'bayesian' in dimensions:
        try:
            bayesian = stats.get('bayesian', [])
            if bayesian:
                desc_list = []
                for item in bayesian:
                    record_flag = ""
                    if item.get('breaking_record', False):
                        record_flag = " \U0001f6a8\u7a81\u7834\u5386\u53f2\u6781\u503c\uff01"
                    elif item['omission'] >= item.get('max_omission', 999) * 0.8:
                        record_flag = " \u26a0\ufe0f\u63a5\u8fd1\u6781\u503c"
                    desc_list.append(f"{item['zodiac']}(\u540e\u9a8c\u6743\u91cd:{item['posterior']} | \u5df2\u9057\u6f0f:{item['omission']}\u671f / \u5386\u53f2\u6781\u503c:{item.get('max_omission','?')}\u671f){record_flag}")
                sections.append(f"### \u2696\ufe0f \u8d1d\u53f6\u65af\u63a8\u65ad(\u6781\u7aef\u53cd\u5f39\u6355\u6349\uff0c\u5168\u90e812\u751f\u8096)\n{chr(10).join(desc_list)}")
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
                sections.append(f"### 🧠 LSTM 时间走势拟合(深层非线性)\n势头最猛前3名生肖：\n{chr(10).join(desc_list)}")
            else:
                sections.append("### 🧠 LSTM 时间走势拟合\n网络未形成明显信号")
        except:
            sections.append("### 🧠 LSTM 时间走势拟合\n暂无数据")
    
    data_block = '\n\n'.join(sections)
    
    from modules.statistics_engine import get_zodiac_mapping
    z_map2 = get_zodiac_mapping(lottery_type)
    zmap_text = "【重要系统设定：当前年份2026马年，1-49生肖精确映射】：\n"
    for zname in ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']:
        nums = [k for k, v in z_map2.items() if v == zname]
        zmap_text += f"{zname}: {nums}；"
    
    weights_info = ""
    if system_weights:
        weight_lines = []
        if 'big_small' in dimensions:
            _big_w = system_weights.get('big_weight', 1.0)
            _small_w = system_weights.get('small_weight', 1.0)
            weight_lines.append(f"- 大号权重: {_big_w:.2f}，小号权重: {_small_w:.2f}")
        if 'odd_even' in dimensions:
            _odd_w = system_weights.get('odd_weight', 1.0)
            _even_w = system_weights.get('even_weight', 1.0)
            weight_lines.append(f"- 单号权重: {_odd_w:.2f}，双号权重: {_even_w:.2f}")
        if 'hot_cold' in dimensions:
            _hc_dict = system_weights.get('hot_cold_weights', {})
            _hc_w = _hc_dict.get(pre_sel_special, 1.0) if isinstance(_hc_dict, dict) else 1.0
            weight_lines.append(f"- 本期核心【{pre_sel_special}号】底层冷热加权: {_hc_w:.2f}")
        if 'tail' in dimensions:
            _tail_dict = system_weights.get('tail_weights', {})
            _tail_w = _tail_dict.get(pre_sel_special % 10, 1.0) if isinstance(_tail_dict, dict) else 1.0
            weight_lines.append(f"- 本期核心【{pre_sel_special}号】底层尾数加权: {_tail_w:.2f}")
        if weight_lines:
            weights_info = "\n## 底层图表算法赋予的核心权重系数参考（数值>1代表看好，<1代表看衰）：\n" + "\n".join(weight_lines) + "\n"

    report_parts = []
    report_parts.append("1. **宏观盘面与走势图景**：结合最近走势和已选维度的开奖信号概述。")
    
    # 强制分维度点评
    conv_parts = []
    if 'big_small' in dimensions: conv_parts.append('大小')
    if 'odd_even' in dimensions: conv_parts.append('单双')
    if 'hot_cold' in dimensions: conv_parts.append('冷热')
    if 'tail' in dimensions: conv_parts.append('尾数')
    if 'color' in dimensions: conv_parts.append('波色')
    if 'zodiac' in dimensions: conv_parts.append('生肖路单')
    if 'markov' in dimensions: conv_parts.append('马尔可夫链')
    if 'consecutive' in dimensions: conv_parts.append('路单连涨防跌')
    if 'bayesian' in dimensions: conv_parts.append('贝叶斯')
    if 'lstm' in dimensions: conv_parts.append('LSTM')
    
    conv_text = '、'.join(conv_parts) if conv_parts else active_dims_text
    
    report_parts.append(f"2. **加权维度逐项剖析**：必须针对本次勾选的【所有 {len(conv_parts)} 个独立维度（{conv_text}）】逐一分段进行说明。不要遗漏任何一个勾选的维度，哪怕该维度当前信号不强烈或权重较小，也要说明它在当前盘面中的中立或制衡作用。（例如：大小维度如何、单双维度的天花板如何、生肖位图如何...）")
    
    if weights_info:
        report_parts.append(f"3. **算法底层加权解码**：结合上述各个维度的剖析，带入底层设定的各个权重系数，解释系统是如何利用权重抑制次要矛盾、放大主要趋势的。")
    
    if is_wheeling:
        report_parts.append(f"4. **多维共振与特别号定胆 ({pre_sel_special}号)**：经过对【{conv_text}】的多维独立分析和权重总结归票，论证在此多重约束下产生的合力是如何完美指向特别号 {pre_sel_special} 这个推算解的。")
        report_parts.append(f"5. **旋转矩阵包牌建议**：简述为什么选择这 {len(pre_sel_nums)} 个精选码池号码 {pre_sel_nums} 并结合特别号 {pre_sel_special} 做旋转矩阵组合（如中5保4等）进行包牌对冲，可以使您的资金效率最大化。")
    else:
        report_parts.append(f"4. **多维共振与最后定胆 ({pre_sel_special}号)**：经过对【{conv_text}】的多维独立分析和权重总结归票，论证在此多重约束下产生的合力是如何完美指向 {pre_sel_special} 这个推算解的。")
        report_parts.append(f"5. **正码矩阵建议**：简述 {pre_sel_nums} 作为本场陪衬或防爆冷的合理性。")
    report_structure = "\n\n".join(report_parts)

    active_algos = []
    if 'big_small' in dimensions or 'odd_even' in dimensions: active_algos.append('高级RLE防连跳')
    if 'markov' in dimensions: active_algos.append('马尔可夫')
    if 'bayesian' in dimensions: active_algos.append('贝叶斯极值反弹')
    if 'lstm' in dimensions: active_algos.append('LSTM')
    if 'hot_cold' in dimensions: active_algos.append('冷热频率')
    if 'tail' in dimensions: active_algos.append('尾数分布')
    algo_desc = '、'.join(active_algos) if active_algos else '统计算法'

    if is_wheeling:
        prompt_nums_str = f"👉 **本期底层算法最终敲定的【旋转矩阵 {len(pre_sel_nums)}码精选码池】：{pre_sel_nums}**"
        target_lock_str = f"1. 目标锁定：你最后的分析结论【必须、无可争议地】指向特别号 {pre_sel_special}，逻辑演绎必须闭环于此号码。精选码池正码 {pre_sel_nums} 在此作为旋转矩阵备选码池进行论证即可。"
    else:
        prompt_nums_str = f"👉 **本期底层算法最终敲定的【正码配置】：{pre_sel_nums}**"
        target_lock_str = f"1. 目标锁定：你最后的分析结论【必须、无可争议地】指向特码 {pre_sel_special}，逻辑演绎必须闭环于此号码。正码 {pre_sel_nums} 在此作为陪衬提及即可。"

    recent_detail_block = f"{recent_detail}" if recent_detail else ""
    prompt = f"""你是一位资深的彩票走势分析专家与系统推理报告撰写者。

【系统高度机密指令】：底层的工业级统计算法（含{algo_desc}等）已经高度结合了图表规则，**精准计算并选定了本期的号码**。
你的唯一任务是：作为系统的“首席分析师”，根据下方的【历史走势数据】与【底层权重系数】，写一篇严丝合缝、极具逻辑说服力的长篇图表规则报告，向用户解释**底层数学模型基于图表为什么推算出了这组号码**，从而彻底消除你的逻辑幻觉，完美匹配图表。

👉 **本期底层算法最终敲定的【特码】：{pre_sel_special}号**
{prompt_nums_str}

{zmap_text}

⚠️ 绝不妥协的纪律要求：
{target_lock_str}
2. 🚫 严格维度隔离：用户本次只勾选了【{active_dims_text}】这些维度。你的分析报告中**只允许引用和讨论这些维度的数据**。绝对禁止提及、引用或编造任何未勾选维度的数据或概念（如用户没勾选马尔可夫就不能提马尔可夫）。违反此条视为严重错误！
3. ✨ 深度关注图像反转与图表多模态综合（极核心）：你必须假装你正盯着几张实时更新的【数据图表】。请用“从最新的走势图、路单连线趋势、大小单双柱状图联动来看”等典型的图表视觉描述手法，把【单双】、【大小】、【尾数】和【路单连涨防跌】这几个图表维度的几何特征联合研判！提取它们在“图表轨迹”上的共振图形缩影（如双向探顶、W底、断崖式极限回踩等），通过大量描绘“图形盘面表征”，向用户论证均值回归规律必然爆发的原因。
4. 杜绝对数据的数值幻觉：你在分析中引用的任何数据百分比，**必须**从下方的《已选维度统计数据》中提取！如果数据里没提，绝对不要自己编造具体数字。

## 最近 300 期原始 【特码】 序列（从旧到新，供你挖掘隐藏视觉规律与 12121 类似的图形）
{raw_special_nums}

{recent_detail_block}

## 已选维度统计数据与底层推算中间变量
{data_block}
{weights_info}

## 分析撰写结构要求（参考字数 800 - 1500 字）
请按以下模块化结构撰写这篇极品分析报告（格式自行美化，可使用加粗等）：
{report_structure}

请严格以如下 JSON 格式回复（将你的长篇推算报告置于 analysis 字段，号码原样回传）：
{{
    "numbers": {pre_sel_nums},
    "special_num": {pre_sel_special},
    "analysis": "你的严密推算报告...",
    "confidence": "高"
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
