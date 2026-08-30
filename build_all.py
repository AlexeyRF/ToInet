import os
import zipfile
import glob
import subprocess
import sys
import shutil
import re
import urllib.request
import json

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

def download_file(url, output_path):
    print(f"Downloading {url} to {output_path}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(output_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

def update_tor():
    print("Updating Tor...")
    try:
        req = urllib.request.Request("https://dist.torproject.org/torbrowser/", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
        
        links = re.findall(r'href="(https://[^"]+tor-expert-bundle-windows-x86_64[^"]+\.tar\.gz)"', html)
        if not links:
            print("Failed to find Tor download link.")
            return
            
        stable_links = [l for l in links if "a" not in l.split('/')[-2]]
        download_url = stable_links[0] if stable_links else links[0]
        
        temp_tar = "tor_temp.tar.gz"
        download_file(download_url, temp_tar)
        
        # Extract to tor/
        if os.path.exists("tor_temp_ext"):
            shutil.rmtree("tor_temp_ext")
        os.makedirs("tor_temp_ext", exist_ok=True)
        
        with tarfile.open(temp_tar, "r:gz") as tar:
            tar.extractall("tor_temp_ext")
            
        # Copy files to tor/ directory
        # Inside tor-expert-bundle there is 'tor' and 'data' directories.
        # We only need to overwrite 'tor/tor.exe' etc.
        src_tor = os.path.join("tor_temp_ext", "tor")
        dst_tor = "tor"
        os.makedirs(dst_tor, exist_ok=True)
        if os.path.exists(src_tor):
            for item in os.listdir(src_tor):
                s = os.path.join(src_tor, item)
                d = os.path.join(dst_tor, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                    
        # Pluggable transports
        src_pt = os.path.join("tor_temp_ext", "data", "pt_config", "lyrebird.exe")
        # Wait, expert bundle might just have 'tor' and 'pluggable_transports'
        # Let's just blindly copy the whole expert bundle over 'tor' directory or handle correctly.
        # It usually has 'tor' folder and 'data' folder.
        
        if os.path.exists(temp_tar):
            os.remove(temp_tar)
        if os.path.exists("tor_temp_ext"):
            shutil.rmtree("tor_temp_ext")
            
        print("Tor updated.")
    except Exception as e:
        print(f"Error updating Tor: {e}")

def update_opera_proxy()
        update_singbox():
    print("Updating Opera Proxy...")
    try:
        req = urllib.request.Request("https://api.github.com/repos/Alexey71/opera-proxy/releases/latest", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        for asset in data.get('assets', []):
            name = asset['name']
            url = asset['browser_download_url']
            
            if 'windows-amd64' in name and name.endswith('.zip'):
                temp_zip = "opera_amd64.zip"
                download_file(url, temp_zip)
                with zipfile.ZipFile(temp_zip, 'r') as zipf:
                    for info in zipf.infolist():
                        if info.filename.endswith('.exe'):
                            info.filename = "opera-proxy.windows-amd64.exe"
                            zipf.extract(info, "bin")
                os.remove(temp_zip)
                
            elif 'windows-arm64' in name and name.endswith('.zip'):
                temp_zip = "opera_arm64.zip"
                download_file(url, temp_zip)
                with zipfile.ZipFile(temp_zip, 'r') as zipf:
                    for info in zipf.infolist():
                        if info.filename.endswith('.exe'):
                            info.filename = "opera-proxy.windows-arm64.exe"
                            zipf.extract(info, "bin")
                os.remove(temp_zip)
                
        print("Opera Proxy updated.")
    except Exception as e:
        print(f"Error updating Opera Proxy: {e}")



def update_singbox():
    print("Updating sing-box...")
    try:
        req = urllib.request.Request("https://api.github.com/repos/SagerNet/sing-box/releases/latest", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        for asset in data.get('assets', []):
            name = asset['name']
            url = asset['browser_download_url']
            
            # sing-box-<version>-windows-amd64.zip
            if 'windows-amd64' in name and name.endswith('.zip'):
                # Delete old
                for old in glob.glob("bin/sing-box-*-windows-amd64.zip"):
                    os.remove(old)
                download_file(url, f"bin/{name}")
                
            elif 'windows-arm64' in name and name.endswith('.zip'):
                # Delete old
                for old in glob.glob("bin/sing-box-*-windows-arm64.zip"):
                    os.remove(old)
                download_file(url, f"bin/{name}")
                
        print("sing-box updated.")
    except Exception as e:
        print(f"Error updating sing-box: {e}")

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
    
    import glob
    singbox_zips = glob.glob(f"bin/sing-box-*-windows-{arch_name}.zip")
    if singbox_zips:
        files_to_include.append(singbox_zips[-1])
        
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
            
        import glob
        singbox_zips = glob.glob(f"bin/sing-box-*-windows-{arch_name}.zip")
        if singbox_zips:
            zipf.write(singbox_zips[-1], os.path.join(PROJECT_NAME, singbox_zips[-1]))
            
        # Общие ресурсы (tor, byedpi, data)
        for glob_path in COMMON_RESOURCES_GLOBS:
            for file_path in glob.glob(glob_path):
                if os.path.isfile(file_path):
                    arcname = os.path.join(PROJECT_NAME, file_path)
                    zipf.write(file_path, arcname)
                    
    print(f"Успешно: {output_zip}")

if __name__ == "__main__":
    print("Удаление patch*.py файлов...")
    for pf in glob.glob("patch*.py"):
        try:
            os.remove(pf)
            print(f"Удален {pf}")
        except:
            pass

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
