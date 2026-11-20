from managers import system_utils as lang
from managers.system_utils import AdoptedProcess

import os

import subprocess

import json

import psutil

import platform
import threading

from PySide6.QtWidgets import QMessageBox

from PySide6.QtCore import QObject, Signal

def _pipe_process_output(proc, prefix="[OperaProxy]"):
    def reader():
        try:
            if not proc or not getattr(proc, 'stdout', None):
                return
            for line in iter(proc.stdout.readline, ''):
                line_str = line.strip()
                if line_str:
                    print(f"{prefix} {line_str}")
        except Exception:
            pass
        finally:
            try:
                if proc and getattr(proc, 'stdout', None):
                    proc.stdout.close()
            except Exception:
                pass

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    return t




from managers.system_utils import get_base_dir
CURRENT_DIR = get_base_dir()



def get_opera_proxy_exe():

    machine = platform.machine().lower()

    if 'arm' in machine or 'aarch64' in machine:

        exe_name = "opera-proxy.windows-arm64.exe"

    else:

        exe_name = "opera-proxy.windows-amd64.exe"

    return os.path.join(CURRENT_DIR, "bin", exe_name)



OPERA_PROXY_EXE = get_opera_proxy_exe()

DEFAULT_OPERA_PARAMS = "-bind-address 127.0.0.1:1785 -verbosity 10 -server-selection random"



class OperaProxyManager(QObject):

    status_changed = Signal(bool)

    error_occurred = Signal(str)



    def __init__(self, config=None):

        super().__init__()

        self.process = None

        self.pool_processes = []

        self.proxy_pool_process = None

        self.running = False

        self.config = config or {}
        self._last_scan_time = 0



    def update_config(self, new_config):

        self.config = new_config



    def is_running(self):

        if self.running and self.process:

            if self.process.poll() is not None:

                self.running = False

                self.process = None

        elif not self.running:
            import time
            now = time.time()
            if now - getattr(self, '_last_scan_time', 0) > 15.0:
                self._last_scan_time = now
                target_port = 1785

                params = self.get_params()

                for i, p in enumerate(params):

                    if p == "-bind-address" and i + 1 < len(params):

                        addr = params[i + 1]

                        if ":" in addr:

                            try:

                                target_port = int(addr.split(":")[1])

                            except:

                                pass

                        break

                existing_pid = self.find_existing_process(target_port)

                if existing_pid:

                    self.process = AdoptedProcess(existing_pid)

                    self.running = True

        return self.running




    def find_existing_process(self, port=1785):

        port_str = str(port)

        exe_name = os.path.basename(OPERA_PROXY_EXE).lower()

        try:

            for proc in psutil.process_iter(['pid', 'name']):

                try:

                    name = (proc.info.get('name') or "").lower()

                    if 'opera-proxy' in name or name == exe_name:

                        cmdline = proc.cmdline() or []

                        if any(port_str in arg for arg in cmdline) or any("-bind-address" in arg for arg in cmdline):

                            return proc.info['pid']

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):

                    continue

        except Exception:

            pass



        try:

            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            sock.settimeout(0.5)

            res = sock.connect_ex(('127.0.0.1', port))

            sock.close()

            if res == 0:

                for proc in psutil.process_iter(['pid', 'name']):

                    try:

                        name = (proc.info.get('name') or "").lower()

                        if 'opera-proxy' in name or name == exe_name:

                            return proc.info['pid']

                    except:

                        pass

        except:

            pass

        return None



    def get_params(self):

        if "opera_params" in self.config and self.config["opera_params"]:

            return self.config["opera_params"].split()

        return DEFAULT_OPERA_PARAMS.split()



    def start(self):

        if self.is_running():

            return True

            

        params = self.get_params()

        target_port = 1785

        for i, p in enumerate(params):

            if p == "-bind-address" and i + 1 < len(params):

                addr = params[i + 1]

                if ":" in addr:

                    try:

                        target_port = int(addr.split(":")[1])

                    except:

                        pass

                break



        existing_pid = self.find_existing_process(target_port)

        if existing_pid:

            print(f"[OperaProxy] Найден уже запущенный процесс (PID {existing_pid}), используем его.")

            self.process = AdoptedProcess(existing_pid)

            self.running = True

            self.status_changed.emit(True)

            return True


            

        if not os.path.exists(OPERA_PROXY_EXE):
            err = lang.T("Файл opera-proxy.exe не найден!", "opera-proxy.exe not found!")
            print(f"[OperaProxy] {err}")
            self.error_occurred.emit(err)
            return False

        params = self.get_params()

        pool_enabled = self.config.get("opera_pool_enabled", False)
        pool_size = int(self.config.get("opera_pool_size", 3))

        try:
            if not pool_enabled or pool_size <= 1:
                print(f"[OperaProxy] Запуск: {' '.join([OPERA_PROXY_EXE] + params)}")
                self.process = subprocess.Popen(
                    [OPERA_PROXY_EXE] + params,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                _pipe_process_output(self.process, "[OperaProxy]")
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
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        bufsize=1,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    _pipe_process_output(proc, f"[OperaProxy] [Pool {i+1}]")
                    self.pool_processes.append(proc)

                    

                # Start proxy pool (removed)

                    

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

                



                    

        except Exception as e:

            print(f"[OperaProxy] Ошибка остановки: {e}")

            

        self.process = None

        self.running = False

        self.status_changed.emit(False)

        print("[OperaProxy] Остановлен")



    def open_settings(self):
        from managers.system_utils import get_base_dir
        base_dir = get_base_dir()
        exe = os.path.join(base_dir, "bin", "opera_settings.exe")
        if os.path.exists(exe):
            subprocess.Popen([exe], cwd=base_dir, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        else:
            from managers import system_utils as utils
            utils.run_script("bin/opera_settings.exe")



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






