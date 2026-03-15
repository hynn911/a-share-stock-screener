"""
数据库模型
"""
from sqlalchemy import create_engine, Column, String, Integer, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Stock(Base):
    """股票基本信息"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # 如 600519
    name = Column(String(50), nullable=False)
    exchange = Column(String(10))  # SH/SZ
    industry = Column(String(50))  # 行业
    concept = Column(String(200))  # 概念板块
    status = Column(String(10), default="active")  # active/ST/*ST/退市
    created_at = Column(DateTime, default=datetime.now)


class StockDaily(Base):
    """日线行情"""
    __tablename__ = "stock_daily"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    amount = Column(Float)
    turnover_rate = Column(Float)


class StockCapitalFlow(Base):
    """资金流向"""
    __tablename__ = "stock_capital_flow"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    main_force_in = Column(Float)  # 主力流入
    main_force_out = Column(Float)  # 主力流出
    net_inflow = Column(Float)  # 净流入
    small_order_in = Column(Float)  # 小单流入
    large_order_in = Column(Float)  # 大单流入


class HotWord(Base):
    """热词"""
    __tablename__ = "hot_words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(50), nullable=False, index=True)
    source = Column(String(20))  # xueqiu/guba/news
    hot_score = Column(Float)
    created_at = Column(DateTime, default=datetime.now, index=True)


class StockNews(Base):
    """新闻"""
    __tablename__ = "stock_news"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    source = Column(String(50))
    publish_time = Column(DateTime, index=True)
    sentiment = Column(String(10))  # positive/neutral/negative
    sentiment_score = Column(Float)
    created_at = Column(DateTime, default=datetime.now)


class Position(Base):
    """持仓"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50))
    buy_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    buy_date = Column(Date)
    stop_loss_rate = Column(Float, default=0.08)  # 止损比例
    target_profit_rate = Column(Float, default=0.30)  # 目标止盈
    max_drawdown_rate = Column(Float, default=0.10)  # 移动止盈回撤
    status = Column(String(20), default="holding")  # holding/sold
    sell_date = Column(Date)
    sell_price = Column(Float)
    sell_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SellSignal(Base):
    """卖点信号"""
    __tablename__ = "sell_signals"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), index=True)
    signal_type = Column(String(20))  # TAKE_PROFIT/STOP_LOSS/TECHNICAL/CAPITAL/NEWS
    signal_time = Column(DateTime, default=datetime.now)
    trigger_price = Column(Float)
    description = Column(Text)
    action_suggestion = Column(String(50))
    priority = Column(String(10))  # CRITICAL/HIGH/MEDIUM/LOW
    is_acknowledged = Column(Integer, default=0)  # 0=未确认，1=已确认


class StockHolderCount(Base):
    """股东户数"""
    __tablename__ = "stock_holder_count"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    holder_count = Column(Integer)  # 股东户数
    holder_count_prev = Column(Integer)  # 上期股东户数
    change_count = Column(Integer)  # 增减数量
    change_ratio = Column(Float)  # 增减比例 (%)
    avg_holdings = Column(Float)  # 户均持股
    avg_holdings_change = Column(Float)  # 户均持股变化
    created_at = Column(DateTime, default=datetime.now)


class CommodityPrice(Base):
    """大宗商品价格"""
    __tablename__ = "commodity_prices"

    id = Column(Integer, primary_key=True, index=True)
    commodity_name = Column(String(50), nullable=False, index=True)  # 商品名称
    trade_date = Column(Date, nullable=False, index=True)  # 交易日期
    spot_price = Column(Float)  # 现货价格
    near_contract = Column(String(20))  # 近月合约
    near_contract_price = Column(Float)  # 近月合约价格
    dominant_contract = Column(String(20))  # 主力合约
    dominant_contract_price = Column(Float)  # 主力合约价格
    price_change_1d = Column(Float)  # 1 日涨跌幅 (%)
    created_at = Column(DateTime, default=datetime.now)


class StockRecommendation(Base):
    """股票推荐结果（盘后预计算）"""
    __tablename__ = "stock_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True)  # 交易日期
    stock_code = Column(String(10), nullable=False, index=True)  # 股票代码
    stock_name = Column(String(50), nullable=False)  # 股票名称
    total_score = Column(Float, nullable=False)  # 综合评分
    capital_score = Column(Float)  # 资金流评分
    technical_score = Column(Float)  # 技术评分
    holder_score = Column(Float)  # 股东户数评分
    news_score = Column(Float)  # 新闻评分
    momentum_score = Column(Float)  # 动量评分
    rank = Column(Integer)  # 排名
    created_at = Column(DateTime, default=datetime.now, index=True)
