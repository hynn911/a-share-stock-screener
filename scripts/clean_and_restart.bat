@echo off
REM 清理缓存并重启 Streamlit (Windows 版本)
REM 用法：scripts\clean_and_restart.bat

echo ========================================
echo   清理 Python 缓存并重启 Streamlit
echo ========================================

REM 切换到项目根目录
cd /d "%~dp0.."

echo.
echo [1/3] 清理 __pycache__ 目录...
for /d /r . %%d in (__pycache__) do @if exist "%%d" (
    rd /s /q "%%d"
    echo   已删除：%%d
)
echo       完成

echo.
echo [2/3] 清理 .pyc 文件...
del /s /q *.pyc 2>nul
echo       完成

echo.
echo [3/3] 清理 Streamlit 缓存...
del /q "%USERPROFILE%\.streamlit\*.proto" 2>nul
echo       完成

echo.
echo ========================================
echo   缓存清理完成！
echo   正在启动 Streamlit...
echo ========================================
echo.

REM 启动 Streamlit
streamlit run ui/app.py
