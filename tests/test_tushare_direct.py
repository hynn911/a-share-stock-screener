"""
直接测试 Tushare API
"""
import requests
import json

# 从 .env 读取 token
from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv("TUSHARE_TOKEN")

print(f"Token: {token[:20]}...{token[-10:]}")
print(f"Token 长度：{len(token)}")

# 直接调用 HTTP API
url = "http://api.tushare.pro"
headers = {
    "Content-Type": "application/json"
}

# 测试 1: 获取交易日历
data = {
    "api_name": "trade_cal",
    "token": token,
    "params": {
        "exchange": "SSE",
        "start_date": "20240101",
        "end_date": "20240102",
        "fields": "calendar_date"
    }
}

print("\n=== 测试交易日历接口 ===")
resp = requests.post(url, headers=headers, data=json.dumps(data))
result = resp.json()
print(f"响应状态：{result.get('code', 'N/A')}")
print(f"响应消息：{result.get('msg', 'N/A')}")
if result.get('code') == 0:
    print("✓ 接口调用成功！")
    if result.get('data') and result['data'].get('items'):
        print(f"数据条数：{len(result['data']['items'])}")
else:
    print("× 接口调用失败")
