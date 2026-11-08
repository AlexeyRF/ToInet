@echo off
chcp 65001 >nul
title zDPI - YouTube 4K Mode
cd /d "%~dp0"
echo ==================================================================
echo         zDPI: Режим YouTube 4K (TLS Split + Fake + QUIC Drop)
echo ==================================================================
echo  Запуск локального SOCKS5 прокси на 127.0.0.1:1080...
echo.
zdpi.exe --preset youtube -p 1080 -x 1
pause
