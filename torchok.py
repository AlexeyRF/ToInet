import sys
import os
import subprocess
import time
import psutil
from PyQt5.QtWidgets import QMessageBox

# Пути к файлам
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TORRC_FILE = os.path.join(CURRENT_DIR, "torrc")
RECREATE_TORRC_FILE = os.path.join(CURRENT_DIR, "recreate_torrc.txt")
LAUNCHER_SCRIPT = os.path.join(CURRENT_DIR, "launcher.pyw")
CLOSER_SCRIPT = os.path.join(CURRENT_DIR, "closer.pyw")
AUTO_MAESTRO_SCRIPT = os.path.join(CURRENT_DIR, "auto_maestro.pyw")
MAESTRO_SCRIPT = os.path.join(CURRENT_DIR, "maestro.pyw")
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
        """Читает флаг пересоздания torrc из файла"""
        if not os.path.exists(RECREATE_TORRC_FILE):
            with open(RECREATE_TORRC_FILE, "w") as f:
                f.write("false")
            return False
        with open(RECREATE_TORRC_FILE, "r") as f:
            return f.read().strip().lower() == "true"

    def _write_recreate_torrc(self, value: bool):
        """Записывает флаг пересоздания torrc в файл"""
        with open(RECREATE_TORRC_FILE, "w") as f:
            f.write("true" if value else "false")

    def _run_script(self, script_name):
        """Запускает скрипт в фоне"""
        if os.path.exists(script_name):
            subprocess.Popen([sys.executable, script_name], 
                           creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        return False

    def _run_script_blocking(self, script_name):
        """Запускает скрипт и ждет его завершения"""
        if os.path.exists(script_name):
            subprocess.call([sys.executable, script_name])
            return True
        return False

    def _delete_torrc_files(self):
        """Удаляет файлы torrc"""
        torrc_paths = [TORRC_FILE, os.path.join(CURRENT_DIR, "for_servers/torrc")]
        
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
                return self._run_script(LAUNCHER_SCRIPT)
        
        # Проверяем существование torrc
        if not os.path.exists(torrc_path):
            log("torrc не найден, запускаем auto_maestro для создания")
            self._run_script_blocking(AUTO_MAESTRO_SCRIPT)
            
            if not os.path.exists(torrc_path):
                log("Не удалось создать torrc, используем launcher.pyw")
                return self._run_script(LAUNCHER_SCRIPT)
        
        # Запускаем tor.exe
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if not self.show_window else 0
            
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
                return self._run_script(LAUNCHER_SCRIPT)
                
        except Exception as e:
            log(f"Ошибка запуска TOR напрямую: {e}")
            return self._run_script(LAUNCHER_SCRIPT)

    def _stop_tor_direct(self):
        """Останавливает TOR, запущенный напрямую"""
        if self.tor_process:
            try:
                # Пытаемся завершить процесс
                self.tor_process.terminate()
                time.sleep(1)
                if self.tor_process.poll() is None:
                    self.tor_process.kill()
                self.tor_process = None
                log("TOR процесс остановлен")
                return True
            except Exception as e:
                log(f"Ошибка остановки TOR процесса: {e}")
        
        # Если не получилось через процесс, используем closer.pyw
        return self._run_script(CLOSER_SCRIPT)

    def start(self):
        """Запускает TOR"""
        if self.tor_running:
            return True

        if self.recreate_torrc:
            self._delete_torrc_files()
            self._run_script_blocking(AUTO_MAESTRO_SCRIPT)

        if not os.path.exists(TORRC_FILE):
            self._run_script_blocking(AUTO_MAESTRO_SCRIPT)
        
        # Пытаемся запустить напрямую через tor.exe
        if self._start_tor_direct():
            self.tor_running = True
            return True
        
        # Если прямой запуск не удался, используем старый метод
        if self._run_script(LAUNCHER_SCRIPT):
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
                QMessageBox.critical(parent, "Ошибка", 
                                   "Не удалось перезапустить TOR")
            return False

    def new_circuit(self, parent=None):
        """Запрашивает новую цепочку (NEWNYM) у TOR"""
        if not self.tor_running:
            if parent:
                QMessageBox.warning(parent, "Ошибка", "TOR не запущен.")
            return False

        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(('127.0.0.1', 9851))
            
            s.sendall(b'AUTHENTICATE ""\r\n')
            resp = s.recv(1024).decode('utf-8')
            if not resp.startswith('250'):
                log(f"ControlPort AUTHENTICATE failed: {resp}")
                s.close()
                if parent:
                    QMessageBox.warning(parent, "Ошибка", f"Ошибка аутентификации ControlPort: {resp}")
                return False
                
            s.sendall(b'SIGNAL NEWNYM\r\n')
            resp = s.recv(1024).decode('utf-8')
            s.close()
            
            if resp.startswith('250'):
                log("Успешно запрошена новая цепочка TOR")
                if parent:
                    QMessageBox.information(parent, "TOR", "Новая цепочка успешно запрошена!")
                return True
            else:
                log(f"Ошибка при запросе NEWNYM: {resp}")
                if parent:
                    QMessageBox.warning(parent, "Ошибка", f"TOR вернул ошибку при запросе новой цепочки: {resp}")
                return False
        except Exception as e:
            log(f"Не удалось подключиться к ControlPort: {e}")
            if parent:
                QMessageBox.warning(parent, "Ошибка", f"Не удалось подключиться к ControlPort TOR (порт 9851).\nВозможно, он не включен в настройках.\nОшибка: {e}")
            return False

    def is_running(self):
        """Возвращает статус работы TOR"""
        # Проверяем, жив ли процесс, если запускали напрямую
        if self.tor_running and self.tor_process:
            if self.tor_process.poll() is not None:
                self.tor_running = False
        return self.tor_running

    def toggle_recreate(self):
        """Переключает флаг пересоздания torrc"""
        self.recreate_torrc = not self.recreate_torrc
        self._write_recreate_torrc(self.recreate_torrc)

    def get_recreate_status(self):
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
        QMessageBox.critical(None, "Ошибка", 
                           f"Не найдены файлы настроек TOR:\n"
                           f"{MAESTRO_SCRIPT}\n"
                           f"или\n{AUTO_MAESTRO_SCRIPT}")
        return False


def log(msg):
    print(f"[TOR Manager] {msg}")

def get_manager():
    """Возвращает экземпляр менеджера TOR"""
    return TorManager()