import os
import sys
import subprocess
import webbrowser
from PyQt5.QtWidgets import QMessageBox

def log(msg):
    print(f"[LOG] {msg}")

def run_script(script_name):
    if os.path.exists(script_name):
        subprocess.Popen([sys.executable, script_name], creationflags=subprocess.CREATE_NO_WINDOW)
        log(f"Started: {script_name}")
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

def open_project_folder(directory):
    log(f"Открытие папки проекта: {directory}")
    try:
        if os.path.exists(directory):
            os.startfile(directory)
            log("Папка проекта открыта")
            return True
        else:
            log("Папка проекта не найдена")
            return False
    except Exception as e:
        log(f"Ошибка открытия папки проекта: {e}")
        QMessageBox.critical(None, "Ошибка", f"Не удалось открыть папку проекта:\n{e}")
        return False

def open_browser_properties():
    try:
        subprocess.run(['inetcpl.cpl'], shell=True)
    except Exception as e:
        QMessageBox.warning(None, "Ошибка", f"Не удалось открыть свойства браузера:\n{e}")
