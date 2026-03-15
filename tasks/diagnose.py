"""
系统状态诊断脚本
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.models import Stock, StockDaily, StockCapitalFlow, StockNews
import akshare as ak


def diagnose():
    """执行系统诊断"""
    print("=" * 60)
    print("系统状态诊断")
    print("=" * 60)

    db = SessionLocal()

    try:
        # 1. 检查股票数据
        total_stocks = db.query(Stock).count()
        stocks_with_industry = db.query(Stock).filter(Stock.industry != None).count()
        stocks_with_concept = db.query(Stock).filter(Stock.concept != None).count()

        print(f"\n1. 股票数据:")
        print(f"   总股票数：{total_stocks}")
        print(f"   有行业数据：{stocks_with_industry} ({stocks_with_industry/total_stocks*100:.1f}%)")
        print(f"   有概念数据：{stocks_with_concept} ({stocks_with_concept/total_stocks*100:.1f}%)")

        # 2. 检查日线数据
        latest_daily = db.query(StockDaily.trade_date).distinct().order_by(StockDaily.trade_date.desc()).first()
        if latest_daily:
            print(f"\n2. 日线数据:")
            print(f"   最新日期：{latest_daily[0]}")

        # 3. 检查资金流数据
        latest_flow = db.query(StockCapitalFlow.trade_date).distinct().order_by(StockCapitalFlow.trade_date.desc()).first()
        if latest_flow:
            print(f"\n3. 资金流数据:")
            print(f"   最新日期：{latest_flow[0]}")

        # 4. 检查新闻数据
        latest_news = db.query(StockNews.publish_time).distinct().order_by(StockNews.publish_time.desc()).first()
        if latest_news:
            print(f"\n4. 新闻数据:")
            print(f"   最新时间：{latest_news[0]}")

        # 5. 测试 AkShare API 连接
        print(f"\n5. AkShare API 测试:")
        try:
            df = ak.stock_zh_a_spot_em()
            print(f"   状态：正常 [OK]")
            print(f"   获取到 {len(df)} 只股票数据")
            print(f"   可用列：{', '.join(df.columns.tolist())}")
        except Exception as e:
            print(f"   状态：失败 [FAIL]")
            print(f"   错误：{e}")
            print(f"\n   建议:")
            print(f"   - 等待 15-30 分钟后重试（可能是临时限流）")
            print(f"   - 检查网络连接")
            print(f"   - AkShare 是完全免费的，不需要注册或购买")

        db.close()

        print("\n" + "=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    diagnose()
