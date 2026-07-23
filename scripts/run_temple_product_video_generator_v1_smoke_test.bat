@echo off
setlocal
cd /d "%~dp0..\apps\temple-product-video-generator"
python server.py --smoke-test
endlocal
