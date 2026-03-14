import logging
import os
import json
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 配置全局 Logger
logger = logging.getLogger('lottery_app')
logger.setLevel(logging.INFO)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "file": record.filename,
            "lineno": record.lineno
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)

# 如果还没有处理器，则添加（防止多次导入导致重复日志）
if not logger.handlers:
    # 文件处理器 (按大小轮转，最大 10MB，保留 5 个备份)
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'app.log'), 
        maxBytes=10*1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(JsonFormatter())
    
    # 控制台处理器 (控制台仍然保持易读文本格式)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


ai_error_logger = logging.getLogger('lottery_ai_errors')
ai_error_logger.setLevel(logging.INFO)

if not ai_error_logger.handlers:
    ai_error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'ai_errors.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    ai_error_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    ai_error_logger.addHandler(ai_error_handler)


def log_ai_failure(payload: dict):
    try:
        ai_error_logger.error(json.dumps(payload, ensure_ascii=False))
    except Exception:
        ai_error_logger.error(str(payload))

def get_logger():
    return logger
