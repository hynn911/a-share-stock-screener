"""
数据获取模块 - 基于 AkShare
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockNews, StockHolderCount


class DataFetcher:
    """数据获取器"""

    def __init__(self):
        self.db = SessionLocal()

    def _convert_name(self, raw_name):
        """转换股票名称编码

        AkShare 返回的姓名已经是正确的 UTF-8，不需要转换。
        此函数保留用于兼容性。
        """
        # 直接返回原始名称，AkShare 已经返回正确的 UTF-8 编码
        return raw_name

    def fetch_stock_list(self):
        """获取 A 股列表（上海、深圳、北京）- 包含行业和概念信息"""
        try:
            stocks = []
            api_success = False

            # 尝试使用 stock_zh_a_spot_em 获取数据（包含行业和概念）
            try:
                df_all = ak.stock_zh_a_spot_em()
                api_success = True

                for _, row in df_all.iterrows():
                    code = str(row['代码'])
                    name = str(row['名称'])
                    industry = str(row.get('行业', '')) if '行业' in row.keys() else ''
                    concept = str(row.get('概念板块', '')) if '概念板块' in row.keys() else ''

                    # 确定交易所
                    if code.startswith('6'):
                        exchange = "SH"
                    elif code.startswith('0') or code.startswith('3'):
                        exchange = "SZ"
                    elif code.startswith('9') or code.startswith('8') or code.startswith('4'):
                        exchange = "BJ"
                    else:
                        exchange = "SH"

                    stocks.append(Stock(
                        code=code,
                        name=name,
                        exchange=exchange,
                        industry=industry if industry and industry != 'nan' else None,
                        concept=concept if concept and concept != 'nan' else None,
                        status="active"
                    ))
            except Exception as e:
                print(f"stock_zh_a_spot_em 失败：{e}，使用备用方案...")

            # 备用方案：分别获取各交易所数据（不包含行业信息）
            if not api_success:
                for market_func, exchange_code in [
                    (ak.stock_sh_a_spot_em, "SH"),
                    (ak.stock_sz_a_spot_em, "SZ"),
                    (ak.stock_bj_a_spot_em, "BJ")
                ]:
                    try:
                        df = market_func()
                        for _, row in df.iterrows():
                            code = str(row.iloc[1])
                            name = self._convert_name(str(row.iloc[2]))
                            stocks.append(Stock(
                                code=code,
                                name=name,
                                exchange=exchange_code,
                                industry=None,
                                concept=None,
                                status="active"
                            ))
                    except Exception:
                        pass

            # 批量插入或更新
            for stock in stocks:
                existing = self.db.query(Stock).filter(Stock.code == stock.code).first()
                if existing:
                    # 更新现有记录
                    existing.name = stock.name
                    existing.exchange = stock.exchange
                    if stock.industry:
                        existing.industry = stock.industry
                    if stock.concept:
                        existing.concept = stock.concept
                else:
                    # 新增记录
                    self.db.add(stock)

            self.db.commit()
            return len(stocks)
        except Exception as e:
            self.db.rollback()
            print(f"获取股票列表失败：{e}")
            return 0

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
