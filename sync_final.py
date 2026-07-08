#!/usr/bin/env python3
"""Full sync: fetch Feishu sheets data and update data.json + index.html"""
import json, os, subprocess, sys, re
from datetime import datetime, timezone, timedelta

# Build token from parts to avoid truncation
TOKEN_P1 = 'VNa'
TOKEN_P2 = 'gwe'
TOKEN_P3 = 'uz3'
TOKEN_P4 = 'iTC'
TOKEN_P5 = 'WFk'
TOKEN_P6 = '0Y3'
TOKEN_P7 = 'wc1'
TOKEN_P8 = 'UL3'
TOKEN_P9 = 'nBf'
TOKEN = TOKEN_P1 + TOKEN_P2 + TOKEN_P3 + TOKEN_P4 + TOKEN_P5 + TOKEN_P6 + TOKEN_P7 + TOKEN_P8 + TOKEN_P9

SHEETS = [
    ('u2L03W', '自评表', 'u2L03W!A1:J100',
     ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级']),
    ('2uluU2', '差距表', '2uluU2!A1:G100',
     ['序号','所属项目','提交人','名称','频率','所属系统','软件功能缺陷问题']),
    ('KU6RfN', '异常表', 'KU6RfN!A1:H200',
     ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间']),
    ('3964d0', '报表清单', '3964d0!A1:D200',
     ['所属园区','报告名称','频率','来源']),
    ('ot4rmu', '积分表', 'ot4rmu!A1:A50',
     ['姓名','差距表数','异常表数','自评表数','总分','备注']),
]

def fetch_sheet(sheet_id, range_str):
    url = f'/open-apis/sheets/v2/spreadsheets/{TOKEN}/values/{range_str}?valueRenderOption=FormattedValue'
    result = subprocess.run(
        ['lark-cli', 'api', 'GET', url, '--as', 'user'],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)

def extract_plain_text(cell_value):
    if cell_value is None:
        return ''
    if isinstance(cell_value, str):
        if cell_value.startswith('[{') and 'segmentStyle' in cell_value:
            try:
                segments = json.loads(cell_value)
                return ''.join(seg.get('text', '') for seg in segments if isinstance(seg, dict)).strip()
            except (json.JSONDecodeError, TypeError):
                return cell_value
        return cell_value
    if isinstance(cell_value, list):
        return ''.join(seg.get('text', '') for seg in cell_value if isinstance(seg, dict)).strip()
    return str(cell_value)

def process_sheet(data, name, headers, data_start_row=3):
    if data.get('code') != 0:
        print(f"  ERROR: {data.get('msg', 'unknown')}")
        return {'name': name, 'headers': headers, 'rows': []}
    
    values = data['data']['valueRange']['values']
    data_rows = values[data_start_row:] if len(values) > data_start_row else values
    
    processed = []
    for row in data_rows:
        padded = list(row) + [''] * (len(headers) - len(row))
        trimmed = padded[:len(headers)]
        cleaned = [extract_plain_text(cell) for cell in trimmed]
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

# Compute scores
print("\nComputing scores...")
score_sheet = result['sheets']['积分表']
gap_sheet = result['sheets']['差距表']
anomaly_sheet = result['sheets']['异常表']
self_sheet = result['sheets']['自评表']

personnel = []
for row in score_sheet['rows']:
    name = row[0].strip()
    if name and name != '姓名':
        personnel.append(name)

for i, row in enumerate(score_sheet['rows']):
    name = row[0].strip()
    if name and name != '姓名':
        gap_count = sum(1 for r in gap_sheet['rows'] if len(r) > 2 and r[2].strip() == name)
        anomaly_count = sum(1 for r in anomaly_sheet['rows'] if len(r) > 2 and r[2].strip() == name)
        self_count = sum(1 for r in self_sheet['rows'] if len(r) > 2 and r[2].strip() == name)
        total = gap_count + anomaly_count + self_count
        score_sheet['rows'][i] = [name, str(gap_count), str(anomaly_count), str(self_count), str(total), '']
        print(f"  {name}: 差距={gap_count}, 异常={anomaly_count}, 自评={self_count}, 总分={total}")

score_sheet['personnel'] = personnel

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
# Use str.replace to avoid re.sub interpreting backslash escapes in data_json
old_block_start = html.find('var DATA = {')
old_block_end = html.find('};', old_block_start) + 2
if old_block_start >= 0 and old_block_end > old_block_start:
    html = html[:old_block_start] + 'var DATA = ' + data_json + ';' + html[old_block_end:]
else:
    html = re.sub(r'var DATA = \{.*?\};', 'var DATA = ' + data_json + ';', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Updated: {html_path}")

# Summary
print("\n=== Sync Summary ===")
for name, sheet in result['sheets'].items():
    print(f"  {name}: {len(sheet['rows'])} rows")
print(f"  Personnel: {len(personnel)} people")
