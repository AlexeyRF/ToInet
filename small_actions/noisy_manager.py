import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from managers import system_utils as lang
from managers.system_utils import AdoptedProcess
import os
import subprocess
import psutil
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal

NOISY_SCRIPT = os.path.join(CURRENT_DIR, os.path.join("small_actions", "noisy.py"))

class NoisyManager(QObject):
    status_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, config=None):
        super().__init__()
        self.process = None
        self.running = False
        self.config = config or {}

    def is_running(self):
        if self.running and self.process:
            if self.process.poll() is not None:
                self.running = False
                self.process = None
        elif not self.running:
            existing_pid = self.find_existing_process()
            if existing_pid:
                self.process = AdoptedProcess(existing_pid)
                self.running = True
        return self.running

    def find_existing_process(self):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = (proc.info.get('name') or "").lower()
                    if 'python' in name:
                        cmdline = proc.cmdline() or []
                        if any('noisy.py' in arg for arg in cmdline):
                            return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        return None

    def start(self):
        if self.is_running():
            return True

        existing_pid = self.find_existing_process()
        if existing_pid:
            print(f"[Noisy] Найден уже запущенный процесс (PID {existing_pid}), используем его.")
            self.process = AdoptedProcess(existing_pid)
            self.running = True
            self.status_changed.emit(True)
            return True

        if not os.path.exists(NOISY_SCRIPT):
            error_msg = f"Файл noisy.py не найден:\n{NOISY_SCRIPT}"
            self.error_occurred.emit(error_msg)
            QMessageBox.critical(None, T("Ошибка", "Error"), error_msg)
            return False

        try:
            import sys
            self.process = subprocess.Popen(
                [sys.executable, NOISY_SCRIPT],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.running = True
            self.status_changed.emit(True)
            print("[Noisy] Фоновый трафик запущен")
            return True
        except Exception as e:
            error_msg = f"Не удалось запустить noisy.py:\n{e}"
            self.error_occurred.emit(error_msg)
            QMessageBox.critical(None, T("Ошибка", "Error"), error_msg)
            return False

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None

        self._kill_all_noisy_processes()

        self.running = False
        self.status_changed.emit(False)
        print("[Noisy] Фоновый трафик остановлен")

    def _kill_all_noisy_processes(self):
        killed_count = 0
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info.get('name')
                    if name and 'python' in name.lower():
                        try:
                            cmdline = proc.cmdline() or []
                        except psutil.AccessDenied:
                            cmdline = []
                        if cmdline and any('noisy.py' in arg for arg in cmdline):
                            p = psutil.Process(proc.info['pid'])
                            p.kill()
                            killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"[Noisy] Ошибка при завершении процессов: {e}")

    def update_config(self, config):
        self.config = config

    def get_status_text(self):
        if self.running:
            return "Остановить генерацию шума"
        return "Включить генерацию шума"

_noisy_manager = None

def get_manager(config=None):
    global _noisy_manager
    if _noisy_manager is None:
        _noisy_manager = NoisyManager(config)
    elif config is not None:
        _noisy_manager.update_config(config)
    return _noisy_manager



