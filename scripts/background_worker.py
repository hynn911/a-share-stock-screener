"""
后台数据刷新服务
定时刷新股票和大宗商品数据
"""
import sys
import time
import schedule
from datetime import datetime

sys.path.insert(0, '..')

# 设置控制台 UTF-8 编码输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def job_refresh_commodities():
    """刷新大宗商品价格"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始刷新大宗商品价格...")
    try:
        from core.commodity import CommodityMonitor, format_alert_text
        from core.database import init_db

        init_db()
        monitor = CommodityMonitor()

        # 获取预警
        alerts = monitor.get_commodities_with_alert(threshold=10.0)

        if alerts:
            print("\n" + format_alert_text(alerts, threshold=10.0))
        else:
            print("[OK] 暂无涨跌幅超过 10% 的大宗商品")

        monitor.close()
        print("大宗商品刷新完成")
    except Exception as e:
        print(f"[ERROR] 刷新大宗商品失败：{e}")


def job_refresh_stock_data():
    """刷新股票数据"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始刷新股票数据...")
    try:
        import subprocess
        result = subprocess.run(
            ["python", "incremental_refresh.py", "--type", "all"],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"[ERROR] 刷新股票数据失败：{e}")


def main():
    print("=" * 60)
    print("后台数据刷新服务")
    print("=" * 60)
    print("启动时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print()
    print("定时任务安排:")
    print("  - 大宗商品价格：每 30 分钟检查一次")
    print("  - 股票数据：每日 17:30 收盘后刷新")
    print()
    print("按 Ctrl+C 停止服务")
    print("-" * 60)

    # 安排定时任务
    schedule.every(30).minutes.do(job_refresh_commodities)
    schedule.every().day.at("17:30").do(job_refresh_stock_data)

    # 立即执行一次
    print("\n[启动] 执行首次刷新...")
    job_refresh_commodities()

    # 主循环
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
