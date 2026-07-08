import json, sys
from datetime import datetime

# Read raw data from stdin
raw = json.load(sys.stdin)

s0_headers = ["差异ID","项目名称","填报人","报告名称","来源","做什么用","报告频率","数据来源","数据质量问题","差异等级"]
s0_data = [dict(zip(s0_headers, row[:len(s0_headers)])) for row in raw["s0"]["data"][2:]]

s1_headers = ["序号","所属项目","提交人","名称","频率","所属系统","软件功能缺陷问题"]
s1_data = [dict(zip(s1_headers, row[:len(s1_headers)])) for row in raw["s1"]["data"][2:]]

s2_headers = ["序号","项目名称","上报人","项目阶段","异常类型","异常描述","异常发生时间","异常发现时间"]
s2_data = [dict(zip(s2_headers, row[:len(s2_headers)])) for row in raw["s2"]["data"][2:]]

s3_headers = ["所属园区","报告名称","频率","来源"]
s3_data = []

s4_actual_headers = raw["s4"]["data"][0][:5]
s4_data = []
personnel = []
for row in raw["s4"]["data"][1:]:
    s4_data.append(dict(zip(s4_actual_headers, row[:5])))
    if row[0]:
        personnel.append(row[0])

result = {
    "timestamp": datetime.now().isoformat(),
    "sheets": {
        "自评表": {"headers": s0_headers, "data": s0_data, "count": len(s0_data)},
        "差距表": {"headers": s1_headers, "data": s1_data, "count": len(s1_data)},
        "异常表": {"headers": s2_headers, "data": s2_data, "count": len(s2_data)},
        "报表清单": {"headers": s3_headers, "data": s3_data, "count": len(s3_data)},
        "积分表": {"headers": s4_actual_headers, "data": s4_data, "personnel": personnel, "count": len(s4_data)}
    }
}

with open('/Users/qkl/.hermes/projects/yixintongying/data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"OK: 自评表={len(s0_data)} 差距表={len(s1_data)} 异常表={len(s2_data)} 报表清单={len(s3_data)} 积分表={len(s4_data)}({len(personnel)}人)")
