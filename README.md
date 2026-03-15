# A 股高价值股票发掘系统

> 基于多维度分析的智能股票推荐系统 - 仅供个人学习使用，不构成投资建议

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 功能特性

| 模块 | 功能描述 |
| :--- | :--- |
| 🎯 **智能荐股** | 五维度综合评分模型，推荐高价值股票 |
| 🔥 **热点看板** | 基于社区热词和个股热度排行，发现市场热点 |
| 💰 **资金监控** | 实时监测主力资金流向，连续流入天数统计 |
| 📊 **技术指标** | MA、MACD、RSI、KDJ、布林带等技术指标分析 |
| 📰 **新闻情绪** | 个股新闻聚合，情绪分析评分 |
| 📈 **持仓管理** | 持仓股票实时监控，止盈止损信号提醒 |
| 👥 **股东户数** | 筹码集中度分析，股东户数变化趋势 |
| 🏭 **板块分析** | 行业板块热度排行，概念板块资金流 |
| 📉 **大宗商品** | 大宗商品价格监控 |

### 智能荐股评分模型

| 维度 | 权重 | 评分说明 |
| :--- | :--- | :--- |
| 💰 资金流 | 25% | 连续流入天数 (40 分) + 净流入金额 (60 分) |
| 📈 技术指标 | 25% | MA 信号 + MACD 信号 + RSI 信号 |
| 👥 股东户数 | 20% | 筹码集中度变化趋势 |
| 📰 新闻热度 | 15% | 新闻情绪分 + 数量奖励 |
| 📊 价格动量 | 15% | 价格相对 MA20 位置 + 20 日涨幅 |

**综合评分 = Σ(各维度分数 × 对应权重)**

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Windows / Linux / macOS

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd stock

# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 初始化数据库

```bash
# 首次运行会自动创建数据库
python main.py
```

### 4. 启动应用

```bash
# 方式一：直接启动（推荐）
streamlit run ui/app.py

# 方式二：使用清理脚本（解决缓存问题）
# Windows:
scripts\clean_and_restart.bat
# Linux/macOS:
bash scripts/clean_and_restart.sh
```

### 5. 访问界面

浏览器打开：<http://localhost:8501>

## 📁 项目结构

<!-- markdownlint-disable MD040 -->
```text
stock/
├── core/                       # 核心业务逻辑模块
│   ├── database.py            # 数据库连接和 Session 管理
│   ├── models.py              # SQLAlchemy 数据模型
│   ├── data_fetcher.py        # 数据抓取 (AkShare)
│   ├── indicator.py           # 技术指标计算
│   ├── capital.py             # 资金流分析
│   ├── hot_words.py           # 热词和板块分析
│   ├── position.py            # 持仓管理
│   ├── shareholder.py         # 股东户数分析
│   ├── stock_scorer.py        # 股票综合评分
│   ├── commodity.py           # 大宗商品监控
│   ├── backtester.py          # 回测模块
│   └── weight_optimizer.py    # 权重优化器
├── ui/
│   └── app.py                 # Streamlit 前端界面
├── tasks/                     # 定时任务和批处理脚本
│   ├── update_stock_list.py   # 更新股票列表（行业/概念）
│   ├── diagnose.py            # 系统诊断
│   └── diagnose_industry.py   # 行业数据诊断
├── scripts/                   # 工具脚本
│   ├── clean_and_restart.sh   # Linux/Mac 清理缓存重启
│   ├── clean_and_restart.bat  # Windows 清理缓存重启
│   └── init_data.py           # 初始化数据
├── data/                      # 本地数据存储（SQLite）
├── docs/                      # 项目文档
├── tests/                     # 测试用例
├── main.py                    # 主入口
├── config.py                  # 配置文件
└── requirements.txt           # Python 依赖
```
<!-- markdownlint-enable MD040 -->

## 📊 数据来源

| 数据类型 | 来源 | 说明 |
| :--- | :--- | :--- |
| 股票列表/行情 | [AkShare](https://akshare.akfamily.xyz/) - 东方财富 | 免费开源 |
| 资金流向 | 东方财富 | 主力净流入、超大单、大单 |
| 技术指标 | 计算得出 | MA、MACD、RSI、KDJ、布林带 |
| 新闻数据 | 东方财富 | 个股新闻、情绪分析 |
| 热度排行 | 雪球、东方财富 | 个股热度、板块热度 |
| 股东户数 | 东方财富 | 定期报告数据 |

> **AkShare 是完全免费的开源 Python 库，不需要注册或购买任何服务**

## 🔧 配置说明

### 数据库配置

默认使用 SQLite 本地数据库，数据存储位置：`data/stock.db`

如需使用 PostgreSQL，修改 `config.py`:

```python
# SQLite (默认)
DATABASE_URL = "sqlite:///data/stock.db"

# PostgreSQL
DATABASE_URL = "postgresql://user:password@localhost:5432/stock_db"
```

### 数据更新

建议每日收盘后更新数据：

```bash
# 更新股票列表（包含行业/概念）
python tasks/update_stock_list.py

# 更新新闻
python scripts/update_news.py

# 更新大宗商品数据
python scripts/refresh_commodities.py
```

## 📝 常见命令

```bash
# 清理缓存并重启
scripts/clean_and_restart.bat  # Windows
bash scripts/clean_and_restart.sh  # Linux/macOS

# 运行诊断
python tasks/diagnose.py
python tasks/diagnose_industry.py

# 更新行业数据
python tasks/update_stock_list.py

# 查看测试 coverage
pytest tests/ --cov=core --cov-report=html
```

## ⚠️ 注意事项

1. **首次使用**需要先获取股票列表和历史数据
2. **数据缓存**：Streamlit 会缓存模块，修改代码后需要清理缓存重启
3. **API 限流**：AkShare 偶尔会有限流，建议设置定时任务在非交易时间更新
4. **行业数据**：如显示为空，点击侧边栏"刷新行业/板块数据"按钮

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [AkShare](https://akshare.akfamily.xyz/) - 开源财经数据接口库
- [Streamlit](https://streamlit.io/) - 快速数据应用框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包

## 📧 反馈与支持

如有问题或建议，请提交 Issue 或 Pull Request。

---

**免责声明**：本项目仅供个人学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
