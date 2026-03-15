"""
数据库索引优化脚本
"""
import sys
sys.path.append('.')

from core.database import engine, SessionLocal
from sqlalchemy import text

def create_indexes():
    """创建优化索引"""
    print("=" * 60)
    print("数据库索引优化")
    print("=" * 60)

    indexes = [
        # 日线数据复合索引
        ("idx_stock_daily_code_date", "stock_daily", "stock_code, trade_date DESC"),

        # 资金流复合索引
        ("idx_stock_flow_code_date", "stock_capital_flow", "stock_code, trade_date DESC"),

        # 资金流按净额索引（用于筛选）
        ("idx_stock_flow_net_inflow", "stock_capital_flow", "net_inflow DESC"),

        # 新闻复合索引
        ("idx_stock_news_code_date", "stock_news", "stock_code, publish_time DESC"),

        # 股东户数复合索引
        ("idx_stock_holder_code_date", "stock_holder_count", "stock_code, trade_date DESC"),

        # 股东户数按变化比例索引（用于筛选筹码集中）
        ("idx_stock_holder_change_ratio", "stock_holder_count", "change_ratio ASC"),

        # 持仓状态索引
        ("idx_position_status", "positions", "status"),

        # 热词统计索引
        ("idx_hot_words_created", "hot_words", "created_at DESC"),
    ]

    db = SessionLocal()

    for idx_name, table, columns in indexes:
        try:
            # 检查索引是否已存在
            result = db.execute(text(f"""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name='{idx_name}'
            """)).fetchone()

            if result:
                print(f"[跳过] 索引 {idx_name} 已存在")
            else:
                # 创建索引
                db.execute(text(f"CREATE INDEX {idx_name} ON {table} ({columns})"))
                db.commit()
                print(f"[OK] 创建索引 {idx_name} ON {table}({columns})")

        except Exception as e:
            print(f"[错误] 创建索引 {idx_name} 失败：{e}")
            db.rollback()

    db.close()

    print("\n" + "=" * 60)
    print("索引优化完成！")
    print("=" * 60)

    # 显示现有索引
    print("\n现有索引列表:")
    db = SessionLocal()
    result = db.execute(text("""
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type='index' AND sql IS NOT NULL
        ORDER BY tbl_name, name
    """)).fetchall()

    for name, tbl_name, sql in result:
        print(f"  {tbl_name}.{name}")

    db.close()


if __name__ == "__main__":
    create_indexes()
