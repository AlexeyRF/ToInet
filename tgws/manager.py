import sys, os
if getattr(sys, 'frozen', False):
    CURRENT_DIR = os.path.dirname(sys.executable)
else:
    CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _find_gatik_exe():
    candidates = [
        os.path.join(CURRENT_DIR, 'bin', 'gatik.exe'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'gatik.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bin', 'gatik.exe'),
        os.path.join(os.path.dirname(sys.executable), 'bin', 'gatik.exe'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None
import threading
import time
import socket
from tgws import tg_ws_proxy, config as tgws_config
import asyncio
from PySide6.QtWidgets import QMessageBox
import sys
import subprocess
import os
import json

class TGWSManager:
    def __init__(self):
        self._running = False
        self.thread = None
        self.stop_event = None
        self.config = {}
        self.gatik_process = None

    @property
    def running(self):
        if self._running:
            if self.thread and not self.thread.is_alive():
                port = self.config.get("tgws_port", 1480)
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    res = sock.connect_ex(('127.0.0.1', port))
                    sock.close()
                    if res != 0:
                        self._running = False
                except:
                    self._running = False
            return self._running
        try:
            port = self.config.get("tgws_port", 1480)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            res = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if res == 0:
                self._running = True
                return True
        except:
            pass
        return False

    @running.setter
    def running(self, val):
        self._running = val

    def is_running(self):
        return self.running

    def log(self, msg):
        print(f"[TGWS] {msg}")

    def update_config(self, config):
        self.config = config

    def _run_thread(self):
        async def runner():
            stop_ev = asyncio.Event()
            self.stop_event = (asyncio.get_running_loop(), stop_ev)
            
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
            tgws_config.proxy_config.fallback_cfproxy = self.config.get("tgws_fallback_cfproxy", True)
            tgws_config.proxy_config.cfproxy_h2_media = self.config.get("tgws_cfproxy_h2_media", True)
            tgws_config.proxy_config.cfproxy_user_domains = tgws_config.coerce_domain_list(self.config.get("tgws_cfproxy_user_domain", ""))
            tgws_config.proxy_config.cfproxy_worker_domains = tgws_config.coerce_domain_list(self.config.get("tgws_cfproxy_worker_domain", ""))
            
            tasks = [tg_ws_proxy._run(stop_event=stop_ev)]
            gatik_exe = os.path.join(CURRENT_DIR, "bin", "gatik.exe")
            if not os.path.exists(gatik_exe):
                try:
                    import importlib.util
                    dev_gatik = os.path.join(CURRENT_DIR, ".dev", "gatik.py")
                    if os.path.exists(dev_gatik):
                        spec = importlib.util.spec_from_file_location("gatik", dev_gatik)
                        gatik = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(gatik)
                        tasks.append(gatik.main(stop_event=stop_ev))
                except Exception as e:
                    self.log(f"Failed to load gatik from .dev for async loop: {e}")
                
            await asyncio.gather(*tasks)

        try:
            asyncio.run(runner())
        except Exception as exc:
            import traceback
            self.log(f"TG WS Proxy thread crashed: {exc}")
            traceback.print_exc()
            if "10048" in str(exc) or "Address already in use" in str(exc):
                port = self.config.get("tgws_port", 1480)
                self.log(f"Порт {port} уже используется другим приложением.")
        finally:
            self.stop_event = None

    def start(self):
        if self.running:
            return True
        
        port = self.config.get("tgws_port", 1480)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            self.log(f"Порт {port} уже занят, возможно TGWS уже запущен. Используем существующий процесс.")
            self.running = True
            return True
        
        pass
        pass
        
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
                        reab_script = os.path.join(base_dir, "small_actions/socks-reabilitator.pyw")
                        if os.path.exists(reab_script):
                            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                            subprocess.Popen([sys.executable, reab_script, "--silent"], creationflags=creationflags)
                            self.log("Socks-Reabilitator запущен в фоне")
            except Exception as e:
                self.log(f"Failed to start reabilitator: {e}")
                
            # Start Gatik (C++) if executable exists
            try:
                gatik_exe = _find_gatik_exe()
                if gatik_exe and os.path.exists(gatik_exe):
                    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    self.gatik_process = subprocess.Popen([gatik_exe], cwd=CURRENT_DIR, creationflags=creationflags)
                    self.log(f"Шлюз Gatik (C++) запущен: {gatik_exe}")
            except Exception as e:
                self.log(f"Failed to start gatik.exe: {e}")
                
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
        
        # Stop CF proxy domain refresh loop
        try:
            from .config import stop_cfproxy_domain_refresh
            stop_cfproxy_domain_refresh()
        except Exception:
            pass

        self.thread = None
        self.stop_event = None
        self.running = False
        self.log("TG WS Proxy остановлен")
        
        # Stop reabilitator
        try:
            base_dir = CURRENT_DIR
            reab_script = os.path.join(base_dir, "small_actions/socks-reabilitator.pyw")
            if os.path.exists(reab_script):
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.Popen([sys.executable, reab_script, "--stop"], creationflags=creationflags)
                self.log("Отправлена команда остановки Socks-Reabilitator")
        except Exception as e:
            self.log(f"Failed to stop reabilitator: {e}")
            
        if hasattr(self, 'gatik_process') and self.gatik_process:
            try:
                self.gatik_process.terminate()
                self.gatik_process.wait(timeout=2)
            except Exception:
                try:
                    self.gatik_process.kill()
                except Exception:
                    pass
            self.gatik_process = None
            self.log("Шлюз Gatik (C++) остановлен")
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if (proc.info.get('name') or '').lower() == 'gatik.exe':
                        proc.kill()
                except Exception:
                    pass
        except Exception:
            pass

    def is_gatik_running(self):
        if hasattr(self, 'gatik_process') and self.gatik_process:
            if self.gatik_process.poll() is None:
                return True
            self.gatik_process = None

        now = time.time()
        if hasattr(self, '_gatik_last_check') and (now - self._gatik_last_check < 2.0):
            return getattr(self, '_gatik_is_running_cached', False)
        self._gatik_last_check = now

        running = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.02)
            res = sock.connect_ex(('127.0.0.1', 1777))
            sock.close()
            if res == 0:
                running = True
        except Exception:
            pass
        self._gatik_is_running_cached = running
        return running

    def start_gatik(self):
        if self.is_gatik_running():
            return True
        try:
            gatik_exe = _find_gatik_exe()
            if gatik_exe and os.path.exists(gatik_exe):
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self.gatik_process = subprocess.Popen([gatik_exe], cwd=CURRENT_DIR, creationflags=creationflags)
                self.log(f'Шлюз Gatik (C++) запущен: {gatik_exe}')
                return True
            else:
                self.log(f'Ошибка: gatik.exe не найден (искали в {CURRENT_DIR})')
        except Exception as e:
            self.log(f'Failed to start gatik.exe: {e}')
        return False

    def stop_gatik(self):
        if hasattr(self, 'gatik_process') and self.gatik_process:
            try:
                self.gatik_process.terminate()
                self.gatik_process.wait(timeout=2)
            except Exception:
                try:
                    self.gatik_process.kill()
                except Exception:
                    pass
            self.gatik_process = None
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if (proc.info.get('name') or '').lower() == 'gatik.exe':
                        proc.kill()
                except Exception:
                    pass
        except Exception:
            pass
        self.log('Шлюз Gatik (C++) остановлен')

_manager = TGWSManager()

def get_manager():
    return _manager






