#!/usr/bin/env python3
"""Sync Feishu sheets data to data.json and update index.html"""
import json, os, subprocess, re
from datetime import datetime, timezone, timedelta

SPREADSHEET_TOKEN = 'PZJLw8SF5igYbEkAba6cq3CznMh'

# Sheet definitions: (sheet_id, name, range, header_names, data_start_row)
SHEETS = [
    ('u2L03W', '自评表', 'u2L03W!A1:J100',
     ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级'],
     2),
    ('2uluU2', '差距表', '2uluU2!A1:G100',
     ['序号','所属项目','提交人','所属场景','名称','频率','所属系统'],
     2),
    ('KU6RfN', '异常表', 'KU6RfN!A1:H200',
     ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间'],
     2),
    ('3964d0', '报表清单', '3964d0!A1:D200',
     ['所属园区','报告名称','频率','来源'],
     1),
    ('ot4rmu', '积分表', 'ot4rmu!A1:F50',
     ['姓名','差距表数','异常表数','自评表数','总分','备注'],
     1),
]

def fetch_sheet(sheet_id, range_str):
    url = f'/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{range_str}?valueRenderOption=ToString'
    result = subprocess.run(
        ['lark-cli', 'api', 'GET', url, '--as', 'user'],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)

def extract_plain_text(cell_value):
    """Extract plain text from rich text cell values"""
    if cell_value is None:
        return ''
    if isinstance(cell_value, str):
        # Check if it's a JSON rich text representation
        if cell_value.startswith('[{"') and '"segmentStyle"' in cell_value:
            try:
                segments = json.loads(cell_value)
                return ''.join(seg.get('text', '') for seg in segments if isinstance(seg, dict)).strip()
            except (json.JSONDecodeError, TypeError):
                return cell_value
        return cell_value
    if isinstance(cell_value, list):
        return ''.join(seg.get('text', '') for seg in cell_value if isinstance(seg, dict)).strip()
    if isinstance(cell_value, (int, float)):
        return str(cell_value)
    return str(cell_value)

def process_sheet(data, name, headers, data_start_row=2):
    if data.get('code') != 0:
        print(f"  ERROR: {data.get('msg', 'unknown')}")
        return {'name': name, 'headers': headers, 'rows': []}
    
    values = data['data']['valueRange']['values']
    # Skip to data rows
    data_rows = values[data_start_row:] if len(values) > data_start_row else []
    
    processed = []
    for row in data_rows:
        # Pad and trim to header length
        padded = list(row) + [''] * (len(headers) - len(row))
        trimmed = padded[:len(headers)]
        cleaned = [extract_plain_text(cell) for cell in trimmed]
        # Check if row has any content
        has_content = any(c and str(c).strip() for c in cleaned)
        if has_content:
            processed.append([str(c) for c in cleaned])
    
    return {'name': name, 'headers': headers, 'rows': processed}

# Fetch all sheets
print("Fetching Feishu spreadsheet data...")
result_sheets = {}
for sheet_id, name, range_str, headers, start_row in SHEETS:
    print(f"  Sheet: {name} ({sheet_id})...", end=' ', flush=True)
    raw = fetch_sheet(sheet_id, range_str)
    processed = process_sheet(raw, name, headers, start_row)
    result_sheets[name] = processed
    print(f"{len(processed['rows'])} rows")

# Remap 差距表: drop column 3 (所属场景), add empty column "软件功能缺陷问题"
gap_sheet = result_sheets['差距表']
new_headers = ['序号','所属项目','提交人','名称','频率','所属系统','软件功能缺陷问题']
new_rows = []
for row in gap_sheet['rows']:
    # Original: 0=序号, 1=所属项目, 2=提交人, 3=所属场景, 4=名称, 5=频率, 6=所属系统
    # New: 0=序号, 1=所属项目, 2=提交人, 3=名称, 4=频率, 5=所属系统, 6=软件功能缺陷问题(empty)
    if len(row) >= 7:
        new_row = [row[0], row[1], row[2], row[4], row[5], row[6], '']
    elif len(row) >= 5:
        new_row = [row[0], row[1], row[2], row[4] if len(row) > 4 else '', row[5] if len(row) > 5 else '', row[6] if len(row) > 6 else '', '']
    else:
        new_row = list(row) + [''] * (7 - len(row))
    new_rows.append(new_row)
result_sheets['差距表'] = {'name': '差距表', 'headers': new_headers, 'rows': new_rows}

# Compute scores for 积分表
print("\nComputing scores...")
gap_rows = result_sheets['差距表']['rows']
anomaly_rows = result_sheets['异常表']['rows']
self_rows = result_sheets['自评表']['rows']
score_rows = result_sheets['积分表']['rows']

personnel = []
for row in score_rows:
    name = row[0].strip()
    if name and name != '姓名' and 'COUNTIF' not in name:
        personnel.append(name)

print(f"  Personnel: {personnel}")

new_score_rows = []
for name in personnel:
    gap_count = sum(1 for r in gap_rows if len(r) > 2 and r[2].strip() == name)
    anomaly_count = sum(1 for r in anomaly_rows if len(r) > 2 and r[2].strip() == name)
    self_count = sum(1 for r in self_rows if len(r) > 2 and r[2].strip() == name)
    total = gap_count + anomaly_count + self_count
    new_score_rows.append([name, str(gap_count), str(anomaly_count), str(self_count), str(total), ''])
    print(f"  {name}: 差距={gap_count}, 异常={anomaly_count}, 自评={self_count}, 总分={total}")

result_sheets['积分表'] = {
    'name': '积分表',
    'headers': ['姓名','差距表数','异常表数','自评表数','总分','备注'],
    'rows': new_score_rows,
    'personnel': personnel
}

# Build final result
tz_shanghai = timezone(timedelta(hours=8))
now = datetime.now(tz_shanghai)
result = {
    'timestamp': now.isoformat(),
    'sync_time': now.strftime('%Y-%m-%d %H:%M:%S'),
    'sheets': result_sheets
}

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
# Use string find to avoid regex issues with special chars in JSON
old_block_start = html.find('var DATA = {')
old_block_end = html.find('};', old_block_start) + 2 if old_block_start >= 0 else -1
if old_block_start >= 0 and old_block_end > old_block_start:
    html = html[:old_block_start] + 'var DATA = ' + data_json + ';' + html[old_block_end:]
else:
    html = re.sub(r'var DATA = \{.*?\};', 'var DATA = ' + data_json + ';', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Updated index.html: {html_path}")

# Summary
print("\n=== Sync Summary ===")
for name, sheet in result['sheets'].items():
    extra = ''
    if 'personnel' in sheet:
        extra = f", {len(sheet['personnel'])} people"
    print(f"  {name}: {len(sheet['rows'])} rows{extra}")
print(f"  Timestamp: {result['sync_time']}")
