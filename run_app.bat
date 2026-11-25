@echo off
setlocal enabledelayedexpansion
title SehatSaathi v2 - Launcher

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo ================================================================
echo           Starting SehatSaathi v2 Full Stack App
echo ================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment .venv\Scripts\python.exe not found.
    pause
    exit /b 1
)

REM 1. Check / Start Local MongoDB Service
echo [1/3] Checking local MongoDB service...
sc query MongoDB | find "RUNNING" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Starting MongoDB service...
    net start MongoDB >nul 2>&1
    if !errorlevel! neq 0 (
        echo       [!] Could not start MongoDB Windows service automatically.
        echo           Ensure MongoDB is running or MONGODB_URI points to Atlas.
    ) else (
        echo       [+] MongoDB started.
    )
) else (
    echo       [+] MongoDB is running.
)
echo.

REM 2. Launch FastAPI Backend (Port 8000, includes built-in WhatsApp QR service)
echo [2/3] Starting FastAPI Backend (Port 8000)...
start "SehatSaathi Backend (Port 8000)" cmd /k "set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
echo       [+] Backend window launched.
echo.

REM 3. Launch Expo Development Server / QR Code
echo [3/3] Starting Expo Dev Server (Metro Bundler and QR Code)...
start "SehatSaathi Expo Go (Port 8081)" cmd /k "npx expo start --go"
echo       [+] Expo Dev Server launched.
echo.

REM 4. Open Web App in default browser after a brief delay
echo Waiting 4 seconds for servers to initialize...
ping -n 5 127.0.0.1 >nul

echo Opening SehatSaathi Web App in browser...
start http://localhost:8000

echo ================================================================
echo  [READY] SehatSaathi services launched!
echo.
echo  * Local Web App:     http://localhost:8000
echo  * Backend API Docs:  http://localhost:8000/docs
echo  * WhatsApp QR Login: Built into the app (no Docker required)
echo  * Expo Dev Server:   Check the 'SehatSaathi Expo Go' window
echo ================================================================
echo.
pause
