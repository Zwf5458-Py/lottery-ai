import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

try:
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get('http://127.0.0.1:5000')

    time.sleep(3)

    logs = driver.get_log('browser')
    formatted = []
    for l in logs:
        if l['level'] != 'INFO':
            formatted.append(l)

    with open('browser_logs.json', 'w', encoding='utf-8') as f:
        json.dump(formatted, f, indent=4, ensure_ascii=False)

    w = driver.execute_script('return document.getElementById("chart-markov-radar").width')
    h = driver.execute_script('return document.getElementById("chart-markov-radar").height')
    cw = driver.execute_script('return document.getElementById("chart-markov-radar").parentElement.clientWidth')
    ch = driver.execute_script('return document.getElementById("chart-markov-radar").parentElement.clientHeight')
    print('CANVAS:', w, 'x', h)
    print('WRAPPER:', cw, 'x', ch)

finally:
    try:
        driver.quit()
    except:
        pass
