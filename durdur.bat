@echo off
title Kopruyu Durdur
echo Kopru durduruluyor...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq XInput to DualShock 4 Controller Bridge*" >nul 2>&1
taskkill /F /FI "COMMANDLINE eq *xinput-to-ds4*app.py*" >nul 2>&1
echo [OK] DualShock 4 koprusu kapatildi.
timeout /t 2 >nul
