"""
用户认证模块
功能：注册、登录、会话管理、权限校验（体验/VIP）
数据库：data/users.db (全局用户表)、data/user_dbs/user_<id>.db (每用户独立库)
安全特性：登录失败限流，防止暴力破解
"""

import sqlite3
import hashlib
import os
import secrets
import string
import time
from functools import wraps
from flask import session, redirect, url_for, jsonify, request

# ==================== 路径常量 ====================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_DB_PATH = os.path.join(BASE_DIR, "data", "users.db")
USER_DBS_DIR = os.path.join(BASE_DIR, "data", "user_dbs")
PBKDF2_ITERATIONS = 260000

# ==================== 登录失败限流配置 ====================

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900
_login_attempts = {}


# ==================== 登录限流辅助函数 ====================


def _get_client_identifier():
    return request.remote_addr if request else "unknown"


def _check_login_lockout(username: str) -> tuple:
    client_id = _get_client_identifier()
    key = f"{client_id}:{username}"
    attempts = _login_attempts.get(key, {"count": 0, "first_attempt": 0})

    if attempts["count"] >= MAX_LOGIN_ATTEMPTS:
        elapsed = time.time() - attempts["first_attempt"]
        if elapsed < LOCKOUT_DURATION:
            remaining = int(LOCKOUT_DURATION - elapsed)
            return True, remaining
        del _login_attempts[key]
    return False, 0


def _record_login_failure(username: str):
    client_id = _get_client_identifier()
    key = f"{client_id}:{username}"

    if key not in _login_attempts:
        _login_attempts[key] = {"count": 0, "first_attempt": time.time()}
    _login_attempts[key]["count"] += 1


def _clear_login_failure(username: str):
    client_id = _get_client_identifier()
    key = f"{client_id}:{username}"
    if key in _login_attempts:
        del _login_attempts[key]


# ==================== 用户数据库初始化 ====================


def init_auth_db():
    """创建全局用户表（启动时调用）"""
    os.makedirs(USER_DBS_DIR, exist_ok=True)
    conn = sqlite3.connect(USERS_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'trial',
            email TEXT DEFAULT '',
            points INTEGER DEFAULT 0,
            referral_code TEXT DEFAULT '',
            referrer_id INTEGER DEFAULT NULL,
            reward_recharge_given INTEGER DEFAULT 0,
            reward_vip_given INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 自动升级旧表：添加 email 字段（如果不存在）
    try:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
    except Exception:
        pass  # 字段已存在
    try:
        conn.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN referral_code TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT NULL")
    except Exception:
        pass
    try:
        conn.execute(
            "ALTER TABLE users ADD COLUMN reward_recharge_given INTEGER DEFAULT 0"
        )
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN reward_vip_given INTEGER DEFAULT 0")
    except Exception:
        pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_points_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            change_amount INTEGER NOT NULL,
            balance INTEGER NOT NULL,
            reason TEXT NOT NULL,
            meta TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_recharges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            points INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# ==================== 用户独立数据库 ====================


def get_user_db_path(user_id: int) -> str:
    """获取用户独立数据库的文件路径"""
    return os.path.join(USER_DBS_DIR, f"user_{user_id}.db")


def get_user_db_connection(user_id: int):
    """获取用户独立数据库的连接，自动初始化表结构"""
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 确保表结构存在
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_type TEXT NOT NULL,
            model_name TEXT NOT NULL,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            dimensions TEXT NOT NULL,
            result_json TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


# ==================== 密码哈希 ====================


def _hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 对密码进行哈希"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """验证密码是否匹配"""
    try:
        if stored_hash.startswith("pbkdf2_sha256$"):
            _, iter_text, salt, expected_hex = stored_hash.split("$", 3)
            iterations = int(iter_text)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
            )
            return secrets.compare_digest(dk.hex(), expected_hex)

        # 兼容旧版本：salt:sha256
        salt, hashed = stored_hash.split(":", 1)
        legacy = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
        return secrets.compare_digest(legacy, hashed)
    except Exception:
        return False


# ==================== 注册 / 登录 ====================


def _generate_referral_code(conn) -> str:
    """生成唯一邀请码 (8位大写字母和数字，排除易混淆字符)"""
    safe_alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "".join(secrets.choice(safe_alphabet) for _ in range(8))
        row = conn.execute(
            "SELECT 1 FROM users WHERE referral_code=?", (code,)
        ).fetchone()
        if not row:
            return code


def register_user(username: str, password: str, ref_code: str = "") -> dict:
    """注册新用户，成功返回 user_id"""
    username = username.strip()
    if not username or not password:
        return {"success": False, "error": "用户名和密码不能为空"}
    if len(username) < 2 or len(username) > 20:
        return {"success": False, "error": "用户名长度需在 2-20 字符之间"}
    if len(password) < 4:
        return {"success": False, "error": "密码长度至少 4 个字符"}

    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        # 检查用户名是否已存在
        existing = conn.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        ).fetchone()
        if existing:
            conn.close()
            return {"success": False, "error": "该用户名已被注册"}

        pw_hash = _hash_password(password)
        # 处理推荐人
        referrer_id = None
        if ref_code:
            row = conn.execute(
                "SELECT id FROM users WHERE referral_code=?", (ref_code.strip(),)
            ).fetchone()
            if row:
                referrer_id = row[0]

        referral_code = _generate_referral_code(conn)
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role, referral_code, referrer_id) VALUES (?, ?, 'trial', ?, ?)",
            (username, pw_hash, referral_code, referrer_id),
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # 创建用户独立数据库
        get_user_db_connection(user_id).close()

        # 注册送积分
        try:
            from modules.config_manager import get_system_config
            from modules.points_manager import add_points

            sys_cfg = get_system_config()
            bonus = int(sys_cfg.get("signup_bonus_points", 0))
            if bonus > 0:
                add_points(user_id, bonus, "signup_bonus")
        except Exception:
            pass

        return {
            "success": True,
            "user_id": user_id,
            "username": username,
            "role": "trial",
        }
    except Exception as e:
        return {"success": False, "error": f"注册失败: {str(e)}"}


def login_user(username: str, password: str) -> dict:
    """验证用户凭据（带登录限流保护）"""
    username = username.strip()
    if not username or not password:
        return {"success": False, "error": "请输入用户名和密码"}

    is_locked, remaining = _check_login_lockout(username)
    if is_locked:
        return {
            "success": False,
            "error": f"登录失败次数过多，请 {remaining} 秒后重试",
            "locked": True,
            "remaining": remaining,
        }

    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        row = conn.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username=?",
            (username,),
        ).fetchone()
        conn.close()

        if not row:
            _record_login_failure(username)
            return {"success": False, "error": "用户名不存在"}

        stored_hash = row[2]
        if not _verify_password(password, stored_hash):
            _record_login_failure(username)
            return {"success": False, "error": "密码错误"}

        _clear_login_failure(username)

        if stored_hash and not stored_hash.startswith("pbkdf2_sha256$"):
            try:
                conn = sqlite3.connect(USERS_DB_PATH)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute(
                    "UPDATE users SET password_hash=? WHERE id=?",
                    (_hash_password(password), row[0]),
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

        return {"success": True, "user_id": row[0], "username": row[1], "role": row[3]}
    except Exception as e:
        return {"success": False, "error": f"登录失败: {str(e)}"}


# ==================== 权限装饰器 ====================


def login_required(f):
    """登录鉴权装饰器：未登录则重定向到登录页"""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            # API 请求返回 JSON，页面请求重定向
            if request.path.startswith("/api/"):
                return jsonify(
                    {"success": False, "error": "请先登录", "redirect": "/login"}
                ), 401
            return redirect(url_for("page_login"))
        return f(*args, **kwargs)

    return decorated


def vip_required(f):
    """VIP 鉴权装饰器：非 VIP 用户拦截"""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify(
                    {"success": False, "error": "请先登录", "redirect": "/login"}
                ), 401
            return redirect(url_for("page_login"))
        if session.get("role") not in ("vip", "admin"):
            return jsonify(
                {
                    "success": False,
                    "error": "该功能仅 VIP 会员可用，请升级后体验 ✨",
                    "vip_required": True,
                }
            ), 403
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """管理员鉴权装饰器：仅 admin 角色可用"""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify(
                    {"success": False, "error": "请先登录", "redirect": "/login"}
                ), 401
            return redirect(url_for("page_login"))
        if session.get("role") != "admin":
            return jsonify({"success": False, "error": "该功能仅管理员可用"}), 403
        return f(*args, **kwargs)

    return decorated


def vip_or_admin_required(f):
    """VIP 或管理员鉴权装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify(
                    {"success": False, "error": "请先登录", "redirect": "/login"}
                ), 401
            return redirect(url_for("page_login"))
        if session.get("role") not in ("vip", "admin"):
            return jsonify(
                {"success": False, "error": "该功能仅 VIP 会员或管理员可用"}
            ), 403
        return f(*args, **kwargs)

    return decorated


def get_current_user() -> dict:
    """获取当前会话用户信息"""
    if "user_id" in session:
        try:
            from modules.points_manager import get_user_points

            points = get_user_points(session["user_id"])
        except Exception:
            points = 0
        return {
            "user_id": session["user_id"],
            "username": session.get("username", ""),
            "role": session.get("role", "trial"),
            "points": points,
        }
    return None


# ==================== 账号管理 ====================


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """修改密码"""
    if not old_password or not new_password:
        return {"success": False, "error": "旧密码和新密码不能为空"}
    if len(new_password) < 4:
        return {"success": False, "error": "新密码长度至少 4 个字符"}
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "用户不存在"}
        if not _verify_password(old_password, row[0]):
            conn.close()
            return {"success": False, "error": "旧密码错误"}
        new_hash = _hash_password(new_password)
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": "密码修改成功"}
    except Exception as e:
        return {"success": False, "error": f"修改失败: {str(e)}"}


def update_email(user_id: int, email: str) -> dict:
    """更新邮箱"""
    email = email.strip()
    if email and "@" not in email:
        return {"success": False, "error": "邮箱格式不正确"}
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("UPDATE users SET email=? WHERE id=?", (email, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": "邮箱已更新"}
    except Exception as e:
        return {"success": False, "error": f"更新失败: {str(e)}"}


def admin_reset_password(user_id: int, new_password: str) -> dict:
    """管理员重置用户密码"""
    if not new_password or len(new_password) < 4:
        return {"success": False, "error": "新密码长度至少 4 个字符"}
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        row = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "用户不存在"}
        new_hash = _hash_password(new_password)
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": "密码已重置"}
    except Exception as e:
        return {"success": False, "error": f"重置失败: {str(e)}"}


def get_user_basic(user_id: int):
    """获取用户基础信息（用于后台模拟登录）"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE id=?", (user_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row[0], "username": row[1], "role": row[2]}
    except Exception:
        return None


def get_user_email(user_id: int) -> str:
    """获取用户邮箱"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        row = conn.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""


def get_user_referral_code(user_id: int) -> str:
    """获取用户的邀请码"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        row = conn.execute(
            "SELECT referral_code FROM users WHERE id=?", (user_id,)
        ).fetchone()
        conn.close()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""


def get_all_users(page: int = 1, per_page: int = 20, search: str = "") -> dict:
    """获取所有用户列表（分页 + 搜索）"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        params = []
        if search:
            like_term = f"%{search}%"
            params = [like_term, like_term]
            total = conn.execute(
                "SELECT COUNT(*) FROM users WHERE username LIKE ? OR email LIKE ?",
                params,
            ).fetchone()[0]
        else:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        offset = (page - 1) * per_page
        if search:
            rows = conn.execute(
                "SELECT id, username, role, email, points, referral_code, created_at FROM users WHERE username LIKE ? OR email LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [per_page, offset],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, username, role, email, points, referral_code, created_at FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()
        conn.close()

        users = []
        for r in rows:
            users.append(
                {
                    "id": r[0],
                    "username": r[1],
                    "role": r[2],
                    "email": r[3] or "",
                    "points": r[4] or 0,
                    "referral_code": r[5] or "",
                    "created_at": r[6],
                }
            )
        return {
            "success": True,
            "users": users,
            "total": total,
            "page": page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_user_role(user_id: int, new_role: str) -> dict:
    """设置用户角色"""
    if new_role not in ("trial", "vip", "admin"):
        return {"success": False, "error": "无效的角色"}
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        prev_row = conn.execute(
            "SELECT role FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not prev_row:
            conn.close()
            return {"success": False, "error": "用户不存在"}
        previous_role = prev_row[0]
        conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
        conn.commit()
        conn.close()

        # 触发分享奖励（被推荐用户成为 VIP）
        reward_result = {
            "success": True,
            "reward_given": False,
            "reason": "not_applicable",
        }
        try:
            if new_role == "vip" and previous_role != "vip":
                from modules.points_manager import (
                    apply_referral_vip_reward,
                    calc_referral_reward_points,
                )
                from modules.config_manager import get_system_config

                sys_cfg = get_system_config()
                reward_ratio = float(sys_cfg.get("share_reward_ratio", 0) or 0)
                reward_points_fixed = int(sys_cfg.get("share_reward_points", 10))
                vip_fee = int(sys_cfg.get("vip_monthly_fee", 99))
                points_per_yuan = int(sys_cfg.get("points_per_yuan", 10))
                vip_points_base = vip_fee * points_per_yuan
                reward_points = calc_referral_reward_points(
                    vip_points_base, reward_ratio, reward_points_fixed
                )
                reward_result = apply_referral_vip_reward(user_id, reward_points)
            elif new_role == "vip" and previous_role == "vip":
                reward_result = {
                    "success": True,
                    "reward_given": False,
                    "reason": "already_vip",
                }
        except Exception:
            reward_result = {
                "success": False,
                "reward_given": False,
                "reason": "reward_exception",
            }
        return {
            "success": True,
            "message": f"用户角色已更新为 {new_role}",
            "previous_role": previous_role,
            "referral_reward": reward_result,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_global_stats() -> dict:
    """全站数据聚合统计（扫描所有用户库）"""
    try:
        total_ai_records = 0
        if os.path.exists(USER_DBS_DIR):
            for filename in os.listdir(USER_DBS_DIR):
                if filename.endswith(".db"):
                    db_path = os.path.join(USER_DBS_DIR, filename)
                    try:
                        conn = sqlite3.connect(db_path)
                        res = conn.execute(
                            "SELECT COUNT(*) FROM ai_analysis_history"
                        ).fetchone()
                        total_ai_records += res[0]
                        conn.close()
                    except Exception:
                        continue
        return {"success": True, "total_ai_count": total_ai_records}
    except Exception as e:
        return {"success": False, "error": str(e)}


def seed_user_data(user_id: int) -> dict:
    """为指定用户生成仿真演示数据"""
    import json
    import random
    from datetime import datetime, timedelta

    try:
        conn = get_user_db_connection(user_id)
        models = ["gemini-2.5-pro", "gemini-3.1-pro-preview", "gpt-4o"]
        lottery_types = ["macaujc", "macaujc2"]

        # 插入 15 条模拟数据
        for i in range(15):
            days_ago = random.randint(0, 30)
            gen_time = (
                datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            ).strftime("%Y-%m-%d %H:%M:%S")

            l_type = random.choice(lottery_types)
            model = random.choice(models)

            # 仿真结果 JSON
            result = {
                "success": True,
                "numbers": [random.randint(1, 49) for _ in range(6)],
                "special_num": random.randint(1, 49),
                "analysis": "根据历史冷热号趋势和贝叶斯概率回归分析，该号码组合在当前周期内具有较高的权重表现...",
                "confidence": round(random.uniform(0.65, 0.95), 2),
            }

            conn.execute(
                """
                INSERT INTO ai_analysis_history (lottery_type, model_name, generated_at, dimensions, result_json)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    l_type,
                    model,
                    gen_time,
                    '["演示数据", "概率增强"]',
                    json.dumps(result, ensure_ascii=False),
                ),
            )

        conn.commit()
        conn.close()
        return {
            "success": True,
            "message": "演示数据已成功注入，请前往【AI 历史档案】查看 ✨",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
