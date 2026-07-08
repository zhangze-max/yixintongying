#!/usr/bin/env python3
"""Process fetched Feishu sheet data and write data.json + update index.html"""
import json, os, re
from datetime import datetime, timezone, timedelta

def extract_plain_text(cell):
    """Extract plain text from Feishu rich text cells"""
    if cell is None:
        return ''
    if isinstance(cell, str):
        # Check if it's JSON array of rich text segments
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
    """Check if a row is completely empty"""
    return not any(cell is not None and str(cell).strip() != '' for cell in row)

# ── Load raw data from fetch outputs ──
# Self-assessment sheet (自评表)
raw_self = json.loads(open('/tmp/feishu_s0.json').read())
# Gap sheet (差距表)  
raw_gap = json.loads(open('/tmp/feishu_s1.json').read())
# Anomaly sheet (异常表)
raw_anomaly = json.loads(open('/tmp/feishu_s2.json').read())
# Report list (报表清单)
raw_reports = json.loads(open('/tmp/feishu_s3.json').read())
# Score sheet (积分表)
raw_score = json.loads(open('/tmp/feishu_s4.json').read())

# ── Process 自评表 ──
s0_vals = raw_self['data']['valueRange']['values']
# Row 0: title, Row 1: headers, Row 2+: data
self_headers = ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级']
self_rows = []
for row in s0_vals[2:]:  # start from row 2 (0-indexed)
    if is_empty_row(row):
        continue
    padded = list(row) + [''] * (len(self_headers) - len(row))
    trimmed = padded[:len(self_headers)]
    cleaned = [extract_plain_text(c) for c in trimmed]
    if any(c.strip() for c in cleaned):
        self_rows.append(cleaned)

# ── Process 差距表 ──
s1_vals = raw_gap['data']['valueRange']['values']
# Row 0: title, Row 1: headers (序号,所属项目,提交人,所属场景,名称,频率,所属系统), Row 2+: data
# Map columns to task headers: [序号(0), 所属项目(1), 提交人(2), 名称(4), 频率(5), 所属系统(6), 软件功能缺陷问题(empty)]
gap_headers = ['序号','所属项目','提交人','名称','频率','所属系统','软件功能缺陷问题']
# Column mapping: 0→0, 1→1, 2→2, 4→3, 5→4, 6→5, new→6
col_map = {0:0, 1:1, 2:2, 4:3, 5:4, 6:5}
gap_rows = []
for row in s1_vals[2:]:
    if is_empty_row(row):
        continue
    cleaned_row = [''] * 7
    for src, dst in col_map.items():
        if src < len(row):
            cleaned_row[dst] = extract_plain_text(row[src])
    # Replace formula-like sequential numbers
    if cleaned_row[0] == 'ROW()-2':
        cleaned_row[0] = str(len(gap_rows) + 1)
    if any(c.strip() for c in cleaned_row):
        gap_rows.append(cleaned_row)

# ── Process 异常表 ──
s2_vals = raw_anomaly['data']['valueRange']['values']
# Row 0: title, Row 1: headers, Row 2+: data
anomaly_headers = ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间']
anomaly_rows = []
for row in s2_vals[2:]:
    if is_empty_row(row):
        continue
    padded = list(row) + [''] * (len(anomaly_headers) - len(row))
    trimmed = padded[:len(anomaly_headers)]
    cleaned = [extract_plain_text(c) for c in trimmed]
    # Convert serial number dates (Excel format) to readable format for cols 6,7
    for idx in [6, 7]:
        try:
            val = int(float(cleaned[idx]))
            if 40000 < val < 60000:
                from datetime import datetime, timedelta
                base = datetime(1899, 12, 30)
                dt = base + timedelta(days=val)
                cleaned[idx] = dt.strftime('%Y-%m-%d')
        except (ValueError, IndexError):
            pass
    if any(c.strip() for c in cleaned):
        anomaly_rows.append(cleaned)

# ── Process 报表清单 ──
s3_vals = raw_reports['data']['valueRange']['values']
# Row 0: headers, Row 1+: data
reports_headers = ['所属园区','报告名称','频率','来源']
reports_rows = []
last_park = ''
for row in s3_vals[1:]:
    if is_empty_row(row):
        continue
    padded = list(row) + [''] * 4
    trimmed = padded[:4]
    cleaned = [extract_plain_text(c) for c in trimmed]
    # Carry forward park name if empty
    if cleaned[0].strip():
        last_park = cleaned[0]
    else:
        cleaned[0] = last_park
    if any(c.strip() for c in cleaned):
        reports_rows.append(cleaned)

# ── Process 积分表 ──
s4_vals = raw_score['data']['valueRange']['values']
# Row 0: headers (姓名, 差距表积分, 异常表积分, 自评表积分, 总积分, null)
# Row 1+: name + formulas - compute actual counts from other sheets
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
    
    # Count from other sheets
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
print(f"Written data.json: {data_path}")

# ── Update index.html ──
html_path = os.path.expanduser('~/.hermes/projects/yixintongying/index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(result, ensure_ascii=False)
# Find and replace DATA block
old_start = html.find('var DATA = {')
old_end = html.find('};', old_start) + 2
if old_start >= 0 and old_end > old_start:
    html = html[:old_start] + 'var DATA = ' + data_json + ';' + html[old_end:]
else:
    html = re.sub(r'var DATA = \{.*?\};', 'var DATA = ' + data_json + ';', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Updated index.html: {html_path}")

# ── Summary ──
print("\n=== Sync Summary ===")
for name, sheet in result['sheets'].items():
    extra = f", personnel={len(sheet.get('personnel',[]))}" if name == '积分表' else ''
    print(f"  {name}: {len(sheet['rows'])} rows{extra}")
print(f"  Total personnel: {len(personnel)}")
print(f"  Sync time: {result['sync_time']}")
