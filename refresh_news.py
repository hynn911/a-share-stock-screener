# -*- coding: utf-8 -*-
"""
刷新新闻数据（增量更新模式）
- 只保留最近 N 天的新闻
- 自动删除旧新闻后获取新数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal
from core.models import Stock, StockNews
from core.data_fetcher import DataFetcher
from datetime import datetime, timedelta
from sqlalchemy import func

REFRESH_DAYS = 7  # 保留最近 7 天的新闻

def refresh_news(limit=100, days=REFRESH_DAYS):
    """
    增量刷新新闻数据

    Args:
        limit: 刷新前 N 只股票
        days: 保留最近 N 天的新闻
    """
    db = SessionLocal()
    fetcher = DataFetcher()

    # 获取股票列表
    stocks = db.query(Stock).limit(limit).all()

    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days)

    total_news = 0
    success_count = 0
    skipped = 0

    for i, stock in enumerate(stocks):
        try:
            # 检查是否有该股票的旧新闻
            old_news_count = db.query(func.count(StockNews.id)).filter(
                StockNews.stock_code == stock.code,
                StockNews.publish_time < cutoff_date
            ).scalar()

            # 删除旧新闻
            if old_news_count > 0:
                db.query(StockNews).filter(
                    StockNews.stock_code == stock.code,
                    StockNews.publish_time < cutoff_date
                ).delete()
                db.commit()

            # 检查最新新闻日期
            latest_news = db.query(func.max(StockNews.publish_time)).filter(
                StockNews.stock_code == stock.code
            ).scalar()

            # 如果已经有最近的新闻，跳过
            if latest_news and latest_news >= cutoff_date:
                skipped += 1
                continue

            # 获取新新闻
            count = fetcher.fetch_stock_news(stock.code)
            total_news += count
            success_count += 1

        except Exception:
            db.rollback()

    db.commit()

    db.close()
    fetcher.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='增量刷新新闻数据')
    parser.add_argument('--limit', type=int, default=100, help='刷新股票数量')
    parser.add_argument('--days', type=int, default=7, help='保留最近 N 天新闻')
    args = parser.parse_args()

    refresh_news(limit=args.limit, days=args.days)
