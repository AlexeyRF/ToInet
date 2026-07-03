import lang
import os
import sys
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
