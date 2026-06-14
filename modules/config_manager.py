"""
全局配置管理器
功能：为每个用户从其独立数据库中读写配置，为所有模块提供统一的配置入口。
对于未登录场景（如 AI 引擎内部调用），降级读取全局 config.json。
安全特性：API Key 使用 Fernet 加密存储。
"""

import json
import os
import copy
import sqlite3
from modules.crypto_utils import (
    encrypt_api_key,
    decrypt_api_key,
    ensure_encryption_key,
    is_encrypted,
)

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"
)
PLATFORM_OWNER_USERNAME = os.environ.get("PLATFORM_OWNER_USERNAME", "zwf5458")

DEFAULT_CONFIG = {
    "ai": {
        "platform": "local",
        "model": "gpt-5.4",
        "api_key": "",
        "backup_platform_1": "",
        "backup_model_1": "",
        "backup_platform_2": "",
        "backup_model_2": "",
        "providers": {
            "google": {"api_base": "", "api_key": ""},
            "openai": {"api_base": "https://api.openai.com/v1", "api_key": ""},
            "nvidia": {"api_base": "https://integrate.api.nvidia.com/v1", "api_key": ""},
            "local": {"api_base": "http://127.0.0.1:8317/v1", "api_key": ""}
        }
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
        "ai_raw_data": 300,
    },
    "system": {
        "signup_bonus_points": 20,
        "ai_sim_cost": 5,
        "settings_change_cost": 1,
        "share_reward_points": 10,
        "share_reward_ratio": 0.2,
        "share_recharge_min": 5,
        "points_per_yuan": 10,
        "vip_monthly_fee": 99,
    },
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

            if has_request_context() and "user_id" in session:
                user_id = session["user_id"]
        except Exception:
            pass

    if user_id is not None:
        return _load_user_config(user_id)

    # 降级：读取全局 config.json
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, cfg)
    except Exception:
        pass
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(data: dict, user_id=None) -> bool:
    """
    保存配置。
    - 如果传入 user_id，保存到该用户的独立数据库；
    - 否则降级保存到全局 config.json。
    - API Key 会自动加密存储。
    """
    if user_id is not None:
        return _save_user_config(data, user_id)

    # 降级：保存到全局 config.json
    try:
        # 1. 备份原先 config.json 中各个供应商的加密 api_key
        current = load_global_config()
        old_keys = {}
        old_providers = current.get("ai", {}).get("providers", {})
        if isinstance(old_providers, dict):
            for p_name, p_cfg in old_providers.items():
                if isinstance(p_cfg, dict) and p_cfg.get("api_key"):
                    old_keys[p_name] = p_cfg["api_key"]

        # 2. 丢弃遮罩密钥以保留原有的加密密钥
        if "ai" in data:
            ai_data = data["ai"]
            if ai_data.get("api_key") and "****" in ai_data["api_key"]:
                del ai_data["api_key"]
            if "providers" in ai_data and isinstance(ai_data["providers"], dict):
                for p_name, p_cfg in list(ai_data["providers"].items()):
                    if isinstance(p_cfg, dict) and p_cfg.get("api_key") and "****" in p_cfg["api_key"]:
                        del p_cfg["api_key"]

        # 3. 深度合并
        merged = _deep_merge(current, data)

        # 4. 精细重构合并后的 providers：以 data 的 providers 结构为准（支持删除和覆盖）
        if "ai" in data and "providers" in data["ai"]:
            merged_providers = copy.deepcopy(data["ai"]["providers"])
            for p_name, p_cfg in merged_providers.items():
                if isinstance(p_cfg, dict):
                    if "api_key" not in p_cfg or not p_cfg["api_key"]:
                        p_cfg["api_key"] = old_keys.get(p_name, "")
            merged["ai"]["providers"] = merged_providers

        # 加密 API Key
        if "ai" in merged and merged["ai"].get("api_key"):
            if not is_encrypted(merged["ai"]["api_key"]):
                merged["ai"]["api_key"] = encrypt_api_key(merged["ai"]["api_key"])
        # 加密各平台（providers）独立的 API Key
        if "ai" in merged and "providers" in merged["ai"] and isinstance(merged["ai"]["providers"], dict):
            for p_name, p_cfg in merged["ai"]["providers"].items():
                if isinstance(p_cfg, dict) and p_cfg.get("api_key"):
                    if not is_encrypted(p_cfg["api_key"]):
                        p_cfg["api_key"] = encrypt_api_key(p_cfg["api_key"])

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_global_config() -> dict:
    """读取全局配置（不走用户会话）"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
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
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_ai_config(user_id=None) -> dict:
    """获取 AI 模型配置（自动解密 API Key）"""
    ai_cfg = load_config(user_id).get("ai", DEFAULT_CONFIG["ai"])
    if ai_cfg.get("api_key"):
        ai_cfg["api_key"] = decrypt_api_key(ai_cfg["api_key"])
    
    # 额外解密各个独立平台（provider）下的 api_key
    providers = ai_cfg.get("providers", {})
    if isinstance(providers, dict):
        for p_name, p_cfg in providers.items():
            if isinstance(p_cfg, dict) and p_cfg.get("api_key"):
                p_cfg["api_key"] = decrypt_api_key(p_cfg["api_key"])
    return ai_cfg


def get_chart_periods(user_id=None, lottery_type: str = 'macaujc') -> dict:
    """获取各图表统计期数，根据彩种类型解耦"""
    branch = 'weilitsai' if lottery_type == 'weilitsai' else 'macaujc'
    cfg = load_config(user_id)
    periods = cfg.get("chart_periods", DEFAULT_CONFIG["chart_periods"])
    
    # 检查是否已经是隔离字典
    if isinstance(periods, dict) and ('macaujc' in periods or 'weilitsai' in periods):
        branch_cfg = periods.get(branch)
        if isinstance(branch_cfg, dict):
            return branch_cfg
            
    # 向下兼容平铺字典
    import copy
    default_flat = DEFAULT_CONFIG["chart_periods"]
    current_flat = periods if isinstance(periods, dict) else default_flat
    return copy.deepcopy(current_flat)


def get_system_config() -> dict:
    """获取系统级配置（积分、费用等）"""
    return load_global_config().get("system", DEFAULT_CONFIG["system"])


def get_platform_owner_ai_config() -> dict:
    """获取平台管理员共享的 AI 配置（平台/模型/API 基础配置）。"""
    try:
        from modules.auth import USERS_DB_PATH, get_user_db_connection

        conn = sqlite3.connect(USERS_DB_PATH)
        row = conn.execute(
            "SELECT id FROM users WHERE username=? LIMIT 1", (PLATFORM_OWNER_USERNAME,)
        ).fetchone()
        conn.close()
        if not row:
            return {}

        user_conn = get_user_db_connection(int(row[0]))
        setting = user_conn.execute(
            "SELECT value FROM user_settings WHERE key='ai'"
        ).fetchone()
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
            (PLATFORM_OWNER_USERNAME,),
        ).fetchone()
        conn.close()
        if not row:
            return {}
        return {"id": int(row[0]), "username": row[1], "role": row[2]}
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
            return copy.deepcopy(DEFAULT_CONFIG)

        config = copy.deepcopy(DEFAULT_CONFIG)
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
        return copy.deepcopy(DEFAULT_CONFIG)


def _save_user_config(data: dict, user_id: int) -> bool:
    """将配置保存到用户独立数据库（自动加密 API Key）"""
    try:
        from modules.auth import get_user_db_connection

        # 1. 备份原先数据库中各个供应商的加密 api_key
        current = _load_user_config(user_id)
        old_keys = {}
        old_providers = current.get("ai", {}).get("providers", {})
        if isinstance(old_providers, dict):
            for p_name, p_cfg in old_providers.items():
                if isinstance(p_cfg, dict) and p_cfg.get("api_key"):
                    old_keys[p_name] = p_cfg["api_key"]

        # 2. 丢弃遮罩密钥以保留原有的加密密钥
        if "ai" in data:
            ai_data = data["ai"]
            if ai_data.get("api_key") and "****" in ai_data["api_key"]:
                del ai_data["api_key"]
            if "providers" in ai_data and isinstance(ai_data["providers"], dict):
                for p_name, p_cfg in list(ai_data["providers"].items()):
                    if isinstance(p_cfg, dict) and p_cfg.get("api_key") and "****" in p_cfg["api_key"]:
                        del p_cfg["api_key"]

        # 3. 深度合并
        merged = _deep_merge(current, data)

        # 4. 精细重构合并后的 providers：以 data 的 providers 结构为准（支持删除和覆盖）
        if "ai" in data and "providers" in data["ai"]:
            merged_providers = copy.deepcopy(data["ai"]["providers"])
            for p_name, p_cfg in merged_providers.items():
                if isinstance(p_cfg, dict):
                    if "api_key" not in p_cfg or not p_cfg["api_key"]:
                        p_cfg["api_key"] = old_keys.get(p_name, "")
            merged["ai"]["providers"] = merged_providers

        # 加密 API Key
        if "ai" in merged and merged["ai"].get("api_key"):
            if not is_encrypted(merged["ai"]["api_key"]):
                merged["ai"]["api_key"] = encrypt_api_key(merged["ai"]["api_key"])
        # 加密各平台（providers）独立的 API Key
        if "ai" in merged and "providers" in merged["ai"] and isinstance(merged["ai"]["providers"], dict):
            for p_name, p_cfg in merged["ai"]["providers"].items():
                if isinstance(p_cfg, dict) and p_cfg.get("api_key"):
                    if not is_encrypted(p_cfg["api_key"]):
                        p_cfg["api_key"] = encrypt_api_key(p_cfg["api_key"])

        conn = get_user_db_connection(user_id)
        for key in ["ai", "chart_periods"]:
            if key in merged:
                conn.execute(
                    "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(merged[key], ensure_ascii=False)),
                )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并字典，override 覆盖 base"""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
