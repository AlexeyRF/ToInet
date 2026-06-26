import threading
import time
import socket
import tg_ws_proxy
import windows as tgws_windows
from PyQt5.QtWidgets import QMessageBox
import sys
import subprocess
import os
import json

class TGWSManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.stop_event = None
        self.config = {}
        self.gatik_process = None

    def log(self, msg):
        print(f"[TGWS] {msg}")

    def update_config(self, config):
        self.config = config

    def _run_thread(self):
        loop = tgws_windows._asyncio.new_event_loop()
        tgws_windows._asyncio.set_event_loop(loop)
        
        stop_ev = tgws_windows._asyncio.Event()
        self.stop_event = (loop, stop_ev)
        
        try:
            port = self.config.get("tgws_port", 1480)
            host = self.config.get("tgws_host", "127.0.0.1")
            dc_ip_list = self.config.get("tgws_dc_ip", ["2:149.154.167.220", "4:149.154.167.220"])
            
            dc_opt = tg_ws_proxy.parse_dc_ip_list(dc_ip_list)
            
            loop.run_until_complete(
                tg_ws_proxy._run(port, dc_opt, stop_event=stop_ev, host=host))
        except Exception as exc:
            self.log(f"TG WS Proxy thread crashed: {exc}")
            if "10048" in str(exc) or "Address already in use" in str(exc):
                QMessageBox.critical(None, "Ошибка TG WS Proxy", 
                                   f"Не удалось запустить TG WS Proxy:\nПорт {port} уже используется другим приложением.")
        finally:
            loop.close()
            self.stop_event = None

    def start(self):
        if self.running:
            return True
        
        port = self.config.get("tgws_port", 1480)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            self.log(f"Порт {port} уже занят, возможно TGWS уже запущен.")
            self.running = True
            return True
        
        tgws_windows._ensure_dirs()
        tgws_windows.setup_logging(self.config.get("tgws_verbose", False))
        
        self.thread = threading.Thread(target=self._run_thread, daemon=True, name="tgws-proxy")
        self.thread.start()
        
        time.sleep(3)
        
        if self.thread.is_alive():
            self.running = True
            self.log("TG WS Proxy запущен")
            
            # Start reabilitator if configured
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, "socks_reabilitator_config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if "host" in cfg and "port" in cfg and "strat" in cfg:
                        reab_script = os.path.join(base_dir, "socks-reabilitator.pyw")
                        if os.path.exists(reab_script):
                            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                            subprocess.Popen([sys.executable, reab_script, "--silent"], creationflags=creationflags)
                            self.log("Socks-Reabilitator запущен в фоне")
            except Exception as e:
                self.log(f"Failed to start reabilitator: {e}")
                
            # Start Gatik
            try:
                gatik_script = os.path.join(base_dir, "gatik.py")
                if os.path.exists(gatik_script):
                    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    self.gatik_process = subprocess.Popen([sys.executable, gatik_script], creationflags=creationflags)
                    self.log("Gatik (Telegram Smart Router) запущен в фоне")
            except Exception as e:
                self.log(f"Failed to start gatik: {e}")
                
            return True
        else:
            self.log("Ошибка: поток TG WS Proxy не запустился")
            return False

    def stop(self):
        if self.stop_event:
            loop, stop_ev = self.stop_event
            loop.call_soon_threadsafe(stop_ev.set)
            if self.thread:
                self.thread.join(timeout=3)
        
        self.thread = None
        self.stop_event = None
        self.running = False
        self.log("TG WS Proxy остановлен")
        
        # Stop reabilitator
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            reab_script = os.path.join(base_dir, "socks-reabilitator.pyw")
            if os.path.exists(reab_script):
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.Popen([sys.executable, reab_script, "--stop"], creationflags=creationflags)
                self.log("Отправлена команда остановки Socks-Reabilitator")
        except Exception as e:
            self.log(f"Failed to stop reabilitator: {e}")
            
        if self.gatik_process:
            try:
                self.gatik_process.terminate()
                self.gatik_process.wait(timeout=3)
            except Exception:
                try:
                    self.gatik_process.kill()
                except:
                    pass
            self.gatik_process = None
            self.log("Gatik (Telegram Smart Router) остановлен")

_manager = TGWSManager()

def get_manager():
    return _manager
