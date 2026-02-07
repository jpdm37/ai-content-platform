@echo off
title AI Content Platform - Setup Wizard
echo.
echo ============================================================
echo    AI Content Platform - Setup Wizard
echo ============================================================
echo.
echo This wizard will help you deploy your AI Content Platform.
echo.
echo Checking Python installation...
python --version 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo Python found!
echo.
echo Starting setup wizard...
echo.
python setup-wizard.py
if errorlevel 1 (
    echo.
    echo Setup encountered an error.
    pause
)
pause
