@echo off
title DualShock 4 Controller Bridge - Otomatik Kurulum
cd /d "%~dp0"
echo ========================================================
echo     DualShock 4 Controller Bridge - Kurulum Sihirbazi
echo ========================================================
echo.

:: 1. Eger setup/DualShock4_Kurulum_Setup.exe varsa onu calistirma secenegi
if exist "setup\DualShock4_Kurulum_Setup.exe" (
    echo [1] Resmi Windows Setup Sihirbazini Calistir (Onerilen)
    echo [2] Python ile Kaynak Koddan Gelistirici Kurulumu Yap
    echo.
    set /p choice="Seciminiz (1 veya 2, Varsayilan: 1): "
    if "%choice%"=="" set choice=1
    if "%choice%"=="1" (
        echo.
        echo Setup calistiriliyor...
        start "" "setup\DualShock4_Kurulum_Setup.exe"
        exit /b 0
    )
)

:: 2. Python ve ViGEmBus Kontrolu
echo.
echo [*] Python surumu kontrol ediliyor...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Sisteminizde Python bulunamadi!
    echo Lutfen https://www.python.org adresinden Python kurun veya
    echo setup\DualShock4_Kurulum_Setup.exe dosyasini calistirin.
    pause
    exit /b 1
)

:: Sanal ortam olustur
if not exist "venv" (
    echo [*] Python sanal ortami (venv) olusturuluyor...
    python -m venv venv
)

:: Paketleri yukle
echo [*] Gerekli paketler yukleniyor (requirements.txt)...
call venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
call venv\Scripts\pip.exe install -r requirements.txt

echo.
echo ========================================================
echo [BASARILI] Kurulum tamamlandi!
echo Uygulamayi baslatmak icin 'baslat.bat' dosyasini acabilirsiniz.
echo ========================================================
echo.
pause
