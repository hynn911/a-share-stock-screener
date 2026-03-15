"""
A 股高价值股票发掘系统 - 主入口
"""
import uvicorn
from core.database import init_db


def main():
    """初始化并启动"""
    init_db()


if __name__ == "__main__":
    main()
