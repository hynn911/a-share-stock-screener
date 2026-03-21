"""
检查 .env 文件中的 token 是否有问题
"""
from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv("TUSHARE_TOKEN")

print(f"原始 token: [{token}]")
print(f"Token 长度：{len(token)}")
print(f"首尾空格检查：[{token[:10]}...{token[-10:]}]")

# 去除可能的空格
token_stripped = token.strip()
print(f"\n去除空格后：[{token_stripped}]")
print(f"去除空格后长度：{len(token_stripped)}")

# 检查是否有不可见字符
for i, c in enumerate(token):
    if ord(c) > 127 or ord(c) < 32:
        print(f"警告：位置 {i} 有特殊字符：{ord(c)}")

# 测试 tushare
import tushare as ts

print("\n使用去除空格的 token 测试...")
ts.set_token(token_stripped)
pro = ts.pro_api()

try:
    df = pro.trade_cal(
        exchange='SSE',
        start_date='20240101',
        end_date='20240107',
        fields='calendar_date,is_open'
    )
    print(f"成功！获取到 {len(df)} 条记录")
    print(df)
except Exception as e:
    print(f"失败：{e}")
