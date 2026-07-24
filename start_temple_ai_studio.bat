@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
echo Starting Temple AI Studio OS...
python scripts\temple_os_cli.py --root "%ROOT%" serve --host 127.0.0.1 --port 8765
endlocal
