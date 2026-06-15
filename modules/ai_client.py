# AI 通信客户端模块
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
    """检查模型链是否都属于同一个平台/自建网关，并返回相应的提示信息（已废弃该提示）"""
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



def _fallback_result(reason: str) -> dict:
    return {
        'success': False,
        'numbers': [],
        'special_num': 0,
        'analysis': reason,
        'confidence': '无'
    }

def call_ai_api(prompt: str, stats_summary: dict, lottery_type: str, dimensions: list, pre_sel_nums: list = None, pre_sel_special: int = 1, is_wheeling: bool = False) -> dict:
    try:
        platform, api_key, model_name, base_url = _resolve_api_config()
        model_chain = [{"name": "主模型", "platform": platform, "api_key": api_key, "model_name": model_name, "base_url": base_url}]
        bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
        if bp1 and bm1: model_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
        bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
        if bp2 and bm2: model_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
            
        result = None
        last_exception = None
        called_model_label = "主模型"
        called_model_name = model_name
        
        for m_info in model_chain:
            try:
                key_len = len(m_info['api_key']) if m_info['api_key'] else 0
                print(f"🤖 正在尝试通过 {m_info['name']} ({m_info['model_name']} @ {m_info['platform']}, key_len={key_len}) 进行预测...")
                
                if not m_info['api_key'] and m_info['platform'] == 'google':
                    raise ValueError("未配置 Gemini API Key")
                
                if m_info['platform'] == 'google':
                    result = _call_gemini(prompt, m_info['api_key'], m_info['model_name'], stats_summary, lottery_type, dimensions)
                else:
                    result = _call_openai_compatible(prompt, m_info['api_key'], m_info['model_name'], m_info['base_url'])
                
                if result and result.get('analysis'):
                    called_model_label = m_info['name']
                    called_model_name = m_info['model_name']
                    break
            except Exception as e:
                print(f"❌ {m_info['name']} ({m_info['model_name']}) 调用失败: {e}")
                last_exception = e
                continue
                
        if not result:
            raise last_exception if last_exception else ValueError("未配置可用模型或尝试均失败")
        
        numbers = sorted(pre_sel_nums) if pre_sel_nums else []
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
            analysis_text = f"【系统提示：由于主模型服务响应失败，系统已自动启用 {called_model_label} ({called_model_name}) 完成预测。】\n\n" + analysis_text
            
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
        try:
            m_chain = [{"name": "主模型", "platform": _resolve_api_config()[0], "api_key": _resolve_api_config()[1], "model_name": _resolve_api_config()[2], "base_url": _resolve_api_config()[3]}]
            bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
            if bp1 and bm1: m_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
            bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
            if bp2 and bm2: m_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
            tip = _check_same_platform_tip(m_chain)
        except:
            tip = ""
        return _fallback_result(f'AI 分析异常 ({type(e).__name__}: {str(e)[:100]}){tip}，已降级为传统加权模式')


def call_zodiac_ai_api(prompt: str, stats_summary: dict, lottery_type: str, dimensions: list) -> dict:
    from modules.prompts.macau import _fallback_zodiac
    try:
        platform, api_key, model_name, base_url = _resolve_api_config()
        model_chain = [{"name": "主模型", "platform": platform, "api_key": api_key, "model_name": model_name, "base_url": base_url}]
        bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
        if bp1 and bm1: model_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
        bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
        if bp2 and bm2: model_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
        
        result = None
        last_exception = None
        called_model_label = "主模型"
        called_model_name = model_name
        
        for m_info in model_chain:
            try:
                if not m_info['api_key'] and m_info['platform'] == 'google':
                    raise ValueError("未配置 Gemini API Key")
                
                if m_info['platform'] == 'google':
                    result = _call_gemini(prompt, m_info['api_key'], m_info['model_name'], stats_summary, lottery_type, dimensions)
                else:
                    result = _call_openai_compatible(prompt, m_info['api_key'], m_info['model_name'], m_info['base_url'])
                
                if result and result.get('analysis'):
                    called_model_label = m_info['name']
                    called_model_name = m_info['model_name']
                    break
            except Exception as e:
                last_exception = e
                continue
                
        if not result:
            raise last_exception if last_exception else ValueError("未配置可用模型或所有尝试失败")
            
        analysis_text = result.get('analysis', 'AI 分析完成')
        if called_model_label != "主模型":
            analysis_text = f"【系统提示：由于主模型服务响应失败，系统已自动启用 {called_model_label} ({called_model_name}) 完成生肖预测。】\n\n" + analysis_text
            
        return {
            'success': True,
            'zodiac_pred': result.get('zodiac_pred', []),
            'analysis': analysis_text,
            'confidence': result.get('confidence', '高')
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _fallback_zodiac(f'AI 分析异常 ({type(e).__name__}: {str(e)[:100]})，已降级为本地系统预测')


# ==================== STREAMING (流式) API 实现 ====================

def _call_openai_compatible_stream(prompt: str, api_key: str, model_name: str, base_url: str):
    import requests
    import json
    
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
        'stream': True  # 开启流式
    }
    
    if 'integrate.api.nvidia.com' not in base_url:
        payload['max_tokens'] = 4096

    print(f"💡 正在发送流式推测请求给本地模型 ({model_name}) @ {base_url}...")
    
    try:
        timeout_cfg = 180 if 'integrate.api.nvidia.com' in base_url else 120
        # 建立连接
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout_cfg, stream=True)
        resp.raise_for_status()
        
        full_content = ""
        for line in resp.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        if chunk_json['choices'] and chunk_json['choices'][0]['delta']:
                            chunk_text = chunk_json['choices'][0]['delta'].get('content', '')
                            if chunk_text:
                                full_content += chunk_text
                                yield {"type": "chunk", "text": chunk_text}
                    except json.JSONDecodeError:
                        pass
                        
        # 结束后统一解析并产出最终 result
        full_content = full_content.strip()
        if full_content.startswith('```'):
            lines = full_content.split('\n')
            if lines[0].startswith('```'): lines = lines[1:]
            if lines and lines[-1].strip() == '```': lines = lines[:-1]
            full_content = '\n'.join(lines)
        
        import re as _re
        full_content = _re.sub(r'"[\s*]*([a-zA-Z_][a-zA-Z0-9_]*)[\s*]*"(\s*:)', r'"\1"\2', full_content)
        
        try:
            result = json.loads(full_content)
            if not isinstance(result, dict):
                result = {
                    "analysis": str(result)[:3000],
                    "confidence": "低（模型未按格式回复对象）"
                }
        except json.JSONDecodeError:
            result = {
                "analysis": full_content[:3000],
                "confidence": "低（模型未按格式回复JSON）"
            }
            
        yield {"type": "result", "payload": result}
        
    except Exception as e:
        raise e


def _call_gemini_stream(prompt: str, api_key: str, model_name: str, stats_summary: dict, lottery_type: str, dimensions: list):
    from google import genai
    import json
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
        pass
    
    print(f"💡 正在发送流式推测请求给 Gemini ({model_name})...")
    
    try:
        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.7,
            }
        )
        
        full_content = ""
        for chunk in response_stream:
            chunk_text = chunk.text
            if chunk_text:
                full_content += chunk_text
                yield {"type": "chunk", "text": chunk_text}
                
        # 结束后返回解析
        full_content = full_content.strip()
        try:
            result = json.loads(full_content)
            if not isinstance(result, dict):
                result = {
                    "analysis": str(result)[:3000],
                    "confidence": "低（流式解析返回了非字典对象）"
                }
        except Exception:
            result = {
                "analysis": full_content[:3000],
                "confidence": "低（流式解析失败）"
            }
        yield {"type": "result", "payload": result}
        
    except Exception as e:
        raise e


def call_ai_api_stream(prompt: str, stats_summary: dict, lottery_type: str, dimensions: list, pre_sel_nums: list = None, pre_sel_special: int = 1, is_wheeling: bool = False):
    import time
    
    try:
        platform, api_key, model_name, base_url = _resolve_api_config()
        model_chain = [{"name": "主模型", "platform": platform, "api_key": api_key, "model_name": model_name, "base_url": base_url}]
        bp1, bk1, bm1, bb1 = _resolve_backup_api_config(1)
        if bp1 and bm1: model_chain.append({"name": "备用模型 2", "platform": bp1, "api_key": bk1, "model_name": bm1, "base_url": bb1})
        bp2, bk2, bm2, bb2 = _resolve_backup_api_config(2)
        if bp2 and bm2: model_chain.append({"name": "备用模型 3", "platform": bp2, "api_key": bk2, "model_name": bm2, "base_url": bb2})
    except Exception:
        yield {"type": "result", "payload": _fallback_result("未配置 AI 模型 API Key，系统降级为本地系统分析。")}
        return
        
    last_exception = None
    
    for i, model_cfg in enumerate(model_chain):
        platform = model_cfg.get('platform')
        api_key = model_cfg.get('api_key')
        model_name = model_cfg.get('model_name')
        base_url = model_cfg.get('base_url')
        
        label = "主模型" if i == 0 else f"备用模型 {i}"
        
        try:
            if platform == 'google':
                gen = _call_gemini_stream(prompt, api_key, model_name, stats_summary, lottery_type, dimensions)
            else:
                gen = _call_openai_compatible_stream(prompt, api_key, model_name, base_url)
                
            has_yielded = False
            final_result = None
            
            for item in gen:
                if item["type"] == "chunk":
                    has_yielded = True
                    yield item
                elif item["type"] == "result":
                    final_result = item["payload"]
                    
            if not final_result:
                raise ValueError("模型未返回最终结果")
                
            analysis_text = final_result.get('analysis', 'AI 分析完成')
            
            same_platform_tip = _check_same_platform_tip(model_chain)
            
            if label != "主模型":
                analysis_text = f"【系统提示：主模型无响应，自动切换至 {label} ({model_name})】\n\n" + analysis_text
                
            analysis_text += same_platform_tip
            final_result['analysis'] = analysis_text
            
            yield {"type": "result", "payload": {
                'success': True,
                'numbers': final_result.get('numbers', []),
                'zodiacs': final_result.get('zodiacs', []),
                'special_num': final_result.get('special_num', pre_sel_special),
                'special_zodiac': final_result.get('special_zodiac', ''),
                'analysis': analysis_text,
                'confidence': final_result.get('confidence', '高'),
                'is_wheeling': is_wheeling,
                'platform': platform
            }}
            return
            
        except Exception as e:
            print(f"⚠️ {label} 流式请求失败: {e}")
            last_exception = e
            continue
            
    yield {"type": "result", "payload": _fallback_result(f"AI 流式分析异常 ({type(last_exception).__name__})，降级为本地预测")}

