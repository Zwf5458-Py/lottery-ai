import multiprocessing
import os

# Gunicorn 配置文件

bind = f"{os.environ.get('FLASK_HOST', '0.0.0.0')}:{os.environ.get('FLASK_PORT', '5000')}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
timeout = 120

# 日志配置
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
