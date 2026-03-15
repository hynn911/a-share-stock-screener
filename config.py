# 配置信息
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录（从环境变量读取，默认为当前目录）
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).parent))

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/stock.db")

# 数据目录
DATA_DIR = PROJECT_ROOT / "data" if isinstance(PROJECT_ROOT, Path) else "data"
CACHE_DIR = PROJECT_ROOT / "data" / "cache" if isinstance(PROJECT_ROOT, Path) else "data/cache"

# 股票池配置
STOCK_EXCHANGES = ["SH", "SZ"]  # 上海、深圳

# 更新配置
DAILY_UPDATE_TIME = "15:30"  # 每日收盘后更新

# 技术指标配置
DEFAULT_MA_PERIODS = [5, 10, 20, 60]

# 资金流入筛选配置
DEFAULT_CONSECUTIVE_DAYS = 3  # 连续 N 日资金流入
DEFAULT_MIN_NET_INFLOW = 10000000  # 最小净流入 1000 万

# 止盈止损配置 (可自定义)
DEFAULT_STOP_LOSS_RATE = 0.08  # 止损 8%
DEFAULT_TARGET_PROFIT_RATE = 0.30  # 止盈 30%
DEFAULT_TRAILING_STOP_RATE = 0.10  # 移动止盈回撤 10%
