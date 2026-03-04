import logging
import os
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 配置全局 Logger
logger = logging.getLogger('lottery_app')
logger.setLevel(logging.INFO)

# 如果还没有处理器，则添加（防止多次导入导致重复日志）
if not logger.handlers:
    # 文件处理器 (按大小轮转，最大 10MB，保留 5 个备份)
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'app.log'), 
        maxBytes=10*1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def get_logger():
    return logger
