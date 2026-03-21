"""
更新股票列表 - 获取行业和概念板块信息
支持缓存和备用数据源
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_fetcher import DataFetcher
from core.database import SessionLocal
from core.models import Stock
from core.data_cache import StockDataCache
import akshare as ak
import time
import socket

def update_stock_info(use_cache=True, force_refresh=False):
    """
    更新股票列表

    Args:
        use_cache: 是否使用缓存（默认 True）
        force_refresh: 是否强制刷新（默认 False）
    """

    print("=" * 60)
    print("开始更新股票列表...")
    print("=" * 60)

    # 检查网络连接
    def check_network():
        try:
            socket.create_connection(("www.eastmoney.com", 80), timeout=5)
            return True
        except:
            return False

    if not check_network():
        print("警告：网络连接不可用，尝试使用缓存...")
        force_refresh = False

    # 尝试从缓存加载
    cache = StockDataCache()
    if use_cache and not force_refresh:
        cached_stocks = cache.get_cached_stock_list(max_age_days=7)
        if cached_stocks:
            print(f"使用缓存数据：{len(cached_stocks)} 只股票")
            # 将缓存数据写入数据库
            db = SessionLocal()
            for item in cached_stocks:
                stock = db.query(Stock).filter(Stock.code == item.get("code")).first()
                if not stock:
                    stock = Stock(
                        code=item.get("code"),
                        name=item.get("name"),
                        exchange=item.get("exchange"),
                        industry=item.get("industry"),
                        concept=item.get("concept"),
                        status="active"
                    )
                    db.add(stock)
            db.commit()
            db.close()
            print("缓存数据已同步到数据库")
            return True

    fetcher = DataFetcher()

    # 增加重试次数和超时时间
    max_retries = 5
    base_delay = 3  # 初始等待时间（秒）

    for i in range(max_retries):
        try:
            print(f"\n尝试第 {i+1}/{max_retries} 次...")

            # 使用 DataFetcher 的备用数据源
            count = fetcher.fetch_stock_list()

            if count > 0:
                print(f"成功获取数据：{count} 只股票")

                # 保存到缓存
                db = SessionLocal()
                all_stocks = db.query(Stock).all()
                stock_data = [
                    {
                        "code": s.code,
                        "name": s.name,
                        "exchange": s.exchange,
                        "industry": s.industry,
                        "concept": s.concept
                    }
                    for s in all_stocks
                ]
                cache.save_stock_list(stock_data)
                db.close()

                # 验证结果
                db = SessionLocal()
                stocks_with_industry = db.query(Stock).filter(Stock.industry != None).count()
                stocks_with_concept = db.query(Stock).filter(Stock.concept != None).count()
                total = db.query(Stock).count()
                db.close()

                print(f"\n统计结果:")
                print(f"  总股票数：{total} 只")
                print(f"  有行业数据的股票：{stocks_with_industry} 只")
                print(f"  有概念数据的股票：{stocks_with_concept} 只")

                fetcher.close()
                return True
            else:
                print("获取到的数据为空")

        except Exception as e:
            print(f"失败：{e}")
            if i < max_retries - 1:
                delay = base_delay * (2 ** i)
                print(f"等待 {delay} 秒后重试...")
                time.sleep(delay)
            else:
                print("\n所有尝试失败")
                # 尝试使用缓存
                if use_cache:
                    print("尝试使用旧缓存数据...")
                    cached_stocks = cache.get_cached_stock_list(max_age_days=30)
                    if cached_stocks:
                        print(f"使用过期缓存：{len(cached_stocks)} 只股票（数据可能不是最新）")
                        return True
                print("无可用缓存，更新失败")
                fetcher.close()
                return False

    fetcher.close()
    return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="更新股票列表")
    parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
    parser.add_argument("--force", action="store_true", help="强制刷新")
    args = parser.parse_args()

    update_stock_info(
        use_cache=not args.no_cache,
        force_refresh=args.force
    )
