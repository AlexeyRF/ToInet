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

# --- UTILS ---
import subprocess
import webbrowser
from PyQt5.QtWidgets import QMessageBox

def log(msg):
    print(f"[LOG] {msg}")

def run_script(script_name, args=None):
    if os.path.exists(script_name):
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
        log(f"Started: {script_name}")
        return True
    else:
        log(f"Script not found: {script_name}")
        return False

def run_console_script(script_name, args=None):
    if os.path.exists(script_name):
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        log(f"Started console: {script_name}")
        return True
    else:
        log(f"Script not found: {script_name}")
        return False

def add_proxy_to_telegram(port):
    host = "127.0.0.1"
    url = f"tg://socks?server={host}&port={port}"
    
    log(f"Adding proxy with port {port} to Telegram")
    try:
        result = webbrowser.open(url)
        if not result:
            raise RuntimeError("webbrowser.open returned False")
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(url)
            QMessageBox.information(None, "Telegram Proxy", 
                                   f"Не удалось открыть Telegram автоматически.\n\n"
                                   f"Ссылка для порта {port} скопирована в буфер обмена:\n{url}")
        except:
            QMessageBox.information(None, "Telegram Proxy", 
                                   f"Ссылка для настройки прокси (порт {port}) в Telegram:\n{url}")

def add_http_proxy_to_telegram(port):
    msg_ru = (f"Данный прокси (порт {port}) работает по протоколу HTTP.\n\n"
              f"Telegram не поддерживает автоматическое добавление HTTP прокси по ссылке. "
              f"Пожалуйста, добавьте его вручную:\n\n"
              f"1. Настройки Telegram -> Продвинутые -> Тип соединения\n"
              f"2. Использовать собственный прокси -> Добавить\n"
              f"3. Выберите 'HTTP' (НЕ SOCKS5)\n"
              f"4. Сервер: 127.0.0.1, Порт: {port}\n"
              f"5. Сохранить")
    msg_en = (f"This proxy (port {port}) uses the HTTP protocol.\n\n"
              f"Telegram does not support automatically adding HTTP proxies via deep links. "
              f"Please add it manually:\n\n"
              f"1. Telegram Settings -> Advanced -> Connection type\n"
              f"2. Use custom proxy -> Add proxy\n"
              f"3. Select 'HTTP' (NOT SOCKS5)\n"
              f"4. Server: 127.0.0.1, Port: {port}\n"
              f"5. Save")
    QMessageBox.information(None, "Telegram HTTP Proxy", msg_en if lang._is_en else msg_ru)

def add_mtproto_to_telegram(port, secret, fake_tls=None):
    host = "127.0.0.1"
    if fake_tls:
        secret_str = "ee" + secret + fake_tls.encode('ascii').hex()
    else:
        secret_str = "dd" + secret
    url = f"tg://proxy?server={host}&port={port}&secret={secret_str}"
    
    log(f"Adding MTProto proxy with port {port} to Telegram")
    try:
        result = webbrowser.open(url)
        if not result:
            raise RuntimeError("webbrowser.open returned False")
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(url)
            QMessageBox.information(None, "Telegram MTProto Proxy", 
                                   f"Не удалось открыть Telegram автоматически.\n\n"
                                   f"Ссылка для порта {port} скопирована в буфер обмена:\n{url}")
        except:
            QMessageBox.information(None, "Telegram MTProto Proxy", 
                                   f"Ссылка для настройки прокси (порт {port}) в Telegram:\n{url}")

def open_project_folder(directory):
    log(f"Открытие папки проекта: {directory}")
    try:
        if os.path.exists(directory):
            os.startfile(directory)
            log(T("Папка проекта открыта", "Project folder opened"))
            return True
        else:
            log(T("Папка проекта не найдена", "Project folder not found"))
            return False
    except Exception as e:
        log(f"Ошибка открытия папки проекта: {e}")
        QMessageBox.critical(None, T("Ошибка", "Error"), f"Не удалось открыть папку проекта:\n{e}")
        return False

def open_browser_properties():
    try:
        subprocess.run(['inetcpl.cpl'], shell=True)
    except Exception as e:
        QMessageBox.warning(None, T("Ошибка", "Error"), f"Не удалось открыть свойства браузера:\n{e}")
