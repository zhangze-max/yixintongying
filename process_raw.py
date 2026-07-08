#!/usr/bin/env python3
"""Process raw Feishu data and build data.json, embed in index.html"""
import json, os, re, sys
from datetime import datetime, timezone, timedelta

tz_shanghai = timezone(timedelta(hours=8))
now = datetime.now(tz_shanghai)
project_dir = '/Users/qkl/.hermes/projects/yixintongying'

# Load raw data from file passed as argument or stdin
raw_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(project_dir, 'raw_sync_data.json')
with open(raw_path, 'r', encoding='utf-8') as f:
    raw = json.load(f)

result_sheets = {}

# s0 -> self_eval: skip first 2 rows (title + header)
s0_data = raw['s0']['data']
s0_rows = [[(row[i] if i < len(row) else '') for i in range(10)] for row in s0_data[2:]]
result_sheets['自评表'] = {
    'headers': ["差异ID","项目名称","填报人","报告名称","来源","做什么用","报告频率","数据来源","数据质量问题","差异等级"],
    'rows': s0_rows
}

# s1 -> gap_table: skip first 2 rows
s1_data = raw['s1']['data']
s1_rows = []
for row in s1_data[2:]:
    trimmed = [row[0], row[1], row[2], row[4] if len(row) > 4 else '', row[5] if len(row) > 5 else '', row[6] if len(row) > 6 else '', row[7] if len(row) > 7 else '']
    s1_rows.append(trimmed)
result_sheets['差距表'] = {
    'headers': ["序号","所属项目","提交人","名称","频率","所属系统","软件功能缺陷问题"],
    'rows': s1_rows
}

# s2 -> exception_table: skip first 2 rows
s2_data = raw['s2']['data']
s2_rows = [[(row[i] if i < len(row) else '') for i in range(8)] for row in s2_data[2:]]
result_sheets['异常表'] = {
    'headers': ["序号","项目名称","上报人","项目阶段","异常类型","异常描述","异常发生时间","异常发现时间"],
    'rows': s2_rows
}

# s3 -> report_list: empty
result_sheets['报表清单'] = {
    'headers': ["所属园区","报告名称","频率","来源"],
    'rows': []
}

# s4 -> score_table
s4_data = raw['s4']['data']
s4_rows = []
personnel = []
for row in s4_data[1:]:
    trimmed = [(row[i] if i < len(row) else '') for i in range(6)]
    s4_rows.append(trimmed)
    if row[0]:
        personnel.append(row[0])
result_sheets['积分表'] = {
    'headers': ["所属园区","报告名称","频率","来源","操作手册","手册优化点"],
    'rows': s4_rows,
    'personnel': personnel
}

output = {
    'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
    'sync_time': now.strftime('%Y-%m-%d %H:%M:%S'),
    'sheets': result_sheets
}

# Write data.json
data_path = os.path.join(project_dir, 'data.json')
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"Written data.json ({os.path.getsize(data_path)} bytes)")

# Embed into index.html
html_path = os.path.join(project_dir, 'index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(output, ensure_ascii=False)
html = re.sub(
    r'var DATA = \{.*?\};',
    'var DATA = ' + data_json + ';',
    html,
    flags=re.DOTALL
)
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Embedded into index.html")

# Summary
print(f"\nSync time: {output['sync_time']}")
for name, sheet in result_sheets.items():
    rc = len(sheet['rows'])
    extra = f", personnel: {len(sheet.get('personnel', []))}人" if name == '积分表' else ''
    print(f"  {name}: {rc} rows{extra}")
