"""
定时任务 - 每天收盘后自动计算推荐股票
可配置为 Windows 任务计划或 Linux cron
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.calculate_recommendations import auto_calculate_latest
import logging
from datetime import datetime

# 确保 logs 目录存在
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "recommendation_task.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def run_daily_calculation():
    """执行每日推荐计算"""
    logger.info("=" * 50)
    logger.info("开始执行每日推荐计算任务")

    try:
        auto_calculate_latest()
        logger.info("任务执行成功")
    except Exception as e:
        logger.error(f"任务执行失败：{e}", exc_info=True)
        raise

    logger.info("=" * 50)


if __name__ == "__main__":
    run_daily_calculation()
