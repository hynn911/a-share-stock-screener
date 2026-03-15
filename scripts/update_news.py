"""
更新新闻数据脚本
"""
import sys
sys.path.append('.')

from core.database import SessionLocal
from core.data_fetcher import DataFetcher
from core.models import Stock


def update_news(limit: int = 20):
    """更新前 N 只股票的新闻"""
    print(f"正在更新新闻数据（前{limit}只股票）...")

    db = SessionLocal()
    stocks = db.query(Stock).limit(limit).all()

    fetcher = DataFetcher()
    total_news = 0
    for i, stock in enumerate(stocks):
        print(f"[{i+1}/{limit}] 获取 {stock.code} - {stock.name} 新闻")

        # 获取新闻
        count = fetcher.fetch_stock_news(stock.code)
        total_news += count
        print(f"  获取 {count} 条新闻")

        # 避免请求过快
        import time
        time.sleep(0.3)

    fetcher.close()
    db.close()
    print(f"\n新闻数据更新完成！共获取 {total_news} 条新闻")


if __name__ == "__main__":
    update_news(limit=20)
