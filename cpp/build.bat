@echo off
setlocal
echo ========================================================
echo Building C++ utilities (cpller, gatik, ssh_tunnel, programs_settings, tgws_accel, zdpi, zdpi_ml_optimizer)
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
    cl.exe /nologo /O2 /EHsc /W3 /DUNICODE /D_UNICODE /Fo:"%~dp0cpller.obj" "%~dp0cpller.cpp" /Fe:"%~dp0..\bin\cpller.exe" /link wininet.lib advapi32.lib
    echo Compiling gatik.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /Fo:"%~dp0gatik.obj" "%~dp0gatik.cpp" /Fe:"%~dp0..\bin\gatik.new.exe" /link ws2_32.lib
    if exist "%~dp0..\bin\gatik.new.exe" (
        move /y "%~dp0..\bin\gatik.exe" "%~dp0..\bin\gatik.old" >nul 2>&1
        move /y "%~dp0..\bin\gatik.new.exe" "%~dp0..\bin\gatik.exe" >nul 2>&1
    )
    echo Compiling ssh_tunnel.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /Fo:"%~dp0ssh_tunnel.obj" "%~dp0ssh_tunnel.cpp" /Fe:"%~dp0..\bin\ssh_tunnel.new.exe" /link ws2_32.lib advapi32.lib
    if exist "%~dp0..\bin\ssh_tunnel.new.exe" (
        move /y "%~dp0..\bin\ssh_tunnel.exe" "%~dp0..\bin\ssh_tunnel.old" >nul 2>&1
        move /y "%~dp0..\bin\ssh_tunnel.new.exe" "%~dp0..\bin\ssh_tunnel.exe" >nul 2>&1
    )
    echo Compiling programs_settings.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo:"%~dp0programs_settings.obj" "%~dp0programs_settings.cpp" /Fe:"%~dp0..\bin\programs_settings.exe" /link user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling tgws_settings.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo:"%~dp0tgws_settings.obj" "%~dp0tgws_settings.cpp" /Fe:"%~dp0..\bin\tgws_settings.exe" /link user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling edit_bridges.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo:"%~dp0edit_bridges.obj" "%~dp0edit_bridges.cpp" /Fe:"%~dp0..\bin\edit_bridges.exe" /link user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling ssh_settings.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo:"%~dp0ssh_settings.obj" "%~dp0ssh_settings.cpp" /Fe:"%~dp0..\bin\ssh_settings.exe" /link ws2_32.lib user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling opera_settings.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo:"%~dp0opera_settings.obj" "%~dp0opera_settings.cpp" /Fe:"%~dp0..\bin\opera_settings.exe" /link user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling rules_editor.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo:"%~dp0rules_editor.obj" "%~dp0rules_editor.cpp" /Fe:"%~dp0..\bin\rules_editor.exe" /link user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib uxtheme.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling autostart_settings.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /DUNICODE /D_UNICODE /Fo:"%~dp0autostart_settings.obj" "%~dp0autostart_settings.cpp" /Fe:"%~dp0..\bin\autostart_settings.exe" /link user32.lib gdi32.lib comdlg32.lib comctl32.lib dwmapi.lib uxtheme.lib advapi32.lib shell32.lib /SUBSYSTEM:WINDOWS
    echo Compiling tgws.exe...
    cl.exe /nologo /O2 /arch:AVX2 /EHsc /W3 /std:c++17 /Fo:"%~dp0tgws/" "%~dp0tgws\*.cpp" /Fe:"%~dp0..\bin\tgws.new.exe" /link ws2_32.lib secur32.lib crypt32.lib bcrypt.lib
    if exist "%~dp0..\bin\tgws.new.exe" (
        move /y "%~dp0..\bin\tgws.exe" "%~dp0..\bin\tgws.old" >nul 2>&1
        move /y "%~dp0..\bin\tgws.new.exe" "%~dp0..\bin\tgws.exe" >nul 2>&1
    )
    echo Compiling tgws_accel.dll...
    cl.exe /nologo /O2 /arch:AVX2 /EHsc /W3 /std:c++17 /LD /Fo:"%~dp0tgws_accel.obj" "%~dp0tgws_accel.cpp" /Fe:"%~dp0..\bin\tgws_accel.new.dll" /link /DLL
    if exist "%~dp0..\bin\tgws_accel.new.dll" (
        move /y "%~dp0..\bin\tgws_accel.dll" "%~dp0..\bin\tgws_accel.old" >nul 2>&1
        move /y "%~dp0..\bin\tgws_accel.new.dll" "%~dp0..\bin\tgws_accel.dll" >nul 2>&1
    )
    echo Compiling zdpi_ml_optimizer.exe...
    cl.exe /nologo /O2 /EHsc /W3 /std:c++17 /utf-8 /Fo:"%~dp0zdpi_ml_optimizer.obj" "%~dp0zdpi_ml_optimizer.cpp" /Fe:"%~dp0..\bin\zdpi_ml_optimizer.exe"
    del /q "%~dp0*.obj" "%~dp0tgws\*.obj" "%~dp0..\bin\*.lib" "%~dp0..\bin\*.exp" 2>nul
    del /q "%~dp0..\*.obj" "cpller.obj" "gatik.obj" "ssh_tunnel.obj" "programs_settings.obj" "tgws_settings.obj" "edit_bridges.obj" "ssh_settings.obj" "opera_settings.obj" "rules_editor.obj" "autostart_settings.obj" "tgws_accel.obj" "zdpi_ml_optimizer.obj" *.obj 2>nul
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
    g++ -O2 -std=c++17 -municode -mwindows "%~dp0tgws_settings.cpp" -o "%~dp0..\bin\tgws_settings.exe" -luser32 -lgdi32 -lcomdlg32 -lcomctl32 -ldwmapi -lshell32
    g++ -O2 -std=c++17 -municode -mwindows "%~dp0edit_bridges.cpp" -o "%~dp0..\bin\edit_bridges.exe" -luser32 -lgdi32 -lcomdlg32 -lcomctl32 -ldwmapi -lshell32
    g++ -O2 -std=c++17 -municode -mwindows "%~dp0ssh_settings.cpp" -o "%~dp0..\bin\ssh_settings.exe" -lws2_32 -luser32 -lgdi32 -lcomdlg32 -lcomctl32 -ldwmapi -lshell32
    g++ -O2 -std=c++17 -municode -mwindows "%~dp0opera_settings.cpp" -o "%~dp0..\bin\opera_settings.exe" -luser32 -lgdi32 -lcomdlg32 -lcomctl32 -ldwmapi -lshell32
    g++ -O2 -std=c++17 -municode -mwindows "%~dp0rules_editor.cpp" -o "%~dp0..\bin\rules_editor.exe" -luser32 -lgdi32 -lcomdlg32 -lcomctl32 -ldwmapi -luxtheme -lshell32
    g++ -O2 -std=c++17 -municode -mwindows "%~dp0autostart_settings.cpp" -o "%~dp0..\bin\autostart_settings.exe" -luser32 -lgdi32 -lcomdlg32 -lcomctl32 -ldwmapi -luxtheme -ladvapi32 -lshell32
    g++ -O2 -std=c++17 "%~dp0zdpi_ml_optimizer.cpp" -o "%~dp0..\bin\zdpi_ml_optimizer.exe"
    g++ -O2 -std=c++17 -mavx2 "%~dp0tgws\*.cpp" -o "%~dp0..\bin\tgws.new.exe" -lws2_32 -lsecur32 -lcrypt32 -lbcrypt
    if exist "%~dp0..\bin\tgws.new.exe" (
        move /y "%~dp0..\bin\tgws.exe" "%~dp0..\bin\tgws.old" >nul 2>&1
        move /y "%~dp0..\bin\tgws.new.exe" "%~dp0..\bin\tgws.exe" >nul 2>&1
    )
    g++ -O2 -std=c++17 -mavx2 -shared "%~dp0tgws_accel.cpp" -o "%~dp0..\bin\tgws_accel.new.dll"
    if exist "%~dp0..\bin\tgws_accel.new.dll" (
        move /y "%~dp0..\bin\tgws_accel.dll" "%~dp0..\bin\tgws_accel.old" >nul 2>&1
        move /y "%~dp0..\bin\tgws_accel.new.dll" "%~dp0..\bin\tgws_accel.dll" >nul 2>&1
    )
    echo Done!
)

if exist "%~dp0zdpi\build.bat" (
    call "%~dp0zdpi\build.bat"
)
