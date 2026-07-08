#!/usr/bin/env python3
"""Sync Feishu spreadsheet via lark_oapi SDK"""
import json, os, sys
from datetime import datetime, timezone, timedelta

# Read credentials
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

client = Client.builder() \
    .app_id(creds['FEISHU_APP_ID']) \
    .app_secret(creds['FEISHU_APP_SECRET']) \
    .build()

token = client.auth.v3.tenant_access_token
print(f"Token: {token[:10]}...")

node_token = 'PZJLw8SF5igYbEkAba6cq3CznMh'

# Try Drive API to get file metadata
print("\n=== Drive file meta ===")
from lark_oapi.api.drive.v1 import GetFileMetaRequest
try:
    req = GetFileMetaRequest.builder().file_token(node_token).build()
    resp = client.drive.get_file_meta(req)
    if resp.success():
        print(f"Name: {resp.data.name}")
        print(f"Type: {resp.data.type}")
        print(f"All: {resp.data}")
    else:
        print(f"Drive error: {resp.code} {resp.msg}")
except Exception as e:
    print(f"Drive exception: {e}")

# Try Sheets API directly
print("\n=== Sheets metainfo ===")
from lark_oapi.api.sheets.v2 import GetSpreadsheetMetaInfoRequest
try:
    req = GetSpreadsheetMetaInfoRequest.builder() \
        .spreadsheet_token(node_token).build()
    resp = client.sheets.get_spreadsheet_meta_info(req)
    if resp.success():
        sheets = resp.data.sheets
        print(f"Spreadsheet title: {resp.data.spreadsheet_title}")
        for s in sheets:
            print(f"  Sheet: {s.sheet_id} = {s.title}")
    else:
        print(f"Sheets error: {resp.code} {resp.msg}")
except Exception as e:
    print(f"Sheets exception: {e}")

# Try Doc API
print("\n=== Doc raw content ===")
from lark_oapi.api.docx.v1 import GetDocumentRawContentRequest
try:
    req = GetDocumentRawContentRequest.builder() \
        .document_id(node_token).build()
    resp = client.docs.get_document_raw_content(req)
    if resp.success():
        print(f"Content: {resp.data.content[:500]}")
    else:
        print(f"Doc error: {resp.code} {resp.msg}")
except Exception as e:
    # Docs might not be accessible under different attribute
    print(f"Doc exception: {e}")

# Try Wiki API
print("\n=== Wiki node info ===")
from lark_oapi.api.wiki.v2 import GetSpaceNodeRequest
try:
    req = GetSpaceNodeRequest.builder() \
        .space_id('g0v8bkvkldw') \
        .node_token(node_token).build()
    resp = client.wiki.get_space_node(req)
    if resp.success():
        print(f"Node: {resp.data}")
    else:
        print(f"Wiki error: {resp.code} {resp.msg}")
except Exception as e:
    print(f"Wiki exception: {e}")

# Try to get tenant scope info
print("\n=== Auth scopes ===")
try:
    # Check what scopes we have
    from lark_oapi.api.auth.v3 import InternalTenantAccessTokenRequest
    req = InternalTenantAccessTokenRequest.builder().build()
    # This won't work but let's see
except Exception as e:
    print(f"Scope check: {e}")
