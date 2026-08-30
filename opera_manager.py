import lang
import os
import subprocess
import json
import psutil
import platform
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def get_opera_proxy_exe():
    machine = platform.machine().lower()
    if 'arm' in machine or 'aarch64' in machine:
        exe_name = "opera-proxy.windows-arm64.exe"
    else:
        exe_name = "opera-proxy.windows-amd64.exe"
    return os.path.join(CURRENT_DIR, "bin", exe_name)

OPERA_PROXY_EXE = get_opera_proxy_exe()
OPERA_CUSTOM_FILE = os.path.join(CURRENT_DIR, "opera_proxy_custom.txt")
DEFAULT_OPERA_PARAMS = "-bind-address 127.0.0.1:1785 -verbosity 10"

class OperaProxyManager(QObject):
    status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, config=None):
        super().__init__()
        self.process = None
        self.pool_processes = []
        self.proxy_pool_process = None
        self.running = False
        self.config = config or {}

    def update_config(self, new_config):
        self.config = new_config

    def is_running(self):
        return self.running

    def get_params(self):
        if "opera_params" in self.config and self.config["opera_params"]:
            return self.config["opera_params"].split()
        if os.path.exists(OPERA_CUSTOM_FILE):
            try:
                with open(OPERA_CUSTOM_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            return line.split()
            except Exception:
                pass
        return DEFAULT_OPERA_PARAMS.split()

    def start(self):
        if self.running:
            return True
            
        if not os.path.exists(OPERA_PROXY_EXE):
            self.error_occurred.emit(lang.T("Файл opera-proxy.exe не найден!", "opera-proxy.exe not found!"))
            return False
            
        params = self.get_params()
        
        pool_enabled = self.config.get("opera_pool_enabled", False)
        pool_size = int(self.config.get("opera_pool_size", 3))
        
        try:
            if not pool_enabled or pool_size <= 1:
                print(f"[OperaProxy] Запуск: {' '.join([OPERA_PROXY_EXE] + params)}")
                self.process = subprocess.Popen(
                    [OPERA_PROXY_EXE] + params,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Pool mode
                self.pool_processes = []
                # Extract original port
                original_port = 1785
                for i, p in enumerate(params):
                    if p == "-bind-address" and i+1 < len(params):
                        addr = params[i+1]
                        if ":" in addr:
                            original_port = int(addr.split(":")[1])
                        break
                        
                upstream_ports = [original_port + 1000 + i for i in range(pool_size)]
                
                print(f"[OperaProxy] Запуск пула из {pool_size} экземпляров...")
                for i, port in enumerate(upstream_ports):
                    # Create custom params for each instance
                    instance_params = list(params)
                    for j, p in enumerate(instance_params):
                        if p == "-bind-address" and j+1 < len(instance_params):
                            addr = instance_params[j+1]
                            ip = addr.split(":")[0] if ":" in addr else "127.0.0.1"
                            instance_params[j+1] = f"{ip}:{port}"
                            break
                            
                    proc = subprocess.Popen(
                        [OPERA_PROXY_EXE] + instance_params,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self.pool_processes.append(proc)
                    
                # Start proxy pool
                pool_script = os.path.join(CURRENT_DIR, "proxy_pool.py")
                if os.path.exists(pool_script):
                    self.proxy_pool_process = subprocess.Popen(
                        [sys.executable, pool_script, "--listen-port", str(original_port), "--upstream-ports", ",".join(map(str, upstream_ports))],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    print("[OperaProxy] Ошибка: proxy_pool.py не найден")
                    
            self.running = True
            self.status_changed.emit(True)
            return True
        except Exception as e:
            print(f"[OperaProxy] Ошибка запуска: {e}")
            self.error_occurred.emit(str(e))
            self.running = False
            return False

    def stop(self):
        if not self.running:
            return
            
        try:
            # Terminate main process
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    
            # Terminate pool processes
            for proc in self.pool_processes:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.2)
                except:
                    try:
                        proc.kill()
                    except:
                        pass
            self.pool_processes = []
            
            # Terminate proxy pool
            if self.proxy_pool_process:
                try:
                    self.proxy_pool_process.terminate()
                    self.proxy_pool_process.wait(timeout=0.2)
                except:
                    try:
                        self.proxy_pool_process.kill()
                    except:
                        pass
                self.proxy_pool_process = None
                
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

