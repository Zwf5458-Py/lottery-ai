"""
本地测试数据生成器
功能：当远程数据源不可用时，创建本地测试数据
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta
import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.constants import get_zodiac_mapping


def generate_test_data(lottery_type="macaujc2", start_date="2026-01-01", num_days=30):
    """生成测试数据"""
    print(f"🎲 生成 {lottery_type} 测试数据 ({num_days} 天)")

    # 数据库路径
    db_path = os.path.join(os.path.dirname(__file__), "lottery.db")

    # 创建数据库和表
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建表（如果没有）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lottery_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_type TEXT NOT NULL DEFAULT 'macaujc',
            draw_number TEXT NOT NULL,
            draw_date TEXT NOT NULL,
            num1 INTEGER NOT NULL,
            num2 INTEGER NOT NULL,
            num3 INTEGER NOT NULL,
            num4 INTEGER NOT NULL,
            num5 INTEGER NOT NULL,
            num6 INTEGER NOT NULL,
            special_num INTEGER NOT NULL,
            wave TEXT,
            zodiac TEXT
        )
    """)

    # 确保索引存在
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lottery_type ON lottery_history(lottery_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lottery_type_date ON lottery_history(lottery_type, draw_date DESC, draw_number DESC)"
        )
    except Exception:
        pass

    # 检查是否已经有测试数据
    cursor.execute(
        "SELECT COUNT(*) FROM lottery_history WHERE lottery_type = ?", (lottery_type,)
    )
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        print(f"  ✅ 已存在 {existing_count} 条 {lottery_type} 数据，跳过生成")
        conn.close()
        return

    # 生成测试数据
    zodiac_mapping = get_zodiac_mapping(lottery_type)

    start = datetime.strptime(start_date, "%Y-%m-%d")
    for i in range(num_days):
        current_date = start + timedelta(days=i)
        draw_date = current_date.strftime("%Y-%m-%d")
        draw_number = current_date.strftime("%Y%m%d")

        # 随机生成7个不重复的号码 (1-49)
        numbers = random.sample(range(1, 50), 7)
        num1, num2, num3, num4, num5, num6, special_num = numbers

        # 根据号码获取生肖
        zodiac_parts = []
        for num in numbers:
            zodiac = zodiac_mapping.get(num, "未知")
            zodiac_parts.append(zodiac)

        # 简单的波色分配
        wave_parts = []
        red_set = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
        blue_set = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
        green_set = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}

        for num in numbers:
            if num in red_set:
                wave_parts.append("red")
            elif num in blue_set:
                wave_parts.append("blue")
            elif num in green_set:
                wave_parts.append("green")
            else:
                wave_parts.append("unknown")

        # 插入数据
        cursor.execute(
            """
            INSERT INTO lottery_history 
            (lottery_type, draw_number, draw_date, num1, num2, num3, num4, num5, num6, special_num, wave, zodiac)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                lottery_type,
                draw_number,
                draw_date,
                num1,
                num2,
                num3,
                num4,
                num5,
                num6,
                special_num,
                ",".join(wave_parts),
                ",".join(zodiac_parts),
            ),
        )

    conn.commit()
    conn.close()

    print(f"  ✅ 成功生成 {num_days} 条测试数据")


def ensure_test_data_exists():
    """确保测试数据存在"""
    print("🔍 检查测试数据...")

    # 为两种彩票类型生成测试数据
    generate_test_data("macaujc", "2026-01-01", 30)
    generate_test_data("macaujc2", "2026-01-01", 30)

    print("✅ 测试数据已就绪")


if __name__ == "__main__":
    ensure_test_data_exists()
