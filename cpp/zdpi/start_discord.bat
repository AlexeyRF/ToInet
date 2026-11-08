@echo off
chcp 65001 >nul
title zDPI - Discord Mode
cd /d "%~dp0"
echo ==================================================================
echo         zDPI: Режим Discord (Голос + Медиа + Чат)
echo ==================================================================
echo  Запуск локального SOCKS5 прокси на 127.0.0.1:1080...
echo.
zdpi.exe --preset discord -p 1080 -x 1
pause
