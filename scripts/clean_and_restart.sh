#!/bin/bash
# 清理缓存并重启 Streamlit
# 用法：bash scripts/clean_and_restart.sh

echo "========================================"
echo "  清理 Python 缓存并重启 Streamlit"
echo "========================================"

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo ""
echo "[1/3] 清理 __pycache__ 目录..."
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
echo "      完成"

echo ""
echo "[2/3] 清理 .pyc 文件..."
find . -name '*.pyc' -delete 2>/dev/null
echo "      完成"

echo ""
echo "[3/3] 清理 Streamlit 缓存..."
rm -rf ~/.streamlit/*.proto 2>/dev/null
echo "      完成"

echo ""
echo "========================================"
echo "  缓存清理完成！"
echo "  正在启动 Streamlit..."
echo "========================================"
echo ""

# 启动 Streamlit
streamlit run ui/app.py
