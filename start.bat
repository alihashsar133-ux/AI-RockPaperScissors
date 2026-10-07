@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title سنگ کاغذ قیچی - AI Rock Paper Scissors
cd /d "%~dp0"

echo.
echo  ========================================
echo     سنگ، کاغذ، قیچی با تشخیص دست
echo     AI Rock-Paper-Scissors (Offline)
echo  ========================================
echo.

if not exist "runtime\python\python.exe" (
    echo [خطا] پوشه runtime\python پیدا نشد.
    echo لطفاً محتویات کامل پوشه را کپی کنید.
    pause
    exit /b 1
)

set PORT=8765
:findport
netstat -an | findstr ":%PORT% " >nul 2>&1
if %errorlevel%==0 (
    set /a PORT+=1
    if !PORT! GTR 8800 (
        echo [خطا] پورت آزاد پیدا نشد.
        pause
        exit /b 1
    )
    goto findport
)

echo [اطلاعات] سرور محلی روی پورت %PORT% راه‌اندازی می‌شود...
echo [اطلاعات] مرورگر به صورت خودکار باز خواهد شد.
echo [نکته] این پنجره را نبندید تا بازی کار کند.
echo.

start "" /b "runtime\python\python.exe" -m http.server %PORT% --bind 127.0.0.1 --directory "%~dp0"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:%PORT%/app/index.html"

echo سرور در حال اجرا است... (پورت %PORT%)
echo آدرس: http://127.0.0.1:%PORT%/app/index.html
echo.
echo برای توقف سرور این پنجره را ببندید.
echo.

:loop
timeout /t 3600 /nobreak >nul
goto loop
