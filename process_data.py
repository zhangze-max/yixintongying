import json
from datetime import datetime, timezone, timedelta

raw = json.load(open('/Users/qkl/.hermes/projects/yixintongying/raw_data.json'))

# s0: 自评表
s0_headers = ["差异ID","项目名称","填报人","报告名称","来源","做什么用","报告频率","数据来源","数据质量问题","差异等级"]
s0_data = [row[:len(s0_headers)] for row in raw["s0"]["data"][2:]]

# s1: 差距表 — skip col 3 (所属场景)
s1_headers = ["序号","所属项目","提交人","名称","频率","所属系统","软件功能缺陷问题"]
s1_col_map = [0, 1, 2, 4, 5, 6, 7]
s1_data = [[row[i] if i < len(row) else "" for i in s1_col_map] for row in raw["s1"]["data"][2:]]

# s2: 异常表 — first 8 columns
s2_headers = ["序号","项目名称","上报人","项目阶段","异常类型","异常描述","异常发生时间","异常发现时间"]
s2_data = [row[:len(s2_headers)] for row in raw["s2"]["data"][2:]]

# s3: 报表清单 — empty
s3_headers = ["所属园区","报告名称","频率","来源"]
s3_data = []

# s4: 积分表
s4_headers = raw["s4"]["data"][0][:5]
s4_data = [row[:5] for row in raw["s4"]["data"][1:]]
s4_personnel = [row[0] for row in s4_data if row[0]]

tz = timezone(timedelta(hours=8))
ts = datetime.now(tz).isoformat()

result = {
    "timestamp": ts,
    "sheets": {
        "自评表": {"headers": s0_headers, "rows": len(s0_data), "data": s0_data},
        "差距表": {"headers": s1_headers, "rows": len(s1_data), "data": s1_data},
        "异常表": {"headers": s2_headers, "rows": len(s2_data), "data": s2_data},
        "报表清单": {"headers": s3_headers, "rows": len(s3_data), "data": s3_data},
        "积分表": {"headers": s4_headers, "rows": len(s4_data), "data": s4_data, "personnel": s4_personnel}
    }
}

with open('/Users/qkl/.hermes/projects/yixintongying/data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"OK: timestamp={ts}")
print(f"自评表={len(s0_data)}, 差距表={len(s1_data)}, 异常表={len(s2_data)}, 报表清单={len(s3_data)}, 积分表={len(s4_data)}({len(s4_personnel)}人)")
