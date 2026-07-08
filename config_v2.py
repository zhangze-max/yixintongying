# 一心通营数据配置 v2
# 旧文档 token: VNagweuz3iTCWFk0Y3wc1UL3nBf (已废弃)
# 新文档链接: https://g0v8bkvkldw.feishu.cn/wiki/PZJLw8SF5igYbEkAba6cq3CznMh

WIKI_TOKEN = 'PZJLw8SF5igYbEkAba6cq3CznMh'
WIKI_URL = f'https://g0v8bkvkldw.feishu.cn/wiki/{WIKI_TOKEN}'

SHEETS = {
    '自评表（数据）': {
        'index': 0,
        'title_row': 0,
        'header_row': 1,
        'data_start': 2,
        'headers': ['差异ID','项目名称','填报人','报告名称','来源','做什么用','报告频率','数据来源','数据质量问题','差异等级','责任部门','责任人'],
    },
    '差距表（功能）': {
        'index': 1,
        'title_row': 0,
        'header_row': 1,
        'data_start': 2,
        'headers': ['序号','所属项目','提交人','所属场景','名称','频率','所属系统','软件功能缺陷问题','问题严重等级','问题详细描述','整改措施','责任部门/责任人'],
    },
    '异常表（情报）': {
        'index': 2,
        'title_row': 0,
        'header_row': 1,
        'data_start': 2,
        'headers': ['序号','项目名称','上报人','项目阶段','异常类型','异常描述','异常发生时间','异常发现时间','责任部门','责任人','异常等级','处理状态'],
    },
    '报表清单': {
        'index': 3,
        'title_row': None,
        'header_row': 0,
        'data_start': 1,
        'headers': ['所属园区','报告名称','频率','来源'],
    },
    '积分表': {
        'index': 4,
        'header_row': 0,
        'data_start': 1,
        'headers': ['姓名','差距表积分','异常表积分','自评表积分','总积分'],
    },
}

# 积分表人员列表（17人）
PERSONNEL = ['欧阳星','刘庆富','覃丽程','彭丹','黄立泰','黄雨嫣','雷丽怡','崔洪醒','林泽坤','冯小容','刘馨语','张泽稷','钟瑜均','孙荣杰','邱惠新','刘云丹','李荣拨']
