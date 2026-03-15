"""
初始化脚本 - 获取股票列表和历史数据
"""
import sys
sys.path.append('.')

from core.database import init_db
from core.data_fetcher import DataFetcher
from core.models import Stock


def init_stock_list():
    """初始化股票列表"""
    print("正在获取 A 股列表...")
    fetcher = DataFetcher()
    count = fetcher.fetch_stock_list()
    print(f"已获取 {count} 只股票")
    fetcher.close()


def init_history_data(limit: int = 100):
    """初始化历史数据（前 N 只股票）"""
    print(f"正在获取历史数据（前{limit}只股票）...")

    db = SessionLocal()
    stocks = db.query(Stock).limit(limit).all()

    fetcher = DataFetcher()
    for i, stock in enumerate(stocks):
        print(f"[{i+1}/{limit}] 获取 {stock.code} - {stock.name}")

        # 获取日线数据
        fetcher.fetch_daily_bars(stock.code, start_date="20230101")

        # 获取资金流
        fetcher.fetch_capital_flow(stock.code)

        # 获取股东户数
        fetcher.fetch_shareholder_count(stock.code)

        # 避免请求过快
        import time
        time.sleep(0.5)

    fetcher.close()
    db.close()
    print("历史数据获取完成!")


if __name__ == "__main__":
    # 初始化数据库
    init_db()

    # 初始化股票列表
    init_stock_list()

    # 初始化历史数据（前 50 只）
    from core.database import SessionLocal
    init_history_data(limit=50)
