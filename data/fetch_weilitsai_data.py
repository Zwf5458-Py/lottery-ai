from bs4 import BeautifulSoup

def parse_html_to_records(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []
    # Simplified parsing logic for the test
    tables = soup.find_all('table')
    if not tables: return []
    for tr in tables[0].find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 9:
            record = {
                'lottery_type': 'weilitsai',
                'draw_issue': tds[0].text.strip(),
                'draw_date': tds[1].text.strip(), # Needs real conversion in actual impl
                'n1': int(tds[2].text.strip()),
                'n2': int(tds[3].text.strip()),
                'n3': int(tds[4].text.strip()),
                'n4': int(tds[5].text.strip()),
                'n5': int(tds[6].text.strip()),
                'n6': int(tds[7].text.strip()),
                'special': int(tds[8].text.strip())
            }
            records.append(record)
    return records
