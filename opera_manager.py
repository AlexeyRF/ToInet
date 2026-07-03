import lang
import os
import subprocess
import json
import psutil
import platform
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal

import sys; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def get_opera_proxy_exe():
    machine = platform.machine().lower()
    if 'arm' in machine or 'aarch64' in machine:
        exe_name = "opera-proxy.windows-arm64.exe"
    else:
        exe_name = "opera-proxy.windows-amd64.exe"
    return os.path.join(CURRENT_DIR, "bin", exe_name)

OPERA_PROXY_EXE = get_opera_proxy_exe()
OPERA_CUSTOM_FILE = os.path.join(CURRENT_DIR, "opera_proxy_custom.txt")
DEFAULT_OPERA_PARAMS = "-bind-address 127.0.0.1:1785 -socks-mode -verbosity 20 -server-selection random -proxy socks5://127.0.0.1:1787"

class OperaProxyManager(QObject):
    status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, config=None):
        super().__init__()
        self.process = None
        self.running = False
        self.config = config or {}

    def update_config(self, new_config):
        self.config = new_config

    def is_running(self):
        return self.running

    def get_params(self):
        params_str = self.config.get("opera_params", DEFAULT_OPERA_PARAMS)
        return params_str.split()

    def start(self):
        if self.running:
            return True
            
        if not os.path.exists(OPERA_PROXY_EXE):
            self.error_occurred.emit(lang.T("Файл opera-proxy.exe не найден!", "opera-proxy.exe not found!"))
            return False
            
        params = self.get_params()
        cmd = [OPERA_PROXY_EXE] + params
        
        try:
            print(f"[OperaProxy] Запуск: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.running = True
            self.status_changed.emit(True)
            return True
        except Exception as e:
            print(f"[OperaProxy] Ошибка запуска: {e}")
            self.error_occurred.emit(str(e))
            self.running = False
            return False

    def stop(self):
        if not self.running or not self.process:
            return
            
        try:
            # Terminate main process
            self.process.terminate()
            try:
                self.process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                
            # Kill stray processes if any
            exe_name = os.path.basename(OPERA_PROXY_EXE).lower()
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == exe_name:
                        p = psutil.Process(proc.info['pid'])
                        p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
        except Exception as e:
            print(f"[OperaProxy] Ошибка остановки: {e}")
            
        self.process = None
        self.running = False
        self.status_changed.emit(False)
        print("[OperaProxy] Остановлен")

    def open_settings(self):
        if not os.path.exists(OPERA_CUSTOM_FILE):
            with open(OPERA_CUSTOM_FILE, 'w', encoding='utf-8') as f:
                f.write("# Настройки для Opera Proxy\n")
                f.write("# Пример:\n")
                f.write("# " + DEFAULT_OPERA_PARAMS + "\n")
        
        import utils
        utils.run_script("opera_settings.pyw")

    def get_status_text(self):
        if self.running:
            return lang.T("Остановить Opera Proxy", "Stop Opera Proxy")
        return lang.T("Запустить Opera Proxy", "Start Opera Proxy")

_manager = None
def get_manager(config=None):
    global _manager
    if _manager is None:
        _manager = OperaProxyManager(config)
    return _manager
