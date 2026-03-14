import os
import re

app_path = r'f:\CODE\六合彩\app.py'
bp_dir = r'f:\CODE\六合彩\blueprints'

os.makedirs(bp_dir, exist_ok=True)
with open(os.path.join(bp_dir, '__init__.py'), 'w') as f:
    pass

with open(app_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find markers
auth_start = -1
pages_start = -1
admin_start = -1
main_start = -1

for i, line in enumerate(lines):
    if "# ==================== 认证路由 ====================" in line:
        auth_start = i
    elif "# ==================== 页面路由 ====================" in line:
        pages_start = i
    elif "# ==================== 后台管理 ====================" in line:
        admin_start = i
    elif "# ==================== 启动服务 ====================" in line:
        main_start = i

if -1 in (auth_start, pages_start, admin_start, main_start):
    print("Could not find all markers.")
    import sys
    sys.exit(1)

# Extract sections
header_lines = lines[:auth_start]
auth_lines = lines[auth_start:pages_start]
mid_lines = lines[pages_start:admin_start]
admin_lines = lines[admin_start:main_start]
footer_lines = lines[main_start:]

def process_bp(bp_name, source_lines):
    content = "".join(source_lines)
    content = content.replace("@app.", f"@{bp_name}.")
    
    # Common imports for blueprints
    imports = f"""from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, current_app
import os, json, sqlite3, time
from extensions import cache, limiter, csrf
from modules.logger import get_logger
from modules.auth import USERS_DB_PATH, require_role, get_user_db_connection

{bp_name} = Blueprint('{bp_name}', __name__)
logger = get_logger()
"""
    return imports + "\n" + content

auth_content = process_bp('auth_bp', auth_lines)
admin_content = process_bp('admin_bp', admin_lines)

# Write blueprints
with open(os.path.join(bp_dir, 'auth.py'), 'w', encoding='utf-8') as f:
    f.write(auth_content)
with open(os.path.join(bp_dir, 'admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin_content)

# Rebuild app.py
new_app_lines = []
for line in header_lines:
    if "app = Flask(__name__)" in line:
        new_app_lines.append(line)
        new_app_lines.append("from extensions import cache, limiter, csrf\n")
        new_app_lines.append("cache.init_app(app)\n")
        new_app_lines.append("limiter.init_app(app)\n")
        new_app_lines.append("csrf.init_app(app)\n")
        new_app_lines.append("\nfrom blueprints.auth import auth_bp\n")
        new_app_lines.append("from blueprints.admin import admin_bp\n")
        new_app_lines.append("app.register_blueprint(auth_bp)\n")
        new_app_lines.append("app.register_blueprint(admin_bp)\n")
    elif "cache = Cache" in line or "limiter =" in line or "csrf =" in line or "storage_uri=" in line or "CACHE_THRESHOLD" in line or "default_limits=" in line or "key_func=" in line or "app=app" in line:
        # Skip original extension inits
        pass
    else:
        new_app_lines.append(line)

new_app_lines.extend(mid_lines)
new_app_lines.extend(footer_lines)

# Clean up leftover extension code chunks we might have missed by a regex
app_text = "".join(new_app_lines)
# Remove the old extension init blocks cleanly
app_text = re.sub(r"# 配置文件系统缓存.*?\}\)", "", app_text, flags=re.DOTALL)
app_text = re.sub(r"# 配置请求限流器.*?\)", "", app_text, flags=re.DOTALL)
app_text = re.sub(r"# 配置 CSRF 防护\ncsrf = CSRFProtect\(app\)", "", app_text)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(app_text)

print("Split auth and admin blueprints successfully.")
