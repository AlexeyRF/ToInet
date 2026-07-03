import lang
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
DEFAULT_BYEDPI_PARAMS = "-p 1780 -o1 -o25+s -T3 -At -d1+s -O1 -s29+s -t 5 -An -Ku -a5 -s443+s -d80+s -s80+s -d53+s -s53+s -d443+s --fake -1 --fake-sni max.ru"

class ByeDPIManager(QObject):
    status_changed = pyqtSignal(bool)  # True - запущен, False - остановлен
    error_occurred = pyqtSignal(str)   # Ошибка
    def __init__(self, config=None, default_port=1780, config_key="byedpi_params"):
        super().__init__()
        self.process = None
        self.running = False
        self.config = config or {}
        self.default_port = default_port
        self.config_key = config_key
        
    def is_running(self):
        return self.running
    
    def get_params(self):
        params_str = self.config.get(self.config_key, "")
        if not params_str:
            params_str = DEFAULT_BYEDPI_PARAMS if self.default_port == 1780 else ""
        params = params_str.split()
        
        # Ensure SOCKS5 port is auto-added if no port is defined
        has_port = False
        for arg in params:
            if arg == '-p' or arg == '--port':
                has_port = True
                break
            elif arg.startswith('-p') and len(arg) > 2 and arg[2].isdigit():
                has_port = True
                break
                
        if not has_port:
            params = ['-p', str(self.default_port)] + params
            
        return params
    
    def start(self):
        if self.running:
            return True
            
        if not os.path.exists(BYEDPI_EXE):
            error_msg = f"Файл Byedpi не найден:\n{BYEDPI_EXE}"
            self.error_occurred.emit(error_msg)
            QMessageBox.critical(None, T("Ошибка", "Error"), error_msg)
            return False
        
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
            print(f"[ByeDPI {self.default_port}] Запущен с параметрами: {params}")
            return True
        except Exception as e:
            error_msg = f"Не удалось запустить Byedpi ({self.default_port}):\n{e}"
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
                pass
            self.process = None
        
        # Дополнительная очистка процессов
        self._kill_all_byedpi_processes()
        
        self.running = False
        self.status_changed.emit(False)
        print(f"[ByeDPI {self.default_port}] Остановлен")
    
    def _kill_all_byedpi_processes(self):
        killed_count = 0
        port_str = str(self.default_port)
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info.get('name')
                    if name and 'ciadpi.exe' in name.lower():
                        try:
                            cmdline = proc.cmdline() or []
                        except psutil.AccessDenied:
                            cmdline = []
                        is_our_process = False
                        if self.process and proc.info['pid'] == self.process.pid:
                            is_our_process = True
                        else:
                            for i, arg in enumerate(cmdline):
                                if arg == '-p' or arg == '--port':
                                    if i + 1 < len(cmdline) and cmdline[i + 1] == port_str:
                                        is_our_process = True
                                        break
                                elif arg == f'-p{port_str}' or arg == f'--port={port_str}':
                                    is_our_process = True
                                    break
                                    
                        if is_our_process:
                            p = psutil.Process(proc.info['pid'])
                            p.kill()
                            killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"[ByeDPI] Ошибка при завершении процессов: {e}")
        
        if killed_count > 0:
            print(f"[ByeDPI {self.default_port}] Завершено процессов: {killed_count}")
    
    def restart(self):
        print(f"[ByeDPI {self.default_port}] Перезапуск...")
        self.stop()
        import time
        time.sleep(1)
        return self.start()
    
    def update_config(self, config):
        self.config = config
    
    def open_settings(self):
        from PyQt5.QtWidgets import QInputDialog
        import config_manager
        
        current_params = self.config.get(self.config_key, "")
        if not current_params:
            current_params = DEFAULT_BYEDPI_PARAMS if self.default_port == 1780 else ""
            
        text, ok = QInputDialog.getText(None, "Настройки ByeDPI", "Параметры запуска ByeDPI:", text=current_params)
        if ok:
            self.config[self.config_key] = text
            config_manager.save_config(self.config)
            QMessageBox.information(None, "Успех", "Настройки сохранены. Пожалуйста, перезапустите обход.")
    
    def get_status_text(self):
        if self.running:
            return f"Остановить BD ({self.default_port})"
        return f"Ручной запуск BD ({self.default_port})"
    
    @staticmethod
    def check_exists():
        return os.path.exists(BYEDPI_EXE)


# Функции для настройки pip.ini прокси

def set_pip_proxy(proxy_url):
    import configparser
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return False
    pip_dir = os.path.join(appdata, "pip")
    if not os.path.exists(pip_dir):
        os.makedirs(pip_dir)
    pip_ini = os.path.join(pip_dir, "pip.ini")
    
    config = configparser.ConfigParser()
    if os.path.exists(pip_ini):
        try:
            config.read(pip_ini, encoding="utf-8")
        except:
            pass
            
    if "global" not in config:
        config["global"] = {}
    config["global"]["proxy"] = proxy_url
    
    try:
        with open(pip_ini, "w", encoding="utf-8") as f:
            config.write(f)
        print(f"[ByeDPI] Прокси {proxy_url} сохранен в pip.ini")
        return True
    except Exception as e:
        print(f"[ByeDPI] Ошибка сохранения прокси в pip.ini: {e}")
        return False

def get_pip_proxy():
    import configparser
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    pip_ini = os.path.join(appdata, "pip", "pip.ini")
    if not os.path.exists(pip_ini):
        return None
        
    config = configparser.ConfigParser()
    try:
        config.read(pip_ini, encoding="utf-8")
        if "global" in config and "proxy" in config["global"]:
            return config["global"]["proxy"]
    except:
        pass
    return None

def clear_pip_proxy():
    import configparser
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return False
    pip_ini = os.path.join(appdata, "pip", "pip.ini")
    if not os.path.exists(pip_ini):
        return True
        
    config = configparser.ConfigParser()
    try:
        config.read(pip_ini, encoding="utf-8")
        if "global" in config and "proxy" in config["global"]:
            del config["global"]["proxy"]
            if not config["global"]:
                config.remove_section("global")
            with open(pip_ini, "w", encoding="utf-8") as f:
                config.write(f)
            print("[ByeDPI] Прокси удален из pip.ini")
        return True
    except Exception as e:
        print(f"[ByeDPI] Ошибка удаления прокси из pip.ini: {e}")
        return False


# Функции для обратной совместимости (чтобы старый код продолжал работать)

_byedpi_manager = None
_byedpi_pip_manager = None

def get_manager(config=None):
    global _byedpi_manager
    if _byedpi_manager is None:
        _byedpi_manager = ByeDPIManager(config, 1780, "byedpi_params")
    elif config is not None:
        _byedpi_manager.update_config(config)
    return _byedpi_manager

def get_pip_manager(config=None):
    global _byedpi_pip_manager
    if _byedpi_pip_manager is None:
        _byedpi_pip_manager = ByeDPIManager(config, 1781, "byedpi_pip_params")
    elif config is not None:
        _byedpi_pip_manager.update_config(config)
    return _byedpi_pip_manager

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
