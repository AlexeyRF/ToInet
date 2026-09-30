from managers import system_utils as lang
import sys
import os
import subprocess
import time
import psutil
from PyQt5.QtWidgets import QMessageBox

# Пути к файлам
import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TORRC_FILE = os.path.join(CURRENT_DIR, "data", "torrc")
MAESTRO_SCRIPT = os.path.join(CURRENT_DIR, os.path.join("ui", "maestro.pyw"))
TOR_EXE = os.path.join(CURRENT_DIR, "tor", "tor.exe")

class TorManager:
    def __init__(self):
        self.tor_running = False
        self.tor_process = None
        self.recreate_torrc = self._read_recreate_torrc()
        self.show_window = False

    def update_config(self, config):
        """Обновляет конфигурацию из основного config"""
        self.show_window = config.get("tor_show_window", False)

    def _read_recreate_torrc(self):
        from managers import config_manager
        cfg = config_manager.load_config()
        val = cfg.get("recreate_torrc", "none")
        if isinstance(val, bool): return "full" if val else "none"
        if val == "true": return "full"
        if val == "false": return "bridges"
        return str(val).lower()

    def _write_recreate_torrc(self, value):
        from managers import config_manager
        cfg = config_manager.load_config()
        cfg["recreate_torrc"] = str(value).lower()
        config_manager.save_config(cfg)

    def _launch_tor_direct(self):
        if not os.path.exists(TOR_EXE):
            log("tor.exe not found!")
            return False
        if not os.path.exists(TORRC_FILE):
            log("torrc not found!")
            return False
            
        creation_flags = subprocess.CREATE_NEW_CONSOLE if self.show_window else subprocess.CREATE_NO_WINDOW
        stdout = None if self.show_window else subprocess.DEVNULL
        stderr = None if self.show_window else subprocess.DEVNULL
        
        try:
            self.tor_process = subprocess.Popen([TOR_EXE, '-f', TORRC_FILE], stdout=stdout, stderr=stderr, creationflags=creation_flags)
            self.tor_running = True
            log("tor.exe started directly")
            return True
        except Exception as e:
            log(f"Failed to start tor.exe: {e}")
            self.tor_running = False
            return False

    def _run_script(self, script_name):
        """Запускает скрипт в фоне"""
        if os.path.exists(script_name):
            subprocess.Popen([sys.executable, script_name], 
                           creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        return False


    def _generate_torrc_from_bridges(self):
        """Generates torrc from bridges.txt"""
        bridges_path = os.path.join(CURRENT_DIR, "data", "bridges.txt")
        if not os.path.exists(bridges_path):
            log(f"bridges.txt not found at {bridges_path}")
            return False
            
        with open(bridges_path, "r", encoding="utf-8") as f:
            bridges = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            
        data_dir = os.path.join(CURRENT_DIR, "data")
        geoip_path = os.path.join(data_dir, "geoip")
        geoip6_path = os.path.join(data_dir, "geoip6")
        lyrebird_path = os.path.join(CURRENT_DIR, "tor", "pluggable_transports", "lyrebird.exe")
        
        torrc_lines = [
            f"DataDirectory {data_dir}",
            f"GeoIPFile {geoip_path}",
            f"GeoIPv6File {geoip6_path}",
            "SocksPort 9853",
            "ControlPort 9851",
            "HashedControlPassword 16:FDD492298759EE7D608D25F04A895488921206AD3109F87E7CC80F09D1",
            "ExitNodes {us},{de},{fr},{nl},{se}",
            "UseBridges 1"
        ]
        torrc_lines.extend([f"Bridge {bridge}" for bridge in bridges])
        torrc_lines.extend([
            f"ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec {lyrebird_path}",
            "AvoidDiskWrites 1",
            "HardwareAccel 1",
            "ClientOnly 1",
            "AutomapHostsOnResolve 1",
            "SafeLogging 1"
        ])
        
        with open(TORRC_FILE, "w", encoding="utf-8") as f:
            f.write('
'.join(torrc_lines))
        log("Generated torrc from bridges")
        return True

    def _update_bridges_in_torrc(self):
        """Updates bridges in existing torrc"""
        bridges_path = os.path.join(CURRENT_DIR, "data", "bridges.txt")
        if not os.path.exists(bridges_path) or not os.path.exists(TORRC_FILE):
            return False
            
        with open(bridges_path, "r", encoding="utf-8") as f:
            bridges = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            
        with open(TORRC_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if not line.strip().startswith("Bridge ") and line.strip() != "UseBridges 1":
                new_lines.append(line.rstrip())
                
        if bridges:
            new_lines.append("UseBridges 1")
            for b in bridges:
                new_lines.append(f"Bridge {b}")
                
        with open(TORRC_FILE, "w", encoding="utf-8") as f:
            f.write('
'.join(new_lines))
        log("Updated bridges in torrc")
        return True

    def _run_script_blocking(self, script_name):
        """Запускает скрипт и ждет его завершения"""
        if os.path.exists(script_name):
            subprocess.call([sys.executable, script_name])
            return True
        return False

    def _delete_torrc_files(self):
        """Удаляет файлы torrc"""
        torrc_paths = [TORRC_FILE, os.path.join(CURRENT_DIR, "server", "torrc")]
        
        for torrc_path in torrc_paths:
            if os.path.exists(torrc_path):
                try:
                    os.remove(torrc_path)
                except Exception as e:
                    pass

    def _start_tor_direct(self):
        """Запускает TOR напрямую через tor.exe -f torrc с абсолютными путями"""
        tor_exe_path = os.path.abspath(TOR_EXE)
        torrc_path = os.path.abspath(TORRC_FILE)
        
        # Проверяем существование tor.exe
        if not os.path.exists(tor_exe_path):
            # Ищем tor.exe в других местах
            possible_paths = [
                os.path.join(CURRENT_DIR, "tor.exe"),
                os.path.join(CURRENT_DIR, "Tor", "tor.exe"),
                os.path.join(CURRENT_DIR, "bin", "tor.exe")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    tor_exe_path = os.path.abspath(path)
                    break
            else:
                log("tor.exe не найден, используется launcher.pyw")
                return self._launch_tor_direct()
        
        # Проверяем существование torrc
        if not os.path.exists(torrc_path):
            log("torrc не найден, запускаем auto_maestro для создания")
            self._generate_torrc_from_bridges()
            
            if not os.path.exists(torrc_path):
                log("Не удалось создать torrc, используем launcher.pyw")
                return self._launch_tor_direct()
        
        # Запускаем tor.exe
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if not self.show_window else subprocess.CREATE_NEW_CONSOLE
            
            if self.show_window:
                # Создаем новое окно консоли
                self.tor_process = subprocess.Popen(
                    [tor_exe_path, "-f", torrc_path],
                    creationflags=creation_flags,
                    cwd=CURRENT_DIR  # Явно задаем рабочую директорию
                )
            else:
                # Без окна
                self.tor_process = subprocess.Popen(
                    [tor_exe_path, "-f", torrc_path],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=CURRENT_DIR  # Явно задаем рабочую директорию
                )
            
            # Небольшая пауза для запуска процесса
            time.sleep(2)
            
            # Проверяем, запустился ли процесс
            if self.tor_process.poll() is None:
                log(f"TOR запущен напрямую через {tor_exe_path}")
                return True
            else:
                log("Не удалось запустить TOR напрямую, используем launcher.pyw")
                self.tor_process = None
                return self._launch_tor_direct()
                
        except Exception as e:
            log(f"Ошибка запуска TOR напрямую: {e}")
            self.tor_process = None
            return self._launch_tor_direct()

    def _stop_tor_direct(self):
        """Останавливает TOR, запущенный напрямую"""
        if self.tor_process:
            try:
                # Пытаемся завершить процесс
                self.tor_process.terminate()
                try:
                    self.tor_process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass
                if self.tor_process.poll() is None:
                    self.tor_process.kill()
                self.tor_process = None
                log("TOR процесс остановлен")
                return True
            except Exception as e:
                log(f"Ошибка остановки TOR процесса: {e}")
        # Если не получилось через процесс, ищем и убиваем процесс tor.exe
        tor_path = os.path.normcase(os.path.normpath(TOR_EXE))
        killed = False
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'tor' in proc.info['name'].lower():
                        exe_path = proc.exe()
                        if exe_path and os.path.normcase(os.path.normpath(exe_path)) == tor_path:
                            proc.kill()
                            killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            if killed:
                log("TOR процесс остановлен через поиск процессов")
            return killed
        except Exception as e:
            log(f"Ошибка при поиске и остановке TOR: {e}")
            return False

    def start(self):
        """Запуск TOR"""
        if self.tor_running:
            return True

        if self.recreate_torrc == "full":
            self._delete_torrc_files()
            self._generate_torrc_from_bridges()
        elif self.recreate_torrc == "bridges":
            self._run_script_blocking(UPDATE_BRIDGES_SCRIPT)
        # if "none", do nothing

        if not os.path.exists(TORRC_FILE):
            self._generate_torrc_from_bridges()
        
        # Только через launcher.pyw, как просил пользователь
        if self._launch_tor_direct():
            self.tor_running = True
            return True

        return False

    def stop(self):
        """Останавливает TOR"""
        if not self.tor_running:
            return
        
        # Пытаемся остановить напрямую
        self._stop_tor_direct()
        self.tor_running = False

    def restart(self, parent=None):
        """Перезапускает TOR"""
        if self.tor_running:
            self.stop()
            time.sleep(2)
        
        if self.start():
            if parent:
                QMessageBox.information(parent, "Перезапуск TOR", 
                                      "TOR успешно перезапущен!")
            return True
        else:
            if parent:
                QMessageBox.critical(parent, T("Ошибка", "Error"), 
                                   "Не удалось перезапустить TOR")
            return False

    def new_circuit(self, parent=None):
        """Запрашивает новую цепочку (NEWNYM) у TOR"""
        if not self.tor_running:
            if parent:
                QMessageBox.warning(parent, T("Ошибка", "Error"), "TOR не запущен.")
            return False

        try:
            import socket
            import json
            pool_enabled = False
            pool_size = 3
            try:
                with open(os.path.join(CURRENT_DIR, "data", "config.json"), "r", encoding="utf-8") as f:
                    config = json.load(f)
                    pool_enabled = config.get("tor_pool_enabled", False)
                    pool_size = int(config.get("tor_pool_size", 3))
            except:
                pass
                
            if pool_enabled and pool_size > 1:
                socks_port = 9853
                try:
                    with open(TORRC_FILE, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith("SocksPort "):
                                socks_port = int(line.split()[1])
                except: pass
                control_ports = [socks_port + 2000 + i for i in range(pool_size)]
            else:
                control_ports = [9851]
                
            success = True
            errors = []
            for cp in control_ports:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    s.connect(('127.0.0.1', cp))
                    s.sendall(b'AUTHENTICATE "toinet"\r\n')
                    resp = s.recv(1024).decode('utf-8')
                    if not resp.startswith('250'):
                        errors.append(f"Auth {cp}: {resp}")
                        success = False
                    else:
                        s.sendall(b'SIGNAL NEWNYM\r\n')
                        resp = s.recv(1024).decode('utf-8')
                        if not resp.startswith('250'):
                            errors.append(f"NEWNYM {cp}: {resp}")
                            success = False
                    s.close()
                except Exception as e:
                    errors.append(f"Port {cp}: {e}")
                    success = False
            
            if success:
                log("Успешно запрошена новая цепочка TOR")
                if parent:
                    QMessageBox.information(parent, "TOR", "Новая цепочка успешно запрошена!")
                return True
            else:
                err_str = "\n".join(errors)
                log(f"Ошибка при запросе NEWNYM: {err_str}")
                if parent:
                    QMessageBox.warning(parent, T("Ошибка", "Error"), f"Ошибка при запросе новой цепочки:\n{err_str}")
                return False
        except Exception as e:
            log(f"Внутренняя ошибка: {e}")
            if parent:
                QMessageBox.warning(parent, T("Ошибка", "Error"), f"Внутренняя ошибка:\n{e}")
            return False

    def is_running(self):
        """Возвращает статус работы TOR"""
        # Проверяем, жив ли процесс, если запускали напрямую
        if self.tor_running and self.tor_process:
            if self.tor_process.poll() is not None:
                self.tor_running = False
        return self.tor_running

    def toggle_recreate(self):
        """Цикличное переключение режима пересоздания torrc"""
        if self.recreate_torrc == "full": self.recreate_torrc = "bridges"
        elif self.recreate_torrc == "bridges": self.recreate_torrc = "none"
        else: self.recreate_torrc = "full"
        self._write_recreate_torrc(self.recreate_torrc)

    def get_recreate_mode(self):
        """Возвращает статус флага пересоздания torrc"""
        return self.recreate_torrc

    def delete_config(self):
        """Удаляет конфигурационные файлы TOR"""
        self._delete_torrc_files()

    def open_settings(self):
        """Открывает настройки TOR (maestro.pyw, НЕ auto_maestro)"""
        # Сначала проверяем наличие maestro.pyw
        if os.path.exists(MAESTRO_SCRIPT):
            try:
                # Запускаем maestro.pyw с обычным окном (не скрытым)
                subprocess.Popen([sys.executable, MAESTRO_SCRIPT])
                log(f"Запущен {MAESTRO_SCRIPT}")
                return True
            except Exception as e:
                log(f"Ошибка запуска {MAESTRO_SCRIPT}: {e}")
        
        # Если maestro.pyw не найден, пробуем auto_maestro.pyw
        if os.path.exists(AUTO_MAESTRO_SCRIPT):
            try:
                subprocess.Popen([sys.executable, AUTO_MAESTRO_SCRIPT])
                log(f"Запущен {AUTO_MAESTRO_SCRIPT} (как запасной вариант)")
                return True
            except Exception as e:
                log(f"Ошибка запуска {AUTO_MAESTRO_SCRIPT}: {e}")
        
        # Если ничего не сработало
        QMessageBox.critical(None, T("Ошибка", "Error"), 
                           f"Не найдены файлы настроек TOR:\n"
                           f"{MAESTRO_SCRIPT}\n"
                           f"или\n{AUTO_MAESTRO_SCRIPT}")
        return False


def log(msg):
    print(f"[TOR Manager] {msg}")

def get_manager():
    """Возвращает экземпляр менеджера TOR"""
    return TorManager()





