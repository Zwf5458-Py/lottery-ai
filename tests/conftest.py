"""
pytest 配置文件
功能：设置测试环境、fixtures 和共享配置
"""

import pytest
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """创建测试用的 Flask 应用"""
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建 CLI 测试运行器"""
    return app.test_cli_runner()
