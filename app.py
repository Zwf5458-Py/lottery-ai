"""
Flask 主程序
功能：提供 Web 界面和 RESTful API，连接前端与后端核心模块。
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os

load_dotenv()

from modules.statistics_engine import get_full_analysis
from modules.simulator import simulate_single, simulate_batch
from modules.data_processor import get_paginated_history
from modules.auth import (
    init_auth_db, login_required, vip_required,
    register_user, login_user, get_current_user,
    get_user_db_connection
)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'lottery-analysis-secret-key-2026')

# 配置内存缓存 (SimpleCache)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 3600})

# 配置请求限流器 (Limiter)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


# ==================== 启动时初始化数据库 ====================
init_auth_db()


# ==================== 认证路由 ====================

@app.route('/login')
def page_login():
    if 'user_id' in session:
        return redirect('/')
    return render_template('login.html')

@app.route('/register')
def page_register():
    if 'user_id' in session:
        return redirect('/')
    return render_template('register.html')

@app.route('/logout')
def page_logout():
    session.clear()
    return redirect('/login')

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    result = register_user(data.get('username', ''), data.get('password', ''))
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    result = login_user(data.get('username', ''), data.get('password', ''))
    if result['success']:
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['role'] = result['role']
        return jsonify(result)
    return jsonify(result), 401

@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    user = get_current_user()
    if user:
        return jsonify({'success': True, 'user': user})
    return jsonify({'success': False}), 401


# ==================== 页面路由 ====================

@app.route('/')
@login_required
def index():
    """渲染主页"""
    user = get_current_user()
    return render_template('index.html', user=user)


# ==================== API 路由 ====================

@app.route('/api/statistics', methods=['GET'])
@cache.cached(timeout=3600, query_string=True)
def api_statistics():
    """
    获取全部统计分析数据
    查询参数: type (macaujc 或 macaujc2)
    返回: JSON 格式的多维度统计结果
    """
    try:
        lottery_type = request.args.get('type', 'macaujc')
        analysis = get_full_analysis(lottery_type)
        return jsonify({
            'success': True,
            'data': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data-check', methods=['GET'])
def api_data_check():
    """检查数据新鲜度"""
    try:
        lottery_type = request.args.get('type', 'macaujc2')
        from data.fetch_real_data import check_data_freshness
        result = check_data_freshness(lottery_type)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync-data', methods=['POST'])
def api_sync_data():
    """增量同步最新数据"""
    try:
        data = request.get_json() or {}
        lottery_type = data.get('type', 'macaujc2')
        from data.fetch_real_data import sync_latest
        result = sync_latest(lottery_type)
        if result.get('new_count', 0) > 0:
            cache.clear()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/simulate', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def api_simulate():
    """
    模拟开奖 API
    请求体 JSON: {
        "count": 模拟期数,
        "type": 彩种,
        "mode": "weighted" | "ai",
        "dimensions": ["big_small", "odd_even", "hot_cold", "tail", "zodiac"]
    }
    """
    try:
        data = request.get_json() or {}
        count = data.get('count', 1)
        lottery_type = data.get('type', 'macaujc')
        mode = data.get('mode', 'weighted')

        # 仅 AI 模式需要 VIP 权限
        if mode in ('ai', 'ai_zodiac') and session.get('role') not in ('vip', 'admin'):
            return jsonify({
                'success': False,
                'error': 'AI 智能分析仅 VIP 会员可用，请升级后体验 ✨',
                'vip_required': True
            }), 403
        dimensions = data.get('dimensions', ['big_small', 'odd_even', 'hot_cold', 'tail', 'zodiac'])
        
        # 参数校验
        if not isinstance(count, int) or count < 1:
            count = 1
        if count > 1000:
            count = 1000
        
        # ====== 数据新鲜度前置守卫 ======
        from data.fetch_real_data import check_data_freshness, sync_latest
        from modules.logger import get_logger
        logger = get_logger()
        freshness = check_data_freshness(lottery_type)
        if not freshness['is_fresh']:
            # 自动尝试同步
            logger.warning(f"⚠️ 数据滞后 {freshness['days_behind']} 天，自动触发同步...")
            sync_result = sync_latest(lottery_type)
            if sync_result.get('new_count', 0) > 0:
                cache.clear()
            # 同步后再次检查
            freshness = check_data_freshness(lottery_type)
            if not freshness['is_fresh']:
                return jsonify({
                    'success': False,
                    'error': f"数据不是最新的！最新数据日期: {freshness['latest_date']}（滞后 {freshness['days_behind']} 天）。"
                             f"请先点击「同步最新」按钮手动同步，确保包含昨天的开奖数据后再进行模拟。",
                    'data_status': freshness
                }), 400
        
        # AI 模式
        if mode == 'ai':
            from modules.ai_engine import analyze_with_ai
            from modules.statistics_engine import get_zodiac_mapping
            import json
            from modules.data_processor import get_db_connection
            from modules.config_manager import load_config
            
            stats = get_full_analysis(lottery_type)
            ai_result = analyze_with_ai(stats, lottery_type, dimensions)
            
            # 为 AI 结果补充生肖映射
            z_map = get_zodiac_mapping(lottery_type)
            if 'numbers' in ai_result and ai_result['numbers']:
                ai_result['zodiacs'] = [z_map.get(n, '') for n in ai_result['numbers']]
            if 'special_num' in ai_result and ai_result['special_num']:
                ai_result['special_zodiac'] = z_map.get(ai_result['special_num'], '')
                
            # ====== 新增：持久化 AI 推理过程到数据库 ======
            try:
                if ai_result.get('success', False):
                    cfg = load_config(session.get('user_id'))
                    model_name = cfg.get('ai', {}).get('model', 'gemini-2.5-pro')
                    conn = get_user_db_connection(session['user_id'])
                    conn.execute('''
                        INSERT INTO ai_analysis_history
                        (lottery_type, model_name, dimensions, result_json)
                        VALUES (?, ?, ?, ?)
                    ''', (lottery_type, model_name, json.dumps(dimensions, ensure_ascii=False), json.dumps(ai_result, ensure_ascii=False)))
                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"保存 AI 分析记录失败: {e}")
            
            # 同时生成传统加权结果作为对比
            weighted_result = simulate_single(lottery_type, dimensions)
            
            return jsonify({
                'success': True,
                'data': {
                    'mode': 'ai',
                    'ai_result': ai_result,
                    'weighted_result': weighted_result,
                    'dimensions': dimensions
                }
            })
        
        # AI 生肖专属推算模式
        if mode == 'ai_zodiac':
            from modules.ai_engine import analyze_zodiac_with_ai
            import json
            from modules.data_processor import get_db_connection
            from modules.config_manager import load_config
            
            stats = get_full_analysis(lottery_type)
            zodiac_result = analyze_zodiac_with_ai(stats, lottery_type, dimensions)
            
            # 持久化到数据库
            try:
                if zodiac_result.get('success', False):
                    cfg = load_config(session.get('user_id'))
                    model_name = cfg.get('ai', {}).get('model', 'gemini-2.5-pro')
                    conn = get_user_db_connection(session['user_id'])
                    conn.execute('''
                        INSERT INTO ai_analysis_history
                        (lottery_type, model_name, dimensions, result_json)
                        VALUES (?, ?, ?, ?)
                    ''', (lottery_type, model_name,
                          json.dumps(['zodiac_mode'] + dimensions, ensure_ascii=False),
                          json.dumps(zodiac_result, ensure_ascii=False)))
                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"保存 AI 生肖推算记录失败: {e}")
            
            return jsonify({
                'success': True,
                'data': {
                    'mode': 'ai_zodiac',
                    'zodiac_result': zodiac_result,
                    'dimensions': dimensions
                }
            })
        
        # 传统加权模式
        if count == 1:
            result = simulate_single(lottery_type, dimensions)
            return jsonify({
                'success': True,
                'data': {
                    'mode': 'weighted',
                    'draws': [result],
                    'summary': None,
                    'dimensions': dimensions
                }
            })
        else:
            result = simulate_batch(count, lottery_type, dimensions)
            result['mode'] = 'weighted'
            result['dimensions'] = dimensions
            return jsonify({
                'success': True,
                'data': result
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history', methods=['GET'])
def api_history():
    """
    获取历史开奖记录（分页）
    查询参数: page（页码）、per_page（每页条数）、type（彩种）
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        lottery_type = request.args.get('type', 'macaujc')
        
        # 参数范围限制
        page = max(1, page)
        per_page = max(1, min(100, per_page))
        
        result = get_paginated_history(page, per_page, lottery_type)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai_history', methods=['GET'])
@login_required
def api_ai_history():
    """获取 AI 分析历史记录（分页）—— 从用户独立数据库读取"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        lottery_type = request.args.get('type', 'macaujc')
        
        page = max(1, page)
        per_page = max(1, min(50, per_page))
        offset = (page - 1) * per_page
        
        import json
        conn = get_user_db_connection(session['user_id'])
        
        # 获取总数
        total = conn.execute("SELECT COUNT(*) FROM ai_analysis_history WHERE lottery_type=?", (lottery_type,)).fetchone()[0]
        
        # 获取分页数据
        rows = conn.execute(
            "SELECT id, model_name, generated_at, dimensions, result_json FROM ai_analysis_history WHERE lottery_type=? ORDER BY generated_at DESC LIMIT ? OFFSET ?",
            (lottery_type, per_page, offset)
        ).fetchall()
        
        items = []
        for r in rows:
            items.append({
                'id': r[0],
                'model_name': r[1],
                'generated_at': r[2],
                'dimensions': json.loads(r[3]) if r[3] else [],
                'result': json.loads(r[4]) if r[4] else {}
            })
            
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai_history/<int:record_id>', methods=['DELETE'])
@login_required
def api_delete_ai_history(record_id):
    """删除单条 AI 分析记录 —— 从用户独立数据库删除"""
    try:
        conn = get_user_db_connection(session['user_id'])
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ai_analysis_history WHERE id=?", (record_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            return jsonify({'success': True, 'message': '已删除'})
        else:
            return jsonify({'success': False, 'error': '找不到该记录'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 设置 API ====================

@app.route('/api/settings', methods=['GET'])
@login_required
def api_get_settings():
    """获取当前用户的个人设置"""
    try:
        from modules.config_manager import load_config
        config = load_config(session['user_id'])
        api_key = config.get('ai', {}).get('api_key', '')
        if api_key and len(api_key) > 8:
            config['ai']['api_key_masked'] = api_key[:4] + '****' + api_key[-4:]
        else:
            config['ai']['api_key_masked'] = api_key
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['POST'])
@login_required
@vip_required
def api_save_settings():
    """保存用户个人设置（VIP 专属）"""
    try:
        from modules.config_manager import save_config
        data = request.get_json() or {}
        success = save_config(data, session['user_id'])
        if success:
            cache.clear()
            return jsonify({'success': True, 'message': '设置已保存'})
        else:
            return jsonify({'success': False, 'error': '保存失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 账号管理 API ====================

@app.route('/api/account/password', methods=['POST'])
@login_required
def api_change_password():
    """修改密码"""
    from modules.auth import change_password
    data = request.get_json() or {}
    result = change_password(session['user_id'], data.get('old_password', ''), data.get('new_password', ''))
    return jsonify(result), 200 if result['success'] else 400

@app.route('/api/account/email', methods=['GET'])
@login_required
def api_get_email():
    """获取当前用户邮箱"""
    from modules.auth import get_user_email
    email = get_user_email(session['user_id'])
    return jsonify({'success': True, 'email': email})

@app.route('/api/account/email', methods=['POST'])
@login_required
def api_update_email():
    """更新邮箱"""
    from modules.auth import update_email
    data = request.get_json() or {}
    result = update_email(session['user_id'], data.get('email', ''))
    return jsonify(result), 200 if result['success'] else 400


# ==================== 后台管理 ====================

@app.route('/admin')
def page_admin():
    """后台管理面板"""
    from modules.auth import admin_required as _ar
    # 手动检查管理员权限
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') != 'admin':
        return redirect('/')
    user = get_current_user()
    return render_template('admin.html', user=user)

@app.route('/api/admin/users', methods=['GET'])
@login_required
def api_admin_users():
    """获取用户列表（管理员专用）"""
    from modules.auth import admin_required, get_all_users
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': '无管理员权限'}), 403
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    result = get_all_users(page=page, search=search)
    return jsonify(result)

@app.route('/api/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
def api_admin_set_role(user_id):
    """设置用户角色（管理员专用）"""
    from modules.auth import set_user_role
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': '无管理员权限'}), 403
    data = request.get_json() or {}
    result = set_user_role(user_id, data.get('role', ''))
    return jsonify(result), 200 if result['success'] else 400


@app.route('/api/admin/global-stats', methods=['GET'])
@login_required
def api_admin_global_stats():
    """全站聚合统计（管理员专用）"""
    from modules.auth import get_global_stats
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': '无管理员权限'}), 403
    return jsonify(get_global_stats())


@app.route('/api/admin/seed-data', methods=['POST'])
@login_required
def api_admin_seed_data():
    """为指定用户生成演示仿真数据（管理员专用）"""
    from modules.auth import seed_user_data
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': '无管理员权限'}), 403
    data = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '未提供用户 ID'}), 400
    return jsonify(seed_user_data(user_id))


# ==================== 启动服务 ====================

if __name__ == '__main__':
    from modules.logger import get_logger
    logger = get_logger()
    logger.info("🎰 澳门六合彩历史数据分析与模拟开奖系统")
    logger.info("📊 访问地址: http://127.0.0.1:5000")
    logger.info("⚠️  免责声明：本系统仅供统计学研究参考")
    app.run(debug=True, host='127.0.0.1', port=5000)

