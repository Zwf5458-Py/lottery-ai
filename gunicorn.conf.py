import multiprocessing
import os

# Gunicorn 配置文件

port = os.environ.get('PORT', os.environ.get('FLASK_PORT', '5000'))
bind = f"{os.environ.get('FLASK_HOST', '0.0.0.0')}:{port}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
timeout = 120

# 日志配置
accesslog = "-"
errorlog = "-"
loglevel = "info"
