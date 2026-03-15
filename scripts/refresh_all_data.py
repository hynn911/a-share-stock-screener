"""
快速刷新数据 - 更新所有股票的最新数据
"""
import sys
sys.path.append('.')

from core.database import init_db, SessionLocal
from core.data_fetcher import DataFetcher
from core.models import Stock
import time


def refresh_all_data():
    """刷新所有股票数据"""
    print("=" * 60)
    print("A 股高价值股票发掘系统 - 数据刷新")
    print("=" * 60)

    # 初始化数据库
    print("\n[1/4] 检查数据库表...")
    init_db()
    print("[OK] 数据库表检查完成")

    # 获取股票列表（如果不存在则获取）
    print("\n[2/4] 检查股票列表...")
    db = SessionLocal()
    stock_count = db.query(Stock).count()
    if stock_count == 0:
        print("股票列表为空，正在获取...")
        fetcher = DataFetcher()
        count = fetcher.fetch_stock_list()
        print(f"[OK] 已获取 {count} 只股票")
        fetcher.close()
    else:
        print(f"[OK] 已有 {stock_count} 只股票")

    # 获取历史数据
    print(f"\n[3/4] 获取历史数据（全部 {stock_count} 只股票）...")
    stocks = db.query(Stock).all()

    fetcher = DataFetcher()
    total_daily = 0
    total_flow = 0
    total_holder = 0
    success_count = 0
    error_count = 0

    for i, stock in enumerate(stocks):
        if i % 10 == 0:
            print(f"进度：{i}/{stock_count} ({i*100//stock_count}%)")

        try:
            # 获取日线数据
            daily_count = fetcher.fetch_daily_bars(stock.code, start_date="20230101")
            total_daily += daily_count

            # 获取资金流
            flow_count = fetcher.fetch_capital_flow(stock.code)
            total_flow += flow_count

            # 获取股东户数
            holder_count = fetcher.fetch_shareholder_count(stock.code)
            total_holder += holder_count

            success_count += 1

        except Exception as e:
            error_count += 1
            print(f"错误：{stock.code} - {e}")

        # 避免请求过快
        time.sleep(0.5)

    fetcher.close()

    print(f"\n[OK] 历史数据获取完成!")
    print(f"   - 成功：{success_count} 只")
    print(f"   - 失败：{error_count} 只")
    print(f"   - 日线数据：{total_daily:,} 条")
    print(f"   - 资金流数据：{total_flow:,} 条")
    print(f"   - 股东户数数据：{total_holder:,} 条")

    # 获取新闻数据
    print(f"\n[4/4] 获取新闻数据（全部 {stock_count} 只股票）...")
    stocks = db.query(Stock).all()

    fetcher = DataFetcher()
    total_news = 0
    news_success = 0

    for i, stock in enumerate(stocks):
        if i % 10 == 0:
            print(f"进度：{i}/{stock_count} ({i*100//stock_count}%)")

        try:
            news_count = fetcher.fetch_stock_news(stock.code)
            total_news += news_count
            if news_count > 0:
                news_success += 1
        except Exception:
            pass

        time.sleep(0.2)

    fetcher.close()
    db.close()

    print(f"\n[OK] 新闻数据获取完成！共 {total_news:,} 条")

    print("\n" + "=" * 60)
    print("数据刷新全部完成！")
    print("=" * 60)


if __name__ == "__main__":
    refresh_all_data()
