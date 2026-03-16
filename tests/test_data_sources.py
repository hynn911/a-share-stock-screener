# 测试备用数据源
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("测试数据源连接")
print("=" * 60)

# 测试 1: 东方财富直连
print("\n[测试 1] 东方财富直连...")
try:
    import requests
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": 100,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
        "fields": "f12,f14,f141,f149"
    }
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    count = len(data.get("data", {}).get("diff", []))
    print(f"OK: 东方财富直连成功：获取到 {count} 只股票")
except Exception as e:
    print(f"FAIL: 东方财富直连失败：{e}")

# 测试 2: 新浪财经
print("\n[测试 2] 新浪财经...")
try:
    resp = requests.get("http://hq.sinajs.cn/list=sh600519", timeout=10)
    if resp.status_code == 200:
        print(f"OK: 新浪财经成功：{resp.text[:50]}...")
    else:
        print(f"FAIL: 新浪财经失败：状态码 {resp.status_code}")
except Exception as e:
    print(f"FAIL: 新浪财经失败：{e}")

# 测试 3: AkShare
print("\n[测试 3] AkShare...")
try:
    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    print(f"OK: AkShare 成功：获取到 {len(df)} 只股票")
except Exception as e:
    print(f"FAIL: AkShare 失败：{e}")

# 测试 4: Tushare (如果有 token)
print("\n[测试 4] Tushare...")
try:
    from core.data_fetcher import TUSHARE_TOKEN
    if TUSHARE_TOKEN:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name', limit=10)
        print(f"OK: Tushare 成功：获取到 {len(df)} 只股票")
    else:
        print("SKIP: Tushare 未配置 token（可选）")
except Exception as e:
    print(f"FAIL: Tushare 失败：{e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
