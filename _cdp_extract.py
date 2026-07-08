import asyncio, json, websockets

WS_URL = "ws://localhost:9222/devtools/page/A8DB070D3030F887FB229B5FEB52056E"
FEISHU_URL = "https://g0v8bkvkldw.feishu.cn/wiki/PZJLw8SF5igYbEkAba6cq3CznMh"
SHEETS = [["\u81ea\u8bc4\u8868", 0, 2, 12, 80], ["\u5dee\u8ddd\u8868", 1, 2, 12, 80], ["\u5f02\u5e38\u8868", 2, 2, 12, 80], ["\u62a5\u8868\u6e05\u5355", 3, 1, 8, 40], ["\u79ef\u5206\u8868", 4, 1, 6, 25]]

CLICK_TABS_JS = '''(function() {
  var tabs = document.querySelectorAll('[class*="sheet"]');
  // Find the sheet tab bar and click each tab
  var sheetTabs = document.querySelectorAll('sectionheader [class*="clickable"], sectionheader [onclick]');
  var clicked = [];
  // Alternative: find by role or by content
  var all = document.querySelectorAll('[cursor\\:pointer]');
  return "found " + all.length;
})()'''

async def extract():
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({"id":1,"method":"Page.navigate","params":{"url":FEISHU_URL}}))
        await asyncio.wait_for(ws.recv(), timeout=15)
        await asyncio.sleep(8)
        
        result = {}
        
        for name, idx, start, cols, maxr in SHEETS:
            # Switch sheet via API
            sw = "spread.setActiveSheetIndex(" + str(idx) + ");"
            await ws.send(json.dumps({"id":10+idx,"method":"Runtime.evaluate","params":{"expression":sw,"returnByValue":True}}))
            await asyncio.wait_for(ws.recv(), timeout=10)
            await asyncio.sleep(3)
            
            # Extract
            js = '''(function() {
var s = spread.getActiveSheet();
var d = [];
for (var r = 0; r < Math.min(s.getRowCount(), ''' + str(maxr) + '''); r++) {
var row = [], has = false;
for (var c = 0; c < Math.min(s.getColumnCount(), ''' + str(cols) + '''); c++) {
var v = s.getValue(r, c);
var val = (v !== null && v !== undefined && v !== '') ? String(v) : '';
row.push(val);
if (val) has = true;
}
if (has) d.push({r:r, d:row});
}
return JSON.stringify(d);
})()'''
            await ws.send(json.dumps({"id":20+idx,"method":"Runtime.evaluate","params":{"expression":js,"returnByValue":True}}))
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=15)
                    d = json.loads(msg)
                    if d.get("id") == 20+idx:
                        val = d.get("result", {}).get("result", {}).get("value")
                        if val:
                            result[name] = val
                        break
            except asyncio.TimeoutError:
                pass
        
        print("OK:", json.dumps({k: len(json.loads(v) if isinstance(v,str) else v) for k,v in result.items()}))

asyncio.run(extract())
