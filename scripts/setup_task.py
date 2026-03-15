"""
Windows 定时任务设置脚本
"""
import subprocess
import sys
import os

def setup_task():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    python_script = os.path.join(script_dir, "auto_update.py")

    # 删除旧任务
    print("[1/3] 删除旧任务...")
    subprocess.run(["schtasks", "/delete", "/tn", "StockDataUpdate", "/f"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 创建新任务
    print("[2/3] 创建新任务...")
    print(f"  脚本路径：{python_script}")

    result = subprocess.run(
        ["schtasks", "/create", "/tn", "StockDataUpdate",
         "/tr", f'cmd /c "python {python_script}"',
         "/sc", "weekly", "/d", "MON,TUE,WED,THU,FRI", "/st", "16:00", "/f"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print("[OK] 定时任务创建成功!")
    else:
        print(f"[错误] {result.stderr}")
        print("请以管理员身份运行此脚本")
        return False

    # 验证任务
    print("[3/3] 验证任务...")
    subprocess.run(["schtasks", "/query", "/tn", "StockDataUpdate"])

    print("\n[完成] 设置完成!")
    print(f"手动运行：python {python_script}")
    return True

if __name__ == "__main__":
    # 检查管理员权限
    import ctypes
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("[警告] 请以管理员身份运行此脚本")
            print("右键点击 -> 以管理员身份运行")
            input("按回车退出...")
            sys.exit(1)
    except:
        pass

    setup_task()
    input("按回车退出...")
