"""
Flask Blueprints 包
功能：模块化路由组织，分离认证、页面、API 和管理员路由
"""

from blueprints.auth import auth_bp
from blueprints.pages import pages_bp
from blueprints.api import api_bp
from blueprints.admin import admin_bp

__all__ = ["auth_bp", "pages_bp", "api_bp", "admin_bp"]
