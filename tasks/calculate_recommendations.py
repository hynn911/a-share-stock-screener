"""
盘后推荐计算任务
每天收盘后自动计算股票推荐结果并存入数据库
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.models import Stock, StockRecommendation, StockDaily
from core.stock_scorer import StockScorer
from datetime import date, datetime, timedelta
from sqlalchemy import desc, func
import time


def calculate_daily_recommendations(trade_date: date = None):
    """
    计算指定日期的股票推荐结果

    Args:
        trade_date: 交易日期，默认为今天
    """
    if trade_date is None:
        trade_date = date.today()

    print(f"开始计算 {trade_date} 的推荐结果...")
    start_time = time.time()

    db = SessionLocal()
    scorer = StockScorer()

    try:
        # 检查是否已经计算过
        existing = db.query(StockRecommendation).filter(
            StockRecommendation.trade_date == trade_date
        ).first()

        if existing:
            print(f"{trade_date} 的推荐结果已存在，是否重新计算？(y/n)")
            choice = input().strip().lower()
            if choice != 'y':
                print("已跳过")
                return

        # 使用 scorer 的优化方法获取推荐结果
        print("正在计算所有股票评分...")
        results = scorer.get_top_stocks_raw(trade_date=trade_date)

        # 批量插入推荐结果
        print(f"正在保存 {len(results)} 条推荐结果...")

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
            db.add(record)

            # 每 100 条提交一次
            if rank % 100 == 0:
                db.commit()
                print(f"  已保存 {rank}/{len(results)} 条")

        db.commit()  # 提交剩余的

        elapsed = time.time() - start_time
        print(f"计算完成！共 {len(results)} 只股票，耗时 {elapsed:.2f}秒")

    except Exception as e:
        db.rollback()
        print(f"计算失败：{e}")
        raise
    finally:
        scorer.close()
        db.close()


def auto_calculate_latest():
    """自动计算最新交易日期的推荐结果"""
    db = SessionLocal()

    try:
        # 获取最新的交易日期（从 stock_daily 表）
        latest_trade = db.query(
            func.max(StockDaily.trade_date)
        ).scalar()

        if not latest_trade:
            print("未找到交易数据")
            return

        # 检查是否已计算
        existing = db.query(StockRecommendation).filter(
            StockRecommendation.trade_date == latest_trade
        ).first()

        if existing:
            print(f"{latest_trade} 的推荐结果已存在")
            return

        print(f"最新交易日期：{latest_trade}")
        calculate_daily_recommendations(latest_trade)

    finally:
        db.close()


if __name__ == "__main__":
    from sqlalchemy import func

    print("=== 盘后推荐计算任务 ===")
    print("1. 计算最新交易日")
    print("2. 计算指定日期")
    choice = input("请选择 (1/2): ").strip()

    if choice == "1":
        auto_calculate_latest()
    else:
        date_str = input("请输入日期 (YYYY-MM-DD): ").strip()
        trade_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        calculate_daily_recommendations(trade_date)
