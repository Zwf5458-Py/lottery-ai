"""
管理员提权工具
用法: python promote_admin.py <用户名>
"""
import sys
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'users.db')

def promote(username):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id, role FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        print(f"❌ 用户 '{username}' 不存在")
        conn.close()
        return
    if row[1] == 'admin':
        print(f"ℹ️ 用户 '{username}' 已经是管理员")
    else:
        conn.execute("UPDATE users SET role='admin' WHERE username=?", (username,))
        conn.commit()
        print(f"✅ 用户 '{username}' 已成功提升为管理员 (admin)")
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python promote_admin.py <用户名>")
        sys.exit(1)
    promote(sys.argv[1])
