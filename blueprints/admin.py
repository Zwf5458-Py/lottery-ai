"""
管理员蓝图
功能：处理管理员相关的路由
"""

from flask import Blueprint, render_template, redirect, session

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/health")
def page_health():
    from modules.auth import login_required, get_current_user

    @login_required
    def _page_health():
        user = get_current_user()
        if not user or user.get("role") != "admin":
            return redirect("/")
        return render_template("health.html", user=user)

    return _page_health()


@admin_bp.route("/ai-ops")
def page_ai_ops():
    from modules.auth import login_required, get_current_user

    @login_required
    def _page_ai_ops():
        user = get_current_user()
        if not user or user.get("role") != "admin":
            return redirect("/")
        return render_template("ai_ops.html", user=user)

    return _page_ai_ops()
