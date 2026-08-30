import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
import threading
import time
import socket
from tgws import tg_ws_proxy, config as tgws_config
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
            
            dc_opt = tgws_config.parse_dc_ip_list(dc_ip_list)
            
            tgws_config.proxy_config.port = port
            tgws_config.proxy_config.host = host
            tgws_config.proxy_config.dc_redirects = dc_opt
            
            secret = self.config.get("tgws_secret")
            if secret:
                try:
                    tgws_config.proxy_config.secret = secret
                except: pass
                
            fake_tls = self.config.get("tgws_fake_tls", "")
            tgws_config.proxy_config.fake_tls_domain = fake_tls
            tgws_config.proxy_config.fronting_sni = self.config.get("tgws_fronting_sni", "")
            
            tasks = [tg_ws_proxy._run(stop_event=stop_ev)]
            
            try:
                import gatik
                tasks.append(gatik.main(stop_event=stop_ev))
            except Exception as e:
                self.log(f"Failed to load gatik for async loop: {e}")
                
            loop.run_until_complete(
                tgws_windows._asyncio.gather(*tasks))
        except Exception as exc:
            self.log(f"TG WS Proxy thread crashed: {exc}")
            if "10048" in str(exc) or "Address already in use" in str(exc):
                QMessageBox.critical(None, "Ошибка TG WS Proxy", 
                                   f"Не удалось запустить TG WS Proxy:\nПорт {port} уже используется другим приложением.")
        finally:
            try:
                pending = tgws_windows._asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(tgws_windows._asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass
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
                base_dir = CURRENT_DIR
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
                
            # Start Gatik is now handled in the thread
                
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
            base_dir = CURRENT_DIR
            reab_script = os.path.join(base_dir, "socks-reabilitator.pyw")
            if os.path.exists(reab_script):
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.Popen([sys.executable, reab_script, "--stop"], creationflags=creationflags)
                self.log("Отправлена команда остановки Socks-Reabilitator")
        except Exception as e:
            self.log(f"Failed to stop reabilitator: {e}")
            
        # Gatik (Telegram Smart Router) остановлен вместе с циклом

_manager = TGWSManager()

def get_manager():
    return _manager



