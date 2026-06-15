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
    def __init__(self, config=None, custom_file_name="byedpi_custom.txt", default_port=1780):
        super().__init__()
        self.process = None
        self.running = False
        self.config = config or {}
        self.custom_file_name = custom_file_name
        self.default_port = default_port
        self.byedpi_custom_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), custom_file_name)
        
    def is_running(self):
        return self.running
    
    def get_params(self):
        use_custom = self.config.get("use_custom_settings", True)
        params = []
        
        if use_custom and os.path.exists(self.byedpi_custom_file):
            try:
                with open(self.byedpi_custom_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                non_comment_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped and not line_stripped.startswith('#'):
                        non_comment_lines.append(line_stripped)
                
                for line in non_comment_lines:
                    params.extend(line.split())
            except Exception as e:
                print(f"[ByeDPI] Ошибка чтения кастомных параметров: {e}")
        
        # If not using custom, or custom file was empty/failed, load predefined
        if not params:
            if self.default_port == 1781:
                params_str = self.config.get("byedpi_pip_params", "-p 1781 -o1 -o25+s -T3 -At -d1+s -O1 -s29+s -t 5 -An -Ku -a5 -s443+s -d80+s -s80+s -d53+s -s53+s -d443+s --fake -1 --fake-sni max.ru")
            else:
                params_str = self.config.get("byedpi_params", DEFAULT_BYEDPI_PARAMS)
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
    
    def create_default_custom_file(self):
        if not os.path.exists(self.byedpi_custom_file):
            try:
                with open(self.byedpi_custom_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Введите свои параметры для запуска Byedpi ({self.custom_file_name})\n")
                    f.write("# Каждый параметр с новой строки или через пробел\n")
                    f.write(f"# Пример: -p {self.default_port} -o1 -o25+s -T3 -At -d1+s -O1 -s29+s -t 5 -An -Ku -a5 -s443+s -d80+s -s80+s -d53+s -s53+s -d443+s --fake -1 --fake-sni max.ru\n")
                    f.write("\n")
                    f.write("# Параметры по умолчанию:\n")
                    if self.default_port == 1781:
                        f.write(self.config.get("byedpi_pip_params", "-p 1781 -o1 -o25+s -T3 -At -d1+s -O1 -s29+s -t 5 -An -Ku -a5 -s443+s -d80+s -s80+s -d53+s -s53+s -d443+s --fake -1 --fake-sni max.ru"))
                    else:
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
            QMessageBox.critical(None, T("Ошибка", "Error"), error_msg)
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
        print(f"[ByeDPI {self.default_port}] Остановлен")
    
    def _kill_all_byedpi_processes(self):
        killed_count = 0
        port_str = str(self.default_port)
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'ciadpi.exe' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline') or []
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
        if self.config.get("use_custom_settings", True):
            self.create_default_custom_file()
            if os.path.exists(self.byedpi_custom_file):
                os.startfile(self.byedpi_custom_file)
            else:
                QMessageBox.information(None, "Настройки Byedpi", 
                                       "Файл настроек не найден.")
        else:
            if self.default_port == 1781:
                params = self.config.get("byedpi_pip_params", "-p 1781 -o1 -o25+s -T3 -At -d1+s -O1 -s29+s -t 5 -An -Ku -a5 -s443+s -d80+s -s80+s -d53+s -s53+s -d443+s --fake -1 --fake-sni max.ru")
            else:
                params = self.config.get("byedpi_params", DEFAULT_BYEDPI_PARAMS)
            QMessageBox.information(None, "Настройки Byedpi", 
                                   f"Текущие предустановленные параметры:\n\n{params}\n\n"
                                   f"Для редактирования параметров переключитесь на кастомные настройки.")
    
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
        _byedpi_manager = ByeDPIManager(config, "byedpi_custom.txt", 1780)
    elif config is not None:
        _byedpi_manager.update_config(config)
    return _byedpi_manager

def get_pip_manager(config=None):
    global _byedpi_pip_manager
    if _byedpi_pip_manager is None:
        _byedpi_pip_manager = ByeDPIManager(config, "byedpi_pip_custom.txt", 1781)
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