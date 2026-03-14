"""
认证模块单元测试
"""

import pytest
from modules.auth import (
    _hash_password,
    _verify_password,
    register_user,
    login_user,
)


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password_returns_string(self):
        """测试密码哈希返回字符串"""
        password = "test_password_123"
        hashed = _hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_contains_algorithm(self):
        """测试哈希值包含算法标识"""
        password = "test_password"
        hashed = _hash_password(password)
        assert hashed.startswith("pbkdf2_sha256$")

    def test_hash_password_unique_salts(self):
        """测试相同密码产生不同哈希"""
        password = "same_password"
        hash1 = _hash_password(password)
        hash2 = _hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "correct_password"
        hashed = _hash_password(password)
        assert _verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = _hash_password(password)
        assert _verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """测试空密码"""
        hashed = _hash_password("some_password")
        assert _verify_password("", hashed) is False


class TestUserRegistration:
    """用户注册测试"""

    def test_register_empty_username(self):
        """测试空用户名注册"""
        result = register_user("", "password123")
        assert result["success"] is False
        assert "用户名" in result["error"]

    def test_register_empty_password(self):
        """测试空密码注册"""
        result = register_user("testuser", "")
        assert result["success"] is False
        assert "密码" in result["error"]

    def test_register_short_username(self):
        """测试过短用户名"""
        result = register_user("a", "password123")
        assert result["success"] is False
        assert "长度" in result["error"]

    def test_register_short_password(self):
        """测试过短密码"""
        result = register_user("testuser", "abc")
        assert result["success"] is False
        assert "密码" in result["error"]


class TestUserLogin:
    """用户登录测试"""

    def test_login_empty_credentials(self):
        """测试空凭据登录"""
        result = login_user("", "")
        assert result["success"] is False

    def test_login_missing_username(self):
        """测试缺失用户名"""
        result = login_user("", "password")
        assert result["success"] is False
