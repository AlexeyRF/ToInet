import os
import subprocess
import psutil
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal

NOISY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "noisy.py")

class NoisyManager(QObject):
    status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, config=None):
        super().__init__()
        self.process = None
        self.running = False
        self.config = config or {}

    def is_running(self):
        return self.running

    def start(self):
        if self.running:
            return True

        if not os.path.exists(NOISY_SCRIPT):
            error_msg = f"Файл noisy.py не найден:\n{NOISY_SCRIPT}"
            self.error_occurred.emit(error_msg)
            QMessageBox.critical(None, "Ошибка", error_msg)
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
            QMessageBox.critical(None, "Ошибка", error_msg)
            return False

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
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
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline and any('noisy.py' in arg for arg in cmdline):
                        p = psutil.Process(proc.info['pid'])
                        p.terminate()
                        try:
                            p.wait(timeout=3)
                        except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                            try:
                                p.kill()
                            except:
                                pass
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
