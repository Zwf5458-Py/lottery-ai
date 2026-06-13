import pytest
from data.fetch_weilitsai_data import parse_html_to_records

def test_parse_html_to_records():
    # Mock HTML structure mimicking Taiwan Lottery
    html = '''
    <table>
        <tr>
            <td>113000001</td>
            <td>113/01/01</td>
            <td>01</td><td>02</td><td>03</td><td>04</td><td>05</td><td>06</td>
            <td>07</td>
        </tr>
    </table>
    '''
    records = parse_html_to_records(html)
    assert len(records) == 1
    assert records[0]['draw_issue'] == '113000001'
    assert records[0]['n1'] == 1
    assert records[0]['special'] == 7
