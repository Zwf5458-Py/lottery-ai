"""
Flask 主程序
功能：提供 Web 界面和 RESTful API，连接前端与后端核心模块。
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent


def _mask_secret(value):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "***" + value[-4:]


def _probe_openai_endpoint(api_base, model, api_key, timeout=15):
    import json
    import urllib.error
    import urllib.request

    if not api_base:
        return {"ok": False, "status": "red", "message": "未配置 API Base"}

    url = api_base.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0,
        "max_tokens": 5,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        return {
            "ok": True,
            "status": "green",
            "message": "连通成功",
            "url": url,
            "preview": body[:300],
        }
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        return {
            "ok": False,
            "status": "yellow" if e.code in (400, 401, 404) else "red",
            "message": f"HTTP {e.code}",
            "url": url,
            "detail": detail[:300],
        }
    except Exception as e:
        return {"ok": False, "status": "red", "message": str(e), "url": url}


def _run_docker_python(container_name, code, timeout=30):
    import json
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"success": False, "error": "当前环境未安装 docker CLI"}
    except Exception as e:
        return {"success": False, "error": str(e)}

    if result.returncode != 0:
        return {
            "success": False,
            "error": "docker exec 执行失败",
            "data": {
                "stderr": (result.stderr or "")[:500],
                "stdout": (result.stdout or "")[:500],
            },
        }

    output = (result.stdout or "").strip()
    try:
        return json.loads(output) if output else {"success": False, "error": "无输出"}
    except Exception:
        return {"success": False, "error": "输出无法解析", "raw": output[:500]}


def _get_docker_ai_env_snapshot(container_name="macau-mark-six"):
    probe_code = r"""
import os, json
data = {
    "LOCAL_AI_BASE": os.environ.get("LOCAL_AI_BASE", ""),
    "HOST_GATEWAY_URL": os.environ.get("HOST_GATEWAY_URL", ""),
    "LOCAL_AI_API_KEY_SET": bool(os.environ.get("LOCAL_AI_API_KEY", "")),
    "PLATFORM_OWNER_USERNAME": os.environ.get("PLATFORM_OWNER_USERNAME", ""),
}
print(json.dumps(data, ensure_ascii=False))
"""
    parsed = _run_docker_python(container_name, probe_code, timeout=20)
    if parsed.get("success") is False and parsed.get("error"):
        return {"ok": False, "container": container_name, **parsed}
    return {"ok": True, "container": container_name, **parsed}


def _run_docker_ai_probe(container_name="macau-mark-six"):
    probe_code = r"""
import json, os, urllib.error, urllib.request
env_base = (os.environ.get("LOCAL_AI_BASE") or "").strip()
gateway_base = (os.environ.get("HOST_GATEWAY_URL") or "").strip()
bases = []
for item in [env_base, gateway_base]:
    if item and item not in bases:
        bases.append(item)
key = os.environ.get("LOCAL_AI_API_KEY") or ""
payload = {"model":"gpt-5.4","messages":[{"role":"user","content":"ping"}],"temperature":0,"max_tokens":5}
headers = {"Content-Type":"application/json"}
if key:
    headers["Authorization"] = f"Bearer {key}"
attempts = []
if not bases:
    print(json.dumps({"success": False, "error": "LOCAL_AI_BASE/HOST_GATEWAY_URL 未配置", "attempts": []}, ensure_ascii=False))
    raise SystemExit(0)
for base in bases:
    url = base.rstrip("/") + "/chat/completions"
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        attempts.append({"base": base, "url": url, "success": True})
        print(json.dumps({"success": True, "base": base, "url": url, "preview": body[:300], "attempts": attempts}, ensure_ascii=False))
        raise SystemExit(0)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        attempts.append({"base": base, "url": url, "success": False, "error": f"HTTP {e.code}", "detail": detail[:200]})
    except Exception as e:
        attempts.append({"base": base, "url": url, "success": False, "error": str(e)})
last = attempts[-1] if attempts else {}
print(json.dumps({"success": False, "base": last.get("base", ""), "url": last.get("url", ""), "error": last.get("error", "未知错误"), "detail": last.get("detail", ""), "attempts": attempts}, ensure_ascii=False))
"""
    parsed = _run_docker_python(container_name, probe_code, timeout=30)
    if parsed.get("success") is False and parsed.get("error"):
        return {"ok": False, "container": container_name, **parsed}
    return {"ok": bool(parsed.get("success")), "container": container_name, **parsed}


def _save_platform_owner_ai_config(ai_payload):
    import json
    from modules.auth import get_user_db_connection
    from modules.config_manager import get_platform_owner_identity

    owner = get_platform_owner_identity()
    if not owner:
        return False, {"error": "未找到平台管理员账号"}

    conn = get_user_db_connection(owner["id"])
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
        ("ai", json.dumps(ai_payload, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    cache.clear()
    return True, owner


def _build_ai_diagnosis_data():
    from modules.config_manager import (
        load_global_config,
        get_platform_owner_ai_config,
        get_platform_owner_identity,
    )

    global_ai = (load_global_config() or {}).get("ai", {})
    owner_ai = get_platform_owner_ai_config() or {}
    owner = get_platform_owner_identity() or {}

    effective_base = (
        owner_ai.get("api_base")
        or global_ai.get("api_base")
        or os.environ.get("LOCAL_AI_BASE", "")
        or os.environ.get("HOST_GATEWAY_URL", "")
    )
    effective_model = owner_ai.get("model") or global_ai.get("model") or "gpt-5.4"
    effective_key = (
        owner_ai.get("api_key")
        or global_ai.get("api_key")
        or os.environ.get("LOCAL_AI_API_KEY", "")
    )

    direct_probe = _probe_openai_endpoint(
        effective_base, effective_model, effective_key
    )

    docker_env = _get_docker_ai_env_snapshot("macau-mark-six")
    docker_probe_raw = _run_docker_ai_probe("macau-mark-six")
    docker_probe = {
        "ok": docker_probe_raw.get("ok", False),
        "status": "green"
        if docker_probe_raw.get("ok")
        else (
            "yellow"
            if str(docker_probe_raw.get("error", "")).startswith("HTTP 4")
            else "red"
        ),
        "message": "容器连通成功"
        if docker_probe_raw.get("ok")
        else (docker_probe_raw.get("error") or "未执行"),
        "url": docker_probe_raw.get("url", ""),
        "detail": docker_probe_raw.get("detail", ""),
        "attempts": docker_probe_raw.get("attempts", []),
        "base": docker_probe_raw.get("base", ""),
    }

    bases = [
        ("平台管理员", owner_ai.get("api_base", "")),
        ("全局默认", global_ai.get("api_base", "")),
        ("本机环境", os.environ.get("LOCAL_AI_BASE", "")),
        ("Docker环境", docker_env.get("LOCAL_AI_BASE", "")),
        ("Docker网关", docker_env.get("HOST_GATEWAY_URL", "")),
    ]
    non_empty = [(label, base) for label, base in bases if base]
    unique_bases = sorted({base for _, base in non_empty})
    base_consistent = len(unique_bases) <= 1

    recommended_base = effective_base
    recommendation_reason = "当前生效地址保持不变"
    if docker_probe.get("ok") and docker_probe.get("base"):
        recommended_base = docker_probe["base"]
        recommendation_reason = "容器内实测成功，优先推荐容器可达地址"
    elif direct_probe.get("ok") and direct_probe.get("url"):
        recommended_base = direct_probe["url"].replace("/chat/completions", "")
        recommendation_reason = "本机实测成功，推荐当前生效地址"
    elif os.environ.get("HOST_GATEWAY_URL"):
        recommended_base = os.environ.get("HOST_GATEWAY_URL")
        recommendation_reason = "优先回退到宿主机网关地址"

    statuses = {
        "effective_config": {
            "status": "green" if effective_base and effective_model else "red",
            "message": f"平台管理员 {owner.get('username', '-')}, 平台={owner_ai.get('platform') or global_ai.get('platform', '-')}, 模型={effective_model}",
        },
        "direct_probe": direct_probe,
        "docker_probe": docker_probe,
        "consistency": {
            "status": "green" if base_consistent else "yellow",
            "message": "配置一致" if base_consistent else "发现多套 API Base 不一致",
            "bases": non_empty,
        },
        "env_snapshot": {
            "status": "green"
            if (docker_env.get("LOCAL_AI_BASE") or docker_env.get("HOST_GATEWAY_URL"))
            else "yellow",
            "message": "已获取环境快照",
            "docker_env": docker_env,
        },
    }

    return {
        "statuses": statuses,
        "recommended_base": recommended_base,
        "recommendation_reason": recommendation_reason,
        "effective_base": effective_base,
        "effective_model": effective_model,
        "owner": owner,
        "docker_probe_attempts": docker_probe.get("attempts", []),
        "autofix_preview": {
            "can_apply": bool(recommended_base),
            "target_base": recommended_base,
            "will_change": bool(
                recommended_base
                and recommended_base != (owner_ai.get("api_base") or effective_base)
            ),
            "reason": recommendation_reason,
            "source": "docker_probe"
            if docker_probe.get("ok")
            else ("direct_probe" if direct_probe.get("ok") else "fallback"),
        },
    }


from modules.statistics_engine import get_full_analysis
from modules.simulator import simulate_single, simulate_batch
from modules.data_processor import get_paginated_history
from modules.auth import (
    init_auth_db,
    login_required,
    vip_required,
    register_user,
    login_user,
    get_current_user,
    get_user_db_connection,
    USERS_DB_PATH,
)

app = Flask(__name__)
secret_key = os.environ.get("FLASK_SECRET_KEY")
if not secret_key:
    secret_key = os.urandom(32).hex()
app.secret_key = secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
)

# 配置文件系统缓存 (FileSystemCache) — 支持多 Worker 共享且重启后持久化
_cache_dir = os.path.join(os.path.dirname(__file__), "data", "cache")
os.makedirs(_cache_dir, exist_ok=True)
cache = Cache(
    app,
    config={
        "CACHE_TYPE": "FileSystemCache",
        "CACHE_DIR": _cache_dir,
        "CACHE_DEFAULT_TIMEOUT": 3600,
        "CACHE_THRESHOLD": 500,  # 最多缓存 500 个键
    },
)

# 配置请求限流器 (Limiter)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# 配置 CSRF 防护
csrf = CSRFProtect(app)


# ==================== 启动时初始化数据库 ====================
init_auth_db()

# 初始化加密密钥
from modules.crypto_utils import ensure_encryption_key

ensure_encryption_key()

# ==================== 注册 Blueprint ====================
# 注：Blueprint 文件已创建在 blueprints/ 目录，但目前使用原有的路由
# 完整迁移后可取消注释以下代码：
# from blueprints import auth_bp, pages_bp, api_bp, admin_bp
# app.register_blueprint(auth_bp)
# app.register_blueprint(pages_bp)
# app.register_blueprint(api_bp, url_prefix='/api')
# app.register_blueprint(admin_bp)


# ==================== 认证路由 ====================


@app.route("/login")
def page_login():
    if "user_id" in session:
        return redirect("/")
    return render_template("login.html")


@app.route("/register")
def page_register():
    if "user_id" in session:
        return redirect("/")
    return render_template("register.html")


@app.route("/logout")
def page_logout():
    session.clear()
    return redirect("/login")


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    result = register_user(data.get("username", ""), data.get("password", ""))
    if result["success"]:
        return jsonify(result)
    return jsonify(result), 400


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    result = login_user(data.get("username", ""), data.get("password", ""))
    if result["success"]:
        session["user_id"] = result["user_id"]
        session["username"] = result["username"]
        session["role"] = result["role"]
        return jsonify(result)
    return jsonify(result), 401


@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    user = get_current_user()
    if user:
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False}), 401


# ==================== 页面路由 ====================


@app.route("/")
@login_required
def index():
    """渲染主页"""
    user = get_current_user()
    return render_template("index.html", user=user)


@app.route("/points")
@login_required
def page_points():
    """积分中心页面"""
    user = get_current_user()
    return render_template("points.html", user=user)


@app.route("/reference")
@login_required
def page_reference():
    """特码对照表页面"""
    user = get_current_user()
    return render_template("reference.html", user=user)


@app.route("/health")
@login_required
def page_health():
    """系统健康页"""
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return redirect("/")
    return render_template("health.html", user=user)


@app.route("/admin/ai-ops")
@login_required
def page_admin_ai_ops():
    """AI 模型运维独立页"""
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return redirect("/")
    return render_template("ai_ops.html", user=user)


# ==================== API 路由 ====================


@app.route("/api/statistics", methods=["GET"])
@cache.cached(timeout=3600, query_string=True)
def api_statistics():
    """
    获取全部统计分析数据
    查询参数: type (macaujc 或 macaujc2)
    返回: JSON 格式的多维度统计结果
    """
    try:
        lottery_type = request.args.get("type", "macaujc")
        analysis = get_full_analysis(lottery_type)
        return jsonify({"success": True, "data": analysis})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/healthz", methods=["GET"])
def healthz():
    """轻量探活接口：供 Docker/Nginx/监控探针使用。"""
    try:
        cache.set("healthz_ping", "ok", timeout=5)
        cache_ok = cache.get("healthz_ping") == "ok"
    except Exception:
        cache_ok = False

    status = "ok" if cache_ok else "degraded"
    return jsonify(
        {"status": status, "service": "lottery_app"}
    ), 200 if cache_ok else 503


@app.route("/api/data-check", methods=["GET"])
def api_data_check():
    """检查数据新鲜度"""
    try:
        lottery_type = request.args.get("type", "macaujc2")
        from data.fetch_real_data import check_data_freshness

        result = check_data_freshness(lottery_type)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sync-data", methods=["POST"])
def api_sync_data():
    """增量同步最新数据"""
    try:
        data = request.get_json() or {}
        lottery_type = data.get("type", "macaujc2")
        from data.fetch_real_data import sync_latest

        result = sync_latest(lottery_type)
        if result.get("new_count", 0) > 0:
            cache.clear()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/simulate", methods=["POST"])
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
        from modules.logger import get_logger

        logger = get_logger()
        data = request.get_json() or {}
        count = data.get("count", 1)
        lottery_type = data.get("type", "macaujc")
        mode = data.get("mode", "weighted")
        points_deducted = 0
        points_balance = None

        dimensions = data.get(
            "dimensions", ["big_small", "odd_even", "hot_cold", "tail", "markov"]
        )
        if not isinstance(dimensions, list):
            dimensions = ["big_small", "odd_even", "hot_cold", "tail", "markov"]
        if "zodiac" in dimensions and "markov" not in dimensions:
            dimensions.append("markov")

        # 参数校验
        if not isinstance(count, int) or count < 1:
            count = 1
        if count > 1000:
            count = 1000

        # AI 调用积分扣费规则：
        # - admin：免费
        # - trial：平台模型扣 5 积分
        # - vip：平台模型扣 5 积分；若使用本人 API Key（自定义模型）免费
        if mode in ("ai", "ai_zodiac") and session.get("role") != "admin":
            from modules.points_manager import deduct_points
            from modules.config_manager import get_ai_config

            ai_cost = 5
            role = session.get("role", "trial")
            user_ai_cfg = get_ai_config(session["user_id"])
            user_api_key = str((user_ai_cfg or {}).get("api_key", "") or "").strip()

            # VIP 自己模型（有个人 API Key）免费
            if role == "vip" and user_api_key:
                ai_cost = 0

            if ai_cost > 0:
                deduct_res = deduct_points(
                    session["user_id"],
                    ai_cost,
                    "ai_simulation",
                    f"mode={mode},lottery_type={lottery_type}",
                )
                if not deduct_res.get("success"):
                    return jsonify(
                        {
                            "success": False,
                            "error": deduct_res.get(
                                "error", "积分不足，无法进行 AI 模拟"
                            ),
                            "points_balance": deduct_res.get("balance", 0),
                            "need_recharge": True,
                        }
                    ), 402
                points_deducted = ai_cost
                points_balance = deduct_res.get("balance")

        # ====== 数据新鲜度前置守卫 (带缓冲) ======
        from data.fetch_real_data import check_data_freshness, sync_latest

        fresh_cache_key = f"freshness_{lottery_type}"
        freshness = cache.get(fresh_cache_key)

        if not freshness:
            freshness = check_data_freshness(lottery_type)
            cache.set(fresh_cache_key, freshness, timeout=300)  # 缓存 5 分钟

        if not freshness["is_fresh"]:
            # 自动尝试同步
            logger.warning(f"⚠️ 数据滞后 {freshness['days_behind']} 天，自动触发同步...")
            sync_result = sync_latest(lottery_type)
            if sync_result.get("new_count", 0) > 0:
                cache.clear()
            # 同步后再次检查并强制更新缓存
            freshness = check_data_freshness(lottery_type)
            cache.set(fresh_cache_key, freshness, timeout=300)

            if not freshness["is_fresh"]:
                return jsonify(
                    {
                        "success": False,
                        "error": f"数据不是最新的！最新数据日期: {freshness['latest_date']}（滞后 {freshness['days_behind']} 天）。"
                        f"请先点击「同步最新」按钮手动同步，确保包含昨天的开奖数据后再进行模拟。",
                        "data_status": freshness,
                    }
                ), 400

        # AI 模式
        if mode == "ai":
            from modules.ai_engine import analyze_with_ai
            from modules.statistics_engine import get_zodiac_mapping
            import json
            from modules.data_processor import get_db_connection
            from modules.config_manager import load_config

            stats = get_full_analysis(lottery_type)
            ai_result = analyze_with_ai(stats, lottery_type, dimensions)

            # 为 AI 结果补充生肖映射
            z_map = get_zodiac_mapping(lottery_type)
            if "numbers" in ai_result and ai_result["numbers"]:
                ai_result["zodiacs"] = [z_map.get(n, "") for n in ai_result["numbers"]]
            if "special_num" in ai_result and ai_result["special_num"]:
                ai_result["special_zodiac"] = z_map.get(ai_result["special_num"], "")

            # ====== 新增：持久化 AI 推理过程到数据库 ======
            try:
                if ai_result.get("success", False):
                    cfg = load_config(session.get("user_id"))
                    model_name = cfg.get("ai", {}).get("model", "gemini-2.5-pro")
                    conn = get_user_db_connection(session["user_id"])
                    conn.execute(
                        """
                        INSERT INTO ai_analysis_history
                        (lottery_type, model_name, dimensions, result_json)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            lottery_type,
                            model_name,
                            json.dumps(dimensions, ensure_ascii=False),
                            json.dumps(ai_result, ensure_ascii=False),
                        ),
                    )
                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"保存 AI 分析记录失败: {e}")

            # 同时生成传统加权结果作为对比
            weighted_result = simulate_single(lottery_type, dimensions)

            # AI 失败则自动退回积分
            if points_deducted > 0 and not ai_result.get("success", False):
                try:
                    from modules.points_manager import add_points

                    refund_res = add_points(
                        session["user_id"],
                        points_deducted,
                        "ai_simulation_refund",
                        f"mode={mode},lottery_type={lottery_type}",
                    )
                    if refund_res.get("success"):
                        points_balance = refund_res.get("balance")
                        points_deducted = 0
                except Exception as refund_error:
                    logger.error(f"AI 失败后积分退回异常: {refund_error}")

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "mode": "ai",
                        "ai_result": ai_result,
                        "weighted_result": weighted_result,
                        "dimensions": dimensions,
                        "points_deducted": points_deducted,
                        "points_balance": points_balance,
                    },
                }
            )

        # AI 生肖专属推算模式
        if mode == "ai_zodiac":
            if lottery_type == 'weilitsai':
                return jsonify({"success": False, "error": "威力彩不支援生肖推算"}), 400
                
            from modules.ai_engine import analyze_zodiac_with_ai
            import json
            from modules.data_processor import get_db_connection
            from modules.config_manager import load_config

            stats = get_full_analysis(lottery_type)
            zodiac_result = analyze_zodiac_with_ai(stats, lottery_type, dimensions)

            # 持久化到数据库
            try:
                if zodiac_result.get("success", False):
                    cfg = load_config(session.get("user_id"))
                    model_name = cfg.get("ai", {}).get("model", "gemini-2.5-pro")
                    conn = get_user_db_connection(session["user_id"])
                    conn.execute(
                        """
                        INSERT INTO ai_analysis_history
                        (lottery_type, model_name, dimensions, result_json)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            lottery_type,
                            model_name,
                            json.dumps(
                                ["zodiac_mode"] + dimensions, ensure_ascii=False
                            ),
                            json.dumps(zodiac_result, ensure_ascii=False),
                        ),
                    )
                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"保存 AI 生肖推算记录失败: {e}")

            # AI 失败则自动退回积分
            if points_deducted > 0 and not zodiac_result.get("success", False):
                try:
                    from modules.points_manager import add_points

                    refund_res = add_points(
                        session["user_id"],
                        points_deducted,
                        "ai_simulation_refund",
                        f"mode={mode},lottery_type={lottery_type}",
                    )
                    if refund_res.get("success"):
                        points_balance = refund_res.get("balance")
                        points_deducted = 0
                except Exception as refund_error:
                    logger.error(f"AI 生肖失败后积分退回异常: {refund_error}")

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "mode": "ai_zodiac",
                        "zodiac_result": zodiac_result,
                        "dimensions": dimensions,
                        "points_deducted": points_deducted,
                        "points_balance": points_balance,
                    },
                }
            )

        # 传统加权模式
        if count == 1:
            result = simulate_single(lottery_type, dimensions)
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "mode": "weighted",
                        "draws": [result],
                        "summary": None,
                        "dimensions": dimensions,
                    },
                }
            )
        else:
            result = simulate_batch(count, lottery_type, dimensions)
            result["mode"] = "weighted"
            result["dimensions"] = dimensions
            return jsonify({"success": True, "data": result})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/simulate/wheeling', methods=['POST'])
@login_required
def api_simulate_wheeling():
    """
    智能模拟开奖 API (旋转矩阵模式)
    """
    data = request.json
    lottery_type = data.get('type', 'macaujc')
    count = min(int(data.get('count', 14)), 1000)
    count = max(count, 4)
    dimensions = data.get('dimensions', [])

    from data.fetch_real_data import check_data_freshness, sync_latest
    from modules.points_manager import deduct_points, get_user_points
    
    freshness = check_data_freshness(lottery_type)
    if not freshness['is_fresh']:
        sync_latest(lottery_type)

    if session.get("role") != "admin":
        deduct_res = deduct_points(session["user_id"], count, "wheeling_system", f"type={lottery_type},count={count}")
        if not deduct_res.get("success"):
            return jsonify({"success": False, "error": "积分不足"})
    
    from modules.wheeling_system import get_best_matrix, apply_matrix
    from modules.simulator import _calculate_trend_weights, _weighted_random_number, simulate_batch
    from modules.constants import get_zodiac_mapping
    
    matrix_template, remaining = get_best_matrix(count)
    
    if not matrix_template:
        # Budget too small, fallback to standard batch
        result = simulate_batch(count, lottery_type, dimensions)
        result['summary']['wheeling_info'] = f"预算 {count} 注过低，已回退为普通 AI 模拟 (最低要求 4 注)。"
        return jsonify({'success': True, 'data': result, 'points': get_user_points(session['user_id'])})
        
    weights_config = _calculate_trend_weights(lottery_type, dimensions)
    z_map = get_zodiac_mapping(lottery_type)
    max_regular = 38 if lottery_type == 'weilitsai' else 49
    max_special = 8 if lottery_type == 'weilitsai' else 49
    
    # Generate weights for 1 to max_regular
    num_weights = []
    for num in range(1, max_regular + 1):
        w = 1.0
        if num in weights_config.get('hot_cold_weights', {}):
            w *= weights_config['hot_cold_weights'][num]
        num_weights.append({'num': num, 'weight': w})
        
    # Sort by weight descending
    num_weights.sort(key=lambda x: x['weight'], reverse=True)
    
    # Pick top N numbers for the pool
    pool_size = matrix_template['pool_size']
    pool = sorted([x['num'] for x in num_weights[:pool_size]])
    
    # Apply matrix to get combinations
    combinations = apply_matrix(matrix_template['matrix'], pool)
    
    draws = []
    for combo in combinations:
        numbers = sorted(combo)
        exclude_special = set(numbers) if lottery_type != 'weilitsai' else None
        special_num = _weighted_random_number(weights_config, z_map, is_special=True, exclude_nums=exclude_special, max_num=max_special)
        draws.append({
            'numbers': numbers,
            'zodiacs': [z_map.get(n, '') for n in numbers],
            'special_num': special_num,
            'special_zodiac': z_map.get(special_num, '')
        })
        
    # Generate remaining tickets using standard AI
    if remaining > 0:
        standard_result = simulate_batch(remaining, lottery_type, dimensions)
        draws.extend(standard_result['draws'])
        
    # Generate summary
    from collections import Counter
    all_numbers = []
    special_nums = []
    special_zodiacs = []
    odd_count = 0
    even_count = 0
    big_count = 0
    small_count = 0
    
    for draw in draws:
        all_numbers.extend(draw['numbers'])
        special_nums.append(draw['special_num'])
        special_zodiacs.append(draw['special_zodiac'])
        if draw['special_num'] % 2 != 0:
            odd_count += 1
        else:
            even_count += 1
        if draw['special_num'] >= 25:
            big_count += 1
        else:
            small_count += 1
            
    number_counts = Counter(all_numbers)
    zodiac_counts = Counter(special_zodiacs)
    
    summary = {
        'total_draws': count,
        'hot_numbers': [num for num, _ in number_counts.most_common(5)],
        'cold_numbers': [num for num, _ in number_counts.most_common()[-5:]],
        'odd_even_ratio': f"{odd_count}:{even_count}",
        'big_small_ratio': f"{big_count}:{small_count}",
        'hot_special_zodiacs': [z for z, _ in zodiac_counts.most_common(3)],
        'wheeling_info': f"启用旋转矩阵：AI 精选 {pool_size} 码池，生成 {matrix_template['tickets']} 注 ({matrix_template['guarantee']})。剩余 {remaining} 注由标准 AI 填补。"
    }
    
    result = {
        'draws': draws,
        'summary': summary
    }

    return jsonify({
        'success': True,
        'data': result,
        'points': get_user_points(session['user_id'])
    })


@app.route("/api/history", methods=["GET"])
def api_history():
    """
    获取历史开奖记录（分页）
    查询参数: page（页码）、per_page（每页条数）、type（彩种）
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        lottery_type = request.args.get("type", "macaujc")

        # 参数范围限制
        page = max(1, page)
        per_page = max(1, min(100, per_page))

        result = get_paginated_history(page, per_page, lottery_type)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai_history", methods=["GET"])
@login_required
def api_ai_history():
    """获取 AI 分析历史记录（分页）—— 从用户独立数据库读取"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        lottery_type = request.args.get("type", "macaujc")

        page = max(1, page)
        per_page = max(1, min(50, per_page))
        offset = (page - 1) * per_page

        import json

        conn = get_user_db_connection(session["user_id"])

        # 获取总数
        total = conn.execute(
            "SELECT COUNT(*) FROM ai_analysis_history WHERE lottery_type=?",
            (lottery_type,),
        ).fetchone()[0]

        # 获取分页数据
        rows = conn.execute(
            "SELECT id, model_name, generated_at, dimensions, result_json FROM ai_analysis_history WHERE lottery_type=? ORDER BY generated_at DESC LIMIT ? OFFSET ?",
            (lottery_type, per_page, offset),
        ).fetchall()

        items = []
        for r in rows:
            items.append(
                {
                    "id": r[0],
                    "model_name": r[1],
                    "generated_at": r[2],
                    "dimensions": json.loads(r[3]) if r[3] else [],
                    "result": json.loads(r[4]) if r[4] else {},
                }
            )

        conn.close()

        return jsonify(
            {
                "success": True,
                "data": {
                    "items": items,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai_history/<int:record_id>", methods=["DELETE"])
@login_required
def api_delete_ai_history(record_id):
    """删除单条 AI 分析记录 —— 从用户独立数据库删除"""
    try:
        conn = get_user_db_connection(session["user_id"])
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ai_analysis_history WHERE id=?", (record_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            return jsonify({"success": True, "message": "已删除"})
        else:
            return jsonify({"success": False, "error": "找不到该记录"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 设置 API ====================


@app.route("/api/settings", methods=["GET"])
@login_required
def api_get_settings():
    """获取当前用户的个人设置"""
    try:
        from modules.config_manager import load_config

        config = load_config(session["user_id"])
        api_key = config.get("ai", {}).get("api_key", "")
        if api_key and len(api_key) > 8:
            config["ai"]["api_key_masked"] = api_key[:4] + "****" + api_key[-4:]
        else:
            config["ai"]["api_key_masked"] = api_key
        return jsonify({"success": True, "data": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
@login_required
def api_save_settings():
    """保存用户个人设置（图表期数对普通用户开放，按变更扣积分）"""
    try:
        from modules.config_manager import save_config, load_config
        from modules.points_manager import deduct_points

        data = request.get_json() or {}
        user_id = session["user_id"]
        role = session.get("role", "trial")

        # 普通用户允许设置 AI 平台与模型，但不允许改 API Key/API Base/自定义平台与模型
        if "ai" in data and role not in ("vip", "admin"):
            ai_in = data.get("ai", {}) if isinstance(data.get("ai"), dict) else {}
            safe_ai = {}
            if "platform" in ai_in:
                safe_ai["platform"] = ai_in.get("platform")
            if "model" in ai_in:
                safe_ai["model"] = ai_in.get("model")
            data["ai"] = safe_ai

        current_cfg = load_config(user_id)
        current_periods = (
            current_cfg.get("chart_periods", {})
            if isinstance(current_cfg, dict)
            else {}
        )
        incoming_periods = (
            data.get("chart_periods", {})
            if isinstance(data.get("chart_periods", {}), dict)
            else {}
        )

        # 每个变更图表扣 1 积分；hot_cold 和 tail 免费
        free_keys = {"hot_cold", "tail"}
        changed_keys = []
        paid_changed_count = 0
        for k, v in incoming_periods.items():
            if current_periods.get(k) != v:
                changed_keys.append(k)
                if k not in free_keys:
                    paid_changed_count += 1

        points_deducted = 0
        points_balance = None
        if paid_changed_count > 0 and role not in ("vip", "admin"):
            deduct_res = deduct_points(
                user_id,
                paid_changed_count,
                "settings_change",
                f"changed={','.join(changed_keys)}",
            )
            if not deduct_res.get("success"):
                return jsonify(
                    {
                        "success": False,
                        "error": deduct_res.get("error", "积分不足，无法保存设置"),
                        "points_balance": deduct_res.get("balance", 0),
                        "need_recharge": True,
                    }
                ), 402
            points_deducted = paid_changed_count
            points_balance = deduct_res.get("balance")

        success = save_config(data, user_id)
        if success:
            cache.clear()
            return jsonify(
                {
                    "success": True,
                    "message": "设置已保存",
                    "points_deducted": points_deducted,
                    "points_balance": points_balance,
                    "changed_keys": changed_keys,
                }
            )
        else:
            return jsonify({"success": False, "error": "保存失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 账号管理 API ====================


@app.route("/api/account/password", methods=["POST"])
@login_required
def api_change_password():
    """修改密码"""
    from modules.auth import change_password

    data = request.get_json() or {}
    result = change_password(
        session["user_id"], data.get("old_password", ""), data.get("new_password", "")
    )
    return jsonify(result), 200 if result["success"] else 400


@app.route("/api/account/email", methods=["GET"])
@login_required
def api_get_email():
    """获取当前用户邮箱"""
    from modules.auth import get_user_email

    email = get_user_email(session["user_id"])
    return jsonify({"success": True, "email": email})


@app.route("/api/account/email", methods=["POST"])
@login_required
def api_update_email():
    """更新邮箱"""
    from modules.auth import update_email

    data = request.get_json() or {}
    result = update_email(session["user_id"], data.get("email", ""))
    return jsonify(result), 200 if result["success"] else 400


@app.route("/api/account/referral", methods=["GET"])
@login_required
def api_get_referral_code():
    """获取当前用户推荐码"""
    from modules.auth import get_user_referral_code

    code = get_user_referral_code(session["user_id"])
    return jsonify({"success": True, "referral_code": code})


@app.route("/api/account/points-center", methods=["GET"])
@login_required
def api_account_points_center():
    """积分中心聚合数据"""
    try:
        from modules.points_manager import (
            get_user_points,
            get_points_ledger,
            get_recharge_history,
        )

        user_id = session["user_id"]
        ledger_page = request.args.get("ledger_page", 1, type=int)
        ledger_page_size = request.args.get("ledger_page_size", 10, type=int)
        recharge_page = request.args.get("recharge_page", 1, type=int)
        recharge_page_size = request.args.get("recharge_page_size", 10, type=int)

        ledger_page = max(1, ledger_page)
        ledger_page_size = max(1, min(100, ledger_page_size))
        recharge_page = max(1, recharge_page)
        recharge_page_size = max(1, min(100, recharge_page_size))

        points_balance = get_user_points(user_id)
        ledger_res = get_points_ledger(user_id, ledger_page, ledger_page_size)
        recharge_res = get_recharge_history(user_id, recharge_page, recharge_page_size)

        if not ledger_res.get("success"):
            return jsonify(
                {"success": False, "error": ledger_res.get("error", "积分流水读取失败")}
            ), 500
        if not recharge_res.get("success"):
            return jsonify(
                {
                    "success": False,
                    "error": recharge_res.get("error", "充值记录读取失败"),
                }
            ), 500

        return jsonify(
            {
                "success": True,
                "data": {
                    "points_balance": points_balance,
                    "points_ledger": ledger_res.get("items", []),
                    "points_ledger_pagination": ledger_res.get("pagination", {}),
                    "recharges": recharge_res.get("items", []),
                    "recharges_pagination": recharge_res.get("pagination", {}),
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 后台管理 ====================


@app.route("/admin")
def page_admin():
    """后台管理面板"""
    from modules.auth import admin_required as _ar

    # 手动检查管理员权限
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") != "admin":
        return redirect("/")
    user = get_current_user()
    return render_template("admin.html", user=user)


@app.route("/api/admin/users", methods=["GET"])
@login_required
def api_admin_users():
    """获取用户列表（管理员专用）"""
    from modules.auth import admin_required, get_all_users

    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    result = get_all_users(page=page, search=search)
    return jsonify(result)


@app.route("/api/admin/users/<int:user_id>/role", methods=["POST"])
@login_required
def api_admin_set_role(user_id):
    """设置用户角色（管理员专用）"""
    from modules.auth import set_user_role

    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403
    data = request.get_json() or {}
    result = set_user_role(user_id, data.get("role", ""))
    return jsonify(result), 200 if result["success"] else 400


@app.route("/api/admin/system-config", methods=["GET", "POST"])
@login_required
def api_admin_system_config():
    """系统计费与奖励配置（管理员专用）"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import get_system_config, save_global_config

    if request.method == "GET":
        return jsonify({"success": True, "data": get_system_config()})

    data = request.get_json() or {}
    payload = {
        "system": {
            "ai_sim_cost": max(0, int(data.get("ai_sim_cost", 5) or 0)),
            "settings_change_cost": max(
                0, int(data.get("settings_change_cost", 1) or 0)
            ),
            "share_reward_ratio": max(
                0.0, float(data.get("share_reward_ratio", 0.2) or 0.0)
            ),
            "share_reward_points": max(
                0, int(data.get("share_reward_points", 10) or 0)
            ),
            "share_recharge_min": max(
                0.0, float(data.get("share_recharge_min", 5) or 0.0)
            ),
            "points_per_yuan": max(0, int(data.get("points_per_yuan", 10) or 0)),
            "vip_monthly_fee": max(0, int(data.get("vip_monthly_fee", 99) or 0)),
        }
    }
    ok = save_global_config(payload)
    if not ok:
        return jsonify({"success": False, "error": "配置保存失败"}), 500
    cache.clear()
    return jsonify(
        {"success": True, "message": "系统配置已保存", "data": get_system_config()}
    )


@app.route("/api/admin/ai-config", methods=["GET"])
@login_required
def api_admin_ai_config():
    """查看平台模型配置与当前生效配置"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    import os
    from modules.config_manager import (
        load_global_config,
        get_platform_owner_ai_config,
        get_platform_owner_identity,
    )

    global_ai = (load_global_config() or {}).get("ai", {})
    owner = get_platform_owner_identity()
    owner_ai = get_platform_owner_ai_config()

    env_cfg = {
        "LOCAL_AI_BASE": os.environ.get("LOCAL_AI_BASE", ""),
        "HOST_GATEWAY_URL": os.environ.get("HOST_GATEWAY_URL", ""),
        "LOCAL_AI_API_KEY": _mask_secret(os.environ.get("LOCAL_AI_API_KEY", "")),
        "PLATFORM_OWNER_USERNAME": os.environ.get("PLATFORM_OWNER_USERNAME", ""),
    }

    effective = {
        "platform": owner_ai.get("platform") or global_ai.get("platform", ""),
        "model": owner_ai.get("model") or global_ai.get("model", ""),
        "api_base": owner_ai.get("api_base")
        or global_ai.get("api_base")
        or os.environ.get("LOCAL_AI_BASE", ""),
        "api_key_masked": _mask_secret(
            owner_ai.get("api_key")
            or global_ai.get("api_key")
            or os.environ.get("LOCAL_AI_API_KEY", "")
        ),
    }

    return jsonify(
        {
            "success": True,
            "data": {
                "platform_owner": owner,
                "platform_owner_ai": owner_ai,
                "global_ai": global_ai,
                "env": env_cfg,
                "effective": effective,
            },
        }
    )


@app.route("/api/admin/ai-config", methods=["POST"])
@login_required
def api_admin_ai_config_save():
    """保存平台管理员 AI 配置"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    data = request.get_json() or {}
    ai_payload = {
        "platform": str(data.get("platform", "local") or "local").strip(),
        "model": str(data.get("model", "gpt-5.4") or "gpt-5.4").strip(),
        "api_base": str(data.get("api_base", "") or "").strip(),
        "api_key": str(data.get("api_key", "") or "").strip(),
    }

    ok, payload_meta = _save_platform_owner_ai_config(ai_payload)
    if not ok:
        return jsonify({"success": False, **payload_meta}), 404
    return jsonify(
        {"success": True, "message": "平台管理员 AI 配置已保存", "data": ai_payload}
    )


@app.route("/api/admin/ai-config/test", methods=["POST"])
@login_required
def api_admin_ai_config_test():
    """一键测试模型接口连通性"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import load_global_config, get_platform_owner_ai_config

    global_ai = (load_global_config() or {}).get("ai", {})
    owner_ai = get_platform_owner_ai_config()
    api_base = (
        owner_ai.get("api_base")
        or global_ai.get("api_base")
        or os.environ.get("LOCAL_AI_BASE", "")
    )
    model = owner_ai.get("model") or global_ai.get("model") or "gpt-5.4"
    api_key = (
        owner_ai.get("api_key")
        or global_ai.get("api_key")
        or os.environ.get("LOCAL_AI_API_KEY", "")
    )

    if not api_base:
        return jsonify({"success": False, "error": "未配置 API Base"}), 400

    result = _probe_openai_endpoint(api_base, model, api_key, timeout=20)
    status_code = 200 if result.get("ok") else 400
    return jsonify(
        {
            "success": bool(result.get("ok")),
            "message": result.get("message", ""),
            "error": None if result.get("ok") else result.get("message", "测试失败"),
            "data": {
                "url": result.get("url", ""),
                "model": model,
                "preview": result.get("preview", ""),
                "detail": result.get("detail", ""),
            },
        }
    ), status_code


@app.route("/api/admin/ai-config/effective-user", methods=["GET"])
@login_required
def api_admin_ai_effective_user():
    """查看指定用户最终继承的 AI 配置来源"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import (
        load_config,
        load_global_config,
        get_platform_owner_ai_config,
        get_platform_owner_identity,
    )

    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"success": False, "error": "缺少 user_id"}), 400

    user_cfg = load_config(user_id).get("ai", {})
    owner = get_platform_owner_identity()
    owner_ai = get_platform_owner_ai_config()
    global_ai = (load_global_config() or {}).get("ai", {})

    effective = {
        "platform": user_cfg.get("platform")
        or owner_ai.get("platform")
        or global_ai.get("platform", ""),
        "model": user_cfg.get("model")
        or owner_ai.get("model")
        or global_ai.get("model", ""),
        "api_base": user_cfg.get("api_base")
        or owner_ai.get("api_base")
        or global_ai.get("api_base", "")
        or os.environ.get("LOCAL_AI_BASE", ""),
        "api_key_source": "user"
        if user_cfg.get("api_key")
        else (
            "platform_owner"
            if owner_ai.get("api_key")
            else (
                "global_or_env"
                if (global_ai.get("api_key") or os.environ.get("LOCAL_AI_API_KEY"))
                else "none"
            )
        ),
    }

    return jsonify(
        {
            "success": True,
            "data": {
                "user_id": user_id,
                "user_ai": user_cfg,
                "platform_owner": owner,
                "platform_owner_ai": owner_ai,
                "global_ai": global_ai,
                "effective": effective,
            },
        }
    )


@app.route("/api/admin/ai-config/test-docker", methods=["POST"])
@login_required
def api_admin_ai_config_test_docker():
    """通过 docker exec 从容器内部真实探测模型连通性"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    container_name = request.get_json(silent=True) or {}
    container_name = (
        str(container_name.get("container", "macau-mark-six")).strip()
        or "macau-mark-six"
    )
    parsed = _run_docker_ai_probe(container_name)
    return jsonify(
        {"success": bool(parsed.get("ok")), "data": parsed}
    ), 200 if parsed.get("ok") else 400


@app.route("/api/admin/ai-config/docker-env", methods=["GET"])
@login_required
def api_admin_ai_config_docker_env():
    """查看 Docker 容器内 AI 相关环境变量快照"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    container_name = (
        request.args.get("container", "macau-mark-six").strip() or "macau-mark-six"
    )
    data = _get_docker_ai_env_snapshot(container_name)
    if not data.get("ok"):
        return jsonify(
            {"success": False, "error": data.get("error", "读取失败"), "data": data}
        ), 400
    return jsonify({"success": True, "data": data})


@app.route("/api/admin/ai-config/compare", methods=["GET"])
@login_required
def api_admin_ai_config_compare():
    """比较本机环境、平台管理员、Docker 容器与全局配置是否一致"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import load_global_config, get_platform_owner_ai_config

    global_ai = (load_global_config() or {}).get("ai", {})
    owner_ai = get_platform_owner_ai_config() or {}
    env_base = os.environ.get("LOCAL_AI_BASE", "")
    env_key = bool(os.environ.get("LOCAL_AI_API_KEY", ""))

    docker_snapshot = _get_docker_ai_env_snapshot("macau-mark-six")
    docker_base = docker_snapshot.get("LOCAL_AI_BASE", "")
    docker_key = bool(docker_snapshot.get("LOCAL_AI_API_KEY_SET"))

    effective_base = owner_ai.get("api_base") or global_ai.get("api_base") or env_base
    consistency = {
        "effective_base": effective_base,
        "owner_base": owner_ai.get("api_base", ""),
        "global_base": global_ai.get("api_base", ""),
        "env_base": env_base,
        "docker_base": docker_base,
        "owner_has_key": bool(owner_ai.get("api_key", "")),
        "global_has_key": bool(global_ai.get("api_key", "")),
        "env_has_key": env_key,
        "docker_has_key": docker_key,
        "base_consistent": len(
            {
                x
                for x in [
                    effective_base,
                    owner_ai.get("api_base", ""),
                    global_ai.get("api_base", ""),
                    env_base,
                    docker_base,
                ]
                if x
            }
        )
        <= 1,
    }
    return jsonify({"success": True, "data": consistency})


@app.route("/api/admin/ai-config/apply-tested-base", methods=["POST"])
@login_required
def api_admin_ai_config_apply_tested_base():
    """将指定 base 一键写入平台管理员 AI 配置"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import get_platform_owner_ai_config

    payload = request.get_json() or {}
    api_base = str(payload.get("api_base", "") or "").strip()
    if not api_base:
        return jsonify({"success": False, "error": "缺少 api_base"}), 400

    current_ai = get_platform_owner_ai_config() or {}
    current_ai["api_base"] = api_base

    ok, payload_meta = _save_platform_owner_ai_config(current_ai)
    if not ok:
        return jsonify({"success": False, **payload_meta}), 404
    return jsonify(
        {"success": True, "message": "已写入平台默认地址", "data": current_ai}
    )


@app.route("/api/admin/ai-config/diagnose", methods=["GET"])
@login_required
def api_admin_ai_config_diagnose():
    """一键 AI 诊断报告：环境、配置一致性、本机连通性、容器连通性。"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403
    return jsonify({"success": True, "data": _build_ai_diagnosis_data()})


@app.route("/api/admin/ai-config/auto-fix", methods=["POST"])
@login_required
def api_admin_ai_config_auto_fix():
    """根据自动诊断结果一键修复平台默认 AI 地址"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import get_platform_owner_ai_config

    diagnose_data = _build_ai_diagnosis_data()
    recommended_base = diagnose_data.get("recommended_base", "")
    if not recommended_base:
        return jsonify({"success": False, "error": "没有可用的推荐地址"}), 400

    current_ai = get_platform_owner_ai_config() or {}
    current_ai["api_base"] = recommended_base

    ok, payload_meta = _save_platform_owner_ai_config(current_ai)
    if not ok:
        return jsonify({"success": False, **payload_meta}), 404

    return jsonify(
        {
            "success": True,
            "message": "已按自动诊断结果修复平台默认地址",
            "data": {
                "recommended_base": recommended_base,
                "ai": current_ai,
                "diagnosis": diagnose_data,
            },
        }
    )


@app.route("/api/admin/ai-config/test-and-auto-fix", methods=["POST"])
@login_required
def api_admin_ai_config_test_and_auto_fix():
    """先执行容器内实测，再按诊断推荐结果自动修复平台默认地址。"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import get_platform_owner_ai_config

    payload = request.get_json(silent=True) or {}
    container_name = (
        str(payload.get("container", "macau-mark-six") or "macau-mark-six").strip()
        or "macau-mark-six"
    )

    docker_probe = _run_docker_ai_probe(container_name)
    diagnosis = _build_ai_diagnosis_data()
    recommended_base = diagnosis.get("recommended_base", "")

    if not docker_probe.get("ok"):
        return jsonify(
            {
                "success": False,
                "error": docker_probe.get("error") or "容器内测试失败，未执行自动修复",
                "data": {
                    "container": container_name,
                    "docker_probe": docker_probe,
                    "diagnosis": diagnosis,
                    "applied": False,
                },
            }
        ), 400

    if not recommended_base:
        return jsonify(
            {
                "success": False,
                "error": "容器测试通过，但未生成可应用的推荐地址",
                "data": {
                    "container": container_name,
                    "docker_probe": docker_probe,
                    "diagnosis": diagnosis,
                    "applied": False,
                },
            }
        ), 400

    current_ai = get_platform_owner_ai_config() or {}
    previous_base = current_ai.get("api_base", "")
    current_ai["api_base"] = recommended_base

    ok, payload_meta = _save_platform_owner_ai_config(current_ai)
    if not ok:
        return jsonify({"success": False, **payload_meta}), 404

    refreshed_diagnosis = _build_ai_diagnosis_data()
    return jsonify(
        {
            "success": True,
            "message": "容器内实测成功，已自动修复平台默认地址",
            "data": {
                "container": container_name,
                "previous_base": previous_base,
                "applied_base": recommended_base,
                "docker_probe": docker_probe,
                "diagnosis": refreshed_diagnosis,
                "applied": True,
            },
        }
    )


@app.route("/api/admin/ai-config/export-diagnosis", methods=["GET"])
@login_required
def api_admin_ai_config_export_diagnosis():
    """导出 AI 诊断报告为 JSON"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403
    return api_admin_ai_config_diagnose()


@app.route("/api/admin/ai-config/recent-failures", methods=["GET"])
@login_required
def api_admin_ai_config_recent_failures():
    """读取最近 AI 故障日志（开发模式从 logs/dev.out 中抓取）"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    import os

    log_path = os.path.join(BASE_DIR, "logs", "dev.out")
    if not os.path.exists(log_path):
        return jsonify({"success": True, "data": {"items": []}})

    keywords = [
        "AI 分析异常",
        "所有候选模型均失败",
        "HTTP 401",
        "HTTP 404",
        "URLError",
        "Connection refused",
    ]
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        matched = [line.strip() for line in lines if any(k in line for k in keywords)]
        return jsonify({"success": True, "data": {"items": matched[-10:]}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/admin/impersonate", methods=["POST"])
@login_required
def api_admin_impersonate():
    """管理员模拟登录为指定用户"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.auth import get_user_basic

    data = request.get_json() or {}
    user_id = data.get("user_id", 0)
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({"success": False, "error": "用户 ID 非法"}), 400

    target = get_user_basic(user_id)
    if not target:
        return jsonify({"success": False, "error": "用户不存在"}), 404

    session["user_id"] = target["id"]
    session["username"] = target["username"]
    session["role"] = target["role"]
    return jsonify(
        {
            "success": True,
            "message": f"已切换为用户 {target['username']}",
            "redirect": "/",
        }
    )


@app.route("/api/admin/reset-password", methods=["POST"])
@login_required
def api_admin_reset_password():
    """管理员重置用户密码"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.auth import admin_reset_password

    data = request.get_json() or {}
    user_id = data.get("user_id", 0)
    password = data.get("password", "")
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({"success": False, "error": "用户 ID 非法"}), 400

    result = admin_reset_password(user_id, password)
    return jsonify(result), 200 if result.get("success") else 400


@app.route("/api/admin/recharge", methods=["POST"])
@login_required
def api_admin_recharge():
    """管理员为指定用户充值积分"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.config_manager import get_system_config
    from modules.points_manager import record_recharge, apply_referral_recharge_reward

    data = request.get_json() or {}
    user_id = data.get("user_id", 0)
    amount = data.get("amount", 0)

    try:
        user_id = int(user_id)
        amount = float(amount)
    except Exception:
        return jsonify({"success": False, "error": "参数格式错误"}), 400

    if amount <= 0:
        return jsonify({"success": False, "error": "充值金额必须大于 0"}), 400

    sys_cfg = get_system_config()
    points_per_yuan = int(sys_cfg.get("points_per_yuan", 10) or 10)
    recharge_min = float(sys_cfg.get("share_recharge_min", 5) or 5)
    reward_ratio = float(sys_cfg.get("share_reward_ratio", 0) or 0)
    reward_fixed = int(sys_cfg.get("share_reward_points", 10) or 10)

    base_points = int(round(amount * points_per_yuan))
    reward_points = (
        int(round(base_points * reward_ratio)) if reward_ratio > 0 else reward_fixed
    )
    if reward_points <= 0:
        reward_points = reward_fixed

    recharge_res = record_recharge(user_id, amount, points_per_yuan)
    if not recharge_res.get("success"):
        return jsonify(recharge_res), 400

    reward_res = apply_referral_recharge_reward(
        user_id, amount, recharge_min, reward_points
    )
    return jsonify(
        {
            "success": True,
            "message": "充值成功",
            "data": {
                "points_added": recharge_res.get("points", 0),
                "recharge_count": recharge_res.get("recharge_count", 0),
                "referral_reward": reward_res,
            },
        }
    )


@app.route("/api/admin/deduct-points", methods=["POST"])
@login_required
def api_admin_deduct_points():
    """管理员为指定用户扣除积分"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    from modules.points_manager import deduct_points

    data = request.get_json() or {}
    user_id = data.get("user_id", 0)
    amount = data.get("amount", 0)
    reason = str(data.get("reason", "admin_adjust")).strip() or "admin_adjust"
    note = str(data.get("note", "")).strip()

    try:
        user_id = int(user_id)
        amount = int(amount)
    except Exception:
        return jsonify({"success": False, "error": "参数格式错误"}), 400

    if amount <= 0:
        return jsonify({"success": False, "error": "扣除积分必须大于 0"}), 400

    meta = f"admin={session.get('username', '')}"
    if note:
        meta = f"{meta},note={note}"

    result = deduct_points(user_id, amount, reason, meta)
    if not result.get("success"):
        return jsonify(result), 400

    return jsonify(
        {
            "success": True,
            "message": f"已扣除 {amount} 积分",
            "data": {
                "user_id": user_id,
                "amount": amount,
                "balance": result.get("balance", 0),
            },
        }
    )


@app.route("/api/admin/global-stats", methods=["GET"])
@login_required
def api_admin_global_stats():
    """全站聚合统计（管理员专用）"""
    from modules.auth import get_global_stats

    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403
    return jsonify(get_global_stats())


@app.route("/api/admin/seed-data", methods=["POST"])
@login_required
def api_admin_seed_data():
    """为指定用户生成演示仿真数据（管理员专用）"""
    from modules.auth import seed_user_data

    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "未提供用户 ID"}), 400
    return jsonify(seed_user_data(user_id))


@app.route("/api/admin/health", methods=["GET"])
@login_required
def api_admin_health():
    """系统健康状态：AI/数据库/抓数/缓存/日志"""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "无管理员权限"}), 403

    import sqlite3
    from data.fetch_real_data import check_data_freshness
    from modules.config_manager import get_platform_owner_ai_config, load_global_config

    health = {}

    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        health["database"] = {"status": "green", "message": "users.db 可读写"}
    except Exception as e:
        health["database"] = {"status": "red", "message": str(e)}

    try:
        freshness = check_data_freshness("macaujc2")
        days = int(freshness.get("days_behind", 999))
        health["data_sync"] = {
            "status": "green" if days <= 1 else ("yellow" if days <= 3 else "red"),
            "message": f"数据滞后 {days} 天",
        }
    except Exception as e:
        health["data_sync"] = {"status": "red", "message": str(e)}

    try:
        owner_ai = get_platform_owner_ai_config() or {}
        global_ai = (load_global_config() or {}).get("ai", {})
        api_base = (
            owner_ai.get("api_base")
            or global_ai.get("api_base")
            or os.environ.get("LOCAL_AI_BASE", "")
        )
        api_key_ok = bool(
            owner_ai.get("api_key")
            or global_ai.get("api_key")
            or os.environ.get("LOCAL_AI_API_KEY", "")
        )
        health["ai"] = {
            "status": "green" if api_base and api_key_ok else "yellow",
            "message": f"API Base={api_base or '-'} ｜ Key={'已配置' if api_key_ok else '未配置'}",
        }
    except Exception as e:
        health["ai"] = {"status": "red", "message": str(e)}

    try:
        cache.set("health_check_key", "ok", timeout=10)
        val = cache.get("health_check_key")
        health["cache"] = {
            "status": "green" if val == "ok" else "yellow",
            "message": "缓存可用" if val == "ok" else "缓存读写异常",
        }
    except Exception as e:
        health["cache"] = {"status": "red", "message": str(e)}

    try:
        ai_log = BASE_DIR / "logs" / "ai_errors.log"
        exists = ai_log.exists()
        size = ai_log.stat().st_size if exists else 0
        health["logs"] = {
            "status": "green" if exists else "yellow",
            "message": f"AI 故障日志 {'存在' if exists else '未生成'} ｜ {size} bytes",
        }
    except Exception as e:
        health["logs"] = {"status": "red", "message": str(e)}

    return jsonify({"success": True, "data": health})


# ==================== 启动服务 ====================

if __name__ == "__main__":
    from modules.logger import get_logger

    logger = get_logger()
    if not os.environ.get("FLASK_SECRET_KEY"):
        logger.warning(
            "FLASK_SECRET_KEY 未设置，当前使用进程内临时密钥（重启后会失效）。"
        )
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    logger.info("🎰 澳门六合彩历史数据分析与模拟开奖系统")
    logger.info(f"📊 访问地址: http://{host}:{port}")
    logger.info("⚠️  免责声明：本系统仅供统计学研究参考")
    app.run(debug=debug_mode, host=host, port=port)
