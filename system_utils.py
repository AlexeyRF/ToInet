import sys
import os
import shutil
import ctypes
import locale

# --- CACHER ---
def clean_data_directory(data_path="data"):
    if not os.path.exists(data_path):
        print(f"Директория {data_path} не существует!")
        return False
    if not os.path.isdir(data_path):
        print(f"{data_path} не является директорией!")
        return False
    keep_files = {'geoip', 'geoip6'}
    for item in os.listdir(data_path):
        item_path = os.path.join(data_path, item)
        if item in keep_files:continue
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path): os.remove(item_path)
            elif os.path.isdir(item_path):shutil.rmtree(item_path)
        except Exception as e: pass

# --- LANG ---
def is_english_system():
    try:
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        return (lang_id & 0xFF) == 0x09
    except Exception:
        try:
            loc = locale.getdefaultlocale()[0]
            if loc:
                return 'en' in loc.lower()
            return False
        except:
            return False

_is_en = is_english_system()

def T(ru_text, en_text):
    return en_text if _is_en else ru_text

import builtins
builtins.T = T

# --- CPLLER ---
def set_proxy(port, mode="classic"):
    port = str(port)
    if mode == "modern":
        if port == "9853": proxy_server = "http=127.0.0.1:9854;https=127.0.0.1:9854;socks=127.0.0.1:9853"
        elif port == "1780": proxy_server = "http=127.0.0.1:1782;https=127.0.0.1:1782;socks=127.0.0.1:1780"
        elif port == "1785": proxy_server = "http=127.0.0.1:1785;https=127.0.0.1:1785;socks=127.0.0.1:1785"
        else: proxy_server = f"socks=127.0.0.1:{port}"
    else:
        if port == "1785": proxy_server = f"http=127.0.0.1:{port};https=127.0.0.1:{port}"
        else: proxy_server = f"socks=127.0.0.1:{port}"
    
    os.system(f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f >nul')
    os.system(f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyServer /t REG_SZ /d "{proxy_server}" /f >nul')
    refresh_internet_settings()

def disable_proxy():
    os.system('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul')
    os.system('reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyServer /f 2>nul')
    refresh_internet_settings()

def refresh_internet_settings():
    INTERNET_OPTION_SETTINGS_CHANGED = 39
    INTERNET_OPTION_REFRESH = 37
    internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
    internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
    internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)

# --- YARLIK ---
def get_desktop_path():
    try:
        CSIDL_DESKTOP = 0x0000
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOP, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value
    except:
        return os.path.join(os.path.expanduser("~"), "Desktop")

def get_app_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def create_shortcut(target_file="main.pyw"):
    try:
        import pythoncom
        from win32com.client import Dispatch
        
        desktop_path = get_desktop_path()
        app_dir = get_app_directory()
        app_name = "ToInet-MAX"
        
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            bat_path = sys.executable
        else:
            bat_path = os.path.join(app_dir, "launch.bat")
            try:
                import subprocess
                subprocess.call([sys.executable, os.path.join(app_dir, "auto_launcher_setuper.py"), target_file])
            except: pass
            
        icon_path = os.path.join(app_dir, "icon.ico")
        shortcut_path = os.path.join(desktop_path, f"{app_name}.lnk")
        
        pythoncom.CoInitialize()
        try:
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = bat_path
            shortcut.WorkingDirectory = app_dir
            if os.path.exists(icon_path): shortcut.IconLocation = icon_path
            else: shortcut.IconLocation = bat_path
            shortcut.save()
        finally:
            pythoncom.CoUninitialize()
        return True
    except: return False

def check_shortcut_exists():
    shortcut_path = os.path.join(get_desktop_path(), "ToInet-MAX.lnk")
    return os.path.exists(shortcut_path)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "cpller":
            port = sys.argv[2]
            flag = sys.argv[3]
            mode = sys.argv[4] if len(sys.argv) > 4 else "classic"
            if flag == '1': set_proxy(port, mode)
            else: disable_proxy()
        elif cmd == "cacher":
            clean_data_directory()
        elif cmd == "yarlik":
            target = sys.argv[2] if len(sys.argv) > 2 else "main.pyw"
            create_shortcut(target)
