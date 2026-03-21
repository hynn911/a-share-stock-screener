"""
智能数据更新脚本 - 混合数据源 + 优先级策略

策略说明：
1. 免费数据源优先（腾讯财经、Baostock）
2. Tushare 作为兜底（15:00 后使用）
3. 优先级更新：持仓 > 荐股 Top200 > 轮动更新

更新配额分配（Tushare 5000 次/天）：
- 持仓股票：每天全量更新（日线 + 资金流）
- 荐股 Top200: 每天更新日线
- 轮动更新：每天 1000 只（5 天轮动一次全部）
"""
import sys
import time
import random
from datetime import datetime, timedelta
from sqlalchemy import desc, func
sys.path.append('.')

from core.database import SessionLocal
from core.models import Stock, StockDaily, Position, StockRecommendation
from core.hybrid_fetcher import HybridDataFetcher


class SmartUpdater:
    """智能更新调度器"""

    def __init__(self):
        self.db = SessionLocal()
        self.fetcher = HybridDataFetcher()

    def get_priority_stocks(self, update_ratio: float = 0.2) -> tuple:
        """
        获取按优先级排序的股票列表

        Args:
            update_ratio: 轮动更新比例（0.2=每天 20%，5 天轮动完）

        Returns:
            (持仓股票，荐股股票，轮动股票)
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

        print(f"[优先级 2] 荐股 Top: {len(recommend_stocks)} 只")

        # === 优先级 3: 轮动更新 ===
        total_stocks = self.db.query(Stock).count()
        target_count = int(total_stocks * update_ratio)

        selected_codes = holding_codes | {s.code for s in recommend_stocks}

        # 按股票代码尾号 + 日期轮动
        today = datetime.now().timetuple().tm_yday
        all_stocks = self.db.query(Stock).all()

        rotation_stocks = []
        for stock in all_stocks:
            if stock.code not in selected_codes:
                last_digit = int(stock.code[-1])
                rotation_group = (today % 5 + last_digit) % 5
                if rotation_group == today % 5:
                    rotation_stocks.append(stock)

        rotation_stocks = rotation_stocks[:target_count]
        print(f"[优先级 3] 轮动更新：{len(rotation_stocks)} 只 (目标{target_count})")

        return holding_stocks, recommend_stocks, rotation_stocks

    def update_daily_bars(self, stocks: list, source: str = "") -> int:
        """
        批量更新日线数据

        Args:
            stocks: 股票列表
            source: 数据源标识

        Returns:
            成功更新的股票数量
        """
        total_saved = 0
        success_count = 0

        for i, stock in enumerate(stocks):
            try:
                # 使用混合数据源（优先免费）
                count = self.fetcher.fetch_daily_bars(
                    stock.code,
                    start_date="20240101"
                )
                total_saved += count
                success_count += 1

                # 每 50 只输出进度
                if (i + 1) % 50 == 0:
                    print(f"  进度：{i+1}/{len(stocks)}，已获取 {total_saved:,} 条")

                # 添加延迟，避免触发反爬
                time.sleep(random.uniform(0.5, 1.0))

            except Exception as e:
                print(f"  获取 {stock.code} 日线失败：{e}")

        source_label = f"({source})" if source else ""
        print(f"[OK] 日线数据更新完成{source_label}，共 {total_saved:,} 条，成功 {success_count}/{len(stocks)} 只")
        return success_count

    def update_realtime_prices(self, stocks: list) -> int:
        """
        批量更新实时价格（使用腾讯财经批量接口）

        Returns:
            成功更新的股票数量
        """
        codes = [s.code for s in stocks]
        prices = self.fetcher.get_batch_prices(codes)

        print(f"  获取到 {len(prices)}/{len(codes)} 只股票的实时价格")
        return len(prices)

    def run_update(self, update_ratio: float = 0.2, skip_daily: bool = False):
        """
        执行更新任务

        Args:
            update_ratio: 轮动更新比例
            skip_daily: 是否跳过日线更新（只获取实时价格）
        """
        print("=" * 60)
        print(f"智能数据更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 检查 Tushare 可用性
        is_tushare_time = self.fetcher.is_tushare_available()
        if is_tushare_time:
            print("[提示] 当前可以使用 Tushare（15:00 后）")
        else:
            print("[提示] 当前使用免费数据源（腾讯财经 + Baostock）")

        # 获取优先级股票
        holding, recommend, rotation = self.get_priority_stocks(update_ratio)

        # 合并所有需要更新的股票
        all_stocks = holding + recommend + rotation
        print()
        print(f"[总计] 待更新 {len(all_stocks)} 只股票")
        print()

        if not all_stocks:
            print("[警告] 没有股票需要更新")
            return

        # === 步骤 1: 获取实时价格（腾讯财经批量） ===
        print("[1/3] 获取实时价格...")
        self.update_realtime_prices(all_stocks)
        print()

        if skip_daily:
            print("[跳过] 日线数据更新")
        else:
            # === 步骤 2: 更新日线数据 ===
            print("[2/3] 更新日线数据...")

            # 分批更新：持仓 > 荐股 > 轮动
            if holding:
                print("\n[持仓股票] 更新日线...")
                self.update_daily_bars(holding, "持仓")

            if recommend:
                print("\n[荐股 Top] 更新日线...")
                self.update_daily_bars(recommend, "荐股")

            if rotation:
                print("\n[轮动更新] 更新日线...")
                self.update_daily_bars(rotation, "轮动")

        print()
        print("[3/3] 资金流数据更新...")
        # 资金流仅 Tushare 支持，15:00 前跳过
        if is_tushare_time:
            flow_count = 0
            for stock in holding[:20]:  # 只更新持仓的前 20 只
                try:
                    count = self.fetcher.fetch_capital_flow(stock.code)
                    flow_count += count
                    time.sleep(random.uniform(0.5, 1.0))
                except Exception as e:
                    pass
            print(f"[OK] 资金流数据更新完成，共 {flow_count:,} 条")
        else:
            print("[跳过] 资金流数据需要 15:00 后使用 Tushare")

        print()
        print("=" * 60)
        print("数据更新完成!")
        print("=" * 60)

    def close(self):
        self.db.close()
        self.fetcher.close()


if __name__ == "__main__":
    # 命令行参数解析
    ratio = 0.2  # 默认轮动比例
    skip_daily = False

    for arg in sys.argv[1:]:
        if arg.startswith("--ratio="):
            try:
                ratio = float(arg.split("=")[1])
                ratio = max(0.0, min(1.0, ratio))
            except ValueError:
                pass
        elif arg == "--skip-daily":
            skip_daily = True
        elif arg.isdigit():
            ratio = int(arg) / 5000  # 根据数量反推比例

    print(f"更新配置：轮动比例={ratio*100:.0f}%, 跳过日线={skip_daily}")
    print()

    updater = SmartUpdater()
    try:
        updater.run_update(update_ratio=ratio, skip_daily=skip_daily)
    finally:
        updater.close()
