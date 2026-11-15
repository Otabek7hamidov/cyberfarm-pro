@echo off
title CyberFarm Pro - Telegram Bot Hub
color 0B
chcp 65001 >nul
echo ================================================================
echo        ⚡ CYBERFARM PRO - TELEGRAM BOSHQARUV BOTI
echo ================================================================
echo.
python telegram_bot.py
if errorlevel 1 (
    echo.
    echo [Diqqat] Bot to'xtadi yoki xatolik yuz berdi.
    pause
)
