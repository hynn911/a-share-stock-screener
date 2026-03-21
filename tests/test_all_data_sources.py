"""
测试所有数据源
"""
import requests

def test_eastmoney():
    """测试东方财富直连"""
    print("测试 1: 东方财富 API...")
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 5,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
            "fields": "f12,f14"
        }
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        stocks = data.get("data", {}).get("diff", [])
        print(f"  [PASS] 东方财富 API 可用")
        print(f"  获取到 {len(stocks)} 只股票:")
        for s in stocks:
            print(f"    - {s['f12']}: {s['f14']}")
        return True
    except Exception as e:
        print(f"  [FAIL] 东方财富 API 失败：{e}")
        return False

def test_sina():
    """测试新浪财经"""
    print("\n测试 2: 新浪财经 API...")
    try:
        url = "http://hq.sinajs.cn/list=sh600519"
        resp = requests.get(url, timeout=10)
        content = resp.text
        if "贵州茅台" in content:
            print(f"  [PASS] 新浪财经 API 可用")
            print(f"  数据：{content[:80]}...")
            return True
        else:
            print(f"  [WARN] 返回数据异常")
            return False
    except Exception as e:
        print(f"  [FAIL] 新浪财经 API 失败：{e}")
        return False

def test_akshare():
    """测试 AkShare"""
    print("\n测试 3: AkShare...")
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is not None and len(df) > 0:
            print(f"  [PASS] AkShare 可用")
            print(f"  获取到 {len(df)} 只股票")
            print(f"  示例：{df.iloc[0]['代码']} - {df.iloc[0]['名称']}")
            return True
        else:
            print(f"  [WARN] 返回数据为空")
            return False
    except Exception as e:
        print(f"  [FAIL] AkShare 失败：{e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("数据源可用性测试")
    print("=" * 60)

    eastmoney_ok = test_eastmoney()
    sina_ok = test_sina()
    akshare_ok = test_akshare()

    print("\n" + "=" * 60)
    print("测试结果总结:")
    print(f"  - 东方财富：{'PASS ✓' if eastmoney_ok else 'FAIL ×'}")
    print(f"  - 新浪财经：{'PASS ✓' if sina_ok else 'FAIL ×'}")
    print(f"  - AkShare:   {'PASS ✓' if akshare_ok else 'FAIL ×'}")
    print("=" * 60)

    if eastmoney_ok:
        print("\n推荐方案：使用东方财富 API 作为主数据源（无需 token）")
    elif akshare_ok:
        print("\n推荐方案：使用 AkShare + 本地缓存")
