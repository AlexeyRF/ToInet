@echo off
chcp 65001 >nul
title zDPI - Advanced ByeDPI + Zapret2 Engine
cd /d "%~dp0"
echo ==================================================================
echo         zDPI: Advanced ByeDPI + Zapret2 DPI Engine
echo ==================================================================
echo  Запуск локального SOCKS5 прокси на 127.0.0.1:1080...
echo  Пресет: GENERAL (YouTube, Discord, блокировки веб-сайтов)
echo.
echo  Для использования укажите в браузере или системе SOCKS5:
echo    IP: 127.0.0.1
echo    Port: 1080
echo ==================================================================
echo.
zdpi.exe --preset general -p 1080 -x 1
pause
