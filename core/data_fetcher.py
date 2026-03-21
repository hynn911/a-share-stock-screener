"""
数据获取模块 - 基于 Tushare（唯一数据源）
"""
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockNews, StockHolderCount

# 加载环境变量（从 .env 文件）
load_dotenv()


# Tushare 配置（从环境变量读取）
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")  # 从 .env 或系统环境变量读取


# Tushare 限流控制
class TushareRateLimiter:
    """Tushare API 限流器 - 每分钟不超过 50 次调用"""

    def __init__(self, max_calls_per_minute=45):
        self.max_calls = max_calls_per_minute
        self.interval = 60.0 / max_calls_per_minute  # 调用间隔（秒）
        self.last_call_time = 0
        self.call_count = 0
        self.minute_start_time = time.time()

    def wait_if_needed(self):
        """如果需要，等待以满足限流要求"""
        current_time = time.time()

        # 检查是否超过一分钟，重置计数器
        if current_time - self.minute_start_time >= 60:
            self.minute_start_time = current_time
            self.call_count = 0
            print(f"[限流] 重置计数器，当前调用数：{self.call_count}/{self.max_calls}")

        # 检查是否达到限流
        if self.call_count >= self.max_calls:
            wait_time = 60 - (current_time - self.minute_start_time)
            if wait_time > 0:
                print(f"[限流] 已达到每分钟{self.max_calls}次限制，等待{wait_time:.1f}秒...")
                time.sleep(wait_time)
                self.minute_start_time = time.time()
                self.call_count = 0

        # 确保最小调用间隔
        elapsed = current_time - self.last_call_time
        if elapsed < self.interval:
            sleep_time = self.interval - elapsed
            time.sleep(sleep_time)

        self.call_count += 1
        self.last_call_time = time.time()

    def reset(self):
        """重置计数器"""
        self.call_count = 0
        self.minute_start_time = time.time()


# 全局限流器实例
_tushare_limiter = TushareRateLimiter(max_calls_per_minute=45)  # 留一些余量


class DataFetcher:
    """数据获取器 - 直接使用 Tushare"""

    def __init__(self):
        self.db = SessionLocal()
        self.limiter = _tushare_limiter  # 使用全局限流器
        self._pro = None

    def _get_pro_api(self):
        """获取 Tushare Pro API 实例"""
        if self._pro is None:
            import tushare as ts
            ts.set_token(TUSHARE_TOKEN)
            self._pro = ts.pro_api()
        return self._pro

    def _convert_name(self, raw_name):
        """转换股票名称编码

        Tushare 返回的姓名已经是正确的 UTF-8，不需要转换。
        """
        return raw_name

    def fetch_stock_list(self):
        """获取 A 股列表 - 直接使用 Tushare"""
        self.limiter.wait_if_needed()

        stocks = []
        try:
            print("使用 Tushare 获取股票列表...")
            pro = self._get_pro_api()
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,market,list_date')

            for _, row in df.iterrows():
                code = str(row['symbol'])
                name = str(row['name'])
                industry = str(row.get('industry', ''))

                # 根据 ts_code 判断交易所
                ts_code = str(row['ts_code'])
                exchange = "SH" if ts_code.endswith('.SH') else "SZ" if ts_code.endswith('.SZ') else "SH"

                stocks.append(Stock(
                    code=code,
                    name=name,
                    exchange=exchange,
                    industry=industry if industry and industry != 'None' else None,
                    concept=None,  # Tushare basic 接口不提供概念数据
                    status="active"
                ))

            print(f"Tushare 成功获取 {len(stocks)} 只股票")

        except Exception as e:
            print(f"Tushare 获取股票列表失败：{e}")
            return 0

        if not stocks:
            print("获取股票列表失败")
            return 0

        # 批量插入或更新
        for stock in stocks:
            existing = self.db.query(Stock).filter(Stock.code == stock.code).first()
            if existing:
                existing.name = stock.name
                existing.exchange = stock.exchange
                if stock.industry:
                    existing.industry = stock.industry
                if stock.concept:
                    existing.concept = stock.concept
            else:
                self.db.add(stock)

        self.db.commit()
        return len(stocks)

    def fetch_daily_bars(self, stock_code: str, start_date: str = None):
        """获取日线数据 - 直接使用 Tushare"""
        self.limiter.wait_if_needed()

        try:
            pro = self._get_pro_api()

            if not start_date:
                start_date = "20200101"

            # Tushare daily 接口
            df = pro.daily(ts_code=stock_code, start_date=start_date)

            if df is None or len(df) == 0:
                return 0

            records = []
            for _, row in df.iterrows():
                records.append(StockDaily(
                    stock_code=stock_code,
                    trade_date=pd.to_datetime(str(row['trade_date'])).date(),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['vol']),
                    amount=float(row['amount']),
                    turnover_rate=float(row.get('turnover_rate', 0))
                ))

            self.db.add_all(records)
            self.db.commit()
            return len(records)

        except Exception as e:
            self.db.rollback()
            print(f"  获取 {stock_code} 日线失败：{e}")
            return 0

    def fetch_capital_flow(self, stock_code: str):
        """获取资金流向 - 使用 Tushare"""
        self.limiter.wait_if_needed()

        try:
            pro = self._get_pro_api()

            # Tushare 资金流接口
            df = pro.moneyflow(ts_code=stock_code)

            if df is None or len(df) == 0:
                return 0

            records = []
            for _, row in df.iterrows():
                records.append(StockCapitalFlow(
                    stock_code=stock_code,
                    trade_date=pd.to_datetime(str(row['trade_date'])).date(),
                    main_force_in=float(row.get('buy_sm_amount', 0)) + float(row.get('buy_bd_amount', 0)),
                    main_force_out=float(row.get('sell_sm_amount', 0)) + float(row.get('sell_bd_amount', 0)),
                    net_inflow=float(row.get('net_m_amount', 0)),
                    small_order_in=float(row.get('buy_sm_amount', 0)),
                    large_order_in=float(row.get('buy_bd_amount', 0))
                ))

            self.db.add_all(records)
            self.db.commit()
            return len(records)

        except Exception as e:
            self.db.rollback()
            print(f"  获取 {stock_code} 资金流失败：{e}")
            return 0

    def fetch_stock_news(self, stock_code: str):
        """获取个股新闻 - 使用 Tushare"""
        self.limiter.wait_if_needed()

        try:
            pro = self._get_pro_api()

            # Tushare 新闻接口
            df = pro.news(ts_code=stock_code)

            if df is None or len(df) == 0:
                return 0

            records = []
            for _, row in df.iterrows():
                records.append(StockNews(
                    stock_code=stock_code,
                    title=str(row.get('title', '')),
                    content=str(row.get('content', '')),
                    source=str(row.get('source', '')),
                    publish_time=pd.to_datetime(row['pubtime']),
                    sentiment="neutral",
                    sentiment_score=0.5
                ))

            self.db.add_all(records)
            self.db.commit()
            return len(records)

        except Exception as e:
            self.db.rollback()
            print(f"  获取 {stock_code} 新闻失败：{e}")
            return 0

    def fetch_shareholder_count(self, stock_code: str):
        """获取股东户数 - 使用 Tushare"""
        self.limiter.wait_if_needed()

        try:
            pro = self._get_pro_api()

            # Tushare 股东户数接口
            df = pro.top10_holders(ts_code=stock_code)

            if df is None or len(df) == 0:
                return 0

            records = []
            for _, row in df.iterrows():
                holder_count = int(row.get('hold_num', 0)) if row.get('hold_num') else 0
                if holder_count == 0:
                    continue

                records.append(StockHolderCount(
                    stock_code=stock_code,
                    trade_date=pd.to_datetime(str(row['end_date'])).date(),
                    holder_count=holder_count,
                    holder_count_prev=0,
                    change_count=0,
                    change_ratio=0.0,
                    avg_holdings=0.0,
                    avg_holdings_change=0.0
                ))

            if records:
                self.db.add_all(records)
                self.db.commit()
                return len(records)
            return 0

        except Exception as e:
            self.db.rollback()
            print(f"  获取 {stock_code} 股东户数失败：{e}")
            return 0

    def fetch_hot_ranking(self):
        """获取个股热度排行"""
        # Tushare 没有直接对应的接口，返回空 DataFrame
        return pd.DataFrame()

    def close(self):
        self.db.close()
