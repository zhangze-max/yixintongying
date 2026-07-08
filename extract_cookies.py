#!/usr/bin/env python3
"""Extract Feishu cookies from Chrome profile"""
import sqlite3, json, os, sys

db_path = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Cookies')
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly, same_site FROM cookies WHERE host_key LIKE '%feishu%' OR host_key LIKE '%lark%' ORDER BY host_key")
    cookies = []
    for row in cursor.fetchall():
        cookies.append({
            'domain': row[0],
            'name': row[1],
            'value': row[2],
            'path': row[3],
            'expires': row[4],
            'secure': bool(row[5]),
            'httponly': bool(row[6]),
            'sameSite': row[7] if row[7] is not None else 'Lax'
        })
    conn.close()
    print(f"Found {len(cookies)} Feishu cookies:")
    for c in cookies:
        print(f"  {c['domain']}: {c['name']}={c['value'][:40]}... (secure={c['secure']})")
    
    # Save to file for injection
    out_path = os.path.expanduser('~/.hermes/projects/yixintongying/feishu_cookies.json')
    with open(out_path, 'w') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
