"""
加密工具模块单元测试
"""

import pytest
from modules.crypto_utils import (
    encrypt_value,
    decrypt_value,
    encrypt_api_key,
    decrypt_api_key,
    is_encrypted,
)


class TestEncryption:
    """加密/解密测试"""

    def test_encrypt_returns_string(self):
        """测试加密返回字符串"""
        plaintext = "my_api_key_123"
        encrypted = encrypt_value(plaintext)
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_encrypt_adds_prefix(self):
        """测试加密值带有前缀"""
        plaintext = "test_value"
        encrypted = encrypt_value(plaintext)
        assert encrypted.startswith("enc:")

    def test_decrypt_returns_original(self):
        """测试解密返回原始值"""
        plaintext = "original_api_key"
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        encrypted = encrypt_value("")
        assert encrypted == ""

    def test_decrypt_empty_string(self):
        """测试解密空字符串"""
        decrypted = decrypt_value("")
        assert decrypted == ""

    def test_encrypt_already_encrypted(self):
        """测试已加密值不会被重复加密"""
        encrypted1 = encrypt_value("test")
        encrypted2 = encrypt_value(encrypted1)
        assert encrypted1 == encrypted2

    def test_decrypt_unencrypted_value(self):
        """测试解密未加密值返回原值"""
        plaintext = "unencrypted_value"
        decrypted = decrypt_value(plaintext)
        assert decrypted == plaintext


class TestIsEncrypted:
    """加密状态检测测试"""

    def test_is_encrypted_true(self):
        """测试检测已加密值"""
        encrypted = encrypt_value("test")
        assert is_encrypted(encrypted) is True

    def test_is_encrypted_false(self):
        """测试检测未加密值"""
        assert is_encrypted("plain_value") is False

    def test_is_encrypted_empty(self):
        """测试空字符串"""
        assert is_encrypted("") is False


class TestApiKeyHelpers:
    """API Key 辅助函数测试"""

    def test_encrypt_api_key(self):
        """测试 API Key 加密"""
        api_key = "sk-1234567890abcdef"
        encrypted = encrypt_api_key(api_key)
        assert encrypted.startswith("enc:")
        assert decrypt_api_key(encrypted) == api_key

    def test_decrypt_api_key(self):
        """测试 API Key 解密"""
        api_key = "sk-abcdefghijklmnop"
        encrypted = encrypt_api_key(api_key)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == api_key

    def test_round_trip(self):
        """测试加密-解密往返"""
        original = "my_secret_api_key_12345"
        encrypted = encrypt_api_key(original)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original
