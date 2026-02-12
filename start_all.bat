@echo off
cd /d "%~dp0"

echo ============================================
echo   FDS ETL System - One-Click Startup
echo ============================================

echo [1/3] Starting Backend API (Port 8000)...
start "Backend API" cmd /k "python api_server.py"

echo [2/3] Starting ETL Scheduler...
start "ETL Scheduler" cmd /k "python etl_core/scheduler.py"

echo [3/3] Starting Frontend (Vite)...
cd biz-dashboard
start "Frontend" cmd /k "npm run dev"

echo.
echo ============================================
echo   All services launched!
echo   - Backend: http://localhost:8000/docs
echo   - Frontend: Localhost (check window)
echo ============================================
pause
