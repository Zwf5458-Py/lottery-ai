import urllib.request
import urllib.error
import ssl
import re
import sqlite3
import os
from datetime import datetime
from bs4 import BeautifulSoup

# Define database path relative to script location
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'lottery.db')
BASE_URL = "https://www.lotto-8.com/Taiwan/listlto.asp"

# Disable SSL verification for scraper
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_date_str(date_str):
    # Expected format: dd/mmyy(星期) e.g. 11/0626(四)
    # dd = 11, mm = 06, yy = 26
    match = re.match(r"(\d{2})/(\d{2})(\d{2})", date_str)
    if not match:
        return None
    dd, mm, yy = match.groups()
    year = 2000 + int(yy)
    return f"{year}-{mm}-{dd}"

def fetch_and_sync():
    raw_records = []
    # Scraping 55 pages to cover more than 10 years (55 * 23 = 1265 draws)
    # The lotto-8 page has ~23 rows per page
    max_pages = 55
    print(f"开始抓取台湾威力彩历史开奖数据，计划翻页 {max_pages} 页...")
    
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}?indexpage={page}"
        print(f"正在抓取第 {page}/{max_pages} 页...")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            tables = soup.find_all('table')
            if len(tables) < 2:
                print(f"  警告: 第 {page} 页没有找到数据表格。")
                continue
                
            table = tables[1]
            rows = table.find_all('tr')
            # Skip header row
            for row in rows[1:]:
                tds = row.find_all('td')
                if len(tds) < 3:
                    continue
                
                date_text = tds[0].text.strip()
                numbers_text = tds[1].text.strip()
                special_text = tds[2].text.strip()
                
                draw_date = parse_date_str(date_text)
                if not draw_date:
                    continue
                
                # Format: "07, 22, 23, 24, 26, 33"
                num_parts = [n.strip() for n in numbers_text.replace('\xa0', '').split(',') if n.strip()]
                if len(num_parts) != 6:
                    continue
                
                try:
                    nums = [int(n) for n in num_parts]
                    special_num = int(special_text)
                except ValueError:
                    continue
                
                raw_records.append({
                    'draw_date': draw_date,
                    'nums': nums,
                    'special_num': special_num
                })
        except Exception as e:
            print(f"  错误: 抓取第 {page} 页失败: {e}")
            
    print(f"抓取完成，共获取原始记录 {len(raw_records)} 条。")
    if not raw_records:
        print("未抓取到任何开奖记录，同步中止！")
        return
        
    # Sort chronologically (oldest to newest) to correctly assign sequence numbers
    raw_records.sort(key=lambda x: x['draw_date'])
    
    # Group by Gregorian year to calculate sequence numbers (seq) per year
    records_by_year = {}
    for record in raw_records:
        dt = datetime.strptime(record['draw_date'], "%Y-%m-%d")
        year = dt.year
        if year not in records_by_year:
            records_by_year[year] = []
        records_by_year[year].append(record)
        
    final_records = []
    for year in sorted(records_by_year.keys()):
        roc_year = year - 1911 # ROC calendar year
        for seq, record in enumerate(records_by_year[year], 1):
            draw_number = f"{roc_year}{seq:06d}"
            
            # Keep records from 2016-01-01 onwards (10 years)
            if record['draw_date'] >= '2016-01-01':
                final_records.append((
                    'weilitsai',
                    draw_number,
                    record['draw_date'],
                    record['nums'][0],
                    record['nums'][1],
                    record['nums'][2],
                    record['nums'][3],
                    record['nums'][4],
                    record['nums'][5],
                    record['special_num'],
                    '', # wave
                    ''  # zodiac
                ))
                
    print(f"过滤 2016-01-01 至今的威力彩历史记录共 {len(final_records)} 期。")
    
    # Write to database
    print(f"正在写入本地数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create table if not exists (just in case)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lottery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type TEXT NOT NULL,
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
        
        # Clear existing weilitsai records to prevent duplicates and ensure clean ordering
        cursor.execute("DELETE FROM lottery_history WHERE lottery_type='weilitsai'")
        deleted_count = cursor.rowcount
        print(f"已清除原有威力彩记录 {deleted_count} 条。")
        
        # Batch insert
        cursor.executemany("""
            INSERT INTO lottery_history
            (lottery_type, draw_number, draw_date, num1, num2, num3, num4, num5, num6, special_num, wave, zodiac)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, final_records)
        
        conn.commit()
        print(f"🎉 成功同步台湾威力彩历史记录 {len(final_records)} 条入库！")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 写入数据库失败: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    fetch_and_sync()
