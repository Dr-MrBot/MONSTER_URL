@echo off
title MONSTER_URL 2.0 Launcher
cls
echo ====================================================================
echo  👾 MONSTER_URL 2.0 — Windows Launcher
echo ====================================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Python is not found in PATH! Please install Python 3.x.
    pause
    exit /b
)

python monster.py
pause
