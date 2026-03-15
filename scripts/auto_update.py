"""
自动数据更新脚本
每天收盘后自动更新所有数据
"""
import sys
import time
from datetime import datetime, timedelta
sys.path.append('.')

from core.database import SessionLocal
from core.data_fetcher import DataFetcher
from core.models import Stock
from core.hot_words import HotWordAnalyzer


def is_trading_day() -> bool:
    """判断是否为交易日（简单实现：周一至周五）"""
    today = datetime.now()
    return today.weekday() < 5  # 0-4 为周一到周五


def is_after_market_close() -> bool:
    """判断是否已收盘（A 股 15:00 收盘）"""
    now = datetime.now()
    # 15:30 之后才更新，确保交易所数据已发布
    return now.hour >= 15 and now.minute >= 30


def check_data_freshness() -> dict:
    """检查数据新鲜度"""
    db = SessionLocal()

    # 检查各类数据的最新日期
    from sqlalchemy import func, desc
    from core.models import StockDaily, StockCapitalFlow, StockHolderCount, StockNews

    # 日线数据
    latest_daily = db.query(func.max(StockDaily.trade_date)).scalar()

    # 资金流数据
    latest_flow = db.query(func.max(StockCapitalFlow.trade_date)).scalar()

    # 股东户数
    latest_holder = db.query(func.max(StockHolderCount.trade_date)).scalar()

    # 新闻
    latest_news = db.query(func.max(StockNews.publish_time)).scalar()

    db.close()

    today = datetime.now().date()

    def days_diff(date_val):
        """计算日期差"""
        if not date_val:
            return 999
        if isinstance(date_val, datetime):
            return (today - date_val.date()).days
        elif isinstance(date_val, datetime):
            return (today - date_val).days
        else:
            return (today - date_val).days

    return {
        'daily': latest_daily,
        'flow': latest_flow,
        'holder': latest_holder,
        'news': latest_news,
        'needs_update': any([
            latest_daily and days_diff(latest_daily) > 1,
            latest_flow and days_diff(latest_flow) > 1,
            latest_holder and days_diff(latest_holder) > 3,
            latest_news and days_diff(latest_news) > 1,
        ])
    }


def update_all_data(stock_limit: int = None):
    """更新所有数据"""
    print("=" * 60)
    print(f"自动数据更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 检查是否为交易日且已收盘
    if is_trading_day() and not is_after_market_close():
        print("[跳过] 尚未收盘，等待 15:30 后再更新")
        return False

    # 检查数据新鲜度
    freshness = check_data_freshness()
    if not freshness['needs_update']:
        print("[OK] 数据已是最新，无需更新")
        return True

    print("\n[1/5] 更新股票列表...")
    fetcher = DataFetcher()
    try:
        fetcher.fetch_stock_list()
        print("[OK] 股票列表更新完成")
    except Exception as e:
        print(f"[错误] 股票列表更新失败：{e}")

    # 获取所有股票
    db = SessionLocal()
    query = db.query(Stock)
    if stock_limit:
        query = query.limit(stock_limit)
    stocks = query.all()

    print(f"\n[2/5] 更新日线数据 ({len(stocks)} 只股票)...")
    total_daily = 0
    for i, stock in enumerate(stocks):
        try:
            count = fetcher.fetch_daily_bars(stock.code, start_date="20240101")
            total_daily += count
            if (i + 1) % 100 == 0:
                print(f"  进度：{i+1}/{len(stocks)}，已获取 {total_daily:,} 条")
        except Exception as e:
            pass
        time.sleep(0.1)  # 避免请求过快
    print(f"[OK] 日线数据更新完成，共 {total_daily:,} 条")

    print(f"\n[3/5] 更新资金流数据...")
    total_flow = 0
    for i, stock in enumerate(stocks):
        try:
            count = fetcher.fetch_capital_flow(stock.code)
            total_flow += count
            if (i + 1) % 100 == 0:
                print(f"  进度：{i+1}/{len(stocks)}，已获取 {total_flow:,} 条")
        except Exception as e:
            pass
        time.sleep(0.1)
    print(f"[OK] 资金流数据更新完成，共 {total_flow:,} 条")

    print(f"\n[4/5] 更新股东户数数据...")
    total_holder = 0
    for i, stock in enumerate(stocks):
        try:
            count = fetcher.fetch_shareholder_count(stock.code)
            total_holder += count
            if (i + 1) % 100 == 0:
                print(f"  进度：{i+1}/{len(stocks)}，已获取 {total_holder:,} 条")
        except Exception as e:
            pass
        time.sleep(0.15)  # 股东户数 API 较慢
    print(f"[OK] 股东户数数据更新完成，共 {total_holder:,} 条")

    print(f"\n[5/5] 更新新闻数据...")
    total_news = 0
    fetcher_news = DataFetcher()
    for i, stock in enumerate(stocks):
        try:
            count = fetcher_news.fetch_stock_news(stock.code)
            total_news += count
            if (i + 1) % 100 == 0:
                print(f"  进度：{i+1}/{len(stocks)}，已获取 {total_news:,} 条新闻")
        except Exception as e:
            pass
        time.sleep(0.2)
    print(f"[OK] 新闻数据更新完成，共 {total_news:,} 条")

    # 更新热词
    print("\n[6/5] 更新市场热词...")
    try:
        analyzer = HotWordAnalyzer()
        analyzer.update_hot_words(days=7)
        analyzer.close()
        print("[OK] 市场热词更新完成")
    except Exception as e:
        print(f"[错误] 热词更新失败：{e}")

    fetcher.close()
    fetcher_news.close()
    db.close()

    print("\n" + "=" * 60)
    print("数据自动更新完成!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    # 可限制更新的股票数量（用于测试）
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass

    update_all_data(limit)
