#!/usr/bin/env python3
"""Full sync: fetch Feishu sheets data and update data.json + index.html"""
import json, os, subprocess, sys, re
from datetime import datetime, timezone, timedelta

SPREADSHEET_TOKEN = 'PZJLw8SF5igYbEkAba6cq3CznMh'

# Sheet definitions
# For sheets with formulas, use FormattedValue; for headers use ToString
SHEETS = [
    ('u2L03W', '自评表', 'u2L03W!A1:J100',
     ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级']),
    ('2uluU2', '差距表', '2uluU2!A1:G100',
     ['序号','所属项目','提交人','名称','频率','所属系统','软件功能缺陷问题']),
    ('KU6RfN', '异常表', 'KU6RfN!A1:H200',
     ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间']),
    ('3964d0', '报表清单', '3964d0!A1:D200',
     ['所属园区','报告名称','频率','来源']),
    ('ot4rmu', '积分表', 'ot4rmu!A1:F50',
     ['姓名','差距表数','异常表数','自评表数','总分','备注']),
]

def fetch_sheet(sheet_id, range_str, value_option='FormattedValue'):
    """Fetch sheet data using lark-cli"""
    url = f'/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{range_str}?valueRenderOption={value_option}'
    result = subprocess.run(
        ['lark-cli', 'api', 'GET', url, '--as', 'user'],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)

def extract_plain_text(cell_value):
    """Extract plain text from rich text formatted cells"""
    if cell_value is None:
        return ''
    if isinstance(cell_value, str):
        # Check if it's JSON array of rich text segments
        if cell_value.startswith('[{') and 'segmentStyle' in cell_value:
            try:
                segments = json.loads(cell_value)
                texts = []
                for seg in segments:
                    if isinstance(seg, dict) and 'text' in seg:
                        texts.append(seg['text'])
                return ''.join(texts).strip()
            except (json.JSONDecodeError, TypeError):
                return cell_value
        return cell_value
    if isinstance(cell_value, list):
        texts = []
        for seg in cell_value:
            if isinstance(seg, dict) and 'text' in seg:
                texts.append(seg['text'])
        return ''.join(texts).strip()
    return str(cell_value)

def process_sheet(data, name, headers, data_start_row=3):
    """Process raw sheet data into structured format"""
    if data.get('code') != 0:
        print(f"  ERROR: {data.get('msg', 'unknown')}")
        return {'name': name, 'headers': headers, 'rows': []}
    
    values = data['data']['valueRange']['values']
    
    # Determine where data starts
    # Row 0: title, Row 1: sub-header, Row 2: actual headers, Row 3+: data
    # But some sheets may vary - let's find the data
    if len(values) <= data_start_row:
        data_rows = values
    else:
        data_rows = values[data_start_row:]
    
    # Filter and process
    processed = []
    for row in data_rows:
        # Pad row to header length
        padded = list(row) + [''] * (len(headers) - len(row))
        trimmed = padded[:len(headers)]
        
        # Extract plain text from rich text cells
        cleaned = [extract_plain_text(cell) for cell in trimmed]
        
        # Check if row has content
        has_content = any(c and str(c).strip() for c in cleaned)
        if has_content:
            processed.append([str(c) for c in cleaned])
    
    return {'name': name, 'headers': headers, 'rows': processed}

# Build result
tz_shanghai = timezone(timedelta(hours=8))
now = datetime.now(tz_shanghai)
result = {
    'timestamp': now.isoformat(),
    'sync_time': now.strftime('%Y-%m-%d %H:%M:%S'),
    'sheets': {}
}

print("Fetching Feishu spreadsheet data...")
for sheet_id, name, range_str, headers in SHEETS:
    print(f"  Sheet: {name} ({sheet_id})...", end=' ', flush=True)
    raw = fetch_sheet(sheet_id, range_str)
    processed = process_sheet(raw, name, headers)
    result['sheets'][name] = processed
    print(f"{len(processed['rows'])} rows")

# Write data.json
data_path = os.path.expanduser('~/.hermes/projects/yixintongying/data.json')
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nWritten: {data_path}")

# Update index.html
html_path = os.path.expanduser('~/.hermes/projects/yixintongying/index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(result, ensure_ascii=False)
html = re.sub(r'var DATA = \{.*?\};', 'var DATA = ' + data_json + ';', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Updated: {html_path}")

# Summary
print("\n=== Sync Summary ===")
for name, sheet in result['sheets'].items():
    print(f"  {name}: {len(sheet['rows'])} rows")
