"""
回补历史推荐数据任务
使用当前算法计算历史日期的推荐结果
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.models import StockRecommendation, StockDaily
from core.stock_scorer import StockScorer
from datetime import date, timedelta
from sqlalchemy import func, desc
import time


def backfill_historical_recommendations(start_date: date = None, end_date: date = None, skip_existing: bool = True):
    """
    回补历史推荐数据

    Args:
        start_date: 开始日期，默认为 60 天前
        end_date: 结束日期，默认为最新交易日
        skip_existing: 是否跳过已计算的日期
    """
    db = SessionLocal()
    scorer = StockScorer()

    if end_date is None:
        # 获取最新交易日
        latest = db.query(func.max(StockDaily.trade_date)).scalar()
        end_date = latest or date.today()

    if start_date is None:
        start_date = end_date - timedelta(days=60)

    print(f"开始回补历史推荐数据")
    print(f"期间：{start_date} 至 {end_date}")
    print(f"跳过已存在：{skip_existing}")
    print("-" * 50)

    # 获取所有交易日
    trade_dates = db.query(StockDaily.trade_date).filter(
        StockDaily.trade_date >= start_date,
        StockDaily.trade_date <= end_date
    ).distinct().order_by(StockDaily.trade_date).all()

    trade_dates = [t[0] for t in trade_dates]
    print(f"共 {len(trade_dates)} 个交易日")

    total_added = 0
    total_skipped = 0

    for i, trade_date in enumerate(trade_dates, 1):
        # 检查是否已存在
        existing = db.query(StockRecommendation).filter(
            StockRecommendation.trade_date == trade_date
        ).first()

        if existing and skip_existing:
            print(f"[{i}/{len(trade_dates)}] {trade_date}: 已存在，跳过")
            total_skipped += 1
            continue

        print(f"[{i}/{len(trade_dates)}] {trade_date}: 正在计算...")
        start_time = time.time()

        try:
            # 使用 scorer 计算推荐结果
            results = scorer.get_top_stocks_raw(trade_date=trade_date)

            # 批量插入
            records = []
            for rank, item in enumerate(results, start=1):
                record = StockRecommendation(
                    trade_date=trade_date,
                    stock_code=item['stock_code'],
                    stock_name=item['stock_name'],
                    total_score=item['total_score'],
                    capital_score=item['scores'].get('capital'),
                    technical_score=item['scores'].get('technical'),
                    holder_score=item['scores'].get('holder'),
                    news_score=item['scores'].get('news'),
                    momentum_score=item['scores'].get('momentum'),
                    rank=rank
                )
                records.append(record)

                # 每 200 条提交一次
                if len(records) % 200 == 0:
                    db.bulk_save_objects(records)
                    db.commit()
                    records = []

            # 提交剩余的
            if records:
                db.bulk_save_objects(records)
                db.commit()

            elapsed = time.time() - start_time
            print(f"  完成：{len(results)} 只股票，耗时 {elapsed:.2f}秒")
            total_added += 1

        except Exception as e:
            db.rollback()
            print(f"  失败：{e}")

    print("-" * 50)
    print(f"回补完成！")
    print(f"新增：{total_added} 天")
    print(f"跳过：{total_skipped} 天")

    scorer.close()
    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="回补历史推荐数据")
    parser.add_argument("--start", type=str, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=60, help="回补天数 (默认 60 天)")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的数据")

    args = parser.parse_args()

    start_date = None
    end_date = None

    if args.start:
        start_date = date.fromisoformat(args.start)
    elif args.days:
        start_date = date.today() - timedelta(days=args.days)

    if args.end:
        end_date = date.fromisoformat(args.end)

    backfill_historical_recommendations(
        start_date=start_date,
        end_date=end_date,
        skip_existing=not args.overwrite
    )
