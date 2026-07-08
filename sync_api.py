#!/usr/bin/env python3
"""一心通营数据同步 — 纯API版（不依赖Chrome，可部署到任意服务器）"""
import subprocess, json, datetime, os, shutil
from pathlib import Path

PROJECT = Path("/Users/qkl/.hermes/projects/yixintongying")
DESKTOP = Path("/Users/qkl/Desktop")
TOKEN = "PZJLw8SF5igYbEkAba6cq3CznMh"
EXCLUDE = {"彭丹", "孙荣杰"}  # 不显示在积分榜

SHEETS = [
    {"name": "自评表", "id": "u2L03W", "range": "A3:L80",
     "headers": ["差异ID","项目名称","填报人","报告名称","来源","做什么用","报告频率","数据来源","数据质量问题","差异等级","责任部门","责任人"]},
    {"name": "差距表", "id": "2uluU2", "range": "A3:L80",
     "headers": ["序号","所属项目","提交人","所属场景","名称","频率","所属系统","软件功能缺陷问题","问题严重等级","问题详细描述","整改措施","责任部门/责任人"]},
    {"name": "异常表", "id": "KU6RfN", "range": "A3:L80",
     "headers": ["序号","项目名称","上报人","项目阶段","异常类型","异常描述","异常发生时间","异常发现时间","责任部门","责任人","异常等级","处理状态"]},
    {"name": "报表清单", "id": "3964d0", "range": "A2:H40",
     "headers": ["所属园区","报告名称","频率","来源"]},
    {"name": "积分表", "id": "nc55YF", "range": "A1:F20",
     "headers": ["姓名","差距表积分","异常表积分","自评表积分","总积分"]},
]


def read_sheet(sheet_id, range_str):
    """Read a sheet via lark-cli API."""
    cmd = [
        "lark-cli", "sheets", "+read",
        "--spreadsheet-token", TOKEN,
        "--sheet-id", sheet_id,
        "--range", range_str,
        "--value-render-option", "FormattedValue",
        "--as", "user"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"Error reading {sheet_id}: {result.stderr[:200]}")
        return []
    
    data = json.loads(result.stdout)
    if not data.get("ok"):
        print(f"API error for {sheet_id}: {data.get('error', 'unknown')}")
        return []
    
    values = data.get("data", {}).get("valueRange", {}).get("values", [])
    return values


def sync():
    """Full sync: read all sheets, write files."""
    sheets_out = {}
    
    for sheet in SHEETS:
        values = read_sheet(sheet["id"], sheet["range"])
        headers = sheet["headers"]
        
        # Filter empty rows
        rows = []
        seen = set()
        for row in values:
            # Pad row to headers length
            while len(row) < len(headers):
                row.append("")
            # Check if row has any non-empty content
            has_content = any(v is not None and str(v).strip() != "" for v in row)
            if not has_content:
                continue
            # Convert all values to strings
            str_row = [str(v) if v is not None else "" for v in row[:len(headers)]]
            # Filter excluded personnel from 积分表
            if sheet["name"] == "积分表" and str_row[0] in EXCLUDE:
                continue
            # Filter header row from 积分表 (someone put "GitHub" in A1)
            if sheet["name"] == "积分表" and (str_row[1] == "差距表积分" or str_row[0] == "GitHub"):
                continue
            # Deduplicate
            key = str_row[0] if str_row[0] else str(str_row[1:3])
            if key not in seen:
                seen.add(key)
                rows.append(str_row)
        
        sheets_out[sheet["name"]] = {
            "headers": headers,
            "data": rows,
            "count": len(rows)
        }
    
    personnel = [row[0] for row in sheets_out["积分表"]["data"] if row[0] and row[0] not in EXCLUDE]
    
    data = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": f"https://g0v8bkvkldw.feishu.cn/wiki/{TOKEN}",
        "sheets": sheets_out,
        "personnel": personnel,
        "summary": {k: v["count"] for k, v in sheets_out.items()}
    }
    
    # Calculate current scores
    scores = {row[0]: int(row[4]) for row in sheets_out["积分表"]["data"] if row[0] and row[4].isdigit()}
    
    # Save daily snapshot for 日/周/月 ranking
    today = datetime.date.today().strftime("%Y-%m-%d")
    snap_dir = PROJECT / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    snap_file = snap_dir / f"{today}.json"
    if not snap_file.exists():
        with open(snap_file, 'w', encoding='utf-8') as f:
            json.dump({"date": today, "scores": scores}, f, ensure_ascii=False)
    
    # Load snapshots for deltas
    snapshots = {"today": {}, "yesterday": {}, "last_week": {}, "last_month": {}}
    for fpath in sorted(snap_dir.glob("*.json")):
        with open(fpath) as f:
            snap = json.load(f)
        snapshots["today"] = snap["scores"]
        if fpath.stem == today:
            break
    
    # Find yesterday
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    y_file = snap_dir / f"{yesterday}.json"
    if y_file.exists():
        with open(y_file) as f:
            snapshots["yesterday"] = json.load(f)["scores"]
    
    # Find last week (7 days ago, closest)
    for days_ago in range(7, 14):
        lw = (datetime.date.today() - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
        lw_file = snap_dir / f"{lw}.json"
        if lw_file.exists():
            with open(lw_file) as f:
                snapshots["last_week"] = json.load(f)["scores"]
            break
    
    # Find last month (30 days ago, closest)
    for days_ago in range(28, 35):
        lm = (datetime.date.today() - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
        lm_file = snap_dir / f"{lm}.json"
        if lm_file.exists():
            with open(lm_file) as f:
                snapshots["last_month"] = json.load(f)["scores"]
            break
    
    data["deltas"] = {}
    for period, snap in [("日", "yesterday"), ("周", "last_week"), ("月", "last_month")]:
        if snapshots[snap]:
            deltas = {}
            for name, score in scores.items():
                prev = snapshots[snap].get(name, 0)
                deltas[name] = score - prev
            data["deltas"][period] = deltas
    
    # Write files
    for p in [PROJECT / "data.json", DESKTOP / "data.json"]:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    js = "var DATA = " + json.dumps(data, ensure_ascii=False) + ";"
    for p in [PROJECT / "data.js", DESKTOP / "data.js"]:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(js)
    
    # Verify
    r = subprocess.run(['node', '--check', str(PROJECT / 'data.js')], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"JS error: {r.stderr}")
        return None
    
    return data


if __name__ == '__main__':
    result = sync()
    if result:
        print(json.dumps(result["summary"], ensure_ascii=False))
        print(f"OK: {result['timestamp']}")
    else:
        print("SYNC FAILED")
        exit(1)
