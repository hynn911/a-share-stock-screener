"""
诊断工具 - 检查行业数据状态并尝试多种数据源获取
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.models import Stock
import akshare as ak
import time

def check_database_status():
    """检查数据库中行业数据状态"""
    db = SessionLocal()
    try:
        total = db.query(Stock).count()
        with_industry = db.query(Stock).filter(
            Stock.industry != None,
            Stock.industry != ''
        ).count()
        with_concept = db.query(Stock).filter(
            Stock.concept != None,
            Stock.concept != ''
        ).count()

        print("=" * 60)
        print("=== 数据库行业数据状态 ===")
        print(f"总股票数：{total}")
        print(f"有行业数据：{with_industry} ({with_industry/total*100:.1f}%)")
        print(f"有概念数据：{with_concept} ({with_concept/total*100:.1f}%)")

        if with_industry > 0:
            print("\n样本数据:")
            samples = db.query(Stock).filter(
                Stock.industry != None,
                Stock.industry != ''
            ).limit(5).all()
            for s in samples:
                print(f"  {s.code} - {s.name}: 行业={s.industry}, 概念={s.concept}")

        return total, with_industry, with_concept
    finally:
        db.close()

def test_akshare_sources():
    """测试多种 AkShare 数据源"""
    print("\n" + "=" * 60)
    print("=== 测试 AkShare 数据源 ===")

    sources = [
        ("stock_zh_a_spot_em", "东方财富-全部 A 股", ak.stock_zh_a_spot_em),
        ("stock_sh_a_spot_em", "东方财富-上海 A 股", ak.stock_sh_a_spot_em),
        ("stock_sz_a_spot_em", "东方财富-深圳 A 股", ak.stock_sz_a_spot_em),
    ]

    for name, desc, func in sources:
        print(f"\n测试 {name} ({desc})...")
        try:
            df = func()
            has_industry = '行业' in df.columns
            has_concept = '概念板块' in df.columns

            print(f"  ✓ 成功获取 {len(df)} 只股票")
            print(f"  行业列：{'✓' if has_industry else '✗'}")
            print(f"  概念列：{'✓' if has_concept else '✗'}")

            if has_industry or has_concept:
                cols = ['代码', '名称']
                if has_industry:
                    cols.append('行业')
                if has_concept:
                    cols.append('概念板块')
                print(f"\n  前 3 行样本:")
                print(df[cols].head(3))
                return True, name, df
        except Exception as e:
            print(f"  ✗ 失败：{e}")

    return False, None, None

def save_to_database(df):
    """将从 AkShare 获取的数据保存到数据库"""
    print("\n" + "=" * 60)
    print("=== 保存数据到数据库 ===")

    db = SessionLocal()
    try:
        updated = 0
        for _, row in df.iterrows():
            code = str(row['代码'])
            industry = str(row.get('行业', ''))
            concept = str(row.get('概念板块', ''))

            if industry == 'nan' or not industry:
                industry = None
            if concept == 'nan' or not concept:
                concept = None

            stock = db.query(Stock).filter(Stock.code == code).first()
            if stock:
                if industry and industry != stock.industry:
                    stock.industry = industry
                    updated += 1
                if concept and concept != stock.concept:
                    stock.concept = concept
                    updated += 1
            else:
                exchange = "SH" if code.startswith('6') else ("SZ" if code.startswith('0') or code.startswith('3') else "BJ")
                new_stock = Stock(
                    code=code,
                    name=str(row['名称']),
                    exchange=exchange,
                    industry=industry,
                    concept=concept,
                    status="active"
                )
                db.add(new_stock)
                updated += 1

        db.commit()
        print(f"✓ 更新/插入完成：{updated} 只股票")
        return updated
    except Exception as e:
        db.rollback()
        print(f"✗ 保存失败：{e}")
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    # 1. 检查数据库状态
    check_database_status()

    # 2. 尝试多次获取 AkShare 数据
    max_retries = 3
    success = False

    for i in range(max_retries):
        print(f"\n尝试第 {i+1}/{max_retries} 次...")
        success, source_name, df = test_akshare_sources()
        if success and df is not None and len(df) > 0:
            print(f"\n✓ 第 {i+1} 次尝试成功！")
            # 保存数据到数据库
            save_to_database(df)
            # 再次检查数据库状态
            print("\n")
            check_database_status()
            break
        else:
            if i < max_retries - 1:
                print(f"等待 {2 * (i+1)} 秒后重试...")
                time.sleep(2 * (i+1))

    if not success:
        print("\n" + "=" * 60)
        print("所有尝试失败，AkShare API 暂时不可用")
        print("建议:")
        print("1. 检查网络连接")
        print("2. 等待 15-30 分钟后重试")
        print("3. AkShare 是免费 API，可能存在临时限流")
