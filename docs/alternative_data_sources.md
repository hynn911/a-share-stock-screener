# AkShare 备选数据源方案

## 问题现状

AkShare 依赖的第三方数据源（东方财富、新浪等）经常出现连接超时或无响应问题：
- `RemoteDisconnected: Remote end closed connection without response`
- `Connection aborted`
- HTTP 403 Forbidden

## 解决方案

### 方案 1: 数据缓存（已实现，推荐）

**优点**:
- 不依赖外部 API
- 响应速度快
- 适合离线环境

**实现**:
```python
# 使用本地缓存
from core.data_cache import StockDataCache

cache = StockDataCache()

# 获取缓存的股票列表（7 天内有效）
stocks = cache.get_cached_stock_list(max_age_days=7)

# 保存股票列表到缓存
cache.save_stock_list(stock_data)
```

**使用方法**:
```bash
# 默认使用缓存（7 天内数据）
python tasks/update_stock_list.py

# 强制刷新，不使用缓存
python tasks/update_stock_list.py --force --no-cache

# 不使用缓存
python tasks/update_stock_list.py --no-cache
```

### 方案 2: Tushare（推荐作为主数据源）

**优点**:
- 数据稳定可靠
- 数据质量高
- 覆盖全面（股票、基金、期货、期权）

**缺点**:
- 需要注册获取 token
- 免费版有积分限制

**配置步骤**:

1. 注册账号：[https://tushare.pro/](https://tushare.pro/)
2. 获取 Token：个人中心 -> 接口 Token
3. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```
4. 编辑 `.env` 文件，填入 Token：
   ```ini
   TUSHARE_TOKEN=your_token_here
   ```

**注意**: 不要将 `.env` 文件提交到 Git！已使用 `.gitignore` 排除。

**使用示例**:

```python
import tushare as ts

ts.set_token("your_token")
pro = ts.pro_api()

# 获取股票列表
df = pro.stock_basic(
    exchange='',      # 交易所：SHE 上交所/SZ 深交所/B 北交所
    list_status='L',  # L 上市/D 退市/P 暂停上市
    fields='ts_code,symbol,name,industry,list_date'
)

# 获取日线数据
df = pro.daily(ts_code='600519.SH', start_date='20240101', end_date='20240131')

# 获取资金流向
df = pro.moneyflow(ts_code='600519.SH', start_date='20240101', end_date='20240131')
```

### 方案 3: 东方财富 API 直连

**优点**:
- 不需要第三方库
- 数据实时

**缺点**:
- 接口不稳定
- 需要处理反爬

**使用示例**:
```python
import requests

url = "https://push2.eastmoney.com/api/qt/clist/get"
params = {
    "pn": 1,
    "pz": 10000,
    "po": 1,
    "np": 1,
    "fltt": 2,
    "invt": 2,
    "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
    "fields": "f12,f14,f141,f149"  # 代码、名称、行业、概念
}

resp = requests.get(url, params=params)
data = resp.json()
stocks = data["data"]["diff"]
```

### 方案 4: 新浪财经 API

**优点**:
- 老牌数据源
- 实时行情

**缺点**:
- 数据格式不统一
- 需要解析特殊格式

**使用示例**:
```python
import requests

# 获取实时行情
url = "http://hq.sinajs.cn/list=sh600519"
resp = requests.get(url)
# 返回格式：var hq_str_sh600519="贵州茅台，1680.00,1680.00,..."

# 获取日线数据
url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
params = {
    "symbol": "sh600519",
    "scale": "day",
    "datalen": "1000"
}
resp = requests.get(url, params=params)
```

### 方案 5: Yahoo Finance (yfinance)

**优点**:
- 完全免费
- 国际股票覆盖好

**缺点**:
- A 股覆盖有限
- 数据延迟

**使用示例**:
```python
import yfinance as yf

# A 股代码格式：600519.SS (上交所), 000001.SZ (深交所)
stock = yf.Ticker("600519.SS")

# 获取历史数据
df = stock.history(period="1y")

# 获取公司信息
info = stock.info
```

## 推荐配置

### 最佳实践

1. **本地缓存为主**：日常使用缓存数据，减少 API 调用
2. **Tushare 为辅**：配置 Tushare token 作为主数据源
3. **AkShare/东财备用**：当 Tushare 不可用时切换

### 配置步骤

**1. 复制环境变量模板**

```bash
cp .env.example .env
```

**2. 编辑 `.env` 文件**

```ini
# 填入你的 Tushare Token（从 https://tushare.pro/ 获取）
TUSHARE_TOKEN=your_token_here

# 离线模式（可选）
STOCK_APP_OFFLINE_MODE=0
```

**3. 验证配置**

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('TUSHARE_TOKEN:', os.getenv('TUSHARE_TOKEN', '未设置'))"
```

### 数据库配置

```ini
DATABASE_URL=sqlite:///data/stock.db
```

## 离线模式

当网络不可用时，可以启用离线模式：

```bash
# 设置环境变量
export STOCK_APP_OFFLINE_MODE=1  # Linux/Mac
$env:STOCK_APP_OFFLINE_MODE = "1"  # Windows PowerShell

# 或者在代码中设置
from core.data_cache import set_offline_mode
set_offline_mode(True)
```

## 数据更新策略

| 数据类型 | 更新频率 | 缓存有效期 | 建议 |
|---------|---------|-----------|------|
| 股票列表 | 每周 | 7 天 | 使用缓存 + 每周刷新 |
| 日线数据 | 每日 | 1 天 | 盘后更新 |
| 资金流向 | 每日 | 1 天 | 盘中/盘后更新 |
| 股东户数 | 每月 | 30 天 | 财报季后更新 |
| 新闻资讯 | 实时 | 1 小时 | 按需获取 |

## 故障排查

### 检查网络连接

```bash
python tests/test_data_sources.py
```

### 查看缓存状态

```python
from core.data_cache import StockDataCache

cache = StockDataCache()
info = cache.get_cache_info()
print(f"缓存目录：{info['cache_dir']}")
print(f"总大小：{info['total_size_mb']:.2f} MB")
```

### 清空缓存

```python
cache.clear_cache()
```

## 总结

| 方案 | 稳定性 | 数据质量 | 成本 | 推荐度 |
|-----|-------|---------|-----|-------|
| 本地缓存 | ★★★★★ | ★★★☆☆ | 免费 | ★★★★☆ |
| Tushare | ★★★★★ | ★★★★★ | 免费/付费 | ★★★★★ |
| 东方财富直连 | ★★★☆☆ | ★★★★☆ | 免费 | ★★★☆☆ |
| AkShare | ★★☆☆☆ | ★★★★☆ | 免费 | ★★☆☆☆ |
| 新浪财经 | ★★★☆☆ | ★★★☆☆ | 免费 | ★★☆☆☆ |
| Yahoo Finance | ★★★★☆ | ★★☆☆☆ (A 股) | 免费 | ★★☆☆☆ |

**最佳实践**: 以本地缓存为基础，配置 Tushare 作为主数据源，AkShare/东财作为备用。
