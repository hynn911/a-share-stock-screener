"""
测试 Tushare API - 详细诊断
"""
from dotenv import load_dotenv
import os

load_dotenv()

import tushare as ts

token = os.getenv("TUSHARE_TOKEN")
print(f"Token: {token[:20]}...{token[-10:]}")
print(f"Token 长度：{len(token)}")

# 设置 token
ts.set_token(token)
pro = ts.pro_api()

# 获取用户信息
print("\n尝试获取用户信息...")
try:
    # 尝试调用一个基础接口
    df = pro.user()
    print("用户信息接口调用成功")
    print(df)
except Exception as e:
    print(f"用户信息接口失败：{e}")

# 尝试交易日历接口（最基础的接口）
print("\n尝试获取交易日历...")
try:
    df = pro.trade_cal(
        exchange='SSE',
        start_date='20240101',
        end_date='20240107',
        fields='calendar_date,is_open'
    )
    print(f"交易日历接口成功：{len(df)} 条记录")
    print(df.head())
except Exception as e:
    print(f"交易日历接口失败：{e}")

# 尝试获取股票列表
print("\n尝试获取股票列表...")
try:
    df = pro.stock_basic(
        exchange='',
        list_status='L',
        fields='ts_code,symbol,name,industry,list_date',
        limit=10
    )
    print(f"股票列表接口成功：{len(df)} 条记录")
    print(df)
except Exception as e:
    print(f"股票列表接口失败：{e}")
