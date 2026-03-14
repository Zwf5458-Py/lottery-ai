from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import os

# 配置文件系统缓存 (FileSystemCache) — 支持多 Worker 共享且重启后持久化
_cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
os.makedirs(_cache_dir, exist_ok=True)

cache = Cache(config={
    'CACHE_TYPE': 'FileSystemCache',
    'CACHE_DIR': _cache_dir,
    'CACHE_DEFAULT_TIMEOUT': 3600,
    'CACHE_THRESHOLD': 500  # 最多缓存 500 个键
})

# 配置请求限流器 (Limiter)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# 配置 CSRF 防护
csrf = CSRFProtect()
