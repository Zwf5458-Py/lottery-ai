"""
API 蓝图
功能：处理核心 API 路由
"""

from flask import Blueprint, request, jsonify, session

api_bp = Blueprint("api", __name__)


@api_bp.route("/statistics", methods=["GET"])
def api_statistics():
    from flask import current_app

    cache = current_app.extensions.get("cache")
    lottery_type = request.args.get("type", "macaujc")
    try:
        from modules.statistics_engine import get_full_analysis

        analysis = get_full_analysis(lottery_type)
        return jsonify({"success": True, "data": analysis})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/healthz", methods=["GET"])
def healthz():
    from flask import current_app

    cache = current_app.extensions.get("cache")
    try:
        cache.set("healthz_ping", "ok", timeout=5)
        cache_ok = cache.get("healthz_ping") == "ok"
    except Exception:
        cache_ok = False
    status = "ok" if cache_ok else "degraded"
    return jsonify(
        {"status": status, "service": "lottery_app"}
    ), 200 if cache_ok else 503


@api_bp.route("/data-check", methods=["GET"])
def api_data_check():
    lottery_type = request.args.get("type", "macaujc2")
    try:
        from data.fetch_real_data import check_data_freshness

        result = check_data_freshness(lottery_type)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/sync-data", methods=["POST"])
def api_sync_data():
    from flask import current_app

    cache = current_app.extensions.get("cache")
    data = request.get_json() or {}
    lottery_type = data.get("type", "macaujc2")
    try:
        from data.fetch_real_data import sync_latest

        result = sync_latest(lottery_type)
        if result.get("new_count", 0) > 0:
            cache.clear()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
