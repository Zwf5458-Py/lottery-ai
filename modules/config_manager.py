"""
全局配置管理器
功能：为每个用户从其独立数据库中读写配置，为所有模块提供统一的配置入口。
对于未登录场景（如 AI 引擎内部调用），降级读取全局 config.json。
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

DEFAULT_CONFIG = {
    "ai": {
        "platform": "google",
        "model": "gemini-2.5-pro",
        "api_key": ""
    },
    "chart_periods": {
        "zodiac_trend": 200,
        "odd_even": 100,
        "big_small": 100,
        "markov": 0,
        "hot_cold": 100,
        "tail": 100,
        "bayesian": 100,
        "lstm": 100,
        "ai_raw_data": 300
    }
}


def load_config(user_id=None) -> dict:
    """
    读取配置。
    - 如果传入 user_id，从该用户的独立数据库读取；
    - 否则尝试从 Flask session 获取 user_id 读取；
    - 最后降级读取全局 config.json（兼容后端引擎内部调用）。
    """
    if user_id is None:
        try:
            from flask import has_request_context, session
            if has_request_context() and 'user_id' in session:
                user_id = session['user_id']
        except Exception:
            pass

    if user_id is not None:
        return _load_user_config(user_id)

    # 降级：读取全局 config.json
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, cfg)
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(data: dict, user_id=None) -> bool:
    """
    保存配置。
    - 如果传入 user_id，保存到该用户的独立数据库；
    - 否则降级保存到全局 config.json。
    """
    if user_id is not None:
        return _save_user_config(data, user_id)

    # 降级：保存到全局 config.json
    try:
        current = load_config()
        merged = _deep_merge(current, data)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_ai_config(user_id=None) -> dict:
    """获取 AI 模型配置"""
    return load_config(user_id).get('ai', DEFAULT_CONFIG['ai'])


def get_chart_periods(user_id=None) -> dict:
    """获取各图表统计期数"""
    return load_config(user_id).get('chart_periods', DEFAULT_CONFIG['chart_periods'])


# ==================== 用户独立数据库配置读写 ====================

def _load_user_config(user_id: int) -> dict:
    """从用户独立数据库加载配置"""
    try:
        from modules.auth import get_user_db_connection
        conn = get_user_db_connection(user_id)
        rows = conn.execute("SELECT key, value FROM user_settings").fetchall()
        conn.close()

        if not rows:
            return DEFAULT_CONFIG.copy()

        config = DEFAULT_CONFIG.copy()
        for r in rows:
            try:
                config[r[0]] = json.loads(r[1])
            except Exception:
                config[r[0]] = r[1]
        return config
    except Exception:
        return DEFAULT_CONFIG.copy()


def _save_user_config(data: dict, user_id: int) -> bool:
    """将配置保存到用户独立数据库"""
    try:
        from modules.auth import get_user_db_connection
        current = _load_user_config(user_id)
        merged = _deep_merge(current, data)

        conn = get_user_db_connection(user_id)
        for key in ['ai', 'chart_periods']:
            if key in merged:
                conn.execute(
                    "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(merged[key], ensure_ascii=False))
                )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并字典，override 覆盖 base"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
