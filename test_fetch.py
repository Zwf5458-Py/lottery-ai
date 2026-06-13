import urllib.request
import ssl
import json
import requests

url = "https://history.macaumarksix.com/history/macaujc2/y/2026"
headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://macaujc.com/",
    "Origin": "https://macaujc.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

print("Testing urllib with CERT_NONE...")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as res:
        print("urllib success!", len(res.read()))
except Exception as e:
    print("urllib failed:", e)

print("\nTesting requests with verify=False...")
try:
    r = requests.get(url, headers=headers, verify=False, timeout=10)
    print("requests success!", len(r.content))
except Exception as e:
    print("requests failed:", e)
