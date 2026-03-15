# A 股高价值股票发掘功能 - 完整开发计划

## 一、项目概述

### 1.1 产品定位
开发一款面向国内 A 股市场的智能选股软件，核心功能是通过多维度数据分析，自动发掘高价值股票，并提供买卖点建议。

### 1.2 第一阶段目标
实现高价值股票发掘的五大核心功能：
1. **市场热点检测** - 基于社区热词识别热点方向
2. **基本面技术指标** - 股票基本面和技术指标分析
3. **资金流入监控** - 检测连续资金流入的股票
4. **消息政策捕捉** - 自动抓取消息面和政策面信息
5. **持仓卖点建议** - 针对已买入股票提供卖出时机建议

---

## 二、技术架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户界面层                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  热点看板   │  │  股票筛选器  │  │  资金监控   │  │  消息中心   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     持仓管理与卖点建议                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API 服务层 (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ 热点 API    │  │ 选股 API    │  │ 资金 API    │  │ 消息 API    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    持仓 API | 卖点建议 API                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           业务逻辑层                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ 热词分析引擎 │  │ 指标计算器  │  │ 资金分析器  │  │ 消息分类器  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              卖点判断引擎 (止盈/止损/技术信号/资金流出)            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           数据采集层                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ 社区爬虫    │  │ 行情数据    │  │ 资金流向    │  │ 新闻聚合    │   │
│  │ (雪球/股吧)  │  │ (AkShare)   │  │ (东方财富)   │  │ (东方财富)   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           数据存储层                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │  PostgreSQL │  │    Redis    │  │  Elasticsearch                  │
│  │  (主数据库)  │  │   (缓存)    │  │   (全文搜索)                     │
│  └─────────────┘  └─────────────┘  └─────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **后端框架** | Python 3.11 + FastAPI | 异步支持、自动 API 文档、高性能 |
| **数据采集** | AkShare + 自定义爬虫 | 免费、数据源丰富、无需 API Key |
| **NLP 处理** | jieba + HanLP | 中文分词、关键词提取、情感分析 |
| **主数据库** | PostgreSQL + TimescaleDB | 时间序列数据优化、SQL 兼容性 |
| **缓存层** | Redis 7.x | 热点数据缓存、实时排行榜 |
| **搜索引擎** | Elasticsearch | 新闻全文搜索、热词聚合 |
| **任务调度** | Celery + Redis | 异步任务、定时数据采集 |
| **前端** | Vue 3 + Element Plus | 快速开发、组件丰富 |

---

## 三、功能模块详细设计

### 3.1 模块一：市场热点检测

#### 3.1.1 功能描述
从股票社区（雪球、东方财富股吧）自动提取热词，识别市场热点方向和板块。

#### 3.1.2 数据源
| 平台 | 数据类型 | 采集方式 |
|------|----------|----------|
| 雪球 | 股票讨论帖、评论 | AkShare `stock_hot_rank_em()` |
| 东方财富股吧 | 个股吧帖子、评论 | 爬虫 + AkShare |
| 新浪财经 | 股票新闻 | AkShare `stock_news_em()` |

#### 3.1.3 技术实现
```
数据采集 → 文本预处理 → 中文分词 → 关键词提取 → 热度计算 → 热点聚合
    │           │           │           │           │          │
    ▼           ▼           ▼           ▼           ▼          ▼
 雪球/股吧    清洗 HTML    jieba 分词   TF-IDF    时间衰减    板块映射
 新闻 API     去除停用词   自定义词典   TextRank   突发检测    热点排行
```

#### 3.1.4 核心算法
1. **TF-IDF 关键词提取** - 识别文档重要词汇
2. **TextRank** - 图排序算法提取关键词
3. **Kleinberg 突发检测** - 识别突然升温的词汇
4. **时间衰减加权** - 新内容权重更高

#### 3.1.5 输出结果
- 实时热词榜（Top 50）
- 热点板块映射（如"AI"→人工智能板块）
- 热点关联股票列表
- 热点趋势图（24 小时热度变化）

---

### 3.2 模块二：基本面技术指标

#### 3.2.1 功能描述
提供股票基本面分析和技术面分析，辅助判断股票价值。

#### 3.2.2 基本面指标
| 类别 | 指标 | 说明 |
|------|------|------|
| **估值指标** | PE(TTM)、PB、PS、PEG | 判断股票估值高低 |
| **盈利能力** | ROE、ROA、毛利率、净利率 | 判断公司盈利能力 |
| **成长能力** | 营收增长率、净利润增长率 | 判断公司成长性 |
| **财务健康** | 资产负债率、流动比率、速动比率 | 判断财务风险 |
| **股本结构** | 总股本、流通股本、股东人数 | 判断股本特征 |

#### 3.2.3 技术指标
| 类别 | 指标 | 说明 |
|------|------|------|
| **趋势指标** | MA5/10/20/60、MACD、ADX | 判断趋势方向 |
| **动能指标** | RSI、KDJ、CCI | 判断超买超卖 |
| **波动指标** | 布林带、ATR | 判断波动范围 |
| **量能指标** | OBV、量比、换手率 | 判断资金参与度 |

#### 3.2.4 技术实现
- **指标计算库**: TA-Lib (150+ 技术指标)
- **数据源**: AkShare 获取历史行情
- **缓存策略**: Redis 缓存计算结果，每日更新

#### 3.2.5 输出结果
- 个股基本面雷达图
- 技术指标信号（金叉/死叉、超买/超卖）
- 综合评分（0-100 分）

---

### 3.3 模块三：资金流入监控

#### 3.3.1 功能描述
监控股票资金流向，识别连续多日资金净流入的股票。

#### 3.3.2 数据源
| 数据类型 | 接口 | 说明 |
|----------|------|------|
| 个股资金流向 | `stock_individual_flow_in_em()` | 主力流入/流出 |
| 北向资金 | `stock_hsgt_north_net_flow_in_em()` | 沪深股通资金 |
| 板块资金流向 | `stock_sector_flow_em()` | 行业板块资金 |

#### 3.3.3 监控规则
```
筛选条件（可配置）:
├── 连续 N 日资金净流入 (默认 N=3)
├── 累计净流入金额 > X 万 (默认 1000 万)
├── 当日换手率 > Y% (默认 3%)
├── 股价位于 Z 日均线上方 (默认 20 日线)
└── 排除 ST、*ST 股票
```

#### 3.3.4 输出结果
- 连续流入股票池（按天数排序）
- 资金流入趋势图（5 日/10 日/20 日）
- 主力 vs 散户资金对比
- 北向资金持仓变化

---

### 3.4 模块四：消息政策捕捉

#### 3.4.1 功能描述
自动抓取和分类股票相关新闻，识别利好/利空消息。

#### 3.4.2 数据源
| 类型 | 来源 | 采集频率 |
|------|------|----------|
| 个股公告 | 巨潮资讯网 | 实时 |
| 财经新闻 | 东方财富、新浪财经 | 每 5 分钟 |
| 行业政策 | 政府网站、行业协会 | 每小时 |
| 宏观政策 | 央行、财政部、发改委 | 每小时 |

#### 3.4.3 消息分类
```
消息分类体系:
├── 公司层面
│   ├── 财报披露（利好/利空）
│   ├── 重大合同（利好）
│   ├── 高管变动（中性）
│   └── 并购重组（利好/利空）
├── 行业层面
│   ├── 产业政策（利好/利空）
│   ├── 行业数据（利好/利空）
│   └── 竞争格局变化（中性）
└── 宏观层面
    ├── 货币政策（利好/利空）
    ├── 财政政策（利好/利空）
    └── 监管政策（利好/利空）
```

#### 3.4.4 情感分析
- 使用 SnowNLP 进行中文情感分析
- 自定义金融情感词典
- 输出：利好/中性/利空 + 置信度

#### 3.4.5 输出结果
- 实时消息流（按时间/重要性排序）
- 个股消息聚合（近 7 日/30 日）
- 利好/利空统计
- 政策受益板块映射

---

### 3.5 模块五：持仓卖点建议（新增）

#### 3.5.1 功能描述
针对用户已买入的股票，提供多维度的卖出时机建议，帮助用户及时止盈止损。

#### 3.5.2 持仓管理

**持仓录入方式**:
```
1. 手动录入
   - 股票代码、买入价格、买入数量、买入日期

2. Excel 导入
   - 支持券商交割单导入

3. 模拟组合
   - 系统内建仓、调仓记录
```

**数据库设计**:
```sql
-- 持仓表
CREATE TABLE user_positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,                     -- 用户 ID（支持多用户）
    stock_code VARCHAR(10) NOT NULL,     -- 股票代码
    stock_name VARCHAR(50),              -- 股票名称
    buy_price DECIMAL(10,2) NOT NULL,    -- 买入均价
    quantity INTEGER NOT NULL,           -- 持仓数量
    buy_date DATE,                       -- 买入日期
    current_price DECIMAL(10,2),         -- 当前价（实时）
    profit_loss DECIMAL(10,4),           -- 盈亏比例（实时）
    profit_amount DECIMAL(15,2),         -- 盈亏金额（实时）
    status VARCHAR(20) DEFAULT 'holding',-- holding/sold
    sell_date DATE,                      -- 卖出日期
    sell_price DECIMAL(10,2),            -- 卖出均价
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 卖点信号记录表
CREATE TABLE sell_signals (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES user_positions(id),
    signal_type VARCHAR(20),             -- 信号类型
    signal_time TIMESTAMPTZ DEFAULT NOW(),
    trigger_price DECIMAL(10,2),         -- 触发价格
    description TEXT,                    -- 信号描述
    action_suggestion VARCHAR(50),       -- 建议操作
    priority VARCHAR(10)                 -- 优先级：HIGH/MEDIUM/LOW
);
```

---

#### 3.5.3 卖点判断维度

**五大维度综合判断**:

```
                        ┌─────────────────┐
                        │   持仓股票      │
                        └────────┬────────┘
                                 │
         ┌───────────┬───────────┼───────────┬───────────┐
         │           │           │           │           │
         ▼           ▼           ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ 止盈信号 │ │ 止损信号 │ │ 技术卖出 │ │ 资金流出 │ │ 利空消息 │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

#### 3.5.4 止盈信号（Take Profit）

| 止盈策略 | 触发条件 | 建议操作 |
|----------|----------|----------|
| **目标收益止盈** | 收益率达到预设目标（如 20%/30%/50%） | 分批卖出 |
| **移动止盈** | 从最高点回撤超过 N%（如 10%） | 清仓或减仓 |
| **估值止盈** | PE/PB 达到历史高位（80% 分位以上） | 分批减仓 |
| **情绪止盈** | 股票热度达到极端高位（Top 10） | 警惕回调 |

**实现逻辑**:
```python
def check_take_profit_signals(position, current_price, historical_data):
    """检查止盈信号"""
    signals = []

    # 1. 目标收益止盈
    profit_rate = (current_price - position.buy_price) / position.buy_price
    if profit_rate >= position.target_profit_rate:
        signals.append({
            'type': 'TARGET_PROFIT',
            'message': f'收益率已达{profit_rate:.1%}，达到目标止盈位',
            'suggestion': f'建议卖出{position.profit_sell_ratio:.0%}仓位',
            'priority': 'HIGH'
        })

    # 2. 移动止盈（从最高点回撤）
    highest_price = max(historical_data['close'])  # 期间最高价
    drawdown = (highest_price - current_price) / highest_price
    if drawdown >= position.max_drawdown:
        signals.append({
            'type': 'TRAILING_STOP',
            'message': f'从最高点{highest_price:.2f}回撤{drawdown:.1%}',
            'suggestion': '建议止盈离场',
            'priority': 'HIGH'
        })

    # 3. 估值止盈
    current_pe = get_current_pe(position.stock_code)
    historical_pe = get_historical_pe_percentile(position.stock_code)
    if historical_pe >= 80:  # 处于历史 80% 分位
        signals.append({
            'type': 'VALUATION_HIGH',
            'message': f'当前 PE 处于历史{historical_pe:.0f}%分位，估值偏高',
            'suggestion': '建议分批减仓',
            'priority': 'MEDIUM'
        })

    return signals
```

---

#### 3.5.5 止损信号（Stop Loss）

| 止损策略 | 触发条件 | 建议操作 |
|----------|----------|----------|
| **固定止损** | 亏损达到预设比例（如 -8%/-10%） | 立即止损 |
| **技术位止损** | 跌破重要支撑位（如 60 日线、前期低点） | 减仓或清仓 |
| **基本面恶化止损** | 财报不及预期、业绩下滑 | 重新评估后决定 |
| **时间止损** | 持仓 N 天后仍未上涨（如 30 天） | 换股操作 |

**实现逻辑**:
```python
def check_stop_loss_signals(position, current_price, technical_data):
    """检查止损信号"""
    signals = []

    # 1. 固定止损
    loss_rate = (current_price - position.buy_price) / position.buy_price
    if loss_rate <= -position.stop_loss_rate:
        signals.append({
            'type': 'FIXED_STOP_LOSS',
            'message': f'亏损已达{loss_rate:.1%}，触及止损线',
            'suggestion': '建议立即止损离场',
            'priority': 'CRITICAL'
        })

    # 2. 技术位止损 - 跌破重要均线
    ma60 = technical_data.get('ma60')
    if current_price < ma60 * 0.97:  # 跌破 60 日线 3%
        signals.append({
            'type': 'MA_BREAK',
            'message': f'股价已跌破 60 日均线{ma60:.2f}',
            'suggestion': '建议减仓或止损',
            'priority': 'HIGH'
        })

    # 3. 技术位止损 - 跌破前低
    prev_low = get_previous_low(position.stock_code, position.buy_date)
    if current_price < prev_low * 0.98:
        signals.append({
            'type': 'SUPPORT_BREAK',
            'message': f'跌破前期支撑位{prev_low:.2f}',
            'suggestion': '建议止损',
            'priority': 'HIGH'
        })

    return signals
```

---

#### 3.5.6 技术卖出信号

| 信号类型 | 触发条件 | 含义 |
|----------|----------|------|
| **死叉信号** | 5 日线下穿 10 日/20 日线 | 短期趋势转弱 |
| **MACD 死叉** | DIF 下穿 DEA | 中期趋势转弱 |
| **顶背离** | 股价新高但 MACD/RSI 未新高 | 上涨动能不足 |
| **超买回调** | RSI > 80 后拐头向下 | 短期可能回调 |
| **跌破布林上轨** | 股价跌破布林带上轨 | 上涨趋势结束 |

**实现逻辑**:
```python
def check_technical_sell_signals(stock_code, daily_data):
    """检查技术面卖出信号"""
    signals = []

    # 计算技术指标
    ma5 = daily_data['ma5'].iloc[-1]
    ma10 = daily_data['ma10'].iloc[-1]
    ma20 = daily_data['ma20'].iloc[-1]

    prev_ma5 = daily_data['ma5'].iloc[-2]
    prev_ma10 = daily_data['ma10'].iloc[-2]

    # 1. 死叉信号
    if prev_ma5 > prev_ma10 and ma5 < ma10:
        signals.append({
            'type': 'DEATH_CROSS',
            'message': '5 日线下穿 10 日线，形成死叉',
            'suggestion': '短期趋势转弱，建议减仓',
            'priority': 'HIGH'
        })

    # 2. MACD 死叉
    macd_dif = daily_data['macd_dif'].iloc[-1]
    macd_dea = daily_data['macd_dea'].iloc[-1]
    prev_dif = daily_data['macd_dif'].iloc[-2]
    prev_dea = daily_data['macd_dea'].iloc[-2]

    if prev_dif > prev_dea and macd_dif < macd_dea:
        signals.append({
            'type': 'MACD_DEATH_CROSS',
            'message': 'MACD 形成死叉',
            'suggestion': '中期趋势转弱',
            'priority': 'HIGH'
        })

    # 3. 顶背离检测
    recent_high = daily_data['high'].rolling(window=20).max().iloc[-1]
    prev_high = daily_data['high'].rolling(window=20).max().iloc[-5]
    macd_recent = daily_data['macd'].iloc[-1]
    macd_prev = daily_data['macd'].iloc[-5]

    if recent_high > prev_high and macd_recent < macd_prev:
        signals.append({
            'type': 'TOP_DIVERGENCE',
            'message': '股价创新高但 MACD 未创新高，顶背离',
            'suggestion': '上涨动能不足，建议减仓',
            'priority': 'MEDIUM'
        })

    # 4. RSI 超买
    rsi = daily_data['rsi'].iloc[-1]
    if rsi > 80:
        signals.append({
            'type': 'OVERBOUGHT',
            'message': f'RSI={rsi:.1f}，进入超买区',
            'suggestion': '短期可能回调',
            'priority': 'MEDIUM'
        })

    return signals
```

---

#### 3.5.7 资金流出信号

| 信号类型 | 触发条件 | 含义 |
|----------|----------|------|
| **主力连续流出** | 连续 3 日主力净流出 | 大资金撤离 |
| **北向资金减持** | 北向资金连续减持 | 外资不看好 |
| **大额净流出** | 单日净流出超过 N 亿 | 大资金出逃 |
| **量价背离** | 股价涨但成交量萎缩 | 买盘不足 |

**实现逻辑**:
```python
def check_capital_outflow_signals(stock_code, flow_data):
    """检查资金流出信号"""
    signals = []

    # 1. 主力连续流出
    consecutive_outflow = count_consecutive_days(flow_data['net_inflow'] < 0)
    if consecutive_outflow >= 3:
        signals.append({
            'type': 'CONSECUTFIVE_OUTFLOW',
            'message': f'主力连续{consecutive_outflow}日净流出',
            'suggestion': '大资金持续撤离，建议警惕',
            'priority': 'HIGH'
        })

    # 2. 大额净流出
    today_net = flow_data['net_inflow'].iloc[-1]
    if today_net < -50000000:  # 净流出超过 5000 万
        signals.append({
            'type': 'LARGE_OUTFLOW',
            'message': f'单日主力净流出{today_net/10000:.1f}万元',
            'suggestion': '大资金出逃，建议减仓',
            'priority': 'HIGH'
        })

    # 3. 北向资金减持
    north_flow = get_northbound_flow(stock_code)
    if north_flow['5day_net'] < -100000000:  # 5 日净减持超 1 亿
        signals.append({
            'type': 'NORTH_REDUCE',
            'message': f'北向资金 5 日净减持{north_flow["5day_net"]/100000000:.2f}亿',
            'suggestion': '外资不看好，建议关注',
            'priority': 'MEDIUM'
        })

    return signals
```

---

#### 3.5.8 利空消息信号

| 信号类型 | 触发条件 | 来源 |
|----------|----------|------|
| **业绩不及预期** | 财报发布后股价大跌 | 财报 + 情感分析 |
| **监管处罚** | 公司收到监管函 | 公司公告 |
| **高管减持** | 重要股东减持公告 | 公司公告 |
| **行业利空** | 行业政策收紧 | 政策新闻 |
| **重大诉讼** | 公司涉及重大诉讼 | 公司公告 |

**实现逻辑**:
```python
def check_negative_news_signals(stock_code, recent_news):
    """检查利空消息信号"""
    signals = []

    negative_keywords = ['处罚', '立案', '诉讼', '减持', '亏损', '下滑', '退市', 'ST']

    for news in recent_news:
        # 情感分析
        sentiment_score = analyze_sentiment(news['content'])

        # 关键词匹配
        contains_negative = any(kw in news['title'] for kw in negative_keywords)

        if sentiment_score < 0.3 or contains_negative:
            signals.append({
                'type': 'NEGATIVE_NEWS',
                'message': f'利空消息：{news["title"]}',
                'source': news['source'],
                'publish_time': news['publish_time'],
                'suggestion': '建议评估影响，必要时减仓',
                'priority': 'HIGH' if contains_negative else 'MEDIUM'
            })

    return signals
```

---

#### 3.5.9 综合卖点评分

**多因子加权评分模型**:

```python
def calculate_sell_score(position, market_data):
    """
    综合计算卖出建议分数
    分数范围：0-100
    0-20: 强烈建议持有
    20-40: 建议持有
    40-60: 观望
    60-80: 建议减仓
    80-100: 强烈建议卖出
    """
    sell_score = 0

    # 1. 止盈信号权重 (30%)
    take_profit_signals = check_take_profit_signals(position, market_data)
    if take_profit_signals:
        sell_score += len(take_profit_signals) * 15
        sell_score = min(sell_score, 30)

    # 2. 止损信号权重 (30%)
    stop_loss_signals = check_stop_loss_signals(position, market_data)
    if stop_loss_signals:
        sell_score += len(stop_loss_signals) * 20
        sell_score = min(sell_score, 30)

    # 3. 技术信号权重 (20%)
    technical_signals = check_technical_sell_signals(position.stock_code, market_data)
    if technical_signals:
        sell_score += len(technical_signals) * 10
        sell_score = min(sell_score, 20)

    # 4. 资金流出权重 (10%)
    capital_signals = check_capital_outflow_signals(position.stock_code, market_data)
    if capital_signals:
        sell_score += len(capital_signals) * 5
        sell_score = min(sell_score, 10)

    # 5. 利空消息权重 (10%)
    news_signals = check_negative_news_signals(position.stock_code, market_data)
    if news_signals:
        sell_score += len(news_signals) * 5
        sell_score = min(sell_score, 10)

    return sell_score
```

---

#### 3.5.10 输出结果

**持仓看板**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         我的持仓                                        │
├──────┬────────┬────────┬────────┬────────┬────────┬────────────────────┤
│ 代码 │ 名称   │ 成本价 │ 当前价 │ 盈亏%  │ 卖点评分 │ 建议操作           │
├──────┼────────┼────────┼────────┼────────┼────────┼────────────────────┤
│600519│ 茅台   │ 1680   │ 1850   │ +10.1% │   35   │ 建议持有           │
│000858│ 五粮液 │ 158    │ 142    │ -10.1% │   75   │ ⚠ 建议减仓         │
│300750│ 宁德   │ 195    │ 228    │ +16.9% │   45   │ 观望               │
└──────┴────────┴────────┴────────┴────────┴────────┴────────────────────┘
```

**卖点详情**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│  000858 五粮液 - 卖点分析              卖点评分：75 (建议减仓)          │
├─────────────────────────────────────────────────────────────────────────┤
│  🔴 CRITICAL                                                            │
│  · 固定止损：亏损已达 -10.1%，触及止损线 (-8%)，建议立即止损离场        │
│                                                                         │
│  ⚠️  HIGH                                                                │
│  · 技术死叉：5 日线下穿 10 日线，形成死叉，短期趋势转弱                   │
│  · 主力流出：连续 3 日主力净流出，累计 -2.3 亿                              │
│                                                                         │
│  ℹ️  MEDIUM                                                              │
│  · RSI 超买：RSI=78，接近超买区，短期可能回调                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 四、数据库设计

### 4.1 核心表结构

```sql
-- 股票基本信息表
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,  -- 如 600519
    name VARCHAR(50) NOT NULL,
    exchange VARCHAR(10),              -- SH/SZ
    industry VARCHAR(50),              -- 行业
    concept VARCHAR(200),              -- 概念板块
    list_date DATE,                    -- 上市日期
    status VARCHAR(10) DEFAULT 'active' -- 状态：active/ST/*ST/退市
);

-- 日线行情表 (TimescaleDB hypertable)
CREATE TABLE stock_daily (
    stock_code VARCHAR(10),
    trade_date DATE,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    amount DECIMAL(20,2),
    turnover_rate DECIMAL(10,4),
    PRIMARY KEY (stock_code, trade_date)
);
SELECT create_hypertable('stock_daily', 'trade_date');

-- 资金流向表
CREATE TABLE stock_capital_flow (
    stock_code VARCHAR(10),
    trade_date DATE,
    main_force_in DECIMAL(20,2),      -- 主力流入
    main_force_out DECIMAL(20,2),     -- 主力流出
    net_inflow DECIMAL(20,2),         -- 净流入
    small_order_in DECIMAL(20,2),     -- 小单流入
    large_order_in DECIMAL(20,2),     -- 大单流入
    PRIMARY KEY (stock_code, trade_date)
);

-- 热词表
CREATE TABLE hot_words (
    id SERIAL PRIMARY KEY,
    word VARCHAR(50) NOT NULL,
    source VARCHAR(20),               -- xueqiu/guba/news
    hot_score DECIMAL(10,2),          -- 热度分数
    burst_level VARCHAR(10),          -- NORMAL/MEDIUM/HIGH/CRITICAL
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 新闻消息表
CREATE TABLE stock_news (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10),
    title VARCHAR(200) NOT NULL,
    content TEXT,
    source VARCHAR(50),
    publish_time TIMESTAMPTZ,
    sentiment VARCHAR(10),            -- positive/neutral/negative
    sentiment_score DECIMAL(5,4),     -- 0-1
    category VARCHAR(50),             -- company/industry/macro
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 技术指标缓存表
CREATE TABLE stock_indicators (
    stock_code VARCHAR(10),
    calc_date DATE,
    indicator_name VARCHAR(50),
    indicator_value DECIMAL(20,6),
    signal VARCHAR(20),               -- buy/sell/hold
    PRIMARY KEY (stock_code, calc_date, indicator_name)
);

-- 用户持仓表（新增）
CREATE TABLE user_positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,                     -- 用户 ID（支持多用户）
    stock_code VARCHAR(10) NOT NULL,     -- 股票代码
    stock_name VARCHAR(50),              -- 股票名称
    buy_price DECIMAL(10,2) NOT NULL,    -- 买入均价
    quantity INTEGER NOT NULL,           -- 持仓数量
    buy_date DATE,                       -- 买入日期
    stop_loss_rate DECIMAL(5,4) DEFAULT 0.08,  -- 止损比例 (默认 8%)
    target_profit_rate DECIMAL(5,4) DEFAULT 0.30, -- 目标止盈比例 (默认 30%)
    profit_sell_ratio DECIMAL(5,4) DEFAULT 0.50,  -- 止盈卖出比例 (默认 50%)
    max_drawdown DECIMAL(5,4) DEFAULT 0.10,  -- 移动止盈回撤 (默认 10%)
    current_price DECIMAL(10,2),         -- 当前价（实时）
    profit_loss DECIMAL(10,4),           -- 盈亏比例（实时）
    profit_amount DECIMAL(15,2),         -- 盈亏金额（实时）
    status VARCHAR(20) DEFAULT 'holding',-- holding/sold
    sell_date DATE,                      -- 卖出日期
    sell_price DECIMAL(10,2),            -- 卖出均价
    sell_reason TEXT,                    -- 卖出原因
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 卖点信号记录表（新增）
CREATE TABLE sell_signals (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES user_positions(id),
    signal_type VARCHAR(20),             -- 信号类型
    signal_time TIMESTAMPTZ DEFAULT NOW(),
    trigger_price DECIMAL(10,2),         -- 触发价格
    description TEXT,                    -- 信号描述
    action_suggestion VARCHAR(50),       -- 建议操作
    priority VARCHAR(10),                -- 优先级：CRITICAL/HIGH/MEDIUM/LOW
    is_acknowledged BOOLEAN DEFAULT FALSE, -- 用户是否已确认
    acknowledged_at TIMESTAMPTZ          -- 确认时间
);
```

### 4.2 Redis 缓存设计

```
# 实时热点排行 (Sorted Set)
hot:words:realtime     -> {word: score}

# 连续流入股票池 (Sorted Set)
stock:inflow:3days     -> {code: net_inflow}
stock:inflow:5days     -> {code: net_inflow}

# 个股热度缓存 (String)
stock:hot:600519       -> {rank, score, trend}

# API 响应缓存 (Hash)
api:cache:stock_info:600519 -> {json_data, expire_at}

# 持仓卖点信号 (Hash)
position:signals:{user_id} -> {code: {score, signals_json}}
```

---

## 五、目录结构

```
stock/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   │
│   ├── api/                    # API 路由层
│   │   ├── __init__.py
│   │   ├── hotspots.py         # 热点 API
│   │   ├── screening.py        # 选股 API
│   │   ├── capital.py          # 资金 API
│   │   ├── news.py             # 消息 API
│   │   └── positions.py        # 持仓 API（新增）
│   │
│   ├── core/                   # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── hot_word_analyzer.py    # 热词分析引擎
│   │   ├── indicator_calculator.py # 指标计算器
│   │   ├── capital_analyzer.py     # 资金分析器
│   │   ├── news_classifier.py      # 消息分类器
│   │   └── sell_signal_engine.py   # 卖点信号引擎（新增）
│   │
│   ├── data/                 # 数据采集层
│   │   ├── __init__.py
│   │   ├── crawler.py            # 爬虫基类
│   │   ├── xueqiu.py             # 雪球数据
│   │   ├── eastmoney.py          # 东方财富数据
│   │   ├── sina.py               # 新浪财经
│   │   └── akshare_client.py     # AkShare 封装
│   │
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   ├── stock.py              # 股票模型
│   │   ├── capital_flow.py       # 资金流模型
│   │   ├── news.py               # 新闻模型
│   │   └── position.py           # 持仓模型（新增）
│   │
│   ├── db/                   # 数据库相关
│   │   ├── __init__.py
│   │   ├── database.py           # 数据库连接
│   │   ├── crud.py               # CRUD 操作
│   │   └── init.sql              # 初始化 SQL
│   │
│   ├── tasks/                # 异步任务
│   │   ├── __init__.py
│   │   ├── celery_app.py         # Celery 配置
│   │   ├── data_sync.py          # 数据同步任务
│   │   ├── indicator_calc.py     # 指标计算任务
│   │   └── signal_monitor.py     # 信号监控任务（新增）
│   │
│   └── utils/                # 工具函数
│       ├── __init__.py
│       ├── nlp.py                # NLP 工具
│       ├── decorators.py         # 装饰器
│       └── logger.py             # 日志配置
│
├── tests/                    # 测试目录
│   ├── __init__.py
│   ├── test_api/
│   ├── test_core/
│   └── test_data/
│
├── frontend/                 # 前端 (可选)
│   ├── src/
│   ├── public/
│   └── package.json
│
├── scripts/                  # 脚本
│   ├── init_db.py            # 初始化数据库
│   └── backfill_data.py      # 补历史数据
│
├── .env                      # 环境变量
├── .env.example              # 环境变量示例
├── requirements.txt          # Python 依赖
├── docker-compose.yml        # Docker 编排
└── README.md                 # 项目说明
```

---

## 六、开发阶段规划

### 阶段一：基础设施搭建（预计 3 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 1.1 项目初始化 | 创建目录结构、配置虚拟环境、安装依赖 | 项目骨架 |
| 1.2 数据库搭建 | PostgreSQL + TimescaleDB 安装、建表 | 数据库环境 |
| 1.3 Redis 配置 | Redis 安装、缓存策略配置 | 缓存环境 |
| 1.4 FastAPI 框架 | 搭建 API 框架、CORS、中间件 | API 骨架 |
| 1.5 Celery 配置 | 任务队列配置、定时任务调度器 | 异步任务环境 |

**验收标准**:
- 数据库可正常连接
- API 返回健康检查响应
- Celery 可执行简单任务

---

### 阶段二：数据采集层开发（预计 5 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 2.1 AkShare 封装 | 封装常用接口、错误处理、重试机制 | `akshare_client.py` |
| 2.2 股票池同步 | 全量 A 股列表、每日更新 | `stock` 表数据 |
| 2.3 行情数据同步 | 日线数据、分钟线数据 | `stock_daily` 表 |
| 2.4 资金流采集 | 个股资金流、北向资金 | `stock_capital_flow` 表 |
| 2.5 新闻采集 | 个股新闻、财经新闻 | `stock_news` 表 |
| 2.6 定时任务 | 数据定时同步、增量更新 | Celery 定时任务 |

**验收标准**:
- 可获取所有 A 股实时行情
- 历史数据可回补（至少 1 年）
- 数据更新任务可自动执行

---

### 阶段三：市场热点检测模块（预计 5 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 3.1 文本预处理 | HTML 清洗、停用词过滤 | 预处理函数 |
| 3.2 中文分词 | jieba 分词、自定义股票词典 | 分词模块 |
| 3.3 关键词提取 | TF-IDF、TextRank 实现 | 提取算法 |
| 3.4 突发检测 | Kleinberg 算法实现 | 突发检测模块 |
| 3.5 热度计算 | 时间衰减、热度评分 | 热度算法 |
| 3.6 热点聚合 | 板块映射、关联股票 | 热点 API |
| 3.7 前端展示 | 热词看板、趋势图 | 热点看板页面 |

**验收标准**:
- 可提取实时热词 Top 50
- 可识别突发热点（如某板块突然升温）
- 热点可映射到具体股票

---

### 阶段四：基本面技术指标模块（预计 4 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 4.1 TA-Lib 集成 | 安装配置、指标测试 | 指标库环境 |
| 4.2 基本面指标 | PE/PB/ROE 等计算 | 基本面数据 |
| 4.3 技术指标 | MA/MACD/RSI 等计算 | 技术指标数据 |
| 4.4 信号生成 | 金叉/死叉、超买/超卖 | 买卖信号 |
| 4.5 综合评分 | 多因子打分模型 | 股票评分 |
| 4.6 前端展示 | 雷达图、K 线图 | 个股分析页面 |

**验收标准**:
- 50+ 常用指标可计算
- 技术指标信号准确
- 综合评分可排序

---

### 阶段五：资金流入监控模块（预计 3 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 5.1 资金流分析 | 连续流入判断逻辑 | 分析函数 |
| 5.2 筛选器 | 多条件筛选、配置化 | 筛选 API |
| 5.3 预警功能 | 满足条件推送通知 | 预警模块 |
| 5.4 可视化 | 资金流趋势图、排行榜 | 监控页面 |

**验收标准**:
- 可筛选连续 3 日/5 日/10 日流入股票
- 可自定义筛选条件
- 预警可及时推送

---

### 阶段六：消息政策捕捉模块（预计 4 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 6.1 新闻分类 | 规则分类 + ML 分类 | 分类模型 |
| 6.2 情感分析 | SnowNLP+ 自定义词典 | 情感分析模块 |
| 6.3 政策映射 | 政策→受益板块 | 映射表 |
| 6.4 消息聚合 | 个股消息时间线 | 聚合 API |
| 6.5 前端展示 | 消息流、利好统计 | 消息中心页面 |

**验收标准**:
- 新闻分类准确率>85%
- 情感判断基本准确
- 可追溯政策受益股

---

### 阶段七：持仓卖点建议模块（预计 5 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 7.1 持仓管理 | 持仓录入、编辑、导入功能 | 持仓 CRUD |
| 7.2 止盈信号 | 目标止盈、移动止盈、估值止盈 | 止盈引擎 |
| 7.3 止损信号 | 固定止损、技术位止损 | 止损引擎 |
| 7.4 技术卖出 | 死叉、顶背离、超买检测 | 技术信号 |
| 7.5 资金流出 | 主力流出、北向减持检测 | 流出信号 |
| 7.6 利空消息 | 负面新闻监控 | 利空信号 |
| 7.7 综合评分 | 多因子加权评分模型 | 卖点评分 |
| 7.8 前端展示 | 持仓看板、信号详情 | 持仓页面 |

**验收标准**:
- 五大维度信号可准确触发
- 综合评分合理
- 支持止盈止损自定义配置

---

### 阶段八：系统集成与测试（预计 3 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 8.1 API 联调 | 接口测试、性能测试 | 测试报告 |
| 8.2 前端集成 | 页面联调、交互优化 | 完整前端 |
| 8.3 性能优化 | 缓存优化、查询优化 | 性能报告 |
| 8.4 Bug 修复 | 问题修复、回归测试 | 稳定版本 |

**验收标准**:
- 核心 API 响应<200ms
- 无严重 Bug
- 用户体验流畅

---

### 阶段九：部署上线（预计 2 天）

| 任务 | 详细说明 | 产出物 |
|------|----------|--------|
| 9.1 Docker 化 | 容器化配置、编排文件 | Docker 镜像 |
| 9.2 生产部署 | 服务器配置、域名绑定 | 生产环境 |
| 9.3 监控配置 | 日志监控、告警配置 | 监控大盘 |
| 9.4 备份策略 | 数据备份、恢复演练 | 备份方案 |

**验收标准**:
- 服务可稳定运行
- 监控告警正常
- 数据可恢复

---

## 七、总工期估算

| 阶段 | 工作内容 | 工期 |
|------|----------|------|
| 阶段一 | 基础设施搭建 | 3 天 |
| 阶段二 | 数据采集层 | 5 天 |
| 阶段三 | 热点检测模块 | 5 天 |
| 阶段四 | 技术指标模块 | 4 天 |
| 阶段五 | 资金监控模块 | 3 天 |
| 阶段六 | 消息捕捉模块 | 4 天 |
| 阶段七 | **持仓卖点建议** | **5 天** |
| 阶段八 | 集成测试 | 3 天 |
| 阶段九 | 部署上线 | 2 天 |
| **合计** | | **34 天** |

---

## 八、风险与应对（更新版）

### 8.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 数据源接口变更 | 数据采集失效 | 多数据源冗余（AkShare+Tushare+BaoStock）、接口监控告警 |
| 反爬虫限制 | 采集频率受限 | IP 代理池、降低频率、增加验证码识别 |
| 数据准确性 | 分析结果错误 | 数据校验、交叉验证、异常值检测 |
| 性能瓶颈 | 响应慢 | Redis 缓存、查询优化、数据库索引 |

### 8.2 法律合规风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 非法投顾风险 | 行政处罚/诉讼 | 定位"信息工具"而非"投顾"、强制免责声明 |
| 数据版权风险 | 法律纠纷 | 仅用公开数据、遵守 robots.txt、不商用爬取数据 |
| 用户亏损诉讼 | 民事赔偿 | 用户协议明确"仅供参考、不构成投资建议" |

### 8.3 工期风险

**实际工期预估：60-90 天（原 34 天的 1.8-2.5 倍）**

| 阶段 | 原估算 | 实际需 | 缓冲 |
|------|--------|--------|------|
| 基础设施 | 3 天 | 5-7 天 | +4 天 |
| 数据采集 | 5 天 | 10-14 天 | +9 天 |
| 热点检测 | 5 天 | 8-10 天 | +5 天 |
| 技术指标 | 4 天 | 6-8 天 | +4 天 |
| 资金监控 | 3 天 | 5-7 天 | +4 天 |
| 消息捕捉 | 4 天 | 7-10 天 | +6 天 |
| 持仓卖点 | 5 天 | 10-14 天 | +9 天 |
| 集成测试 | 3 天 | 7-10 天 | +7 天 |
| 部署上线 | 2 天 | 3-5 天 | +3 天 |
| **合计** | **34 天** | **61-85 天** | **+46 天** |

### 8.4 关键依赖验证

**开发前必须完成**:
- [ ] AkShare 稳定性测试（至少 2 周）
- [ ] Tushare Pro 备选方案测试
- [ ] 卖点信号历史回测验证
- [ ] 法律免责声明审查

---

## 九、开源项目借鉴

### 9.1 数据层可借鉴项目

| 项目 | Stars | 可借鉴点 |
| :--- | :--- | :--- |
| **AkShare** | 16K+ | 多数据源统一 API 设计、模块化数据提供商架构 |
| **Tushare** | 10K+ | Freemium 数据 API 设计、清晰的 SDK 结构 |
| **BaoStock** | 4K+ | 免费数据层设计、简单 API 封装 |

**采纳方案**: 直接依赖 AkShare 作为主要数据源，避免重复造轮子

---

### 9.2 量化框架可借鉴项目

| 项目 | Stars | 可借鉴点 |
| :--- | :--- | :--- |
| **VN.PY (VeighNa)** | 25K+ | 事件驱动架构、插件式 Broker 对接、风控模块设计 |
| **Freqtrade** | 25K+ | Trailing Stop 实现、ROI 止盈策略、时间止损 |
| **Backtrader** | 10K+ | Bracket Order(止损止盈单)、100+ 技术指标集成 |
| **Lean (QuantConnect)** | 7K+ | Bracket Order 模式、多资产支持、机构级风控 |
| **Jesse** | 3K+ | 装饰器风格止盈止损定义、清晰的策略模板 |

**采纳方案**:
- 止盈止损引擎参考 Freqtrade 的 Trailing Stop 实现
- 信号生成参考 Backtrader 的指标集成方式
- 订单管理参考 Lean 的 Bracket Order 模式

---

### 9.3 NLP 可借鉴项目

| 项目 | 可借鉴点 |
| :--- | :--- |
| **HanLP** | 工业级中文 NLP、金融领域自定义模型 |
| **FunNLP** | 金融文本挖掘资源集合、NER 工具 |
| **Chinese-Financial-Sentiment-Analysis** | BERT 微调金融情感分类 |
| **LTP (哈工大)** | 完整中文 NLP 管道、可微调金融领域 |

**采纳方案**:
- 分词：jieba + 自定义股票词典
- 情感分析：SnowNLP + 金融情感词典
- 关键词提取：TextRank + TF-IDF 组合

---

### 9.4 可直接采用的代码模式

**1. Trailing Stop 实现 (参考 Freqtrade)**:

```python
def update_trailing_stop(highest_price, current_price, trailing_pct=0.10):
    """从最高点回撤超过阈值时触发"""
    drawdown = (highest_price - current_price) / highest_price
    return drawdown >= trailing_pct
```

**2. Bracket Order 模式 (参考 Lean)**:

```python
# 同时设置止损和止盈订单
stop_loss_price = entry_price * 0.92   # -8% 止损
take_profit_price = entry_price * 1.30  # +30% 止盈
```

**3. 多因子综合评分模型**:

```python
def calculate_sell_score(position, market_data):
    score = 0
    # 止盈信号 (30%) + 止损信号 (30%) + 技术信号 (20%) + 资金流出 (10%) + 利空消息 (10%)
    # 总分 0-100: 0-20 强烈持有，80-100 强烈卖出
    return score
```

---

## 十一、个人自用版方案（最终简化版）

### 11.1 定位调整

**产品定位**：个人本地使用，非商用

**简化原则**：
- 只实现核心功能，不追求完美
- 优先使用现成库，不重复造轮子
- 单机运行，不需要高并发
- 数据存本地，不需要复杂的分布式架构

---

### 11.2 技术栈简化

| 组件 | 原计划 | 简化后 |
|------|--------|--------|
| 数据库 | PostgreSQL + TimescaleDB | SQLite（免安装） |
| 缓存 | Redis | 不需要 |
| 搜索 | Elasticsearch | 不需要 |
| 任务队列 | Celery + Redis | APScheduler（定时任务） |
| 后端框架 | FastAPI | 保留（API 清晰） |
| 前端 | Vue 3 + Element Plus | Streamlit（快速搭建） |
| 部署 | Docker | 本地 Python 运行 |

---

### 11.3 功能裁剪

**保留的核心功能**：
- [x] 数据采集（AkShare 直接获取）
- [x] 热点词频统计（简化版）
- [x] 技术指标计算（TA-Lib/pandas-ta）
- [x] 资金流入筛选（连续 N 日净流入）
- [x] 新闻聚合（简单爬取）
- [x] 持仓管理（本地录入）
- [x] 止盈止损信号（固定比例 + 简单技术信号）

**砍掉的功能**：
- [ ] 多用户认证
- [ ] 复杂的 NLP 情感分析（用关键词匹配代替）
- [ ] 实时热点检测（改为每日更新）
- [ ] 复杂的回测框架
- [ ] 移动端支持
- [ ] 消息推送

---

### 11.4 简化后工期

| 阶段 | 原工期 | 简化后 |
|------|--------|--------|
| 环境搭建 | 5-7 天 | **0.5 天** |
| 数据采集 | 10-14 天 | **1 天** |
| 热点检测 | 8-10 天 | **1 天** |
| 技术指标 | 6-8 天 | **1 天** |
| 资金监控 | 5-7 天 | **0.5 天** |
| 消息捕捉 | 7-10 天 | **1 天** |
| 持仓卖点 | 10-14 天 | **2 天** |
| Streamlit 界面 | - | **1 天** |
| **合计** | **61-85 天** | **~7 天** |

---

### 11.5 目录结构（简化版）

```
stock/
├── data/                   # 数据存储
│   ├── stock.db           # SQLite 数据库
│   └── cache/             # 临时缓存
│
├── core/                   # 核心逻辑
│   ├── __init__.py
│   ├── data_fetcher.py    # 数据获取（AkShare）
│   ├── indicator.py       # 技术指标
│   ├── capital.py         # 资金分析
│   ├── hot_words.py       # 热词统计
│   └── position.py        # 持仓管理
│
├── api/                    # API 接口
│   ├── __init__.py
│   └── routes.py
│
├── ui/                     # Streamlit 界面
│   └── app.py
│
├── config.py               # 配置
├── main.py                 # 入口
├── requirements.txt        # 依赖
└── README.md              # 说明
```

---

### 11.6 开发顺序

```
Day 1:  环境搭建 + 数据获取测试
Day 2:  数据库设计 + 技术指标计算
Day 3:  资金流入筛选 + 热点词频
Day 4:  持仓管理 + 止盈止损
Day 5:  新闻聚合
Day 6:  Streamlit 界面整合
Day 7:  测试 + 文档
```

---

## 十二、下一步行动

**确认即可开始 Day 1 开发：**

1. [x] 技术栈：Python + SQLite + FastAPI + Streamlit
2. [x] 数据源：AkShare（免费、免 Key）
3. [x] 功能范围：7 天 MVP 核心功能
4. [x] 部署方式：本地运行

**请回复 "开始" 即可进入 Day 1 开发。**
