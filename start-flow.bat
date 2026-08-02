@echo off
echo ═══════════════════════════════════════
echo           Flow Desktop App
echo ═══════════════════════════════════════
echo.

:: Kill any existing processes on ports 1420 and 8000
echo [1/2] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1420" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start the FastAPI backend in a new window
echo [2/2] Starting API and Desktop...
start "Flow API" cmd /c "title Flow API & uvicorn api.main:app --port 8000 --host 127.0.0.1"

:: Wait for API to be ready
timeout /t 4 /nobreak >nul

:: Start Tauri desktop
call npm run tauri dev

echo.
echo Flow has closed. Run this script again to restart.
pause
