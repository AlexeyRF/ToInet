import os
import zipfile
import glob
import subprocess
import sys
import shutil

PROJECT_NAME = "ToInet-MAX"

# Базовые скрипты, которые идут в python-версию
PYTHON_EXTENSIONS = ['*.py', '*.pyw', 'tgws/*.py', 'tgws/*.pyw', '*.ico', '*.bat']
PYTHON_SPECIFIC_FILES = ['bridges.txt', "byedpi_tester_priority_sites.txt", "byedpi_tester_sites.txt", "byedpi_tester_strategies.txt", "Toinet.pbprofile"]

# Бинарники и ресурсы (общие для python и portable)
COMMON_RESOURCES_GLOBS = [
    'data/geoip',
    'data/geoip6',
    'byedpi/ciadpi.exe',
    'byedpi/lists/*',
    'byedpi/bin/*',
    'tor/tor.exe',
    'tor/tor-gencert.exe',
    'tor/pluggable_transports/conjure-client.exe',
    'tor/pluggable_transports/lyrebird.exe',
    'tor/pluggable_transports/pt_config.json'
]

def build_python_zip(arch_name, exe_name, opera_exe):
    output_zip = f"{PROJECT_NAME}-python_{arch_name}.zip"
    print(f"Сборка PYTHON релиза ({arch_name}) -> {output_zip}...")
    
    files_to_include = []
    
    for ext in PYTHON_EXTENSIONS:
        files_to_include.extend(glob.glob(ext))
    
    for filename in PYTHON_SPECIFIC_FILES:
        if os.path.exists(filename):
            files_to_include.append(filename)

    if os.path.exists(exe_name):
        files_to_include.append(exe_name)
    if os.path.exists(opera_exe):
        files_to_include.append(opera_exe)
        
    current_script = os.path.basename(__file__)
    files_to_include = [f for f in files_to_include if f != current_script and not f.startswith("build_")]
    files_to_include = list(set(files_to_include))
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_include:
            arcname = os.path.join(PROJECT_NAME, file)
            zipf.write(file, arcname)
        
        for glob_path in COMMON_RESOURCES_GLOBS:
            for file_path in glob.glob(glob_path):
                if os.path.isfile(file_path):
                    arcname = os.path.join(PROJECT_NAME, file_path)
                    zipf.write(file_path, arcname)
                    
    print(f"Успешно: {output_zip}")

def compile_exe():
    print("Компиляция ToInet.exe через PyInstaller...")
    if os.path.exists("build"):
        shutil.rmtree("build")
        
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "ToInet",
        "--onefile",
        "--windowed",
        "--icon", "icon.ico",
        "--noconfirm",
        "--hidden-import", "requests",
        "--hidden-import", "pythoncom",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
    ]
    
    datas = [
        ("*.py", "."),
        ("*.pyw", "."),
        ("tgws/*.py", "tgws"),
        ("tgws/*.pyw", "tgws"),
        ("icon.ico", ".")
    ]
    sep = ";" if os.name == "nt" else ":"
    for src, dst in datas:
        cmd.extend(["--add-data", f"{src}{sep}{dst}"])
        
    cmd.append("main.pyw")
    
    subprocess.check_call(cmd)
    exe_path = os.path.join("dist", "ToInet.exe")
    if not os.path.exists(exe_path):
        raise FileNotFoundError("EXE файл не был создан!")
    return exe_path

def build_portable_zip(arch_name, exe_name, opera_exe, compiled_exe_path):
    output_zip = f"{PROJECT_NAME}-portable_{arch_name}.zip"
    print(f"Сборка PORTABLE релиза ({arch_name}) -> {output_zip}...")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Добавляем сам ToInet.exe
        zipf.write(compiled_exe_path, os.path.join(PROJECT_NAME, "ToInet.exe"))
        
        # Добавляем специфичные файлы (bridges, configs)
        for filename in PYTHON_SPECIFIC_FILES:
            if os.path.exists(filename):
                zipf.write(filename, os.path.join(PROJECT_NAME, filename))
                
        # Иконка тоже может пригодиться рядом (на всякий случай, хоть она и вшита в EXE)
        if os.path.exists("icon.ico"):
            zipf.write("icon.ico", os.path.join(PROJECT_NAME, "icon.ico"))
            
        # Бинарники архитектуры
        if os.path.exists(exe_name):
            zipf.write(exe_name, os.path.join(PROJECT_NAME, exe_name))
        if os.path.exists(opera_exe):
            zipf.write(opera_exe, os.path.join(PROJECT_NAME, opera_exe))
            
        # Общие ресурсы (tor, byedpi, data)
        for glob_path in COMMON_RESOURCES_GLOBS:
            for file_path in glob.glob(glob_path):
                if os.path.isfile(file_path):
                    arcname = os.path.join(PROJECT_NAME, file_path)
                    zipf.write(file_path, arcname)
                    
    print(f"Успешно: {output_zip}")

if __name__ == "__main__":
    print("Начинаем сборку 4 архивов ToInet-MAX...")
    
    # 1. Собираем Python версии
    build_python_zip("amd64", "bin/client-windows-amd64.exe", "bin/opera-proxy.windows-amd64.exe")
    build_python_zip("arm64", "bin/client-windows-arm64.exe", "bin/opera-proxy.windows-arm64.exe")
    
    # 2. Компилируем EXE
    exe_path = compile_exe()
    
    # 3. Собираем Portable версии
    build_portable_zip("amd64", "bin/client-windows-amd64.exe", "bin/opera-proxy.windows-amd64.exe", exe_path)
    build_portable_zip("arm64", "bin/client-windows-arm64.exe", "bin/opera-proxy.windows-arm64.exe", exe_path)
    
    print("\nВсе 4 архива успешно собраны!")
