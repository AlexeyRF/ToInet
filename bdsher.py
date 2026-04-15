import os
import subprocess
import json
import psutil
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal

# Константы
BYEDPI_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"byedpi\ciadpi.exe")
BYEDPI_CUSTOM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "byedpi_custom.txt")

# Параметры по умолчанию
DEFAULT_BYEDPI_PARAMS = "--split 1 --disorder 3+s --mod-http=h,d --auto=torst --tlsrec 1+s"

class ByeDPIManager(QObject):
    status_changed = pyqtSignal(bool)  # True - запущен, False - остановлен
    error_occurred = pyqtSignal(str)   # Ошибка
    def __init__(self, config=None):
        super().__init__()
        self.process = None
        self.running = False
        self.config = config or {}
        
    def is_running(self):
        return self.running
    
    def get_params(self):
        use_custom = self.config.get("use_custom_settings", True)
        
        if use_custom:
            if os.path.exists(BYEDPI_CUSTOM_FILE):
                try:
                    with open(BYEDPI_CUSTOM_FILE, 'r', encoding='utf-8') as f:
                        custom_params = f.read().strip()
                        if custom_params and not custom_params.startswith('#'):
                            return custom_params.split()
                except Exception as e:
                    print(f"[ByeDPI] Ошибка чтения кастомных параметров: {e}")
        else:
            # Используем предустановленные параметры
            params_str = self.config.get("byedpi_params", DEFAULT_BYEDPI_PARAMS)
            return params_str.split()
        
        return []
    
    def create_default_custom_file(self):
        if not os.path.exists(BYEDPI_CUSTOM_FILE):
            try:
                with open(BYEDPI_CUSTOM_FILE, 'w', encoding='utf-8') as f:
                    f.write("# Введите свои параметры для запуска Byedpi\n")
                    f.write("# Каждый параметр с новой строки или через пробел\n")
                    f.write("# Пример: --split 1 --disorder 3+s --mod-http=h,d --auto=torst --tlsrec 1+s\n")
                    f.write("\n")
                    f.write("# Параметры по умолчанию:\n")
                    f.write(self.config.get("byedpi_params", DEFAULT_BYEDPI_PARAMS))
                return True
            except Exception as e:
                print(f"[ByeDPI] Ошибка создания кастомного файла: {e}")
                return False
        return True
    
    def start(self):
        if self.running:
            return True
            
        if not os.path.exists(BYEDPI_EXE):
            error_msg = f"Файл Byedpi не найден:\n{BYEDPI_EXE}"
            self.error_occurred.emit(error_msg)
            QMessageBox.critical(None, "Ошибка", error_msg)
            return False
        
        # Создаем файл кастомных настроек если нужно
        if self.config.get("use_custom_settings", True):
            self.create_default_custom_file()
        
        params = self.get_params()
        cmd = [BYEDPI_EXE] + params
        
        try:
            self.process = subprocess.Popen(
                cmd, 
                creationflags=subprocess.CREATE_NO_WINDOW, 
                shell=True
            )
            self.running = True
            self.status_changed.emit(True)
            print(f"[ByeDPI] Запущен с параметрами: {params}")
            return True
        except Exception as e:
            error_msg = f"Не удалось запустить Byedpi:\n{e}"
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
        
        # Дополнительная очистка процессов
        self._kill_all_byedpi_processes()
        
        self.running = False
        self.status_changed.emit(False)
        print("[ByeDPI] Остановлен")
    
    def _kill_all_byedpi_processes(self):
        killed_count = 0
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'ciadpi.exe' in proc.info['name'].lower():
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
            print(f"[ByeDPI] Ошибка при завершении процессов: {e}")
        
        if killed_count > 0:
            print(f"[ByeDPI] Завершено процессов: {killed_count}")
    
    def restart(self):
        print("[ByeDPI] Перезапуск...")
        self.stop()
        import time
        time.sleep(1)
        return self.start()
    
    def update_config(self, config):
        self.config = config
    
    def open_settings(self):
        if self.config.get("use_custom_settings", True):
            self.create_default_custom_file()
            if os.path.exists(BYEDPI_CUSTOM_FILE):
                os.startfile(BYEDPI_CUSTOM_FILE)
            else:
                QMessageBox.information(None, "Настройки Byedpi", 
                                       "Файл настроек не найден.")
        else:
            params = self.config.get("byedpi_params", DEFAULT_BYEDPI_PARAMS)
            QMessageBox.information(None, "Настройки Byedpi", 
                                   f"Текущие предустановленные параметры:\n\n{params}\n\n"
                                   f"Для редактирования параметров переключитесь на кастомные настройки.")
    
    def get_status_text(self):
        if self.running:
            return "Остановить BD"
        return "Ручной запуск BD"
    
    @staticmethod
    def check_exists():
        return os.path.exists(BYEDPI_EXE)


# Функции для обратной совместимости (чтобы старый код продолжал работать)

_byedpi_manager = None

def get_manager(config=None):
    global _byedpi_manager
    if _byedpi_manager is None:
        _byedpi_manager = ByeDPIManager(config)
    elif config is not None:
        _byedpi_manager.update_config(config)
    return _byedpi_manager

def start_byedpi():
    manager = get_manager()
    return manager.start()

def stop_byedpi():
    manager = get_manager()
    manager.stop()

def is_byedpi_running():
    manager = get_manager()
    return manager.is_running()

def open_byedpi_settings():
    manager = get_manager()
    manager.open_settings()

def get_byedpi_params():
    manager = get_manager()
    return manager.get_params()