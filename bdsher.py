import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
import lang
import os
import subprocess
import json
import psutil
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal

# Константы
BYEDPI_EXE = os.path.join(CURRENT_DIR, r"byedpi\ciadpi.exe")
BYEDPI_CUSTOM_FILE = os.path.join(CURRENT_DIR, "byedpi_custom.txt")

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
        use_custom = self.config.get("use_custom_settings", True)
        params_str = self.config.get(self.config_key, "") if use_custom else ""
        if not params_str:
            params_str = DEFAULT_BYEDPI_PARAMS if self.default_port == 1780 else ""
            
        if params_str.strip().startswith("{"):
            return params_str.strip()
            
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
            
        params = self.get_params()
        if isinstance(params, str) and params.startswith("{"):
            router_script = os.path.join(CURRENT_DIR, "byedpi_router.py")
            if not os.path.exists(router_script):
                error_msg = f"Файл маршрутизатора не найден:\n{router_script}"
                self.error_occurred.emit(error_msg)
                return False
                
            cmd = [sys.executable, router_script, str(self.default_port), params]
            try:
                self.process = subprocess.Popen(
                    cmd, 
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                self.running = True
                self.status_changed.emit(True)
                print(f"[ByeDPI Router {self.default_port}] Запущен маршрутизатор.")
                return True
            except Exception as e:
                error_msg = f"Не удалось запустить маршрутизатор ({self.default_port}):\n{e}"
                self.error_occurred.emit(error_msg)
                return False

        if not os.path.exists(BYEDPI_EXE):
            error_msg = f"Файл Byedpi не найден:\n{BYEDPI_EXE}"
            self.error_occurred.emit(error_msg)
            QMessageBox.critical(None, T("Ошибка", "Error"), error_msg)
            return False
        
        cmd = [BYEDPI_EXE] + params
        
        try:
            self.process = subprocess.Popen(
                cmd, 
                creationflags=subprocess.CREATE_NO_WINDOW
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
        
        router_pids = []
        if self.process:
            router_pids.append(self.process.pid)
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    router_pids.append(child.pid)
            except:
                pass

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
                        if proc.info['pid'] in router_pids:
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
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton
        import config_manager
        import os
        import subprocess
        import sys
        
        dialog = QDialog()
        dialog.setWindowTitle("Настройки ByeDPI")
        dialog.resize(600, 180)
        
        # Dark Theme
        dialog.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QLabel { color: white; }
            QLineEdit { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 5px; }
            QCheckBox { color: white; }
            QPushButton { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 5px 15px; }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton:pressed { background-color: #1d1d1d; }
        """)
        
        layout = QVBoxLayout(dialog)
        
        use_custom = self.config.get("use_custom_settings", True)
        current_params = self.config.get(self.config_key, "")
        preset_params = DEFAULT_BYEDPI_PARAMS if self.default_port == 1780 else ""
        
        if not current_params:
            current_params = preset_params
            
        layout.addWidget(QLabel("Параметры ByeDPI:"))
        
        edit = QLineEdit(preset_params if not use_custom else current_params)
        layout.addWidget(edit)
        
        cb_preset = QCheckBox("Использовать предустановленные настройки")
        cb_preset.setChecked(not use_custom)
        
        # Cache to store custom settings when checking the box
        self._custom_config_cache = current_params if current_params != preset_params else ""
        
        def on_toggle(checked):
            edit.setEnabled(not checked)
            if checked:
                # Save current custom text to cache if it's not the preset
                if edit.text() != preset_params:
                    self._custom_config_cache = edit.text()
                edit.setText(preset_params)
            else:
                edit.setText(self._custom_config_cache)
        
        cb_preset.toggled.connect(on_toggle)
        on_toggle(not use_custom)
        
        layout.addWidget(cb_preset)
        
        btn_layout = QHBoxLayout()
        
        # Tester Button
        tester_btn = QPushButton("Запустить Тестер (byedpi_tester_gui.pyw)")
        def run_tester():
            subprocess.Popen([sys.executable, "byedpi_tester_gui.pyw"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        tester_btn.clicked.connect(run_tester)
        
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(tester_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec_():
            self.config["use_custom_settings"] = not cb_preset.isChecked()
            # Always update the actual config key so we keep custom text if unchecked, OR if checked, we just don't touch the custom key?
            # If checked (use preset), the edit.text() is the preset. If we save it, we lose the custom cache!
            # We should save `edit.text().strip()` IF custom. If preset, we just let it be.
            if not cb_preset.isChecked():
                self.config[self.config_key] = edit.text().strip()
            # If they check the box, we can preserve the hidden custom config by setting it to cache!
            else:
                self.config[self.config_key] = self._custom_config_cache
                
            config_manager.save_config(self.config)
            
            try:
                main_mod = sys.modules.get('__main__')
                if main_mod and hasattr(main_mod, 'update_menu'):
                    main_mod.update_menu()
            except:
                pass
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(None, "Успех", "Настройки ByeDPI сохранены.")

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



