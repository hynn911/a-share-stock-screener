@echo off
chcp 65001 >nul
echo Creating scheduled task...
schtasks /create /tn "StockDataUpdate" /tr "python e:\work\cc\stock\scripts\auto_update.py" /sc weekly /d MON,TUE,WED,THU,FRI /st 16:00 /f
if %ERRORLEVEL% equ 0 (
    echo [OK] Task created successfully!
    echo Run manually: python e:\work\cc\stock\scripts\auto_update.py
) else (
    echo [Error] Failed to create task. Run as Administrator.
)
pause
