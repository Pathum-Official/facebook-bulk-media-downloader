@echo off
title PTM Prime - Facebook Media Downloader
color 0B

echo ======================================================================
echo       ____ _____ __  __   ____       _                 
echo      ^|  _ \_   _^|  \/  ^| ^|  _ \ _ __(_)_ __ ___   ___  
echo      ^| ^|_) ^|^| ^| ^| ^|\/^| ^| ^| ^|_) ^| '__^| ^| '_ ` _ \ / _ \ 
echo      ^|  __/ ^| ^| ^| ^|  ^| ^| ^|  __/^| ^|  ^| ^| ^| ^| ^| ^| ^|  __/ 
echo      ^|_^|    ^|_^| ^|_^|  ^|_^| ^|_^|   ^|_^|  ^|_^|_^| ^|_^| ^|_^|\___^| 
echo.
echo           Facebook Media Downloader (Photos ^& Videos)
echo                    * Powered by PTM Prime *
echo ======================================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not detected on your computer!
    echo Please install Python 3.10 or higher from: https://www.python.org/downloads/
    echo Make sure to check the box "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b
)

:: 2. Check and install dependencies
echo [*] Checking required packages...
pip show flask gallery-dl yt-dlp >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Installing required dependencies from requirements.txt...
    echo [*] This will only happen once! Please wait...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b
    )
    echo [OK] Dependencies installed successfully!
) else (
    echo [OK] All required packages are already installed.
)

:: 3. Launch Application
echo.
echo ======================================================================
echo [*] Launching PTM Prime Dashboard...
echo [*] Opening your web browser automatically at http://127.0.0.1:5000
echo [*] Press Ctrl+C in this window anytime to stop the server.
echo ======================================================================
echo.

python app.py

pause
