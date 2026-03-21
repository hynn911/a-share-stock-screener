"""
Tushare 配置和权限测试

Tushare 积分规则：
https://tushare.pro/document/1?doc_id=290

积分数 | 可访问接口
-------|----------
120    | 股票非复权日线行情 (daily 接口)
2000+  | stock_basic 等基础接口
5000+  | 更多特色数据
"""
from dotenv import load_dotenv
import os
import sys

# 设置 UTF-8 编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()

def test_tushare():
    """测试 Tushare 配置和权限"""
    import tushare as ts

    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        print("[FAIL] TUSHARE_TOKEN 未配置")
        return

    print(f"Token: {token[:20]}...{token[-10:]}")
    ts.set_token(token)
    pro = ts.pro_api()

    # 测试 1: daily 接口（120 积分即可）
    print("\n[测试 1] daily 接口（120 积分）...")
    try:
        df = pro.daily(ts_code='600519.SH', start_date='20240101', end_date='20240105')
        if df is not None and len(df) > 0:
            print(f"  [PASS] 获取到 {len(df)} 条日线数据")
            print(f"    示例：{df.iloc[0]['ts_code']} 收盘价 {df.iloc[0]['close']}")
        else:
            print(f"  [FAIL] 返回空数据")
    except Exception as e:
        print(f"  [FAIL] {e}")

    # 测试 2: stock_basic 接口（需要 2000+ 积分）
    print("\n[测试 2] stock_basic 接口（需要 2000+ 积分）...")
    try:
        df = pro.stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,industry',
            limit=5
        )
        if df is not None and len(df) > 0:
            print(f"  [PASS] 获取到 {len(df)} 只股票")
            print(f"    示例：{df.iloc[0]['ts_code']} - {df.iloc[0]['name']}")
        else:
            print(f"  [FAIL] 返回空数据")
    except Exception as e:
        error_msg = str(e)
        if "没有接口访问权限" in error_msg or "40203" in error_msg:
            print(f"  [FAIL] 权限不足（需要 2000+ 积分）")
            print(f"    错误码：40203")
        elif "每小时限制" in error_msg:
            print(f"  [WARN] 频率限制（每小时 1 次），请稍后再试")
        else:
            print(f"  [FAIL] {e}")

    # 测试 3: trade_cal 接口
    print("\n[测试 3] trade_cal 接口（交易日历）...")
    try:
        df = pro.trade_cal(
            exchange='SSE',
            start_date='20240101',
            end_date='20240107',
            fields='calendar_date,is_open'
        )
        if df is not None and len(df) > 0:
            print(f"  [PASS] 获取到 {len(df)} 条交易日历")
        else:
            print(f"  [FAIL] 返回空数据")
    except Exception as e:
        error_msg = str(e)
        if "没有接口访问权限" in error_msg or "40203" in error_msg:
            print(f"  [FAIL] 权限不足")
        else:
            print(f"  [FAIL] {e}")

    print("\n" + "=" * 60)
    print("积分说明:")
    print("  - 120 积分：只能访问 daily 接口（日线行情）")
    print("  - 2000+ 积分：可访问 stock_basic 等基础接口")
    print("  - 5000+ 积分：更多特色数据权限")
    print("\n升级积分：https://tushare.pro/user/new")
    print("=" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("Tushare 配置和权限测试")
    print("=" * 60)
    test_tushare()
