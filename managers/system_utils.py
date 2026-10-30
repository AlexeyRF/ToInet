import sys
import os
import winreg
import shutil
import ctypes
import locale

# --- CACHER & LOGS ---
def clean_logs(logs_path="logs", max_size_mb=2, keep_last_kb=200):
    """Автоматическая очистка логов: ротация при превышении max_size_mb"""
    if not os.path.exists(logs_path):
        return
    max_bytes = max_size_mb * 1024 * 1024
    keep_bytes = keep_last_kb * 1024
    try:
        for item in os.listdir(logs_path):
            item_path = os.path.join(logs_path, item)
            if not os.path.isfile(item_path):
                continue
            try:
                size = os.path.getsize(item_path)
                if size > max_bytes:
                    with open(item_path, "rb") as f:
                        f.seek(-keep_bytes, os.SEEK_END)
                        tail = f.read()
                    nl = tail.find(b"\n")
                    if nl != -1:
                        tail = tail[nl + 1:]
                    with open(item_path, "wb") as f:
                        f.write(b"--- [LOG AUTO-CLEANED] ---\n" + tail)
            except Exception:
                pass
    except Exception:
        pass

def clean_data_directory(data_path="data"):
    clean_logs("logs")
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
def get_system_lang():
    # 1. Config preference if set
    try:
        from managers import config_manager
        cfg = config_manager.load_config()
        chosen = str(cfg.get("language", "auto")).lower()
        if chosen in ("ru", "en", "fr"):
            return chosen
    except Exception:
        pass

    # 2. Windows UI Language via WinAPI
    try:
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        primary = lang_id & 0xFF
        if primary == 0x0C:
            return "fr"
        elif primary == 0x09:
            return "en"
        elif primary == 0x19:
            return "ru"
    except Exception:
        pass

    # 3. Locale fallback
    try:
        import locale
        loc = locale.getdefaultlocale()[0]
        if loc:
            loc = loc.lower()
            if loc.startswith("fr"):
                return "fr"
            elif loc.startswith("en"):
                return "en"
            elif loc.startswith("ru"):
                return "ru"
    except Exception:
        pass

    return "ru"

def is_english_system():
    return get_system_lang() == "en"

def is_french_system():
    return get_system_lang() == "fr"

def get_language():
    return get_system_lang()

_current_lang = get_system_lang()
_is_en = (_current_lang == "en")
_is_fr = (_current_lang == "fr")
_is_ru = (_current_lang == "ru")

def T(ru_text, en_text, fr_text=None, fr=None):
    if fr is not None:
        fr_text = fr
    cur = get_system_lang()
    if cur == "fr":
        return fr_text if fr_text is not None else (en_text if en_text is not None else ru_text)
    elif cur == "en":
        return en_text if en_text is not None else ru_text
    return ru_text

import builtins
builtins.T = T

# --- CPLLER ---
def set_proxy(port, mode=None):
    port = str(port)
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
                create_launch_bat(target_file)
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

# --- AUTO START ---
def get_app_path():
    """Получает путь к исполняемому файлу"""
    if getattr(sys, 'frozen', False):
        # Если приложение скомпилировано в exe
        return sys.executable
    else:
        # Если запущено как скрипт - возвращаем путь к launch.bat
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(script_dir, "launch.bat")

def get_app_name():
    """Получает имя приложения"""
    return "ToInet-MAX"

def create_launch_bat(target_file="main.pyw"):
    """Создает launch.bat файл если его нет"""
    if getattr(sys, 'frozen', False):
        return sys.executable

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    launch_bat_path = os.path.join(script_dir, "launch.bat")
    
    try:
        main_pyw_path = os.path.join(script_dir, target_file)
        with open(launch_bat_path, 'w', encoding='utf-8') as f:
            f.write(f'@echo off\n')
            f.write(f'cd /d "{script_dir}"\n')
            f.write(f'start /b pythonw "{main_pyw_path}"\n')
        print(f"[AutoLauncher] Создан/Обновлен файл {launch_bat_path}")
    except Exception as e:
        print(f"[AutoLauncher] Ошибка создания launch.bat: {e}")
    
    return launch_bat_path

def enable_auto_start(target_file="main.pyw"):
    """Включает автозапуск приложения через launch.bat"""
    try:
        # Создаем launch.bat если его нет (или получаем путь к exe)
        launch_bat_path = create_launch_bat(target_file)
        
        if not os.path.exists(launch_bat_path):
            print(f"[AutoLauncher] Файл {launch_bat_path} не существует")
            return False
        
        app_name = get_app_name()
        
        # Открываем ключ автозапуска
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Добавляем запись с путем к launch.bat
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, launch_bat_path)
        winreg.CloseKey(key)
        
        print(f"[AutoLauncher] Автозапуск включен для {app_name} -> {launch_bat_path}")
        return True
    except Exception as e:
        print(f"[AutoLauncher] Ошибка включения автозапуска: {e}")
        return False

def disable_auto_start():
    """Отключает автозапуск приложения"""
    try:
        app_name = get_app_name()
        
        # Открываем ключ автозапуска
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Удаляем запись
        try:
            winreg.DeleteValue(key, app_name)
        except FileNotFoundError:
            # Запись не найдена - ничего страшного
            pass
        
        winreg.CloseKey(key)
        
        print(f"[AutoLauncher] Автозапуск отключен для {app_name}")
        return True
    except Exception as e:
        print(f"[AutoLauncher] Ошибка отключения автозапуска: {e}")
        return False

def check_auto_start():
    """Проверяет, включен ли автозапуск"""
    try:
        app_name = get_app_name()
        
        # Открываем ключ автозапуска
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        
        # Проверяем наличие записи
        try:
            value, _ = winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            if getattr(sys, 'frozen', False):
                return value == sys.executable
            # Проверяем, что значение указывает на launch.bat
            return value.endswith("launch.bat") and os.path.exists(value)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        print(f"[AutoLauncher] Ошибка проверки автозапуска: {e}")
        return False


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

class AdoptedProcess:
    """Обертка над psutil.Process для прозрачной совместимости с subprocess.Popen"""
    def __init__(self, pid):
        self.pid = pid
        try:
            import psutil
            self._proc = psutil.Process(pid)
        except Exception:
            self._proc = None

    def poll(self):
        if not self._proc:
            return 0
        try:
            import psutil
            if not self._proc.is_running() or self._proc.status() == psutil.STATUS_ZOMBIE:
                return 0
            return None
        except Exception:
            return 0

    def terminate(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def kill(self):
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass

    def wait(self, timeout=None):
        if self._proc:
            return self._proc.wait(timeout=timeout)
        return 0

    def is_running(self):
        return self.poll() is None

