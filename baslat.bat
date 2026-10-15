@echo off
title XInput -> Sony DualShock 4 Controller Bridge
cd /d "%~dp0"

if exist "dist\XInputToDS4\XInputToDS4.exe" (
    start "" "dist\XInputToDS4\XInputToDS4.exe"
) else if exist "venv\Scripts\python.exe" (
    call venv\Scripts\python.exe app.py
) else (
    python app.py
)
