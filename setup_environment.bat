@echo off
title CyberControl Setup & Launcher
echo ====================================================
echo  CYBERCONTROL - AVTOMATIK SOZLASH VA ISHGA TUSHIRISH
echo ====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATOLIK] Python kompyuterda topilmadi!
    echo Iltimos, Python 3.10 yoki yangirog'ini o'rnating va "Add Python to PATH" katagini belgilang.
    pause
    exit /b
)

echo [1/2] Kerakli Python kutubxonalari o'rnatilmoqda...
pip install -r requirements.txt

echo.
echo [2/2] Boshqaruv paneli ishga tushirilmoqda...
echo Brauzerda http://localhost:8501 ochiladi.
start http://localhost:8501
streamlit run dashboard.py

pause
