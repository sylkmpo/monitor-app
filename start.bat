@echo off
chcp 65001 >nul
echo ==============================================
echo        Intelligent Monitor System - Startup
echo ==============================================
echo.

echo [1/4] Starting WebRTC Server (MediaMTX)...
cd mediamtx_v1.17.1_windows_amd64
start "MediaMTX Server" cmd /k "mediamtx.exe"
cd ..

echo [2/4] Starting FastAPI Control Center...
cd yolov26
start "API Server" cmd /k "conda activate sta && python api_server.py"

echo [3/4] Starting AI Camera Service...
start "AI Server" cmd /k "conda activate sta && python ai_server.py"
cd ..

echo [4/4] Starting Vue3 Frontend Dashboard...
cd monitor-app
start "Frontend UI" cmd /k "npm run dev"
cd ..

echo.
echo ==============================================
echo  All services mounted successfully! 
echo  Access your dashboard at: http://localhost:5173
echo ==============================================
pause
