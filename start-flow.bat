@echo off
echo ═══════════════════════════════════════
echo           Flow Desktop App
echo ═══════════════════════════════════════
echo.

:: Kill any existing processes on ports 1420, 8001
echo [1/2] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1420" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start the FastAPI backend in a new window (--reload auto-restarts on .py changes)
echo [2/2] Starting API and UI...
start "Flow API" cmd /c "title Flow API & python -m uvicorn api.main:app --port 8001 --host 127.0.0.1 --reload"

:: Wait for API to be ready
timeout /t 4 /nobreak >nul

:: Start React dev server (HMR auto-reloads on .tsx/.ts/.css changes)
call npm run dev

echo.
echo Flow has closed. Run this script again to restart.
pause
