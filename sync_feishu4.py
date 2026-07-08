#!/usr/bin/env python3
"""Sync Feishu spreadsheet - full script with lark_oapi SDK"""
import json, os, sys
from datetime import datetime, timezone, timedelta

env_path = os.path.expanduser('~/.hermes/.env')
creds = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            if k in ('FEISHU_APP_ID', 'FEISHU_APP_SECRET'):
                creds[k] = v

from lark_oapi import Client
from lark_oapi.api.auth.v3 import InternalTenantAccessTokenRequest, InternalTenantAccessTokenRequestBody

client = Client.builder() \
    .app_id(creds['FEISHU_APP_ID']) \
    .app_secret(creds['FEISHU_APP_SECRET']) \
    .build()

# Get token
tat = client.auth.v3.tenant_access_token
body = InternalTenantAccessTokenRequestBody.builder() \
    .app_id(creds['FEISHU_APP_ID']) \
    .app_secret(creds['FEISHU_APP_SECRET']) \
    .build()
req = InternalTenantAccessTokenRequest.builder().request_body(body).build()
resp = tat.internal(req)
token = json.loads(resp.raw.content)['tenant_access_token']

node_token = 'PZJLw8SF5igYbEkAba6cq3CznMh'

# Try Sheets API
print("=== Sheets metainfo ===")
from lark_oapi.api.sheets.v2 import GetSpreadsheetMetaInfoRequest
try:
    req = GetSpreadsheetMetaInfoRequest.builder() \
        .spreadsheet_token(node_token).build()
    resp = client.sheets.v2.spreadsheet.get_meta_info(req)
    if resp.success():
        print("Success!")
        raw = json.loads(resp.raw.content)
        print(json.dumps(raw, ensure_ascii=False, indent=2)[:1000])
    else:
        print(f"Error: {resp.code} {resp.msg}")
        if resp.raw:
            print(f"Raw: {resp.raw.content.decode()[:300]}")
except Exception as e:
    print(f"Exception: {e}")

# Try with different API paths
print("\n=== Sheets v3 metainfo ===")
try:
    req = GetSpreadsheetMetaInfoRequest.builder() \
        .spreadsheet_token(node_token).build()
    resp = client.sheets.v3.spreadsheet.get_meta_info(req)
    if resp.success():
        print("Success v3!")
        raw = json.loads(resp.raw.content)
        print(json.dumps(raw, ensure_ascii=False, indent=2)[:1000])
    else:
        print(f"v3 Error: {resp.code} {resp.msg}")
except Exception as e:
    print(f"v3 Exception: {e}")

# Check what's available on client.sheets
print("\n=== Client sheets API surface ===")
for attr in dir(client.sheets):
    if not attr.startswith('_'):
        print(f"  {attr}")
