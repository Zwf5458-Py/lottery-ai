"""
用户认证模块
功能：注册、登录、会话管理、权限校验（体验/VIP）
数据库：data/users.db (全局用户表)、data/user_dbs/user_<id>.db (每用户独立库)
"""

import sqlite3
import hashlib
import os
import secrets
from functools import wraps
from flask import session, redirect, url_for, jsonify, request

# ==================== 路径常量 ====================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_DB_PATH = os.path.join(BASE_DIR, 'data', 'users.db')
USER_DBS_DIR = os.path.join(BASE_DIR, 'data', 'user_dbs')


# ==================== 用户数据库初始化 ====================

def init_auth_db():
    """创建全局用户表（启动时调用）"""
    os.makedirs(USER_DBS_DIR, exist_ok=True)
    conn = sqlite3.connect(USERS_DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'trial',
            email TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 自动升级旧表：添加 email 字段（如果不存在）
    try:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
    except Exception:
        pass  # 字段已存在
    conn.commit()
    conn.close()


# ==================== 用户独立数据库 ====================

def get_user_db_path(user_id: int) -> str:
    """获取用户独立数据库的文件路径"""
    return os.path.join(USER_DBS_DIR, f'user_{user_id}.db')


def get_user_db_connection(user_id: int):
    """获取用户独立数据库的连接，自动初始化表结构"""
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 确保表结构存在
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ai_analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_type TEXT NOT NULL,
            model_name TEXT NOT NULL,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            dimensions TEXT NOT NULL,
            result_json TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    conn.commit()
    return conn


# ==================== 密码哈希 ====================

def _hash_password(password: str) -> str:
    """使用 SHA-256 + 盐值对密码进行哈希"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """验证密码是否匹配"""
    try:
        salt, hashed = stored_hash.split(':', 1)
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest() == hashed
    except Exception:
        return False


# ==================== 注册 / 登录 ====================

def register_user(username: str, password: str) -> dict:
    """注册新用户，成功返回 user_id"""
    username = username.strip()
    if not username or not password:
        return {'success': False, 'error': '用户名和密码不能为空'}
    if len(username) < 2 or len(username) > 20:
        return {'success': False, 'error': '用户名长度需在 2-20 字符之间'}
    if len(password) < 4:
        return {'success': False, 'error': '密码长度至少 4 个字符'}

    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        # 检查用户名是否已存在
        existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            conn.close()
            return {'success': False, 'error': '该用户名已被注册'}

        pw_hash = _hash_password(password)
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'trial')",
            (username, pw_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # 创建用户独立数据库
        get_user_db_connection(user_id).close()

        return {'success': True, 'user_id': user_id, 'username': username, 'role': 'trial'}
    except Exception as e:
        return {'success': False, 'error': f'注册失败: {str(e)}'}


def login_user(username: str, password: str) -> dict:
    """验证用户凭据"""
    username = username.strip()
    if not username or not password:
        return {'success': False, 'error': '请输入用户名和密码'}

    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        row = conn.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if not row:
            return {'success': False, 'error': '用户名不存在'}

        if not _verify_password(password, row[2]):
            return {'success': False, 'error': '密码错误'}

        return {
            'success': True,
            'user_id': row[0],
            'username': row[1],
            'role': row[3]
        }
    except Exception as e:
        return {'success': False, 'error': f'登录失败: {str(e)}'}


# ==================== 权限装饰器 ====================

def login_required(f):
    """登录鉴权装饰器：未登录则重定向到登录页"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            # API 请求返回 JSON，页面请求重定向
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '请先登录', 'redirect': '/login'}), 401
            return redirect(url_for('page_login'))
        return f(*args, **kwargs)
    return decorated


def vip_required(f):
    """VIP 鉴权装饰器：非 VIP 用户拦截"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '请先登录', 'redirect': '/login'}), 401
            return redirect(url_for('page_login'))
        if session.get('role') not in ('vip', 'admin'):
            return jsonify({
                'success': False,
                'error': '该功能仅 VIP 会员可用，请升级后体验 ✨',
                'vip_required': True
            }), 403
        return f(*args, **kwargs)
    return decorated


def get_current_user() -> dict:
    """获取当前会话用户信息"""
    if 'user_id' in session:
        return {
            'user_id': session['user_id'],
            'username': session.get('username', ''),
            'role': session.get('role', 'trial')
        }
    return None


# ==================== 账号管理 ====================

def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """修改密码"""
    if not old_password or not new_password:
        return {'success': False, 'error': '旧密码和新密码不能为空'}
    if len(new_password) < 4:
        return {'success': False, 'error': '新密码长度至少 4 个字符'}
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            conn.close()
            return {'success': False, 'error': '用户不存在'}
        if not _verify_password(old_password, row[0]):
            conn.close()
            return {'success': False, 'error': '旧密码错误'}
        new_hash = _hash_password(new_password)
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
        conn.commit()
        conn.close()
        return {'success': True, 'message': '密码修改成功'}
    except Exception as e:
        return {'success': False, 'error': f'修改失败: {str(e)}'}


def update_email(user_id: int, email: str) -> dict:
    """更新邮箱"""
    email = email.strip()
    if email and '@' not in email:
        return {'success': False, 'error': '邮箱格式不正确'}
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("UPDATE users SET email=? WHERE id=?", (email, user_id))
        conn.commit()
        conn.close()
        return {'success': True, 'message': '邮箱已更新'}
    except Exception as e:
        return {'success': False, 'error': f'更新失败: {str(e)}'}


def get_user_email(user_id: int) -> str:
    """获取用户邮箱"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        row = conn.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return row[0] if row and row[0] else ''
    except Exception:
        return ''


# ==================== 后台管理 ====================

def admin_required(f):
    """管理员鉴权装饰器：仅 role='admin' 可访问"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '请先登录', 'redirect': '/login'}), 401
            return redirect(url_for('page_login'))
        if session.get('role') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '无管理员权限'}), 403
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


def get_all_users(page: int = 1, per_page: int = 20, search: str = '') -> dict:
    """获取所有用户列表（分页 + 搜索）"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        where = ''
        params = []
        if search:
            where = "WHERE username LIKE ? OR email LIKE ?"
            params = [f'%{search}%', f'%{search}%']

        total = conn.execute(f"SELECT COUNT(*) FROM users {where}", params).fetchone()[0]
        offset = (page - 1) * per_page
        rows = conn.execute(
            f"SELECT id, username, role, email, created_at FROM users {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        conn.close()

        users = []
        for r in rows:
            users.append({
                'id': r[0], 'username': r[1], 'role': r[2],
                'email': r[3] or '', 'created_at': r[4]
            })
        return {
            'success': True,
            'users': users,
            'total': total,
            'page': page,
            'total_pages': (total + per_page - 1) // per_page
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def set_user_role(user_id: int, new_role: str) -> dict:
    """设置用户角色"""
    if new_role not in ('trial', 'vip', 'admin'):
        return {'success': False, 'error': '无效的角色'}
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
        conn.commit()
        conn.close()
        return {'success': True, 'message': f'用户角色已更新为 {new_role}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_global_stats() -> dict:
    """全站数据聚合统计（扫描所有用户库）"""
    try:
        total_ai_records = 0
        if os.path.exists(USER_DBS_DIR):
            for filename in os.listdir(USER_DBS_DIR):
                if filename.endswith('.db'):
                    db_path = os.path.join(USER_DBS_DIR, filename)
                    try:
                        conn = sqlite3.connect(db_path)
                        res = conn.execute("SELECT COUNT(*) FROM ai_analysis_history").fetchone()
                        total_ai_records += res[0]
                        conn.close()
                    except Exception:
                        continue
        return {'success': True, 'total_ai_count': total_ai_records}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def seed_user_data(user_id: int) -> dict:
    """为指定用户生成仿真演示数据"""
    import json
    import random
    from datetime import datetime, timedelta
    try:
        conn = get_user_db_connection(user_id)
        models = ['gemini-2.5-pro', 'gemini-3.1-pro-preview', 'gpt-4o']
        lottery_types = ['macaujc', 'macaujc2']
        
        # 插入 15 条模拟数据
        for i in range(15):
            days_ago = random.randint(0, 30)
            gen_time = (datetime.now() - timedelta(days=days_ago, hours=random.randint(0,23))).strftime('%Y-%m-%d %H:%M:%S')
            
            l_type = random.choice(lottery_types)
            model = random.choice(models)
            
            # 仿真结果 JSON
            result = {
                "success": True,
                "numbers": [random.randint(1, 49) for _ in range(6)],
                "special_num": random.randint(1, 49),
                "analysis": "根据历史冷热号趋势和贝叶斯概率回归分析，该号码组合在当前周期内具有较高的权重表现...",
                "confidence": round(random.uniform(0.65, 0.95), 2)
            }
            
            conn.execute('''
                INSERT INTO ai_analysis_history (lottery_type, model_name, generated_at, dimensions, result_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (l_type, model, gen_time, '["演示数据", "概率增强"]', json.dumps(result, ensure_ascii=False)))
            
        conn.commit()
        conn.close()
        return {'success': True, 'message': '演示数据已成功注入，请前往【AI 历史档案】查看 ✨'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
