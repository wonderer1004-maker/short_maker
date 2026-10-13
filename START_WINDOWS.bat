@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\install_font.py
if not exist config.json copy config.example.json config.json >nul
.venv\Scripts\python.exe app.py doctor
if not exist output\demo\short.mp4 .venv\Scripts\python.exe app.py demo
.venv\Scripts\python.exe app.py dashboard
pause
