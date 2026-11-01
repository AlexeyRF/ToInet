import time
import os

import subprocess

import json

import platform

import psutil

from PyQt5.QtCore import QObject, pyqtSignal

import sys

import zipfile

import shutil

from managers import system_utils as lang
from managers.system_utils import AdoptedProcess

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(CURRENT_DIR, "bin")
SING_BOX_DIR = os.path.join(BIN_DIR, "sing-box")
SING_BOX_EXE = os.path.join(SING_BOX_DIR, "sing-box.exe")

class VlessManager(QObject):
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
        if self.running and self.process:
            if self.process.poll() is not None:
                self.running = False
                self.process = None
                return False
            return True

        now = time.time()
        if hasattr(self, '_last_check') and (now - self._last_check < 2.0):
            return getattr(self, '_cached_running', False)
        self._last_check = now

        existing_pid = self.find_existing_process()
        if existing_pid:
            self.process = AdoptedProcess(existing_pid)
            self.running = True
        else:
            self.running = False
        self._cached_running = self.running
        return self.running

    def find_existing_process(self):
        # Quick loopback port check first - if port 1790 isn't open, sing-box vless isn't running
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.02)
            res = sock.connect_ex(('127.0.0.1', 1790))
            sock.close()
            if res != 0:
                return None
        except Exception:
            return None

        # Port is open, find the pid quickly
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = (proc.info.get('name') or "").lower()
                    if 'sing-box' in name:
                        return proc.info['pid']
                    elif 'python' in name:
                        cmdline = proc.cmdline() or []
                        if any('wl_torred_vless.py' in arg for arg in cmdline):
                            return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        return None



    def extract_sing_box(self):

        if os.path.exists(SING_BOX_EXE):

            return True

            

        machine = platform.machine().lower()

        import glob

        if 'arm' in machine or 'aarch64' in machine:

            pattern = os.path.join(BIN_DIR, "sing-box-*-windows-arm64.zip")

        else:

            pattern = os.path.join(BIN_DIR, "sing-box-*-windows-amd64.zip")

            

        matches = glob.glob(pattern)

        if not matches:

            self.error_occurred.emit(lang.T("Архив sing-box не найден!", "sing-box zip not found!"))

            return False

        zip_path = matches[-1]

        if not os.path.exists(zip_path):

            self.error_occurred.emit(lang.T("Файл sing-box не найден!", "sing-box zip not found!"))

            return False

            

        try:

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:

                temp_extract = os.path.join(BIN_DIR, "temp_sing_box")

                zip_ref.extractall(temp_extract)

                

                # Flatten directory

                os.makedirs(SING_BOX_DIR, exist_ok=True)

                for root, _, files in os.walk(temp_extract):

                    for file in files:

                        if file.endswith('.exe') or file.endswith('.dll'):

                            shutil.move(os.path.join(root, file), os.path.join(SING_BOX_DIR, file))

                            

                shutil.rmtree(temp_extract, ignore_errors=True)

            return True

        except Exception as e:

            self.error_occurred.emit(f"Extract error: {e}")

            return False



    def generate_standard_config(self):

        server = self.config.get("vless_server", "")

        port = int(self.config.get("vless_port", 443))

        uuid = self.config.get("vless_uuid", "")

        sni = self.config.get("vless_sni", "")

        pbk = self.config.get("vless_pbk", "")

        sid = self.config.get("vless_sid", "")

        

        cfg = {

            "log": {"level": "info"},

            "inbounds": [{

                "type": "socks",

                "tag": "socks-in",

                "listen": "127.0.0.1",

                "listen_port": 1790

            }],

            "outbounds": [{

                "type": "vless",

                "tag": "vless-out",

                "server": server,

                "server_port": port,

                "uuid": uuid,

                "flow": "xtls-rprx-vision" if pbk else "",

                "tls": {

                    "enabled": True,

                    "server_name": sni if sni else server,

                    "insecure": not bool(sni),

                    "utls": {"enabled": True, "fingerprint": "chrome"}

                }

            }]

        }

        

        if pbk:

            cfg["outbounds"][0]["tls"]["reality"] = {

                "enabled": True,

                "public_key": pbk,

                "short_id": sid

            }



        config_path = os.path.join(SING_BOX_DIR, "config.json")

        with open(config_path, "w", encoding="utf-8") as f:

            json.dump(cfg, f, indent=2)

            

        return config_path



    def start(self):
        if self.is_running():
            return True

        existing_pid = self.find_existing_process()
        if existing_pid:
            print(f"[VLESS] Найден уже запущенный процесс (PID {existing_pid}), используем его.")
            self.process = AdoptedProcess(existing_pid)
            self.running = True
            self.status_changed.emit(True)
            return True

        if not self.extract_sing_box():
            return False

        from managers import config_manager

        self.config = config_manager.load_config()

        mode = self.config.get("vless_mode", "standard")

        

        try:

            if mode == "standard":

                config_path = self.generate_standard_config()

                self.process = subprocess.Popen(

                    [SING_BOX_EXE, "run", "-c", config_path],

                    cwd=SING_BOX_DIR,

                    stdout=subprocess.DEVNULL,

                    stderr=subprocess.DEVNULL,

                    creationflags=subprocess.CREATE_NO_WINDOW

                )

            else:

                script_path = os.path.join(CURRENT_DIR, "evpn/wl_torred_vless.py")

                

                # Support passing arguments like "next", "prev", "keep"

                args = [sys.executable, script_path]

                if getattr(self, "rot_cmd", None):

                    args.append(self.rot_cmd)

                    self.rot_cmd = None

                

                env = os.environ.copy()

                env["PYTHONIOENCODING"] = "utf-8"

                self.process = subprocess.Popen(

                    args,

                    stdout=subprocess.PIPE,

                    stderr=subprocess.STDOUT,

                    creationflags=subprocess.CREATE_NO_WINDOW,

                    text=True,

                    bufsize=1,

                    encoding='utf-8',

                    env=env

                )

                import threading

                def read_logs():

                    try:

                        for line in self.process.stdout:

                            print(line, end='')

                    except:

                        pass

                threading.Thread(target=read_logs, daemon=True).start()

                

            self.running = True

            self.status_changed.emit(True)

            return True

        except Exception as e:

            with open(os.path.join(CURRENT_DIR, 'logs', 'vless_manager_error.log'), 'w', encoding='utf-8') as f:

                f.write(str(e))

            self.error_occurred.emit(str(e))

            self.running = False

            return False



    def stop(self):

        if not self.running:

            return

            

        try:

            if self.process:

                self.process.terminate()

                try:

                    self.process.wait(timeout=0.2)

                except subprocess.TimeoutExpired:

                    self.process.kill()

                    

            # Kill stray sing-box processes

            for proc in psutil.process_iter(['name', 'pid']):

                try:

                    if proc.info['name'] and proc.info['name'].lower() == "sing-box.exe":

                        p = psutil.Process(proc.info['pid'])

                        p.kill()

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):

                    pass

                    

            # Also kill evpn/wl_torred_vless.py python processes if any

            # It's tricky to kill just that python script cleanly without affecting the main app

            # But the process object kill should have handled it mostly.

            

        except Exception as e:

            pass

            

        self.process = None

        self.running = False

        self.status_changed.emit(False)



    def open_settings(self):

        from managers import system_utils as utils

        utils.run_script("evpn/vless_settings.pyw")



    def get_status_text(self):

        if self.running:

            return lang.T("Остановить VLESS Proxy", "Stop VLESS Proxy")

        return lang.T("Запустить VLESS Proxy", "Start VLESS Proxy")



_manager = None

def get_manager(config=None):

    global _manager

    if _manager is None:

        _manager = VlessManager(config)

    return _manager





