"""
自动数据更新脚本
每天收盘后自动更新所有数据

更新优先级：
1. 持仓股票（positions 表）
2. 智能荐股得分高的股票（按 total_score 降序）
3. 其他股票（可选，由更新比例控制）
"""
import sys
import time
from datetime import datetime, timedelta
from sqlalchemy import desc, func
sys.path.append('.')

from core.database import SessionLocal
from core.data_fetcher import DataFetcher
from core.models import Stock, StockDaily, Position, StockRecommendation
from core.hot_words import HotWordAnalyzer


def get_stocks_without_daily() -> list:
    """获取没有日 K 数据的股票列表"""
    db = SessionLocal()

    # 查询有股票信息但没有日 K 数据的股票
    stocks_with_daily = db.query(StockDaily.stock_code).distinct().subquery()
    stocks_without = db.query(Stock).filter(
        ~Stock.code.in_(stocks_with_daily)
    ).all()

    db.close()
    return stocks_without


def get_prioritized_stocks(update_ratio: float = 0.5) -> list:
    """
    获取按优先级排序的股票列表

    Args:
        update_ratio: 更新比例 (0.0-1.0)，默认 0.5 表示只更新前 50%

    Returns:
        按优先级排序的股票列表
    """
    db = SessionLocal()
    result = []
    seen_codes = set()

    # 1. 首先获取持仓股票（最高优先级）
    print("\n[优先级 1] 获取持仓股票...")
    positions = db.query(Position).filter(Position.status == "holding").all()
    for pos in positions:
        if pos.stock_code not in seen_codes:
            stock = db.query(Stock).filter(Stock.code == pos.stock_code).first()
            if stock:
                result.append((stock, 1, 0))  # (股票，优先级，得分)
                seen_codes.add(pos.stock_code)
    print(f"  找到 {len(positions)} 只持仓股票")

    # 2. 获取最新日期的智能荐股数据，按得分排序
    print("\n[优先级 2] 获取智能荐股推荐...")
    latest_recommendations = db.query(
        StockRecommendation.stock_code,
        StockRecommendation.total_score,
        func.max(StockRecommendation.trade_date).label('latest_date')
    ).group_by(StockRecommendation.stock_code).all()

    # 按得分降序排序
    sorted_recs = sorted(latest_recommendations, key=lambda x: x[1] if x[1] else 0, reverse=True)

    # 计算需要更新的股票总数
    total_stocks = db.query(Stock).count()
    target_count = int(total_stocks * update_ratio)

    print(f"  数据库共有 {total_stocks} 只股票")
    print(f"  目标更新数量：{target_count} (更新比例 {update_ratio*100:.0f}%)")
    print(f"  已选持仓股票：{len(result)} 只")

    # 添加荐股股票（排除已选过的）
    remaining_slots = target_count - len(result)
    added_count = 0

    for rec in sorted_recs:
        if added_count >= remaining_slots:
            break
        if rec.stock_code not in seen_codes:
            stock = db.query(Stock).filter(Stock.code == rec.stock_code).first()
            if stock:
                result.append((stock, 2, rec.total_score or 0))
                seen_codes.add(rec.stock_code)
                added_count += 1

    print(f"  新增荐股股票：{added_count} 只")
    print(f"  总计：{len(result)} 只股票待更新")

    db.close()

    # 只返回 Stock 对象
    return [item[0] for item in result]


def update_all_data(stock_limit: int = None, test_no_daily: bool = False, update_ratio: float = 0.5):
    """更新所有数据

    Args:
        stock_limit: 限制更新的股票数量（用于测试）
        test_no_daily: 是否只测试没有日 K 数据的股票
        update_ratio: 更新比例 (0.0-1.0)，默认 0.5 表示只更新前 50%
    """
    print("=" * 60)
    print(f"自动数据更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    db = SessionLocal()
    fetcher = DataFetcher()

    if test_no_daily:
        # 测试模式：只处理没有日 K 数据的股票
        print("\n[测试模式] 获取没有日 K 数据的股票...")
        stocks = get_stocks_without_daily()
        print(f"找到 {len(stocks)} 只没有日 K 数据的股票")

        if stock_limit:
            stocks = stocks[:stock_limit]
            print(f"限制测试前 {stock_limit} 只股票")

        if not stocks:
            print("[OK] 所有股票都有日 K 数据，无需测试")
            db.close()
            fetcher.close()
            return True

        # 重置限流器计数器，开始新的测试周期
        fetcher.limiter.reset()

        print(f"\n[测试] 更新日 K 数据 ({len(stocks)} 只股票)...")
        total_daily = 0
        success_count = 0
        fail_count = 0

        for i, stock in enumerate(stocks):
            try:
                count = fetcher.fetch_daily_bars(stock.code, start_date="20240101")
                total_daily += count
                if count > 0:
                    success_count += 1
                    print(f"  进度：{i+1}/{len(stocks)} | {stock.code} {stock.name} | 成功获取 {count} 条 | 总成功：{success_count} | 失败：{fail_count}")
                else:
                    fail_count += 1
                    print(f"  进度：{i+1}/{len(stocks)} | {stock.code} {stock.name} | 无数据 | 总成功：{success_count} | 失败：{fail_count}")
            except Exception as e:
                fail_count += 1
                print(f"  进度：{i+1}/{len(stocks)} | {stock.code} {stock.name} | 异常：{e}")
            time.sleep(0.1)  # 额外延迟，确保限流

        print(f"\n[测试完成] 成功：{success_count}/{len(stocks)}, 失败：{fail_count}, 总条数：{total_daily:,}")
        fetcher.close()
        db.close()
        return True

    # 正常更新模式
    print("\n[1/5] 更新股票列表...")
    try:
        fetcher.fetch_stock_list()
        print("[OK] 股票列表更新完成")
    except Exception as e:
        print(f"[错误] 股票列表更新失败：{e}")

    # 获取按优先级排序的股票列表
    print(f"\n[智能排序] 按优先级获取股票列表 (更新比例：{update_ratio*100:.0f}%)...")
    stocks = get_prioritized_stocks(update_ratio=update_ratio)

    if stock_limit:
        stocks = stocks[:stock_limit]
        print(f"[限制] 限定更新前 {stock_limit} 只股票")

    if not stocks:
        print("[警告] 没有股票需要更新")
        db.close()
        fetcher.close()
        return True

    # 重置限流器计数器
    fetcher.limiter.reset()

    print(f"\n[2/5] 更新日线数据 ({len(stocks)} 只股票)...")
    total_daily = 0
    for i, stock in enumerate(stocks):
        try:
            count = fetcher.fetch_daily_bars(stock.code, start_date="20240101")
            total_daily += count
            if (i + 1) % 50 == 0:
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
            if (i + 1) % 50 == 0:
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
            if (i + 1) % 50 == 0:
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
            if (i + 1) % 50 == 0:
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
    print(f"更新股票数：{len(stocks)} / 总数 (比例：{update_ratio*100:.0f}%)")
    print("=" * 60)

    return True


if __name__ == "__main__":
    # 命令行参数解析
    limit = None
    test_no_daily = False
    update_ratio = 0.5  # 默认更新 50%

    for arg in sys.argv[1:]:
        if arg == "--test-no-daily":
            test_no_daily = True
        elif arg.startswith("--ratio="):
            try:
                update_ratio = float(arg.split("=")[1])
                # 限制在 0.0-1.0 范围
                update_ratio = max(0.0, min(1.0, update_ratio))
            except ValueError:
                pass
        elif arg.isdigit():
            limit = int(arg)

    if test_no_daily:
        print("测试模式：只更新没有日 K 数据的股票")
    elif limit is None:
        print(f"正常模式：按优先级更新前 {update_ratio*100:.0f}% 的股票")
    else:
        print(f"正常模式：按优先级更新前 {limit} 只股票")

    update_all_data(limit, test_no_daily, update_ratio)
