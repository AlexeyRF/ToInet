@echo off
chcp 65001 > nul
echo ==================================================
echo   ToInet-MAX: Сборка релизов с обновлением
echo ==================================================
cd /d "%~dp0"
python build/build_with_update.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ОШИБКА] Сборка с обновлением завершилась с ошибкой!
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [ГОТОВО] Сборка успешно завершена! Архивы в папке releases/
pause
