import sys
import os
import time
import socket
import subprocess

from managers.system_utils import get_base_dir
CURRENT_DIR = get_base_dir()

def _find_gatik_exe():
    candidates = [
        os.path.join(CURRENT_DIR, 'bin', 'gatik.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bin', 'gatik.exe'),
        os.path.join(os.path.dirname(sys.executable), 'bin', 'gatik.exe'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None

def _find_tgws_exe():
    candidates = [
        os.path.join(CURRENT_DIR, 'bin', 'tgws.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bin', 'tgws.exe'),
        os.path.join(os.path.dirname(sys.executable), 'bin', 'tgws.exe'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None

class TGWSManager:
    def __init__(self):
        self._running = False
        self.config = {}
        self.gatik_process = None
        self.tgws_process = None
        self._gatik_last_check = 0
        self._gatik_is_running_cached = False

    @property
    def running(self):
        if hasattr(self, 'tgws_process') and self.tgws_process:
            if self.tgws_process.poll() is None:
                self._running = True
                return True
            else:
                self.tgws_process = None
                self._running = False
        try:
            port = int(self.config.get("tgws_port", 1480))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            res = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if res == 0:
                return True
        except Exception:
            pass
        return self._running

    @running.setter
    def running(self, val):
        self._running = val

    def is_running(self):
        return self.running

    def log(self, msg):
        print(f"[TGWS] {msg}")

    def update_config(self, config):
        self.config = config

    def start(self):
        if self.running:
            return True

        port = int(self.config.get("tgws_port", 1480))
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                self.log(f"Порт {port} уже занят, возможно TGWS уже запущен. Используем существующий процесс.")
                self.running = True
                return True
        except Exception:
            pass

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        tgws_exe = _find_tgws_exe()
        if tgws_exe and os.path.exists(tgws_exe):
            try:
                self.tgws_process = subprocess.Popen([tgws_exe], cwd=CURRENT_DIR, creationflags=creationflags)
                time.sleep(1)
                if self.is_running():
                    self.running = True
                    self.log(f"TGWS Proxy (C++) запущен: {tgws_exe}")

                    # Start Gatik (C++) if executable exists
                    try:
                        gatik_exe = _find_gatik_exe()
                        if gatik_exe and os.path.exists(gatik_exe):
                            self.gatik_process = subprocess.Popen([gatik_exe], cwd=CURRENT_DIR, creationflags=creationflags)
                            self.log(f"Шлюз Gatik (C++) запущен: {gatik_exe}")
                    except Exception as e:
                        self.log(f"Failed to start gatik.exe: {e}")

                    return True
                else:
                    self.log(f"TGWS process exited immediately after launch.")
            except Exception as e:
                self.log(f"Failed to start C++ tgws.exe: {e}")
        else:
            self.log(f"Ошибка: tgws.exe не найден (искали в {CURRENT_DIR}\\bin)")

        return False

    def stop(self):
        if hasattr(self, 'tgws_process') and self.tgws_process:
            try:
                self.tgws_process.terminate()
                self.tgws_process.wait(timeout=2)
            except Exception:
                try:
                    self.tgws_process.kill()
                except Exception:
                    pass
            self.tgws_process = None
            self.log("TGWS Proxy (C++) остановлен")

        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if (proc.info.get('name') or '').lower() == 'tgws.exe':
                        proc.kill()
                except Exception:
                    pass
        except Exception:
            pass

        self._running = False

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
