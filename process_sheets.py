#!/usr/bin/env python3
"""Process saved Feishu sheet data and update data.json + index.html"""
import json, os, re
from datetime import datetime, timezone, timedelta

DATA_DIR = '/tmp/feishu_sheets'
PROJECT_DIR = os.path.expanduser('~/.hermes/projects/yixintongying')

SHEET_CONFIG = [
    ('s0.json', '自评表', ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级']),
    ('s1.json', '差距表', ['序号','所属项目','提交人','名称','频率','所属系统','软件功能缺陷问题']),
    ('s2.json', '异常表', ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间']),
    ('s3.json', '报表清单', ['所属园区','报告名称','频率','来源']),
    ('s4.json', '积分表', ['姓名','差距表数','异常表数','自评表数','总分','备注']),
]

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

def process_sheet(filepath, name, headers):
    with open(filepath) as f:
        data = json.load(f)
    
    if data.get('code') != 0:
        print(f"  ERROR: {data.get('msg', 'unknown')}")
        return {'name': name, 'headers': headers, 'rows': []}
    
    values = data['data']['valueRange']['values']
    # Skip first 3 rows (title, subheader, actual header row)
    data_rows = values[3:] if len(values) > 3 else values
    
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

print("Processing sheets...")
for filename, name, headers in SHEET_CONFIG:
    filepath = os.path.join(DATA_DIR, filename)
    print(f"  {name}...", end=' ', flush=True)
    result['sheets'][name] = process_sheet(filepath, name, headers)
    print(f"{len(result['sheets'][name]['rows'])} rows")

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
data_path = os.path.join(PROJECT_DIR, 'data.json')
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nWritten: {data_path}")

# Update index.html
html_path = os.path.join(PROJECT_DIR, 'index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(result, ensure_ascii=False)
html = re.sub(r'var DATA = \{.*?\};', 'var DATA = ' + data_json + ';', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Updated: {html_path}")

# Summary
print("\n=== Sync Summary ===")
print(f"  Time: {result['sync_time']}")
for name, sheet in result['sheets'].items():
    print(f"  {name}: {len(sheet['rows'])} rows")
print(f"  Personnel: {len(personnel)} people")
