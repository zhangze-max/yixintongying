#!/usr/bin/env python3
"""Restore data from data.js, update timestamp, write to data.json and embed in index.html"""
import json, os, re
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)

project_dir = '/Users/qkl/.hermes/projects/yixintongying'

# Read data.js and extract JSON
with open(os.path.join(project_dir, 'data.js'), 'r') as f:
    js_content = f.read()

# Extract JSON between 'var DATA = ' and the final ';'
match = re.search(r'var DATA = (.+?);?\s*$', js_content, re.DOTALL)
if not match:
    print("ERROR: Could not extract JSON from data.js")
    exit(1)

data = json.loads(match.group(1))
print(f"Extracted data with sheets: {list(data['sheets'].keys())}")

# Update timestamp
data['timestamp'] = now.isoformat()
data['sync_time'] = now.strftime('%Y-%m-%d %H:%M:%S')

# Write data.json
data_path = os.path.join(project_dir, 'data.json')
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Written data.json with timestamp {data['sync_time']}")

# Embed in index.html
html_path = os.path.join(project_dir, 'index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(data, ensure_ascii=False)
html = re.sub(
    r'var DATA = \{.*?\};',
    'var DATA = ' + data_json + ';',
    html,
    flags=re.DOTALL
)
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Embedded into index.html")

# Print summary
print(f"\n=== Sync Summary ===")
print(f"Sync time: {data['sync_time']}")
for name, sheet in data['sheets'].items():
    hr = sheet.get('row_count', len(sheet.get('rows', [])))
    print(f"  {name}: {hr} rows")
