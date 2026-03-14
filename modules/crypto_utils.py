"""
加密工具模块
功能：提供 API Key 等敏感数据的加密/解密功能
使用 Fernet (AES-128) 对称加密算法
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 加密密钥文件路径
KEY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".secret_key"
)
_SALT = b"liuhecai_encryption_salt_v1"  # 固定盐值，用于密钥派生


def _get_or_create_key() -> bytes:
    """
    获取或创建加密密钥。
    如果密钥文件不存在，自动生成一个新密钥。
    """
    # 确保目录存在
    key_dir = os.path.dirname(KEY_FILE)
    if not os.path.exists(key_dir):
        os.makedirs(key_dir, exist_ok=True)

    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()

    # 生成新密钥
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)

    # 设置文件权限为仅所有者可读写
    os.chmod(KEY_FILE, 0o600)

    return key


def _get_fernet() -> Fernet:
    """获取 Fernet 实例"""
    key = _get_or_create_key()
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """
    加密字符串

    Args:
        plaintext: 明文字符串

    Returns:
        加密后的 Base64 编码字符串（带前缀 'enc:' 标识）
    """
    if not plaintext:
        return ""

    # 如果已经加密过，直接返回
    if plaintext.startswith("enc:"):
        return plaintext

    try:
        f = _get_fernet()
        encrypted = f.encrypt(plaintext.encode("utf-8"))
        return "enc:" + encrypted.decode("utf-8")
    except Exception as e:
        # 加密失败，返回原文（兼容旧数据）
        print(f"⚠️ 加密失败: {e}")
        return plaintext


def decrypt_value(ciphertext: str) -> str:
    """
    解密字符串

    Args:
        ciphertext: 加密后的字符串（带 'enc:' 前缀）

    Returns:
        解密后的明文字符串
    """
    if not ciphertext:
        return ""

    # 如果没有加密前缀，直接返回（兼容旧数据）
    if not ciphertext.startswith("enc:"):
        return ciphertext

    try:
        f = _get_fernet()
        encrypted = ciphertext[4:].encode("utf-8")  # 移除 'enc:' 前缀
        decrypted = f.decrypt(encrypted)
        return decrypted.decode("utf-8")
    except Exception as e:
        # 解密失败，返回原文（兼容旧数据）
        print(f"⚠️ 解密失败: {e}")
        return ciphertext


def is_encrypted(value: str) -> bool:
    """检查值是否已加密"""
    return value.startswith("enc:") if value else False


def encrypt_api_key(api_key: str) -> str:
    """加密 API Key 的便捷方法"""
    return encrypt_value(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API Key 的便捷方法"""
    return decrypt_value(encrypted_key)


# ==================== 初始化检查 ====================


def ensure_encryption_key():
    """确保加密密钥存在（启动时调用）"""
    try:
        _get_or_create_key()
        return True
    except Exception as e:
        print(f"⚠️ 无法创建加密密钥: {e}")
        return False
