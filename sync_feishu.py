#!/usr/bin/env python3
"""Sync Feishu spreadsheet data to data.json"""
import json, os, urllib.request, sys
from datetime import datetime, timezone, timedelta

# Read credentials from .env
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

# Step 1: Get tenant access token
print("Getting tenant access token...")
data = json.dumps({'app_id': app_id, 'app_secret': app_secret}).encode()
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
print(f"Got token: {token[:10]}...")

# Step 2: Get wiki node info to find the spreadsheet
node_token = 'PZJLw8SF5igYbEkAba6cq3CznMh'
space_id = 'g0v8bkvkldw'
print(f"Getting wiki node info for {node_token}...")

req2 = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes/{node_token}',
    headers={'Authorization': f'Bearer {token}'})
try:
    resp2 = urllib.request.urlopen(req2)
    node_info = json.loads(resp2.read())
    print(f"Node code: {node_info.get('code')}, msg: {node_info.get('msg')}")
    data_obj = node_info.get('data', {})
    print(f"Node type: {data_obj.get('obj_type')}")
    print(f"Node title: {data_obj.get('title')}")
    
    # Check if it has a spreadsheet token
    node_type = data_obj.get('obj_type', '')
    if node_type == 'sheet':
        spreadsheet_token = data_obj.get('obj_token', node_token)
        print(f"Spreadsheet token: {spreadsheet_token}")
    else:
        # Try to find children that are sheets
        print("Checking children...")
        children = data_obj.get('children', [])
        for child in children:
            print(f"  Child: {child.get('title')} ({child.get('obj_type')})")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    body = e.read().decode()
    print(f"Body: {body[:500]}")
