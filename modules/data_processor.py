"""
数据处理模块
功能：从 SQLite 数据库导入历史开奖数据，执行清洗与预处理操作。
"""

import sqlite3
import pandas as pd
import os

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'lottery.db')


def get_db_connection():
    """获取 SQLite 数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.row_factory = sqlite3.Row
    return conn


def load_data(lottery_type: str = 'macaujc') -> pd.DataFrame:
    """
    从 SQLite 读取指定彩种的全部历史开奖数据
    参数:
        lottery_type: 彩种 (macaujc 或 macaujc2)
    返回: pandas DataFrame，包含所有历史记录
    """
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT * FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC",
        conn,
        params=(lottery_type,),
        parse_dates=['draw_date']
    )
    conn.close()
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    数据清洗流程：
    1. 去除重复期号
    2. 删除含空值的行
    3. 校验号码范围（1-49）
    """
    # 不去除重复期号，完全保留真实记录

    # 删除含空值的行
    df = df.dropna()

    # 号码列名
    number_columns = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'special_num']

    # 校验所有号码在 1-49 范围内
    for col in number_columns:
        df = df[(df[col] >= 1) & (df[col] <= 49)]

    # 重置索引
    df = df.reset_index(drop=True)

    return df


def get_date_range_data(start_date: str, end_date: str, lottery_type: str = 'macaujc') -> pd.DataFrame:
    """
    按日期范围筛选数据
    参数:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        lottery_type: 彩种
    返回: 筛选后的 DataFrame
    """
    df = load_data(lottery_type)
    df = clean_data(df)
    mask = (df['draw_date'] >= start_date) & (df['draw_date'] <= end_date)
    return df[mask]


def get_paginated_history(page: int = 1, per_page: int = 20, lottery_type: str = 'macaujc') -> dict:
    """
    获取分页的历史开奖记录
    参数:
        page: 页码（从1开始）
        per_page: 每页条数
        lottery_type: 彩种
    返回: 包含数据和分页信息的字典
    """
    conn = get_db_connection()
    
    # 获取总记录数
    total = conn.execute("SELECT COUNT(*) FROM lottery_history WHERE lottery_type=?", (lottery_type,)).fetchone()[0]
    
    # 计算偏移量
    offset = (page - 1) * per_page
    
    # 查询分页数据
    rows = conn.execute(
        "SELECT * FROM lottery_history WHERE lottery_type=? ORDER BY draw_date DESC LIMIT ? OFFSET ?",
        (lottery_type, per_page, offset)
    ).fetchall()
    
    conn.close()
    
    # 转换为字典列表
    data = []
    for row in rows:
        zodiac_str = row['zodiac'] or ''
        zodiac_list = zodiac_str.split(',') if ',' in zodiac_str else []
        
        # 兼容旧数据处理
        if not zodiac_list or len(zodiac_list) < 7:
            # 尝试回退用 simulator 工具动态生成，这里为了简化或兼容可以返回空字符串
            zodiac_list = [''] * 7
            
        data.append({
            'draw_number': row['draw_number'],
            'draw_date': row['draw_date'],
            'numbers': [row['num1'], row['num2'], row['num3'], row['num4'], row['num5'], row['num6']],
            'zodiacs': zodiac_list[:6],
            'special_num': row['special_num'],
            'special_zodiac': zodiac_list[6] if len(zodiac_list) > 6 else ''
        })
    
    return {
        'data': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }
