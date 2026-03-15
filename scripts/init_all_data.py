"""
完整数据初始化脚本 - 一次性初始化所有数据
"""
import sys
sys.path.append('.')

from core.database import init_db, SessionLocal
from core.data_fetcher import DataFetcher
from core.models import Stock
import time


def init_all_data(stock_limit: int = 100):
    """初始化所有数据"""
    print("=" * 60)
    print("A 股高价值股票发掘系统 - 数据初始化")
    print("=" * 60)

    # 初始化数据库
    print("\n[1/4] 初始化数据库表...")
    init_db()
    print("[OK] 数据库表初始化完成")

    # 获取股票列表
    print("\n[2/4] 获取 A 股列表...")
    fetcher = DataFetcher()
    stock_count = fetcher.fetch_stock_list()
    print(f"[OK] 已获取 {stock_count} 只股票")

    # 获取历史数据
    print(f"\n[3/4] 获取历史数据（前 {stock_limit} 只股票）...")
    db = SessionLocal()
    stocks = db.query(Stock).limit(stock_limit).all()

    total_daily = 0
    total_flow = 0
    total_holder = 0

    for i, stock in enumerate(stocks):
        print(f"[{i+1}/{stock_limit}] {stock.code} - {stock.name}")

        try:
            # 获取日线数据
            daily_count = fetcher.fetch_daily_bars(stock.code, start_date="20230101")
            total_daily += daily_count
            print(f"    日线：{daily_count} 条")

            # 获取资金流
            flow_count = fetcher.fetch_capital_flow(stock.code)
            total_flow += flow_count
            print(f"    资金流：{flow_count} 条")

            # 获取股东户数
            holder_count = fetcher.fetch_shareholder_count(stock.code)
            total_holder += holder_count
            print(f"    股东户数：{holder_count} 条")

        except Exception as e:
            print(f"    错误：{e}")

        # 避免请求过快
        time.sleep(0.8)

    fetcher.close()
    db.close()

    print(f"\n[OK] 历史数据获取完成!")
    print(f"   - 日线数据：{total_daily:,} 条")
    print(f"   - 资金流数据：{total_flow:,} 条")
    print(f"   - 股东户数数据：{total_holder:,} 条")

    # 获取新闻数据
    print(f"\n[4/4] 获取新闻数据（前 {stock_limit} 只股票）...")
    db = SessionLocal()
    stocks = db.query(Stock).limit(stock_limit).all()

    fetcher = DataFetcher()
    total_news = 0

    for i, stock in enumerate(stocks):
        try:
            news_count = fetcher.fetch_stock_news(stock.code)
            total_news += news_count
            if news_count > 0:
                print(f"[{i+1}/{stock_limit}] {stock.code} - {stock.name}: {news_count} 条新闻")
        except Exception as e:
            pass

        time.sleep(0.3)

    fetcher.close()
    db.close()

    print(f"\n[OK] 新闻数据获取完成！共 {total_news:,} 条")

    print("\n" + "=" * 60)
    print("数据初始化全部完成！")
    print("=" * 60)
    print("\n使用说明:")
    print("1. 启动 Streamlit 界面：streamlit run ui/app.py")
    print("2. 在浏览器中打开 http://localhost:8501")
    print("3. 开始使用系统功能")
    print("\n功能页面:")
    print("  - 首页：系统概览")
    print("  - 热点看板：市场热词分析")
    print("  - 资金监控：连续资金流入筛选")
    print("  - 选股器：技术指标分析")
    print("  - 持仓管理：持仓管理与卖点建议")
    print("  - 消息中心：个股新闻")
    print("  - 股东户数：股东户数变化分析")


if __name__ == "__main__":
    # 可自定义初始化的股票数量
    stock_limit = 100 if len(sys.argv) < 2 else int(sys.argv[1])
    init_all_data(stock_limit)
