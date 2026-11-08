@echo off
setlocal
echo ========================================================
echo Building zdpi (C DPI circumvention tool)
echo ========================================================

if exist "C:\msys64\mingw64\bin\gcc.exe" (
    set "PATH=C:\msys64\mingw64\bin;%PATH%"
)

where gcc >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: gcc compiler not found in PATH or C:\msys64\mingw64\bin.
    exit /b 1
)

where mingw32-make >nul 2>nul
if %ERRORLEVEL% equ 0 (
    mingw32-make %*
) else (
    where make >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        make %*
    ) else (
        echo Make not found, compiling directly with gcc...
        gcc -O2 -Wall -Isrc src\conev.c src\desync.c src\extend.c src\fake_data.c src\helpers.c src\main.c src\mpool.c src\packets.c src\protocol.c src\proxy.c src\win_service.c src\crypto\aes-ctr.c src\crypto\aes-gcm.c src\crypto\aes.c src\crypto\gcm.c src\crypto\hkdf.c src\crypto\hmac.c src\crypto\sha224-256.c src\crypto\usha.c -o zdpi.exe -lws2_32 -lmswsock -ladvapi32
    )
)

if exist zdpi.exe (
    echo Successfully built zdpi.exe!
    if exist "%~dp0..\..\byedpi\" (
        echo Copying zdpi.exe to byedpi directory...
        copy /y zdpi.exe "%~dp0..\..\byedpi\zdpi.exe" >nul 2>nul
        if errorlevel 1 (
            echo Note: byedpi\zdpi.exe is currently running. New binary is ready at %~dp0zdpi.exe
        )
    )
)
