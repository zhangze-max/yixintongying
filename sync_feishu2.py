#!/usr/bin/env python3
"""Sync Feishu spreadsheet - try different APIs"""
import json, os, urllib.request, urllib.error, sys

env_path = os.path.expanduser('~/.hermes/.env')
creds = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            if k in ('FEISHU_APP_ID', 'FEISHU_APP_SECRET'):
                creds[k] = v

app_id = creds['FEISHU_APP_ID']
app_secret = creds['FEISHU_APP_SECRET']

# Get token
data = json.dumps({'app_id': app_id, 'app_secret': app_secret}).encode()
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
token = result['tenant_access_token']

node_token = 'PZJLw8SF5igYbEkAba6cq3CznMh'
space_id = 'g0v8bkvkldw'

# Try 1: Doc API raw_content
print("=== Try Doc API ===")
try:
    req = urllib.request.Request(
        f'https://open.feishu.cn/open-apis/docx/v1/documents/{node_token}/raw_content',
        headers={'Authorization': f'Bearer {token}'})
    resp = urllib.request.urlopen(req)
    content = json.loads(resp.read())
    print(f"Doc code: {content.get('code')}, msg: {content.get('msg')}")
    if content.get('code') == 0:
        c = content.get('data', {}).get('content', '')
        print(f"Content length: {len(c)}, preview: {c[:200]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Doc HTTP {e.code}: {body[:300]}")

# Try 2: Drive API file meta
print("\n=== Try Drive API ===")
try:
    req = urllib.request.Request(
        f'https://open.feishu.cn/open-apis/drive/v1/files/{node_token}/meta',
        headers={'Authorization': f'Bearer {token}'})
    resp = urllib.request.urlopen(req)
    meta = json.loads(resp.read())
    print(f"Drive code: {meta.get('code')}, msg: {meta.get('msg')}")
    if meta.get('code') == 0:
        d = meta.get('data', {})
        print(f"Name: {d.get('name')}")
        print(f"Type: {d.get('type')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Drive HTTP {e.code}: {body[:300]}")

# Try 3: Sheets API with node_token as spreadsheet token
print("\n=== Try Sheets API ===")
try:
    req = urllib.request.Request(
        f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{node_token}/metainfo',
        headers={'Authorization': f'Bearer {token}'})
    resp = urllib.request.urlopen(req)
    sheets = json.loads(resp.read())
    print(f"Sheets code: {sheets.get('code')}, msg: {sheets.get('msg')}")
    if sheets.get('code') == 0:
        sdata = sheets.get('data', {})
        print(f"Properties: {json.dumps(sdata, ensure_ascii=False)[:500]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Sheets HTTP {e.code}: {body[:300]}")

# Try 4: Drive API list files (search)
print("\n=== Try Drive search ===")
try:
    req = urllib.request.Request(
        'https://open.feishu.cn/open-apis/drive/v1/files?page_size=10',
        headers={'Authorization': f'Bearer {token}'})
    resp = urllib.request.urlopen(req)
    files = json.loads(resp.read())
    print(f"Drive list code: {files.get('code')}, msg: {files.get('msg')}")
    if files.get('code') == 0:
        for f in files.get('data', {}).get('files', [])[:5]:
            print(f"  {f.get('name')} ({f.get('type')}) token={f.get('token')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Drive list HTTP {e.code}: {body[:300]}")
