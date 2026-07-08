#!/usr/bin/env python3
"""Full sync: fetch Feishu sheets via lark-cli and update data.json + index.html"""
import json, os, subprocess, sys, re
from datetime import datetime, timezone, timedelta

SPREADSHEET_TOKEN = 'PZJLw8SF5igYbEkAba6cq3CznMh'

# Sheet definitions: (sheet_id, name, range, header_names)
SHEETS = [
    ('u2L03W', '自评表', 'u2L03W!A1:U100',
     ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级']),
    ('2uluU2', '差距表', '2uluU2!A1:U100',
     ['序号','所属项目','提交人','名称','频率','所属系统','软件功能缺陷问题']),
    ('KU6RfN', '异常表', 'KU6RfN!A1:T200',
     ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间']),
    ('3964d0', '报表清单', '3964d0!A1:V200',
     ['所属园区','报告名称','频率','来源']),
    ('ot4rmu', '积分表', 'ot4rmu!A1:T142',
     ['所属园区','报告名称','频率','来源','操作手册','手册优化点']),
]

LARK_CLI = os.path.expanduser('~/.hermes/node/bin/lark-cli')

def fetch_sheet(sheet_id, range_str):
    """Fetch sheet data using lark-cli"""
    url = f'/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{range_str}?valueRenderOption=ToString'
    result = subprocess.run(
        [LARK_CLI, 'api', 'GET', url, '--as', 'user'],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"  lark-cli error: {result.stderr}")
        return {'code': -1, 'msg': result.stderr}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        print(f"  stdout: {result.stdout[:500]}")
        return {'code': -1, 'msg': str(e)}

def process_sheet(data, name, headers, data_start_row=2):
    """Process raw sheet data into structured format"""
    if data.get('code') != 0:
        print(f"  ERROR: {data.get('msg', 'unknown')}")
        return {'name': name, 'headers': headers, 'rows': []}
    
    values = data['data']['valueRange']['values']
    data_rows = values[data_start_row:] if len(values) > data_start_row else []
    
    processed = []
    for row in data_rows:
        padded = list(row) + [''] * (len(headers) - len(row))
        trimmed = padded[:len(headers)]
        has_content = any(cell is not None and str(cell).strip() for cell in trimmed)
        if has_content:
            processed.append([str(cell) if cell is not None else '' for cell in trimmed])
    
    return {'name': name, 'headers': headers, 'rows': processed}

# Build result
tz_shanghai = timezone(timedelta(hours=8))
now = datetime.now(tz_shanghai)
result = {
    'timestamp': now.isoformat(),
    'sync_time': now.strftime('%Y-%m-%d %H:%M:%S'),
    'sheets': {}
}

print("=== Fetching Feishu spreadsheet data ===")
print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print()

for sheet_id, name, range_str, headers in SHEETS:
    print(f"  Sheet: {name} ({sheet_id})...")
    raw = fetch_sheet(sheet_id, range_str)
    processed = process_sheet(raw, name, headers, data_start_row=2)
    result['sheets'][name] = processed
    print(f"    Rows: {len(processed['rows'])}")

# For s4 (积分表), extract personnel from first column bottom rows
if '积分表' in result['sheets']:
    rows = result['sheets']['积分表']['rows']
    personnel = []
    for row in rows:
        first_cell = row[0].strip() if row else ''
        # Personnel names appear at the bottom
        if first_cell and first_cell not in ['所属园区', '']:
            # Check if it looks like a person name (not a data row)
            pass
    result['sheets']['积分表']['personnel'] = []

# Write data.json
data_path = os.path.expanduser('~/.hermes/projects/yixintongying/data.json')
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nWritten data.json: {data_path}")

# Update index.html
html_path = os.path.expanduser('~/.hermes/projects/yixintongying/index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(result, ensure_ascii=False)
html = re.sub(r'var DATA = \{.*?\};', 'var DATA = ' + data_json + ';', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Updated index.html: {html_path}")

# Summary
print("\n=== Sync Summary ===")
for name, sheet in result['sheets'].items():
    print(f"  {name}: {len(sheet['rows'])} rows")
print(f"\nDone! Timestamp: {result['sync_time']}")
