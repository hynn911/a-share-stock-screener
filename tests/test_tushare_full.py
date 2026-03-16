"""
Tushare 权限和积分查询
"""
from dotenv import load_dotenv
import os
import tushare as ts

load_dotenv()

token = os.getenv("TUSHARE_TOKEN")
print(f"Token: {token}")

ts.set_token(token)
pro = ts.pro_api()

# 1. 测试最简单的接口 - 获取当前交易日
print("\n=== 测试基础接口 ===")

interfaces_to_test = [
    ('trade_cal', {'exchange': 'SSE', 'start_date': '20240101', 'end_date': '20240102', 'fields': 'calendar_date'}),
    ('stock_basic', {'exchange': '', 'list_status': 'L', 'fields': 'ts_code,symbol,name', 'limit': 5}),
    ('daily', {'ts_code': '600519.SH', 'start_date': '20240101', 'end_date': '20240105'}),
    ('moneyflow', {'ts_code': '600519.SH', 'start_date': '20240101', 'end_date': '20240105'}),
]

for name, params in interfaces_to_test:
    print(f"\n测试接口：{name}")
    try:
        func = getattr(pro, name)
        df = func(**params)
        print(f"  ✓ 成功！获取到 {len(df)} 条记录")
        if len(df) > 0:
            print(f"  示例：{df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"  × 失败：{e}")

# 2. 检查用户积分（如果有这个接口）
print("\n=== 尝试获取用户信息 ===")
try:
    # 尝试调用 user 接口
    df = pro.user()
    print(f"用户信息：{df}")
except Exception as e:
    print(f"用户信息接口不可用：{e}")

print("\n=== 建议 ===")
print("1. 访问 https://tushare.pro/user/new 查看当前积分")
print("2. 基础接口需要 120 积分")
print("3. 可以通过每日签到或充值获取积分")
