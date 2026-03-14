"""
页面蓝图
功能：处理页面渲染相关的路由
"""

from flask import Blueprint, render_template, redirect

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    from modules.auth import login_required, get_current_user

    @login_required
    def _index():
        user = get_current_user()
        return render_template("index.html", user=user)

    return _index()


@pages_bp.route("/points")
def page_points():
    from modules.auth import login_required, get_current_user

    @login_required
    def _page_points():
        user = get_current_user()
        return render_template("points.html", user=user)

    return _page_points()


@pages_bp.route("/reference")
def page_reference():
    from modules.auth import login_required, get_current_user

    @login_required
    def _page_reference():
        user = get_current_user()
        return render_template("reference.html", user=user)

    return _page_reference()
