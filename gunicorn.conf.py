import multiprocessing
import os

# Gunicorn 配置文件

port = os.environ.get('PORT', os.environ.get('FLASK_PORT', '5000'))
bind = f"{os.environ.get('FLASK_HOST', '0.0.0.0')}:{port}"
# 限制 worker 数量以防低配容器 OOM，默认使用 2 个 workers
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
worker_class = "gthread"
threads = 4
timeout = 120

# 日志配置
accesslog = "-"
errorlog = "-"
loglevel = "info"
