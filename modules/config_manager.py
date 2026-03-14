"""
全局配置管理器
功能：为每个用户从其独立数据库中读写配置，为所有模块提供统一的配置入口。
对于未登录场景（如 AI 引擎内部调用），降级读取全局 config.json。
"""

import json
import os
import sqlite3

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
PLATFORM_OWNER_USERNAME = os.environ.get('PLATFORM_OWNER_USERNAME', 'zwf5458')

DEFAULT_CONFIG = {
    "ai": {
        "platform": "local",
        "model": "gpt-5.4",
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
    },
    "system": {
        "signup_bonus_points": 20,
        "ai_sim_cost": 5,
        "settings_change_cost": 1,
        "share_reward_points": 10,
        "share_reward_ratio": 0.2,
        "share_recharge_min": 5,
        "points_per_yuan": 10,
        "vip_monthly_fee": 99
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


def load_global_config() -> dict:
    """读取全局配置（不走用户会话）"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, cfg)
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_global_config(data: dict) -> bool:
    """保存全局配置（不走用户会话）"""
    try:
        current = load_global_config()
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


def get_system_config() -> dict:
    """获取系统级配置（积分、费用等）"""
    return load_global_config().get('system', DEFAULT_CONFIG['system'])


def get_platform_owner_ai_config() -> dict:
    """获取平台管理员共享的 AI 配置（平台/模型/API 基础配置）。"""
    try:
        from modules.auth import USERS_DB_PATH, get_user_db_connection

        conn = sqlite3.connect(USERS_DB_PATH)
        row = conn.execute(
            "SELECT id FROM users WHERE username=? LIMIT 1",
            (PLATFORM_OWNER_USERNAME,)
        ).fetchone()
        conn.close()
        if not row:
            return {}

        user_conn = get_user_db_connection(int(row[0]))
        setting = user_conn.execute("SELECT value FROM user_settings WHERE key='ai'").fetchone()
        user_conn.close()
        if not setting:
            return {}

        data = json.loads(setting[0])
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_platform_owner_identity() -> dict:
    """获取平台管理员身份信息。"""
    try:
        from modules.auth import USERS_DB_PATH
        conn = sqlite3.connect(USERS_DB_PATH)
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE username=? LIMIT 1",
            (PLATFORM_OWNER_USERNAME,)
        ).fetchone()
        conn.close()
        if not row:
            return {}
        return {'id': int(row[0]), 'username': row[1], 'role': row[2]}
    except Exception:
        return {}


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
                loaded = json.loads(r[1])
                if isinstance(config.get(r[0]), dict) and isinstance(loaded, dict):
                    config[r[0]] = _deep_merge(config[r[0]], loaded)
                else:
                    config[r[0]] = loaded
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
