@echo off
setlocal
cd /d "%~dp0"
echo Temple Product Video Generator V1
echo.
echo Opening http://127.0.0.1:4173
echo Keep this window open while using the application.
echo.
netstat -ano | findstr ":4173" | findstr "LISTENING" >nul
if %ERRORLEVEL%==0 (
  echo The service is already running.
  start "" "http://127.0.0.1:4173"
  echo You can close this window.
  pause
  exit /b 0
)
start "" "http://127.0.0.1:4173"
python server.py
endlocal
