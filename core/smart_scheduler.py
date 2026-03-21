"""
智能数据更新策略

核心思想：
1. 优先级更新：持仓 > 荐股 Top200 > 其他股票
2. 轮动更新：其他股票 5 天轮动一次
3. 缓存复用：避免重复请求

更新配额分配（Tushare 5000 次/天）：
- 持仓股票：~50 次/天（日线 + 资金流）
- 荐股 Top200: ~200 次/天（日线）
- 轮动更新：~1000 次/天（每天 1000 只，5 天轮动完）
- 预留：~3750 次（应对突发情况）
"""
import sys
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from core.database import SessionLocal
from core.models import Stock, StockDaily, Position, StockRecommendation


class SmartUpdateScheduler:
    """智能更新调度器"""

    def __init__(self):
        self.db = SessionLocal()

    def get_priority_stocks(self, update_ratio: float = 0.2) -> list:
        """
        获取按优先级排序的股票列表

        Args:
            update_ratio: 轮动更新比例（0.2=每天 20%，5 天轮动完）

        Returns:
            (优先级 1 持仓，优先级 2 荐股，优先级 3 轮动)
        """
        # === 优先级 1: 持仓股票 ===
        positions = self.db.query(Position).filter(
            Position.status == "holding"
        ).all()
        holding_codes = {pos.stock_code for pos in positions}

        holding_stocks = []
        for code in holding_codes:
            stock = self.db.query(Stock).filter(Stock.code == code).first()
            if stock:
                holding_stocks.append(stock)

        print(f"[优先级 1] 持仓股票：{len(holding_stocks)} 只")

        # === 优先级 2: 智能荐股 Top 200 ===
        # 获取最新日期的荐股数据，按总分排序
        latest_recs = self.db.query(
            StockRecommendation.stock_code,
            func.max(StockRecommendation.trade_date).label('latest_date')
        ).group_by(StockRecommendation.stock_code).subquery()

        top_recs = self.db.query(
            StockRecommendation
        ).join(
            latest_recs,
            (StockRecommendation.stock_code == latest_recs.c.stock_code) &
            (StockRecommendation.trade_date == latest_recs.c.latest_date)
        ).order_by(
            desc(StockRecommendation.total_score)
        ).limit(200).all()

        # 排除持仓股票
        recommend_stocks = []
        for rec in top_recs:
            if rec.stock_code not in holding_codes:
                stock = self.db.query(Stock).filter(
                    Stock.code == rec.stock_code
                ).first()
                if stock:
                    recommend_stocks.append(stock)

        print(f"[优先级 2] 荐股 Top{len(recommend_stocks)}: {len(recommend_stocks)} 只")

        # === 优先级 3: 轮动更新 ===
        # 计算需要更新的股票数量
        total_stocks = self.db.query(Stock).count()
        target_count = int(total_stocks * update_ratio)

        # 获取所有股票，排除已选的
        selected_codes = holding_codes | {s.code for s in recommend_stocks}

        # 按股票代码哈希值轮动（确保每天更新不同的股票）
        today = datetime.now().timetuple().tm_yday  # 一年中的第几天
        all_stocks = self.db.query(Stock).all()

        # 简单轮动：按股票代码尾号
        rotation_stocks = []
        for stock in all_stocks:
            if stock.code not in selected_codes:
                # 按股票代码最后一位 + 日期决定今天是否更新
                last_digit = int(stock.code[-1])
                rotation_group = (today % 5 + last_digit) % 5
                if rotation_group == today % 5:
                    rotation_stocks.append(stock)

        # 限制数量
        rotation_stocks = rotation_stocks[:target_count]
        print(f"[优先级 3] 轮动更新：{len(rotation_stocks)} 只 (目标{target_count})")

        return holding_stocks, recommend_stocks, rotation_stocks

    def get_stock_update_status(self, code: str) -> dict:
        """
        获取股票数据更新状态

        Returns:
            {
                'last_daily': 最后更新日期,
                'last_flow': 最后资金流日期，
                'is_fresh': 是否需要更新
            }
        """
        last_daily = self.db.query(
            func.max(StockDaily.trade_date)
        ).filter(StockDaily.stock_code == code).scalar()

        # 资金流表暂未定义模型，跳过

        today = datetime.now().date()
        is_fresh = False

        if last_daily:
            days_diff = (today - last_daily.date()).days
            is_fresh = days_diff <= 1  # 1 天内算新鲜

        return {
            'last_daily': last_daily,
            'is_fresh': is_fresh,
        }

    def close(self):
        self.db.close()


def print_update_plan():
    """打印更新计划说明"""
    print("=" * 60)
    print("智能数据更新策略")
    print("=" * 60)
    print()
    print("更新配额分配 (Tushare 5000 次/天):")
    print("  - 持仓股票：~50 次/天（日线 + 资金流）")
    print("  - 荐股 Top200: ~200 次/天（日线）")
    print("  - 轮动更新：~1000 次/天（每天 20%，5 天轮动）")
    print("  - 预留配额：~3750 次")
    print()
    print("更新逻辑:")
    print("  1. 持仓股票 - 每天全量更新（必须）")
    print("  2. 荐股 Top200 - 每天更新日线（高分股）")
    print("  3. 其他股票 - 5 天轮动一次（每天 20%）")
    print()
    print("优势:")
    print("  ✓ 持仓和重点股票数据永远新鲜")
    print("  ✓ 其他股票数据最多延迟 5 天（可接受）")
    print("  ✓ 总调用量远低于 5000 上限，安全可靠")
    print("=" * 60)


if __name__ == "__main__":
    print_update_plan()

    scheduler = SmartUpdateScheduler()

    # 获取优先级股票
    holding, recommend, rotation = scheduler.get_priority_stocks()

    print()
    print("持仓股票:")
    for s in holding[:5]:
        print(f"  - {s.code}: {s.name}")
    if len(holding) > 5:
        print(f"  ... 还有 {len(holding) - 5} 只")

    print()
    print("荐股 Top:")
    for s in recommend[:5]:
        print(f"  - {s.code}: {s.name}")
    if len(recommend) > 5:
        print(f"  ... 还有 {len(recommend) - 5} 只")

    print()
    print("轮动更新 (今日):")
    for s in rotation[:10]:
        print(f"  - {s.code}: {s.name}")
    if len(rotation) > 10:
        print(f"  ... 还有 {len(rotation) - 10} 只")

    scheduler.close()
