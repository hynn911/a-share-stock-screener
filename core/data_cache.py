"""
本地股票数据缓存和离线模式支持
当外部 API 不可用时，使用本地缓存数据
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json

# 本地缓存目录
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class StockDataCache:
    """股票数据缓存管理器"""

    def __init__(self):
        self.cache_dir = CACHE_DIR

    def get_cached_stock_list(self, max_age_days=7):
        """
        获取缓存的股票列表

        Args:
            max_age_days: 缓存最大有效期（天）

        Returns:
            list: 股票列表，如果缓存过期或不存在返回 None
        """
        cache_file = self.cache_dir / "stock_list.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(data.get("cache_time", ""))
            if datetime.now() - cache_time > timedelta(days=max_age_days):
                print(f"缓存已过期 ({max_age_days} 天)")
                return None

            stocks = data.get("stocks", [])
            print(f"从缓存加载 {len(stocks)} 只股票")
            return stocks

        except Exception as e:
            print(f"读取缓存失败：{e}")
            return None

    def save_stock_list(self, stocks: list):
        """保存股票列表到缓存"""
        cache_file = self.cache_dir / "stock_list.json"

        data = {
            "cache_time": datetime.now().isoformat(),
            "stocks": stocks
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"股票列表已缓存到 {cache_file}")
        except Exception as e:
            print(f"保存缓存失败：{e}")

    def get_cached_daily_data(self, stock_code: str, max_age_days=1):
        """获取缓存的日线数据"""
        cache_file = self.cache_dir / "daily" / f"{stock_code}.csv"

        if not cache_file.exists():
            return None

        try:
            df = pd.read_csv(cache_file, parse_dates=['trade_date'])

            # 检查是否需要更新
            last_date = df['trade_date'].max()
            if datetime.now().date() - last_date.date() > timedelta(days=max_age_days):
                return None  # 需要更新

            return df

        except Exception as e:
            print(f"读取日线缓存失败：{e}")
            return None

    def save_daily_data(self, stock_code: str, df: pd.DataFrame):
        """保存日线数据到缓存"""
        daily_cache_dir = self.cache_dir / "daily"
        daily_cache_dir.mkdir(parents=True, exist_ok=True)

        cache_file = daily_cache_dir / f"{stock_code}.csv"

        try:
            df.to_csv(cache_file, index=False, encoding='utf-8')
        except Exception as e:
            print(f"保存日线缓存失败：{e}")

    def clear_cache(self):
        """清空所有缓存"""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print("缓存已清空")

    def get_cache_info(self):
        """获取缓存信息"""
        info = {
            "cache_dir": str(self.cache_dir),
            "stock_list_cache": None,
            "daily_cache_count": 0,
            "total_size_mb": 0
        }

        stock_list_cache = self.cache_dir / "stock_list.json"
        if stock_list_cache.exists():
            info["stock_list_cache"] = {
                "exists": True,
                "size_kb": stock_list_cache.stat().st_size / 1024
            }

        daily_dir = self.cache_dir / "daily"
        if daily_dir.exists():
            daily_files = list(daily_dir.glob("*.csv"))
            info["daily_cache_count"] = len(daily_files)

        # 计算总大小
        total_size = sum(f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file())
        info["total_size_mb"] = total_size / (1024 * 1024)

        return info


# 离线模式支持
def is_offline_mode():
    """检查是否启用离线模式"""
    import os
    return os.environ.get("STOCK_APP_OFFLINE_MODE", "0") == "1"


def set_offline_mode(enabled: bool):
    """设置离线模式"""
    import os
    os.environ["STOCK_APP_OFFLINE_MODE"] = "1" if enabled else "0"
