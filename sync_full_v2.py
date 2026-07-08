#!/usr/bin/env python3
"""Fetch Feishu sheets via lark-cli, process, and write data.json + update index.html"""
import json, os, re, subprocess, sys
from datetime import datetime, timezone, timedelta

SPREADSHEET_TOKEN = 'PZJLw8SF5igYbEkAba6cq3CznMh'

SHEETS = [
    ('u2L03W', '自评表', 'u2L03W!A1:J100'),
    ('2uluU2', '差距表', '2uluU2!A1:G100'),
    ('KU6RfN', '异常表', 'KU6RfN!A1:H200'),
    ('3964d0', '报表清单', '3964d0!A1:D200'),
    ('ot4rmu', '积分表', 'ot4rmu!A1:F50'),
]

def fetch_sheet(sheet_id, range_str):
    url = f'/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{range_str}?valueRenderOption=FormattedValue'
    result = subprocess.run(
        ['lark-cli', 'api', 'GET', url, '--as', 'user'],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)

def extract_plain_text(cell):
    if cell is None:
        return ''
    if isinstance(cell, str):
        if cell.startswith('[{') and 'segmentStyle' in cell:
            try:
                segments = json.loads(cell)
                return ''.join(seg.get('text', '') for seg in segments if isinstance(seg, dict)).strip()
            except (json.JSONDecodeError, TypeError):
                return cell
        return cell
    if isinstance(cell, list):
        return ''.join(seg.get('text', '') for seg in cell if isinstance(seg, dict)).strip()
    if isinstance(cell, (int, float)):
        return str(cell)
    return str(cell)

def is_empty_row(row):
    return not any(cell is not None and str(cell).strip() != '' for cell in row)

def excel_serial_to_date(val):
    try:
        v = int(float(val))
        if 40000 < v < 60000:
            from datetime import datetime, timedelta
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=v)).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        pass
    return str(val)

print("Fetching Feishu sheets...")
raw_data = {}
for sheet_id, name, range_str in SHEETS:
    print(f"  {name} ({sheet_id})...", end=' ', flush=True)
    raw_data[name] = fetch_sheet(sheet_id, range_str)
    vals = raw_data[name]['data']['valueRange']['values']
    print(f"{len(vals)} rows raw")

# ── Process 自评表 (s0) ──
print("\nProcessing sheets...")
s0_vals = raw_data['自评表']['data']['valueRange']['values']
self_headers = ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级']
self_rows = []
for row in s0_vals[2:]:
    if is_empty_row(row):
        continue
    padded = list(row) + [''] * 10
    trimmed = padded[:10]
    cleaned = [extract_plain_text(c) for c in trimmed]
    if any(c.strip() for c in cleaned):
        self_rows.append(cleaned)

# ── Process 差距表 (s1) ──
s1_vals = raw_data['差距表']['data']['valueRange']['values']
# Actual: Row[0]=title, Row[1]=[序号,所属项目,提交人,所属场景,名称,频率,所属系统]
# Map: col 0→0(序号), 1→1(所属项目), 2→2(提交人), 4→3(名称), 5→4(频率), 6→5(所属系统), new→6(软件功能缺陷问题)
gap_headers = ['序号','所属项目','提交人','名称','频率','所属系统','软件功能缺陷问题']
col_map = [(0,0), (1,1), (2,2), (4,3), (5,4), (6,5)]
gap_rows = []
for row in s1_vals[2:]:
    if is_empty_row(row):
        continue
    cleaned = [''] * 7
    for src, dst in col_map:
        if src < len(row):
            cleaned[dst] = extract_plain_text(row[src])
    if cleaned[0] == 'ROW()-2':
        cleaned[0] = str(len(gap_rows) + 1)
    if any(c.strip() for c in cleaned):
        gap_rows.append(cleaned)

# ── Process 异常表 (s2) ──
s2_vals = raw_data['异常表']['data']['valueRange']['values']
anomaly_headers = ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间']
anomaly_rows = []
for row in s2_vals[2:]:
    if is_empty_row(row):
        continue
    padded = list(row) + [''] * 8
    trimmed = padded[:8]
    cleaned = [extract_plain_text(c) for c in trimmed]
    cleaned[6] = excel_serial_to_date(cleaned[6])
    cleaned[7] = excel_serial_to_date(cleaned[7])
    if any(c.strip() for c in cleaned):
        anomaly_rows.append(cleaned)

# ── Process 报表清单 (s3) ──
s3_vals = raw_data['报表清单']['data']['valueRange']['values']
reports_headers = ['所属园区','报告名称','频率','来源']
reports_rows = []
last_park = ''
for row in s3_vals[1:]:
    if is_empty_row(row):
        continue
    padded = list(row) + [''] * 4
    trimmed = padded[:4]
    cleaned = [extract_plain_text(c) for c in trimmed]
    if cleaned[0].strip():
        last_park = cleaned[0]
    else:
        cleaned[0] = last_park
    if any(c.strip() for c in cleaned):
        reports_rows.append(cleaned)

# ── Process 积分表 (s4) ──
s4_vals = raw_data['积分表']['data']['valueRange']['values']
score_headers = ['姓名','差距表数','异常表数','自评表数','总分','备注']
score_rows = []
personnel = []

for row in s4_vals[1:]:
    if is_empty_row(row):
        continue
    name_val = extract_plain_text(row[0])
    if not name_val or name_val == '姓名':
        continue
    personnel.append(name_val)
    gap_count = sum(1 for r in gap_rows if len(r) > 2 and r[2].strip() == name_val)
    anomaly_count = sum(1 for r in anomaly_rows if len(r) > 2 and r[2].strip() == name_val)
    self_count = sum(1 for r in self_rows if len(r) > 2 and r[2].strip() == name_val)
    total = gap_count + anomaly_count + self_count
    score_rows.append([name_val, str(gap_count), str(anomaly_count), str(self_count), str(total), ''])

# ── Build result ──
tz_shanghai = timezone(timedelta(hours=8))
now = datetime.now(tz_shanghai)
result = {
    'timestamp': now.isoformat(),
    'sync_time': now.strftime('%Y-%m-%d %H:%M:%S'),
    'sheets': {
        '自评表': {'name': '自评表', 'headers': self_headers, 'rows': self_rows},
        '差距表': {'name': '差距表', 'headers': gap_headers, 'rows': gap_rows},
        '异常表': {'name': '异常表', 'headers': anomaly_headers, 'rows': anomaly_rows},
        '报表清单': {'name': '报表清单', 'headers': reports_headers, 'rows': reports_rows},
        '积分表': {'name': '积分表', 'headers': score_headers, 'rows': score_rows, 'personnel': personnel}
    }
}

# ── Write data.json ──
data_path = os.path.expanduser('~/.hermes/projects/yixintongying/data.json')
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nWritten: {data_path} ({os.path.getsize(data_path)} bytes)")

# ── Update index.html ──
html_path = os.path.expanduser('~/.hermes/projects/yixintongying/index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(result, ensure_ascii=False)
old_start = html.find('var DATA = {')
old_end = html.find('};', old_start) + 2
if old_start >= 0 and old_end > old_start:
    html = html[:old_start] + 'var DATA = ' + data_json + ';' + html[old_end:]
else:
    html = re.sub(r'var DATA = \{.*?\};', 'var DATA = ' + data_json + ';', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Updated: {html_path} ({os.path.getsize(html_path)} bytes)")

# ── Summary ──
print("\n=== Sync Summary ===")
for name, sheet in result['sheets'].items():
    extra = f", personnel={len(sheet.get('personnel',[]))}" if name == '积分表' else ''
    print(f"  {name}: {len(sheet['rows'])} rows{extra}")
print(f"  Total personnel: {len(personnel)}")
print(f"  Sync time: {result['sync_time']}")
