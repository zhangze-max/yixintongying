import json, datetime, re

with open("/Users/qkl/.hermes/projects/yixintongying/raw_data.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

s0_headers = ["差异ID","项目名称","填报人","报告名称","来源","做什么用","报告频率","数据来源","数据质量问题","差异等级"]
s1_headers = ["序号","所属项目","提交人","名称","频率","所属系统","软件功能缺陷问题"]
s2_headers = ["序号","项目名称","上报人","项目阶段","异常类型","异常描述","异常发生时间","异常发现时间"]
s3_headers = ["所属园区","报告名称","频率","来源"]
s4_orig_headers = ["姓名", "差距表积分", "异常表积分", "自评表积分", "总积分"]

def slice_rows(data, ncols, start_idx=2):
    result = []
    for row in data["data"][start_idx:]:
        result.append(row[:ncols])
    return result

sheets = {}

s0_rows = slice_rows(raw["s0"], len(s0_headers), 2)
sheets["自评表"] = {"headers": s0_headers, "rows": s0_rows}

s1_rows = slice_rows(raw["s1"], len(s1_headers), 2)
sheets["差距表"] = {"headers": s1_headers, "rows": s1_rows}

s2_rows = slice_rows(raw["s2"], len(s2_headers), 2)
sheets["异常表"] = {"headers": s2_headers, "rows": s2_rows}

sheets["报表清单"] = {"headers": s3_headers, "rows": []}

s4_data = raw["s4"]["data"]
personnel = [row[0].strip() for row in s4_data[1:] if row[0].strip()]
s4_rows = [row[:len(s4_orig_headers)] for row in s4_data[1:]]
sheets["积分表"] = {"headers": s4_orig_headers, "rows": s4_rows, "personnel": personnel}

output = {"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "sheets": sheets}

with open("/Users/qkl/.hermes/projects/yixintongying/data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("OK")
for name, sheet in sheets.items():
    extra = f", {len(sheet.get('personnel', []))} personnel" if name == "积分表" else ""
    print(f"  {name}: {len(sheet['rows'])} rows{extra}")
