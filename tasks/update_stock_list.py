"""
更新股票列表 - 获取行业和概念板块信息
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_fetcher import DataFetcher
from core.database import SessionLocal
from core.models import Stock
import akshare as ak
import time

def update_stock_info():
    """更新股票列表，尝试多次获取行业信息"""

    print("=" * 60)
    print("开始更新股票列表...")
    print("=" * 60)

    fetcher = DataFetcher()

    # 尝试多次获取数据
    max_retries = 5
    for i in range(max_retries):
        try:
            print(f"\n尝试第 {i+1}/{max_retries} 次...")

            # 使用 AkShare 获取全量股票数据
            df = ak.stock_zh_a_spot_em()

            print(f"成功获取数据：{len(df)} 只股票")

            db = fetcher.db

            # 更新股票信息
            updated = 0
            for _, row in df.iterrows():
                code = str(row['代码'])
                name = str(row['名称'])
                industry = str(row.get('行业', ''))
                concept = str(row.get('概念板块', ''))

                # 清理无效数据
                if industry == 'nan' or not industry:
                    industry = None
                if concept == 'nan' or not concept:
                    concept = None

                # 更新或插入
                stock = db.query(Stock).filter(Stock.code == code).first()
                if stock:
                    if industry:
                        stock.industry = industry
                    if concept:
                        stock.concept = concept
                    updated += 1
                else:
                    # 确定交易所
                    if code.startswith('6'):
                        exchange = "SH"
                    elif code.startswith('0') or code.startswith('3'):
                        exchange = "SZ"
                    else:
                        exchange = "BJ"

                    new_stock = Stock(
                        code=code,
                        name=name,
                        exchange=exchange,
                        industry=industry,
                        concept=concept,
                        status="active"
                    )
                    db.add(new_stock)
                    updated += 1

            db.commit()
            print(f"\n更新完成：{updated} 只股票")

            # 验证结果
            stocks_with_industry = db.query(Stock).filter(Stock.industry != None).count()
            stocks_with_concept = db.query(Stock).filter(Stock.concept != None).count()
            print(f"\n统计结果:")
            print(f"  有行业数据的股票：{stocks_with_industry} 只")
            print(f"  有概念数据的股票：{stocks_with_concept} 只")

            fetcher.close()
            return True

        except Exception as e:
            print(f"失败：{e}")
            if i < max_retries - 1:
                print(f"等待 {2 * (i+1)} 秒后重试...")
                time.sleep(2 * (i+1))
            else:
                print("\n所有尝试失败，请检查网络连接或稍后再试")
                fetcher.close()
                return False

if __name__ == "__main__":
    update_stock_info()
