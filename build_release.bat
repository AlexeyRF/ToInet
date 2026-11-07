@echo off
chcp 65001 > nul
echo ==================================================
echo   ToInet-MAX: Обычная сборка релизов
echo ==================================================
cd /d "%~dp0"
python build/build_release.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ОШИБКА] Сборка завершилась с ошибкой!
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [ГОТОВО] Сборка успешно завершена! Файлы и архивы в папке releases/
pause
