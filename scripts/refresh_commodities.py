"""
大宗商品价格刷新脚本
"""
import argparse
import os
import sys
import pandas as pd
from datetime import datetime

# 添加项目根目录到 Python 路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# 设置控制台 UTF-8 编码输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from core.database import SessionLocal
from core.commodity import CommodityMonitor, format_alert_text
from core.models import CommodityPrice


def refresh_commodity_prices():
    """刷新大宗商品价格数据"""
    print("=" * 50)
    print("大宗商品价格刷新")
    print("=" * 50)

    # 初始化数据库表
    from core.database import init_db
    init_db()

    db = SessionLocal()
    monitor = CommodityMonitor()

    try:
        # 获取最新价格数据
        print("\n正在获取大宗商品价格...")
        data = monitor.fetch_commodity_prices()

        if data.empty:
            print("[WARN] 未能获取大宗商品价格数据")
            return

        print(f"[OK] 获取到 {len(data)} 个商品价格")

        # 保存到数据库
        saved_count = 0
        for _, row in data.iterrows():
            try:
                commodity_name = row.get('commodity_name', '')
                trade_date = row.get('trade_date', datetime.now().date())
                spot_price = row.get('spot_price', 0)

                # 检查是否已存在
                existing = db.query(CommodityPrice).filter(
                    CommodityPrice.commodity_name == commodity_name,
                    CommodityPrice.trade_date == trade_date
                ).first()

                if existing:
                    # 更新现有记录
                    existing.spot_price = spot_price
                    existing.near_contract = row.get('near_contract', '')
                    existing.near_contract_price = row.get('near_contract_price', 0)
                    existing.dominant_contract = row.get('dominant_contract', '')
                    existing.dominant_contract_price = row.get('dominant_contract_price', 0)
                    if 'dom_basis_rate' in row:
                        try:
                            existing.price_change_1d = float(row['dom_basis_rate']) * 100
                        except (ValueError, TypeError):
                            pass
                else:
                    # 插入新记录
                    price_record = CommodityPrice(
                        commodity_name=commodity_name,
                        trade_date=trade_date,
                        spot_price=spot_price,
                        near_contract=row.get('near_contract', ''),
                        near_contract_price=row.get('near_contract_price', 0),
                        dominant_contract=row.get('dominant_contract', ''),
                        dominant_contract_price=row.get('dominant_contract_price', 0)
                    )
                    if 'dom_basis_rate' in row:
                        try:
                            price_record.price_change_1d = float(row['dom_basis_rate']) * 100
                        except (ValueError, TypeError):
                            pass

                    db.add(price_record)
                    saved_count += 1

            except Exception as e:
                print(f"[WARN] 处理 {commodity_name if 'commodity_name' in locals() else 'unknown'} 失败：{e}")
                continue

        # 提交事务
        db.commit()
        print(f"[OK] 保存 {saved_count} 条新记录")

        # 检查预警
        print("\n正在检查价格预警...")
        alerts = monitor.get_commodities_with_alert(threshold=10.0)

        # 输出格式化的预警信息
        print("\n" + format_alert_text(alerts, threshold=10.0))

    except Exception as e:
        print(f"[ERROR] 刷新失败：{e}")
        db.rollback()
    finally:
        db.close()
        monitor.close()

    print("\n" + "=" * 50)
    print("刷新完成")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="刷新大宗商品价格数据")
    parser.add_argument("--check-alerts", action="store_true", help="仅检查预警，不更新数据")
    parser.add_argument("--threshold", type=float, default=10.0, help="预警阈值 (默认：10.0%)")

    args = parser.parse_args()

    if args.check_alerts:
        monitor = CommodityMonitor()
        try:
            alerts = monitor.get_commodities_with_alert(threshold=args.threshold)
            print(format_alert_text(alerts, threshold=args.threshold))
        finally:
            monitor.close()
    else:
        refresh_commodity_prices()
