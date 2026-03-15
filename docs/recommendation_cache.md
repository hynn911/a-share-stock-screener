# 智能荐股预计算功能

## 功能说明

将智能荐股的计算结果盘后预计算并存入数据库，查询时直接读取预计算结果，将查询时间从 18-22 秒降低到秒级。

## 数据库迁移

首次使用需要创建推荐结果表：

```bash
cd stock
python migrate_add_recommendations.py
```

## 手动计算推荐结果

```bash
cd stock
python tasks/calculate_recommendations.py
```

选择：
1. 计算最新交易日
2. 计算指定日期

## 定时任务配置

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 名称：股票推荐计算
4. 触发器：每个交易日 16:00（收盘后）
5. 操作：启动程序
   - 程序：`python.exe`
   - 参数：`tasks/scheduled_task.py`
   - 起始目录：`stock`

### Linux Cron

```bash
# 编辑 crontab
crontab -e

# 添加（每个交易日 16:00 执行）
0 16 * * 1-5 cd /path/to/stock && python tasks/scheduled_task.py
```

## 使用说明

### UI 界面

1. 打开 Streamlit 应用
2. 进入"智能荐股"页面
3. 勾选"使用预计算结果"
4. 点击"开始智能选股"

**查询速度：1-2 秒** ⚡

### 实时计算（备用）

如果未勾选"使用预计算结果"，系统会实时计算（18-22 秒）

## 数据表结构

```sql
CREATE TABLE stock_recommendations (
    id INTEGER PRIMARY KEY,
    trade_date DATE NOT NULL,           -- 交易日期
    stock_code VARCHAR(10) NOT NULL,    -- 股票代码
    stock_name VARCHAR(50) NOT NULL,    -- 股票名称
    total_score FLOAT NOT NULL,         -- 综合评分
    capital_score FLOAT,                -- 资金流评分
    technical_score FLOAT,              -- 技术评分
    holder_score FLOAT,                 -- 股东户数评分
    news_score FLOAT,                   -- 新闻评分
    momentum_score FLOAT,               -- 动量评分
    rank INTEGER,                       -- 排名
    created_at DATETIME                 -- 创建时间
);

-- 索引
CREATE INDEX idx_date_rank ON stock_recommendations(trade_date, rank);
CREATE INDEX idx_date_score ON stock_recommendations(trade_date, total_score);
CREATE INDEX idx_stock_code ON stock_recommendations(stock_code);
```

## 性能对比

| 场景 | 时间 | 说明 |
|------|------|------|
| 实时计算 | 18-22 秒 | 5469 只活跃股票 |
| 预计算查询 | 1-2 秒 | 直接读取数据库 |
| 盘后计算 | 13-15 秒 | 批量存储到数据库 |

## 注意事项

1. **计算时间**：建议每天收盘后（15:30 以后）执行，确保当日数据已更新
2. **存储空间**：每天约 2000 条记录，每条约 200 字节，每年约 150MB
3. **数据清理**：可定期清理 3 个月前的数据
4. **节假日**：非交易日无需执行

## 清理旧数据（可选）

```python
from core.database import SessionLocal
from core.models import StockRecommendation
from datetime import datetime, timedelta

db = SessionLocal()
cutoff = datetime.now() - timedelta(days=90)

db.query(StockRecommendation).filter(
    StockRecommendation.trade_date < cutoff
).delete()

db.commit()
db.close()
```
