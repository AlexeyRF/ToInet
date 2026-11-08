@echo off
setlocal
echo ========================================================
echo Building C++ utilities (cpller, gatik, ssh_tunnel, programs_settings, tgws_accel, zdpi)
echo ========================================================

set "VS_VCVARS="
if exist "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    set "VS_VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VS_VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VS_VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VS_VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
)

if not "%VS_VCVARS%"=="" (
    call "%VS_VCVARS%"
    echo Compiling cpller.exe...
    cl.exe /nologo /O2 /EHsc /W3 /DUNICODE /D_UNICODE "%~dp0cpller.cpp" /Fe:"%~dp0..\bin\cpller.exe" /link wininet.lib advapi32.lib
    echo Compiling gatik.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 "%~dp0gatik.cpp" /Fe:"%~dp0..\bin\gatik.exe" /link ws2_32.lib
    echo Compiling ssh_tunnel.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 "%~dp0ssh_tunnel.cpp" /Fe:"%~dp0..\bin\ssh_tunnel.new.exe" /link ws2_32.lib advapi32.lib
    if exist "%~dp0..\bin\ssh_tunnel.new.exe" (
        move /y "%~dp0..\bin\ssh_tunnel.exe" "%~dp0..\bin\ssh_tunnel.old" >nul 2>&1
        move /y "%~dp0..\bin\ssh_tunnel.new.exe" "%~dp0..\bin\ssh_tunnel.exe" >nul 2>&1
    )
    echo Compiling programs_settings.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE "%~dp0programs_settings.cpp" /Fe:"%~dp0..\bin\programs_settings.exe" /link user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling tgws_accel.dll...
    cl.exe /nologo /O2 /arch:AVX2 /EHsc /W3 /std:c++17 /LD "%~dp0tgws_accel.cpp" /Fe:"%~dp0..\bin\tgws_accel.dll" /link /DLL
    del /q "%~dp0*.obj" "%~dp0..\bin\*.lib" "%~dp0..\bin\*.exp" 2>nul
    del /q "cpller.obj" "gatik.obj" "ssh_tunnel.obj" "programs_settings.obj" "tgws_accel.obj" 2>nul
    echo Done!
) else (
    echo MSVC vcvars64.bat not found. Trying g++...
    g++ -O2 -std=c++17 "%~dp0cpller.cpp" -o "%~dp0..\bin\cpller.exe" -lwininet -ladvapi32
    g++ -O2 -std=c++17 "%~dp0gatik.cpp" -o "%~dp0..\bin\gatik.exe" -lws2_32
    g++ -O2 -std=c++17 "%~dp0ssh_tunnel.cpp" -o "%~dp0..\bin\ssh_tunnel.new.exe" -lws2_32 -ladvapi32
    if exist "%~dp0..\bin\ssh_tunnel.new.exe" (
        move /y "%~dp0..\bin\ssh_tunnel.exe" "%~dp0..\bin\ssh_tunnel.old" >nul 2>&1
        move /y "%~dp0..\bin\ssh_tunnel.new.exe" "%~dp0..\bin\ssh_tunnel.exe" >nul 2>&1
    )
    g++ -O2 -std=c++17 -municode -mwindows "%~dp0programs_settings.cpp" -o "%~dp0..\bin\programs_settings.exe" -luser32 -lgdi32 -lcomdlg32 -lcomctl32 -ldwmapi -lshell32
    g++ -O2 -std=c++17 -mavx2 -shared "%~dp0tgws_accel.cpp" -o "%~dp0..\bin\tgws_accel.dll"
    echo Done!
)

if exist "%~dp0zdpi\build.bat" (
    call "%~dp0zdpi\build.bat"
)
