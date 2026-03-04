"""
真实历史数据抓取脚本
功能：从 macaujc.com 官网 API 抓取澳门六合彩真实历史开奖数据。
数据源：https://history.macaumarksix.com/history/macaujc/y/{year}
"""

import sqlite3
import json
import time
import sys
import os
import ssl
import urllib.request
import urllib.error

# 确保能导入上一级目录的 modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.logger import get_logger

logger = get_logger()

# 创建不验证证书的 SSL 上下文（解决部分环境 SSL 握手失败问题）
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 数据库路径
DB_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(DB_DIR, 'lottery.db')

# API 基础 URL
API_BASE = "https://history.macaumarksix.com/history/macaujc/y/{year}"

# 抓取年份范围（2011-2026）
START_YEAR = 2011
END_YEAR = 2026

# 彩种配置
LOTTERY_TYPES = {
    'macaujc': '澳门六合彩',
    'macaujc2': '新澳门六合彩'
}


def create_database():
    """创建/重置数据库表结构 (增量增加 lottery_type)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 如果表不存在则创建
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lottery_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_type TEXT NOT NULL DEFAULT 'macaujc', -- 彩种
            draw_number TEXT NOT NULL,           -- 期号 (可能重复)
            draw_date TEXT NOT NULL,             -- 开奖日期 YYYY-MM-DD
            num1 INTEGER NOT NULL,               -- 正码1
            num2 INTEGER NOT NULL,               -- 正码2
            num3 INTEGER NOT NULL,               -- 正码3
            num4 INTEGER NOT NULL,               -- 正码4
            num5 INTEGER NOT NULL,               -- 正码5
            num6 INTEGER NOT NULL,               -- 正码6
            special_num INTEGER NOT NULL,         -- 特码
            wave TEXT,                            -- 波色
            zodiac TEXT                           -- 生肖
        )
    ''')
    
    # 建立一个单独用于记录 AI 模拟分析结果的表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_type TEXT NOT NULL,          -- 针对哪个彩种
            model_name TEXT NOT NULL,            -- 例如 gemini-2.5-pro
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 生成时间
            dimensions TEXT NOT NULL,            -- 参考的维度 JSON
            result_json TEXT NOT NULL            -- 完整结果包含号码、分析文本等 JSON
        )
    ''')
    
    # 尝试创建索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lottery_type ON lottery_history(lottery_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lottery_type_date ON lottery_history(lottery_type, draw_date DESC, draw_number DESC)")
    except Exception:
        pass

    conn.commit()
    return conn


def fetch_year_data(year: int, lottery_type: str = 'macaujc', max_retries: int = 3) -> list:
    """
    从 API 获取指定年份的全部开奖数据（带重试机制）
    参数:
        year: 年份 (如 2024)
        lottery_type: 彩种 (macaujc 或 macaujc2)
        max_retries: 最大重试次数
    返回: 开奖记录列表
    """
    url = API_BASE.replace('macaujc', lottery_type).format(year=year)

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://macaujc.com/',
                    'Origin': 'https://macaujc.com'
                }
            )
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data.get('result') and data.get('data'):
                return data['data']
            else:
                logger.warning(f"  ⚠️  {year} 年数据为空或请求失败")
                return []

        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.info(f"  ⏳ 重试 ({attempt+1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                logger.error(f"  ❌ {year} 年请求失败 ({max_retries}次重试后): {e}")
                return []
        except json.JSONDecodeError:
            logger.error(f"  ❌ {year} 年数据解析失败")
            return []


def parse_record(record: dict) -> tuple:
    """
    解析单条开奖记录
    API 返回格式:
        openCode: "05,15,42,34,18,11,10" (前6个为正码，第7个为特码)
        openTime: "2026-02-25 22:32:32"
        expect: "2026056"
        wave: "green,blue,blue,red,red,green,blue"
        zodiac: "虎,龍,牛,雞,牛,猴,雞"
    """
    try:
        draw_number = record['expect']
        open_time = record['openTime']
        draw_date = open_time.split(' ')[0]  # 只取日期部分

        # 解析号码
        codes = record['openCode'].split(',')
        numbers = [int(c) for c in codes]

        if len(numbers) != 7:
            return None

        # 前6个为正码，第7个为特码
        num1, num2, num3, num4, num5, num6 = numbers[:6]
        special_num = numbers[6]

        # 波色和生肖
        wave = record.get('wave', '')
        zodiac = record.get('zodiac', '')

        return (draw_number, draw_date, num1, num2, num3, num4, num5, num6,
                special_num, wave, zodiac)

    except (KeyError, ValueError, IndexError) as e:
        return None


def fetch_all_data():
    """抓取所有年份的多类历史数据并写入数据库"""
    logger.info("🎰 开始从 macaujc.com 抓取真实历史开奖数据...")
    logger.info(f"📅 年份范围: {START_YEAR} - {END_YEAR}")
    logger.info(f"🏷️ 抓取类型: {', '.join(LOTTERY_TYPES.values())}")

    conn = create_database()
    cursor = conn.cursor()

    for lottery_type, type_name in LOTTERY_TYPES.items():
        total_count = 0
        failed_years = []
        
        logger.info(f"[{type_name} ({lottery_type})]")
        
        for year in range(START_YEAR, END_YEAR + 1):
            logger.info(f"📥 正在抓取 {year} 年数据...")

            records = fetch_year_data(year, lottery_type)

            if not records:
                failed_years.append(year)
                logger.warning("跳过")
                continue

            year_count = 0
            for record in records:
                parsed = parse_record(record)
                if parsed:
                    # 检查是否已存在 (避免重复运行脚本导致加倍，但不按 draw_number 单独去重)
                    exists = cursor.execute(
                        "SELECT 1 FROM lottery_history WHERE lottery_type=? AND draw_number=?", 
                        (lottery_type, parsed[0])
                    ).fetchone()
                    
                    if not exists:
                        cursor.execute('''
                            INSERT INTO lottery_history
                            (lottery_type, draw_number, draw_date, num1, num2, num3, num4, num5, num6,
                             special_num, wave, zodiac)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (lottery_type,) + parsed)
                        year_count += 1

            conn.commit()
            total_count += year_count
            logger.info(f"✅ {year_count} 期 (新增)")

            # 请求间隔，避免过快
            time.sleep(0.5)

        logger.info(f"📊 {type_name} 总导入新增期数: {total_count}")
        if failed_years:
            logger.warning(f"⚠️  {type_name} 无数据年份: {failed_years}")

    conn.close()

    logger.info("="*50)
    logger.info("✅ 所有数据抓取及同步完毕！")
    logger.info(f"📁 数据库位置: {DB_PATH}")
    logger.info("="*50)


def check_data_freshness(lottery_type: str = 'macaujc2') -> dict:
    """
    检查本地数据库中指定彩种的最新数据日期，与当前日期对比。
    返回: {'is_fresh': bool, 'latest_date': str, 'latest_draw': str, 'days_behind': int}
    """
    from datetime import datetime, timedelta
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    row = cursor.execute(
        "SELECT draw_date, draw_number FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC, draw_number DESC LIMIT 1",
        (lottery_type,)
    ).fetchone()
    conn.close()
    
    if not row:
        return {'is_fresh': False, 'latest_date': '无数据', 'latest_draw': '无', 'days_behind': 999}
    
    latest_date_str = row[0]
    latest_draw = row[1]
    
    try:
        latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # 若最新数据日期是昨天或今天，视为已同步
        days_behind = (today - latest_date).days
        is_fresh = days_behind <= 1
    except:
        days_behind = 999
        is_fresh = False
    
    return {
        'is_fresh': is_fresh,
        'latest_date': latest_date_str,
        'latest_draw': latest_draw,
        'days_behind': days_behind
    }


def sync_latest(lottery_type: str = 'macaujc2') -> dict:
    """
    增量同步指定彩种的最新数据（只抓取当年）
    返回: {'success': bool, 'new_count': int, 'message': str}
    """
    from datetime import datetime
    
    year = datetime.now().year
    logger.info(f"🔄 增量同步 {lottery_type} {year}年最新数据...")
    
    conn = create_database()
    cursor = conn.cursor()
    
    records = fetch_year_data(year, lottery_type)
    if not records:
        conn.close()
        return {'success': False, 'new_count': 0, 'message': f'{year}年暂无新数据'}
    
    new_count = 0
    for record in records:
        parsed = parse_record(record)
        if parsed:
            exists = cursor.execute(
                "SELECT 1 FROM lottery_history WHERE lottery_type=? AND draw_number=?",
                (lottery_type, parsed[0])
            ).fetchone()
            if not exists:
                cursor.execute('''
                    INSERT INTO lottery_history
                    (lottery_type, draw_number, draw_date, num1, num2, num3, num4, num5, num6,
                     special_num, wave, zodiac)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (lottery_type,) + parsed)
                new_count += 1
    
    conn.commit()
    conn.close()
    
    msg = f'同步完成！新增 {new_count} 期数据' if new_count > 0 else '数据已是最新，无需同步'
    logger.info(f"✅ {msg}")
    return {'success': True, 'new_count': new_count, 'message': msg}


if __name__ == '__main__':
    fetch_all_data()
