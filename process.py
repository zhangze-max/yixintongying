import json
from datetime import datetime

with open('/Users/qkl/.hermes/projects/yixintongying/raw_data.json', 'r') as f:
    raw = json.load(f)

# s0: headers + data from row index 2
z0_headers = ["差异ID","项目名称","填报人","报告名称","来源","做什么用","报告频率","数据来源","数据质量问题","差异等级"]
z0_data = raw["s0"]["data"][2:]

# s1: headers + data from row index 2
z1_headers = ["序号","所属项目","提交人","名称","频率","所属系统","软件功能缺陷问题"]
z1_data = raw["s1"]["data"][2:]

# s2: headers + data from row index 2
z2_headers = ["序号","项目名称","上报人","项目阶段","异常类型","异常描述","异常发生时间","异常发现时间"]
z2_data = raw["s2"]["data"][2:]

# s3: empty
z3_headers = ["所属园区","报告名称","频率","来源"]
z3_data = []

# s4: personnel scoreboard
z4_headers = raw["s4"]["data"][0][:5]
z4_data = raw["s4"]["data"][1:]
z4_personnel = [row[0] for row in z4_data if row[0]]

def rows_to_dicts(headers, rows):
    return [{headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))} for row in rows]

output = {
    "timestamp": datetime.now().isoformat(),
    "sheets": {
        "自评表": {"headers": z0_headers, "rows": len(z0_data), "data": rows_to_dicts(z0_headers, z0_data)},
        "差距表": {"headers": z1_headers, "rows": len(z1_data), "data": rows_to_dicts(z1_headers, z1_data)},
        "异常表": {"headers": z2_headers, "rows": len(z2_data), "data": rows_to_dicts(z2_headers, z2_data)},
        "报表清单": {"headers": z3_headers, "rows": 0, "data": []},
        "积分表": {"headers": z4_headers, "rows": len(z4_data), "personnel": z4_personnel, "data": rows_to_dicts(z4_headers, z4_data)}
    }
}

with open('/Users/qkl/.hermes/projects/yixintongying/data.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("data.json written successfully")
print(f"自评表: {len(z0_data)} rows")
print(f"差距表: {len(z1_data)} rows")
print(f"异常表: {len(z2_data)} rows")
print(f"报表清单: {len(z3_data)} rows (empty)")
print(f"积分表: {len(z4_data)} rows, {len(z4_personnel)} personnel")
