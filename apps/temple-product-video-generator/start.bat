@echo off
setlocal
cd /d "%~dp0"
echo Temple Product Video Generator V1
echo.
echo Opening http://127.0.0.1:4173
echo Keep this window open while using the application.
echo.
start "" "http://127.0.0.1:4173"
python server.py
endlocal
