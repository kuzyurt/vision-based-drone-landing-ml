@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "try { $r = Invoke-RestMethod 'http://127.0.0.1:8765/api/status' -TimeoutSec 2; if ($null -ne $r.ready) { exit 0 }; exit 1 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  start "" http://127.0.0.1:8765
  exit /b 0
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -c "import mujoco, numpy, PIL, fastapi, uvicorn; assert mujoco.__version__ == '3.14.0'" >nul 2>&1
if errorlevel 1 (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
start "" http://127.0.0.1:8765
.venv\Scripts\python.exe server.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Boat launch failed. Read the error above. Python 3.11 or newer is required.
pause
exit /b 1
