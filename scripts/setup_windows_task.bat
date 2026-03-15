@echo off
REM A 股高价值股票发掘系统 - 数据更新定时任务设置脚本
REM 适用于 Windows 系统

echo ========================================
echo 数据更新定时任务设置
echo ========================================
echo.

REM 获取当前脚本所在目录
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%auto_update.py
set LOG_FILE=%SCRIPT_DIR%auto_update.log

REM 获取 Python 路径
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 并添加到 PATH
    pause
    exit /b 1
)

REM 删除旧任务（如果存在）
echo [1/3] 删除旧的定时任务...
schtasks /delete /tn "StockDataUpdate" /f >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] 已删除旧的定时任务
) else (
    echo [信息] 未发现旧的定时任务
)

REM 创建新任务
echo [2/3] 创建新的定时任务...
echo.
echo 任务配置:
echo   - 任务名称：StockDataUpdate
echo   - 执行时间：每周一至周五 16:00（收盘后）
echo   - Python 脚本：%PYTHON_SCRIPT%
echo   - 日志文件：%LOG_FILE%
echo.

schtasks /create /tn "StockDataUpdate" ^
    /tr "cmd /c \"cd /d %SCRIPT_DIR% && python %PYTHON_SCRIPT% >> %LOG_FILE% 2>&1\"" ^
    /sc weekly /d MON,TUE,WED,THU,FRI /st 16:00 ^
    /ru SYSTEM ^
    /f

if %ERRORLEVEL% equ 0 (
    echo [OK] 定时任务创建成功!
) else (
    echo [错误] 定时任务创建失败，请尝试以管理员身份运行此脚本
    pause
    exit /b 1
)

REM 验证任务
echo [3/3] 验证定时任务...
echo.
schtasks /query /tn "StockDataUpdate"
echo.

echo ========================================
echo 设置完成!
echo ========================================
echo.
echo 手动运行更新命令:
echo   python scripts\auto_update.py
echo.
echo 查看任务日志:
echo   type scripts\auto_update.log
echo.
echo 删除定时任务:
echo   schtasks /delete /tn "StockDataUpdate" /f
echo.

pause
