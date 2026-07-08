#!/usr/bin/env python3
"""Complete Feishu sync: fetch spreadsheet -> data.json -> embed in index.html"""
import json, os, sys, urllib.request, urllib.error, time, re
from datetime import datetime, timezone, timedelta

# ── Credentials ──────────────────────────────────────────────────────────
env_path = os.path.expanduser('~/.hermes/.env')
creds = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            if k in ('FEISHU_APP_ID', 'FEISHU_APP_SECRET'):
                creds[k] = v

APP_ID = creds['FEISHU_APP_ID']
APP_SECRET = creds['FEISHU_APP_SECRET']

# ── Step 1: Get tenant access token ─────────────────────────────────────
print("[1/6] Getting tenant access token...")
data = json.dumps({'app_id': APP_ID, 'app_secret': APP_SECRET}).encode()
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=data,
    headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
if result.get('code') != 0:
    print(f"Token error: {result}")
    sys.exit(1)
token = result['tenant_access_token']
print(f"  Got token: {token[:10]}...")

AUTH = {'Authorization': f'Bearer {token}'}

def api_get(url):
    """Helper to call Feishu API GET"""
    req = urllib.request.Request(url, headers=AUTH)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:300]}")
        return {'code': e.code, 'msg': body}

# ── Step 2: Find the spreadsheet token via Wiki API ──────────────────────
SPACE_ID = 'g0v8bkvkldw'
NODE_TOKEN = 'PZJLw8SF5igYbEkAba6cq3CznMh'

print(f"\n[2/6] Finding spreadsheet via Wiki API...")
# The wiki node may be a doc/sheet. Try getting its info.
wiki_url = f'https://open.feishu.cn/open-apis/wiki/v2/spaces/{SPACE_ID}/nodes/{NODE_TOKEN}'
wiki_result = api_get(wiki_url)
print(f"  Wiki node: code={wiki_result.get('code')}, msg={wiki_result.get('msg')}")

spreadsheet_token = None
if wiki_result.get('code') == 0:
    node_data = wiki_result.get('data', {}).get('node', wiki_result.get('data', {}))
    obj_type = node_data.get('obj_type', '')
    obj_token = node_data.get('obj_token', '')
    title = node_data.get('title', '')
    print(f"  obj_type={obj_type}, obj_token={obj_token}, title={title}")
    if obj_type in ('sheet', 'bitable'):
        spreadsheet_token = obj_token
    elif obj_token:
        # Try using the obj_token as spreadsheet token anyway
        spreadsheet_token = obj_token

# If Wiki API didn't give us the token, try the node_token directly
if not spreadsheet_token:
    print("  Wiki API didn't return a sheet token. Trying node_token directly...")
    spreadsheet_token = NODE_TOKEN

print(f"  Using spreadsheet_token: {spreadsheet_token}")

# ── Step 3: Get spreadsheet metainfo (sheet names) ──────────────────────
print(f"\n[3/6] Getting spreadsheet metainfo...")
meta_url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}'
meta_result = api_get(meta_url)
print(f"  Meta: code={meta_result.get('code')}, msg={meta_result.get('msg')}")

sheets_meta = []
if meta_result.get('code') == 0:
    ss_data = meta_result.get('data', {}).get('spreadsheet', meta_result.get('data', {}))
    title = ss_data.get('title', '')
    print(f"  Spreadsheet title: {title}")
    sheets_meta = ss_data.get('sheets', [])
    for s in sheets_meta:
        print(f"    Sheet: {s.get('sheet_id')} = {s.get('title')}")

if not sheets_meta:
    # Fallback: try v2 API
    print("  Trying v2 metainfo API...")
    meta_url2 = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo'
    meta_result2 = api_get(meta_url2)
    print(f"  Meta v2: code={meta_result2.get('code')}, msg={meta_result2.get('msg')}")
    if meta_result2.get('code') == 0:
        md = meta_result2.get('data', {})
        sheets_meta = md.get('sheets', md.get('sheet_list', []))
        print(f"  Spreadsheet: {md.get('spreadsheet_title', '')}")
        for s in sheets_meta:
            print(f"    Sheet: {s.get('sheet_id', s.get('sheetId'))} = {s.get('title')}")

# ── Step 4: Fetch each sheet's data ─────────────────────────────────────
print(f"\n[4/6] Fetching sheet data...")

# Mapping from sheet index to our naming
SHEET_NAMES = ['自评表', '差距表', '异常表', '报表清单', '积分表']

# Try v3 query API for all sheets
all_sheet_data = {}
for i, sm in enumerate(sheets_meta):
    sheet_id = sm.get('sheet_id', sm.get('sheetId', ''))
    title = sm.get('title', f'sheet{i}')
    print(f"  Fetching sheet {sheet_id} ({title})...")
    
    # Try v3 Query API
    range_str = f'{sheet_id}!A1:O100'
    query_url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}/values/{range_str}?valueRenderOption=ToString&dateTimeRenderOption=FormattedString'
    qr = api_get(query_url)
    
    if qr.get('code') == 0:
        values = qr.get('data', [])
        if isinstance(values, dict):
            values = values.get('valueRange', {}).get('values', values.get('values', []))
        all_sheet_data[i] = {
            'title': title,
            'sheet_id': sheet_id,
            'values': values
        }
        print(f"    Got {len(values)} rows (v3)")
    else:
        # Fallback: v2 get API
        print(f"    v3 failed. Trying v2...")
        range_str2 = f'{sheet_id}!A1:O100'
        query_url2 = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_str2}?valueRenderOption=ToString'
        qr2 = api_get(query_url2)
        if qr2.get('code') == 0:
            values = qr2.get('data', [])
            if isinstance(values, dict):
                values = values.get('valueRange', {}).get('values', values.get('values', []))
            all_sheet_data[i] = {
                'title': title,
                'sheet_id': sheet_id,
                'values': values
            }
            print(f"    Got {len(values)} rows (v2)")
        else:
            print(f"    Both v2/v3 failed for this sheet.")
            all_sheet_data[i] = {'title': title, 'sheet_id': sheet_id, 'values': []}

# ── Step 5: Structure the data ──────────────────────────────────────────
print(f"\n[5/6] Structuring data...")

tz_shanghai = timezone(timedelta(hours=8))
now = datetime.now(tz_shanghai)

def safe_str(v):
    """Convert cell value to string, treating None/null/empty as ''"""
    if v is None or v == '':
        return ''
    if isinstance(v, (int, float)):
        if v == int(v):
            return str(int(v))
        return str(v)
    return str(v).strip()

def extract_rows(values, header_rows=0):
    """Extract data rows, skipping header rows and empty rows"""
    rows = []
    for i in range(header_rows, len(values)):
        row_vals = values[i]
        row = [safe_str(c) for c in row_vals]
        # Pad to ensure at least the column count
        row = row[:15] + [''] * max(0, 15 - len(row))
        # Check if row has any data
        has_data = any(cell for cell in row)
        if has_data:
            rows.append(row)
    return rows

result_sheets = {}

# s0 -> 自评表
if 0 in all_sheet_data:
    sd = all_sheet_data[0]
    vals = sd['values']
    rows = extract_rows(vals, header_rows=2)  # skip header rows
    # Take standard columns
    trimmed = [r[:10] for r in rows]
    result_sheets['自评表'] = {
        'headers': ["差异ID","项目名称","填报人","报告名称","来源","做什么用","报告频率","数据来源","数据质量问题","差异等级"],
        'rows': trimmed
    }
    print(f"  自评表: {len(trimmed)} rows")
else:
    result_sheets['自评表'] = {'headers': [], 'rows': []}
    print(f"  自评表: no data")

# s1 -> 差距表
if 1 in all_sheet_data:
    sd = all_sheet_data[1]
    vals = sd['values']
    rows = extract_rows(vals, header_rows=1)
    trimmed = [r[:7] for r in rows]
    result_sheets['差距表'] = {
        'headers': ["序号","所属项目","提交人","名称","频率","所属系统","软件功能缺陷问题"],
        'rows': trimmed
    }
    print(f"  差距表: {len(trimmed)} rows")
else:
    result_sheets['差距表'] = {'headers': [], 'rows': []}
    print(f"  差距表: no data")

# s2 -> 异常表
if 2 in all_sheet_data:
    sd = all_sheet_data[2]
    vals = sd['values']
    rows = extract_rows(vals, header_rows=1)
    trimmed = [r[:8] for r in rows]
    result_sheets['异常表'] = {
        'headers': ["序号","项目名称","上报人","项目阶段","异常类型","异常描述","异常发生时间","异常发现时间"],
        'rows': trimmed
    }
    print(f"  异常表: {len(trimmed)} rows")
else:
    result_sheets['异常表'] = {'headers': [], 'rows': []}
    print(f"  异常表: no data")

# s3 -> 报表清单
if 3 in all_sheet_data:
    sd = all_sheet_data[3]
    vals = sd['values']
    rows = extract_rows(vals, header_rows=1)
    trimmed = [r[:4] for r in rows]
    result_sheets['报表清单'] = {
        'headers': ["所属园区","报告名称","频率","来源"],
        'rows': trimmed
    }
    print(f"  报表清单: {len(trimmed)} rows")
else:
    result_sheets['报表清单'] = {'headers': [], 'rows': []}
    print(f"  报表清单: no data")

# s4 -> 积分表
personnel = []
if 4 in all_sheet_data:
    sd = all_sheet_data[4]
    vals = sd['values']
    rows = extract_rows(vals, header_rows=1)
    trimmed = [r[:6] for r in rows]
    result_sheets['积分表'] = {
        'headers': ["所属园区","报告名称","频率","来源","操作手册","手册优化点"],
        'rows': trimmed
    }
    # Extract personnel from last column / bottom rows if available
    # Look for names in the data
    if len(trimmed) > 0 and len(trimmed[0]) > 0:
        personnel = [trimmed[0][0]] if trimmed[0][0] else []
    if len(trimmed) > 1:
        for r in trimmed:
            if r[0] and r[0] not in personnel:
                personnel.append(r[0])
    print(f"  积分表: {len(trimmed)} rows, personnel: {personnel}")
else:
    result_sheets['积分表'] = {'headers': [], 'rows': []}
    print(f"  积分表: no data")

# Build final output
output = {
    'timestamp': now.isoformat(),
    'sync_time': now.strftime('%Y-%m-%d %H:%M:%S'),
    'sheets': result_sheets
}

# ── Step 6: Write data.json and embed into index.html ──────────────────
project_dir = '/Users/qkl/.hermes/projects/yixintongying'
data_path = os.path.join(project_dir, 'data.json')
html_path = os.path.join(project_dir, 'index.html')

print(f"\n[6/6] Writing data.json...")
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"  Written to {data_path}")

print(f"Embedding into index.html...")
data_json = json.dumps(output, ensure_ascii=False)
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Replace var DATA = {...};
html = re.sub(
    r'var DATA = \{.*?\};',
    'var DATA = ' + data_json + ';',
    html,
    flags=re.DOTALL
)
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"  Embedded into {html_path}")

# ── Summary ──────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Sync complete: {output['sync_time']}")
for name, sheet in result_sheets.items():
    print(f"  {name}: {len(sheet['rows'])} rows")
print(f"{'='*60}")
