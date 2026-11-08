@echo off
chcp 65001 > nul
echo ==================================================
echo   ToInet-MAX: Сборка One-File релиза (1 exe)
echo ==================================================
cd /d "%~dp0"
python build/build_onefile.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ОШИБКА] Сборка One-File завершилась с ошибкой!
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [ГОТОВО] Сборка One-File успешно завершена! Файл в папке build\releases\
pause
