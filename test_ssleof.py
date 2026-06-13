import requests
import time
import sys

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://macaujc.com/",
    "Origin": "https://macaujc.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

import urllib3
urllib3.disable_warnings()

url2 = "https://history.macaumarksix.com/history/macaujc2/y/2026"

print("Trying macaujc2 again...")
for i in range(5):
    try:
        r = requests.get(url2, headers=headers, verify=False, timeout=10)
        print(f"Attempt {i}: success", len(r.content))
    except Exception as e:
        print(f"Attempt {i}: failed:", e)
    time.sleep(1)
