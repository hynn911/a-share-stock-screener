"""
数据获取模块 - 基于 AkShare（含备用数据源）
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import random
import os
from dotenv import load_dotenv
from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockNews, StockHolderCount

# 加载环境变量（从 .env 文件）
load_dotenv()


# 备用数据源配置
ALT_DATA_SOURCES = {
    "tushare": False,  # 需要配置 token
    "eastmoney_direct": True,  # 东方财富直连
    "sina": True,  # 新浪财经
}

# Tushare 配置（从环境变量读取）
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")  # 从 .env 或系统环境变量读取


class DataFetcher:
    """数据获取器"""

    def __init__(self):
        self.db = SessionLocal()
        self.session = self._create_session()

    def _create_session(self):
        """创建带重试和代理支持的 HTTP Session"""
        import requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        })
        return session

    def _retry_request(self, url, max_retries=5, base_delay=2, **kwargs):
        """带指数退避的 HTTP 请求"""
        import requests

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30, **kwargs)
                response.raise_for_status()
                return response
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"请求失败 (第{attempt + 1}/{max_retries}次): {e}")
                    print(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    raise
        return None

    def _convert_name(self, raw_name):
        """转换股票名称编码

        AkShare 返回的姓名已经是正确的 UTF-8，不需要转换。
        此函数保留用于兼容性。
        """
        # 直接返回原始名称，AkShare 已经返回正确的 UTF-8 编码
        return raw_name

    def _fetch_stock_list_from_eastmoney(self):
        """备用方案：直接调用东方财富 API 获取股票列表"""
        import requests

        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": 10000,  # 一次性获取所有
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",  # 沪深 A 股
                "fields": "f12,f14,f141,f149"  # 代码、名称、行业、概念
            }

            resp = self._retry_request(url, params=params)
            if resp and resp.status_code == 200:
                data = resp.json()
                stocks = []
                for item in data.get("data", {}).get("diff", []):
                    code = str(item.get("f12", ""))
                    name = str(item.get("f14", ""))
                    industry = str(item.get("f141", "")) if item.get("f141") else ""
                    concept = str(item.get("f149", "")) if item.get("f149") else ""

                    if not code or code == "NaN":
                        continue

                    exchange = "SH" if code.startswith("6") else \
                               "SZ" if code.startswith(("0", "3")) else \
                               "BJ" if code.startswith(("9", "8", "4")) else "SH"

                    stocks.append(Stock(
                        code=code,
                        name=name,
                        exchange=exchange,
                        industry=industry if industry and industry != "NaN" else None,
                        concept=concept if concept and concept != "NaN" else None,
                        status="active"
                    ))
                return stocks
        except Exception as e:
            print(f"东方财富直连失败：{e}")
        return []

    def fetch_stock_list(self):
        """获取 A 股列表（上海、深圳、北京）- 包含行业和概念信息"""
        stocks = []

        # 方案 1: AkShare 主接口
        try:
            print("尝试 AkShare 主接口...")
            df_all = ak.stock_zh_a_spot_em()

            for _, row in df_all.iterrows():
                code = str(row['代码'])
                name = str(row['名称'])
                industry = str(row.get('行业', '')) if '行业' in row.keys() else ''
                concept = str(row.get('概念板块', '')) if '概念板块' in row.keys() else ''

                if not code or code == 'nan':
                    continue

                exchange = "SH" if code.startswith('6') else \
                           "SZ" if code.startswith(('0', '3')) else \
                           "BJ" if code.startswith(('9', '8', '4')) else "SH"

                stocks.append(Stock(
                    code=code,
                    name=name,
                    exchange=exchange,
                    industry=industry if industry and industry != 'nan' else None,
                    concept=concept if concept and concept != 'nan' else None,
                    status="active"
                ))
            print(f"AkShare 成功获取 {len(stocks)} 只股票")

        except Exception as e:
            print(f"AkShare 失败：{e}，切换到备用数据源...")

            # 方案 2: 东方财富直连
            stocks = self._fetch_stock_list_from_eastmoney()
            if stocks:
                print(f"东方财富直连成功获取 {len(stocks)} 只股票")
            else:
                # 方案 3: 尝试 Tushare（如果配置了 token）
                if TUSHARE_TOKEN:
                    try:
                        import tushare as ts
                        ts.set_token(TUSHARE_TOKEN)
                        pro = ts.pro_api()
                        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,industry,list_date')

                        for _, row in df.iterrows():
                            code = str(row['symbol'])
                            name = str(row['name'])
                            industry = str(row.get('industry', ''))

                            exchange = "SH" if code.startswith('6') else \
                                       "SZ" if code.startswith(('0', '3')) else "SH"

                            stocks.append(Stock(
                                code=code,
                                name=name,
                                exchange=exchange,
                                industry=industry if industry and industry != 'None' else None,
                                concept=None,
                                status="active"
                            ))
                        print(f"Tushare 成功获取 {len(stocks)} 只股票")
                    except Exception as te:
                        print(f"Tushare 失败：{te}")

        if not stocks:
            print("所有数据源均失败")
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
        """获取日线数据"""
        try:
            if not start_date:
                start_date = "20200101"

            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                adjust="qfq"  # 前复权
            )

            if df.empty:
                return 0

            records = []
            for _, row in df.iterrows():
                records.append(StockDaily(
                    stock_code=stock_code,
                    trade_date=pd.to_datetime(row["日期"]).date(),
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=int(row["成交量"]),
                    amount=float(row["成交额"]),
                    turnover_rate=float(row.get("换手率", 0))
                ))

            self.db.add_all(records)
            self.db.commit()
            return len(records)
        except Exception as e:
            self.db.rollback()
            return 0

    def fetch_capital_flow(self, stock_code: str):
        """获取资金流向"""
        try:
            # 确定市场
            if stock_code.startswith('6'):
                market = 'sh'
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                market = 'sz'
            elif stock_code.startswith('9') or stock_code.startswith('8') or stock_code.startswith('4'):
                market = 'bj'  # 北交所
            else:
                market = 'sz'  # 默认

            # 新 API: stock_individual_fund_flow
            df = ak.stock_individual_fund_flow(stock=stock_code, market=market)

            if df.empty:
                return 0

            records = []
            for _, row in df.iterrows():
                # 使用列索引访问数据（避免编码问题）
                # 列 0: 日期，列 3: 主力净流入，列 5: 超大单流入，列 7: 大单流入，列 11: 小单流入
                records.append(StockCapitalFlow(
                    stock_code=stock_code,
                    trade_date=row.iloc[0] if isinstance(row.iloc[0], (pd.Timestamp, type(pd.Timestamp.now()))) else pd.to_datetime(row.iloc[0]).date(),
                    main_force_in=float(row.iloc[5]) + float(row.iloc[7]) if len(row) > 7 else 0,  # 超大单 + 大单
                    main_force_out=0,  # 流出数据需要另外计算
                    net_inflow=float(row.iloc[3]) if len(row) > 3 else 0,  # 主力净流入
                    small_order_in=float(row.iloc[11]) if len(row) > 11 else 0,  # 小单流入
                    large_order_in=float(row.iloc[5]) if len(row) > 5 else 0  # 超大单流入
                ))

            self.db.add_all(records)
            self.db.commit()
            return len(records)
        except Exception:
            self.db.rollback()
            return 0

    def fetch_hot_ranking(self):
        """获取个股热度排行"""
        try:
            df = ak.stock_hot_rank_em()
            return df
        except Exception:
            return pd.DataFrame()

    def fetch_stock_news(self, stock_code: str):
        """获取个股新闻"""
        try:
            df = ak.stock_news_em(symbol=stock_code)

            if df.empty:
                return 0

            records = []
            for _, row in df.iterrows():
                # 使用列索引访问（避免编码问题）
                # 列 0: 关键词，列 1: 标题，列 2: 内容，列 3: 发布时间，列 4: 来源
                records.append(StockNews(
                    stock_code=stock_code,
                    title=str(row.iloc[1]) if len(row) > 1 else "",
                    content=str(row.iloc[2]) if len(row) > 2 else "",
                    source=str(row.iloc[4]) if len(row) > 4 else "",
                    publish_time=pd.to_datetime(row.iloc[3]) if len(row) > 3 else datetime.now(),
                    sentiment="neutral",
                    sentiment_score=0.5
                ))

            self.db.add_all(records)
            self.db.commit()
            return len(records)
        except Exception:
            self.db.rollback()
            return 0

    def fetch_shareholder_count(self, stock_code: str):
        """获取股东户数变化数据"""
        try:
            df = ak.stock_zh_a_gdhs_detail_em(symbol=stock_code)

            if df.empty:
                return 0

            records = []
            for _, row in df.iterrows():
                # 使用列索引访问数据（避免编码问题）
                # 列 0: 股东户数统计截止日，列 2: 股东户数 - 本次，列 3: 股东户数 - 上次
                # 列 4: 股东户数 - 增减，列 5: 股东户数 - 增减比例
                # 列 7: 户均持股数量，列 6: 户均持股市值
                try:
                    holder_count = int(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else 0
                    holder_count_prev = int(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else 0
                    change_count = int(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else 0
                    change_ratio = float(row.iloc[5]) if len(row) > 5 and pd.notna(row.iloc[5]) else 0
                    avg_holdings = float(row.iloc[7]) if len(row) > 7 and pd.notna(row.iloc[7]) else 0
                    avg_holdings_change = 0.0  # 户均持股变化需要计算

                    trade_date = pd.to_datetime(row.iloc[0]).date() if len(row) > 0 else None

                    if trade_date is None:
                        continue

                    records.append(StockHolderCount(
                        stock_code=stock_code,
                        trade_date=trade_date,
                        holder_count=holder_count,
                        holder_count_prev=holder_count_prev,
                        change_count=change_count,
                        change_ratio=change_ratio,
                        avg_holdings=avg_holdings,
                        avg_holdings_change=avg_holdings_change
                    ))
                except Exception:
                    continue

            if records:
                self.db.add_all(records)
                self.db.commit()
                return len(records)
            return 0
        except Exception:
            self.db.rollback()
            return 0

    def close(self):
        self.db.close()
