"""
认证蓝图
功能：处理用户认证相关的页面和 API
"""

from flask import Blueprint, render_template, redirect, request, jsonify, session

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login")
def page_login():
    if "user_id" in session:
        return redirect("/")
    return render_template("login.html")


@auth_bp.route("/register")
def page_register():
    if "user_id" in session:
        return redirect("/")
    return render_template("register.html")


@auth_bp.route("/logout")
def page_logout():
    session.clear()
    return redirect("/login")


@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    from modules.auth import register_user

    data = request.get_json() or {}
    result = register_user(data.get("username", ""), data.get("password", ""))
    if result["success"]:
        return jsonify(result)
    return jsonify(result), 400


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    from modules.auth import login_user

    data = request.get_json() or {}
    result = login_user(data.get("username", ""), data.get("password", ""))
    if result["success"]:
        session["user_id"] = result["user_id"]
        session["username"] = result["username"]
        session["role"] = result["role"]
        return jsonify(result)
    return jsonify(result), 401


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    from modules.auth import get_current_user

    user = get_current_user()
    if user:
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False}), 401
