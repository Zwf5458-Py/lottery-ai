"""
历史开奖数据生成脚本
功能：生成 15 年（约 5400 期）模拟历史开奖数据并写入 SQLite 数据库。

澳门六合彩规则：
- 每期从 1-49 中不重复抽取 6 个正码
- 从 1-49 中抽取 1 个特码（可与正码重复）
- 每日开奖一期
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

# 数据库文件路径
DB_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(DB_DIR, 'lottery.db')


def create_database():
    """创建数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lottery_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_number TEXT UNIQUE NOT NULL,    -- 期号，如 "2011001"
            draw_date TEXT NOT NULL,             -- 开奖日期 YYYY-MM-DD
            num1 INTEGER NOT NULL,               -- 正码1
            num2 INTEGER NOT NULL,               -- 正码2
            num3 INTEGER NOT NULL,               -- 正码3
            num4 INTEGER NOT NULL,               -- 正码4
            num5 INTEGER NOT NULL,               -- 正码5
            num6 INTEGER NOT NULL,               -- 正码6
            special_num INTEGER NOT NULL          -- 特码
        )
    ''')
    
    conn.commit()
    return conn


def generate_single_draw() -> tuple:
    """
    生成单期开奖数据
    返回: (正码1, 正码2, ..., 正码6, 特码) — 正码已排序
    """
    # 注意：此处使用普通 random 生成历史模拟数据
    # 实际模拟开奖模块使用 secrets 强随机数
    numbers = sorted(random.sample(range(1, 50), 6))
    special = random.randint(1, 49)
    return tuple(numbers) + (special,)


def generate_all_data():
    """
    生成 15 年的模拟历史开奖数据
    时间范围：2011-01-01 至 2025-12-31
    频率：每日一期
    """
    print("🎰 开始生成澳门六合彩模拟历史数据...")
    
    conn = create_database()
    cursor = conn.cursor()
    
    # 清空旧数据
    cursor.execute("DELETE FROM lottery_history")
    
    start_date = datetime(2011, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    current_date = start_date
    draw_count = 0
    batch_data = []
    
    while current_date <= end_date:
        # 期号格式：年份 + 3位序号
        year = current_date.year
        day_of_year = (current_date - datetime(year, 1, 1)).days + 1
        draw_number = f"{year}{day_of_year:03d}"
        
        # 生成开奖数据
        draw = generate_single_draw()
        
        batch_data.append((
            draw_number,
            current_date.strftime('%Y-%m-%d'),
            *draw
        ))
        
        draw_count += 1
        current_date += timedelta(days=1)
    
    # 批量插入
    cursor.executemany('''
        INSERT OR IGNORE INTO lottery_history 
        (draw_number, draw_date, num1, num2, num3, num4, num5, num6, special_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', batch_data)
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据生成完毕！共 {draw_count} 期")
    print(f"📁 数据库位置：{DB_PATH}")
    print(f"📅 时间范围：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")


if __name__ == '__main__':
    generate_all_data()
