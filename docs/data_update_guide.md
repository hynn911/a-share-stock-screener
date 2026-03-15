# 数据更新指南

## 概述

本系统需要定期更新以下数据：
- **日线数据**：每日收盘后更新（15:30 后）
- **资金流数据**：每日收盘后更新
- **股东户数**：每季度更新（财报披露后）
- **新闻数据**：每日更新
- **市场热词**：每周更新

## 自动更新（推荐）

### Windows 系统

1. **设置定时任务**（管理员权限运行）：
```bash
cd e:\work\cc\stock\scripts
setup_windows_task.bat
```

定时任务配置：
- 任务名称：`StockDataUpdate`
- 执行时间：每周一至周五 16:00
- 执行脚本：`scripts/auto_update.py`
- 日志文件：`scripts/auto_update.log`

2. **查看任务状态**：
```bash
schtasks /query /tn "StockDataUpdate"
```

3. **查看更新日志**：
```bash
type scripts\auto_update.log
```

4. **删除定时任务**：
```bash
schtasks /delete /tn "StockDataUpdate" /f
```

### Linux/Mac 系统

配置 cron 定时任务：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周一至周五 16:00 执行）
30 16 * * 1-5 cd /path/to/stock && /usr/bin/python3 scripts/auto_update.py >> scripts/auto_update.log 2>&1
```

## 手动更新

### 更新所有数据

```bash
# 更新所有股票数据
python scripts/auto_update.py

# 更新前 100 只股票（测试用）
python scripts/auto_update.py 100
```

### 初始化全部数据

如果是首次运行或需要重新初始化：

```bash
# 初始化前 100 只股票（快速测试）
python scripts/init_all_data.py 100

# 初始化所有股票（完整数据）
python scripts/init_all_data.py
```

### 单独更新某类数据

```bash
# 仅更新新闻
python scripts/update_news.py 20

# 优化数据库索引
python scripts/optimize_indexes.py
```

## 数据新鲜度检查

在 Streamlit 应用首页会显示数据新鲜度状态：

- 如果数据过期，会显示警告提示
- 可点击"数据更新说明"查看更新方法

## 更新日志

日志文件位置：`scripts/auto_update.log`

日志内容包括：
- 更新时间
- 各类数据更新条数
- 错误信息（如有）

## 注意事项

1. **API 限流**：AkShare API 有频率限制，批量更新时已自动添加延时
2. **磁盘空间**：完整数据约需 1-2GB 磁盘空间
3. **更新时长**：全量更新 5000+ 股票约需 30-60 分钟
4. **网络环境**：需要稳定的网络环境访问 A 股数据源

## 故障排查

### 更新失败

检查日志文件，常见错误：
- 网络连接问题：检查网络后重试
- API 限流：等待一段时间后重试
- 数据库锁定：关闭其他访问数据库的程序

### 数据不完整

1. 检查股票列表是否完整：
```bash
python -c "from core.database import SessionLocal; from core.models import Stock; db=SessionLocal(); print(db.query(Stock).count())"
```

2. 重新获取股票列表：
```bash
python -c "from core.data_fetcher import DataFetcher; f=DataFetcher(); f.fetch_stock_list(); f.close()"
```

### 内存不足

减少单次更新的股票数量：
```bash
python scripts/auto_update.py 500
```

分批次运行直到完成全部更新。

## 最佳实践

1. **每日更新**：设置定时任务在交易日 16:00 自动更新
2. **周末检查**：每周末检查数据完整性
3. **日志监控**：定期检查更新日志，发现异常及时处理
4. **数据备份**：定期备份数据库文件（`data/stocks.db`）

## 数据库备份

```bash
# Windows
copy data\stocks.db data\stocks_backup_%date:~0,10%.db

# Linux/Mac
cp data/stocks.db data/stocks_backup_$(date +%Y%m%d).db
```
