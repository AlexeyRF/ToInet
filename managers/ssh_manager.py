from managers import system_utils as lang
from managers.system_utils import AdoptedProcess
from managers import config_manager

import os
import sys
import subprocess
import threading
import psutil
from PyQt5.QtCore import QObject, pyqtSignal

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSH_TUNNEL_EXE = os.path.join(CURRENT_DIR, "bin", "ssh_tunnel.exe")

def _pipe_process_output(proc, prefix="[SSHTunnel]"):
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

class SSHTunnelManager(QObject):
    status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, config=None):
        super().__init__()
        self.process = None
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
                self.status_changed.emit(False)
            else:
                return True
        elif not self.running:
            import time
            now = time.time()
            if now - getattr(self, '_last_scan_time', 0) > 15.0:
                self._last_scan_time = now
                socks_port = self.config.get("ssh_socks_port", 1770)
                existing_pid = self.find_existing_process(socks_port)
                if existing_pid:
                    self.process = AdoptedProcess(existing_pid)
                    self.running = True
                    self.status_changed.emit(True)
                    return True
        return self.running

    def find_existing_process(self, port=1770):
        exe_name = os.path.basename(SSH_TUNNEL_EXE).lower()
        
        # 1. Поиск по имени процесса (ssh_tunnel.exe) - всегда в приоритете
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = (proc.info.get('name') or "").lower()
                    if name == exe_name or 'ssh_tunnel' in name:
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass

        # 2. Проверка доступности локального порта
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            res = sock.connect_ex(('127.0.0.1', int(port)))
            sock.close()
            if res == 0:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        name = (proc.info.get('name') or "").lower()
                        if name == exe_name or 'ssh_tunnel' in name:
                            return proc.info['pid']
                        elif name == 'ssh.exe':
                            cmdline = " ".join(proc.info.get('cmdline') or [])
                            if f":{port}" in cmdline or "-D" in cmdline:
                                return proc.info['pid']
                    except Exception:
                        pass
        except Exception:
            pass

        return None

    def start(self, silent_if_not_configured=False):
        try:
            from managers import config_manager
            latest = config_manager.load_config()
            if latest:
                self.config.update(latest)
        except Exception:
            pass
        if self.is_running():
            return True

        host = self.config.get("ssh_host", "").strip()
        user = self.config.get("ssh_user", "").strip()
        port = int(self.config.get("ssh_port", 22))
        password = self.config.get("ssh_pass", "")
        socks_port = int(self.config.get("ssh_socks_port", 1770))
        share_lan = bool(self.config.get("ssh_share_lan", False))
        bind_addr = "0.0.0.0" if share_lan else "127.0.0.1"
        auto_reconnect = self.config.get("ssh_auto_reconnect", True)
        reconnect_interval = int(self.config.get("ssh_reconnect_interval", 5))

        if not host or not user:
            msg = lang.T(
                "SSH сервер или логин не настроены. Откройте настройки SSH.",
                "SSH host or username is not configured. Open SSH settings."
            )
            print(f"[SSHTunnel] {msg}")
            if not silent_if_not_configured:
                self.error_occurred.emit(msg)
                self.open_settings()
            return False

        if not os.path.exists(SSH_TUNNEL_EXE):
            err = lang.T(
                f"Файл {SSH_TUNNEL_EXE} не найден! Выполните сборку через cpp/build.bat",
                f"File {SSH_TUNNEL_EXE} not found! Build it via cpp/build.bat"
            )
            print(f"[SSHTunnel] {err}")
            self.error_occurred.emit(err)
            return False

        key_file = None
        cmd = [
            SSH_TUNNEL_EXE,
            "--host", host,
            "--port", str(port),
            "--user", user,
            "--socks-port", str(socks_port),
            "--bind", bind_addr,
            "--interval", str(reconnect_interval)
        ]

        if password:
            # Генерация одноразового ключа шифрования в файле
            key_bytes = os.urandom(32)
            key_hex = key_bytes.hex()
            pass_bytes = password.encode('utf-8')
            enc_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(pass_bytes)])
            enc_pass_hex = enc_bytes.hex()

            temp_dir = os.path.join(CURRENT_DIR, "data", "temp")
            os.makedirs(temp_dir, exist_ok=True)
            key_file = os.path.join(temp_dir, f".sk_{os.urandom(6).hex()}.key")
            with open(key_file, "w", encoding="utf-8") as kf:
                kf.write(key_hex)

            self.key_file = key_file
            cmd.extend(["--enc-pass", enc_pass_hex, "--key-file", key_file])

        if not auto_reconnect:
            cmd.append("--no-reconnect")

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        try:
            env = os.environ.copy()
            env["TOINET_SSH_HOST"] = host
            env["TOINET_SSH_USER"] = user

            print(f"[SSHTunnel] Запуск туннеля на {bind_addr}:{socks_port} -> {user}@{host}:{port}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags,
                env=env
            )
            self.running = True
            _pipe_process_output(self.process, "[SSHTunnel]")
            self.status_changed.emit(True)
            return True
        except Exception as e:
            err = f"Ошибка запуска SSH туннеля: {e}"
            print(f"[SSHTunnel] {err}")
            self.error_occurred.emit(err)
            self.running = False
            return False

    def stop(self):
        if not self.is_running() and not self.process:
            return True

        print("[SSHTunnel] Остановка SSH туннеля...")
        try:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except Exception:
                    self.process.kill()
                self.process = None
        except Exception as e:
            print(f"[SSHTunnel] Ошибка при остановке: {e}")

        # Kill any orphan ssh_tunnel.exe and associated ssh.exe
        exe_name = os.path.basename(SSH_TUNNEL_EXE).lower()
        socks_port = str(self.config.get("ssh_socks_port", 1770))
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    name = (proc.info.get('name') or "").lower()
                    if name == exe_name or 'ssh_tunnel' in name:
                        proc.kill()
                    elif name == 'ssh.exe':
                        cmdline = " ".join(proc.info.get('cmdline') or [])
                        if f":{socks_port}" in cmdline or "-D" in cmdline:
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

        if hasattr(self, 'key_file') and self.key_file and os.path.exists(self.key_file):
            try:
                os.remove(self.key_file)
            except Exception:
                pass
            self.key_file = None

        self.running = False
        self.status_changed.emit(False)
        return True

    def restart(self):
        self.stop()
        import time
        socks_port = int(self.config.get("ssh_socks_port", 1770))
        for _ in range(20):
            if not self.find_existing_process(socks_port):
                break
            time.sleep(0.1)
        time.sleep(0.2)
        return self.start()

    def open_settings(self):
        script_path = os.path.join(CURRENT_DIR, "ui", "ssh_settings.pyw")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.Popen([sys.executable, script_path], creationflags=creationflags)

_manager = None

def get_manager(config=None):
    global _manager
    if _manager is None:
        if config is None:
            config = config_manager.load_config()
        _manager = SSHTunnelManager(config)
    elif config is not None:
        _manager.update_config(config)
    return _manager
