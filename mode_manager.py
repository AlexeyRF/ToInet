import os
import sys
import subprocess
import time
from PyQt5.QtWidgets import QMessageBox
import lang
import config_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CPLLER_SCRIPT = os.path.join(CURRENT_DIR, "cpller.pyw")

class ModeManager:
    def __init__(self):
        self.tun_process = None
        self.inetcpl_tor_active = False
        self.inetcpl_bd_active = False
        self.inetcpl_opera_active = False
        self.inetcpl_vless_active = False

    def log(self, msg):
        print(f"[MODE] {msg}")

    def run_cpller(self, port, action_flag):
        config = config_manager.load_config()
        mode = config.get("inetcpl_mode", "classic")
        cmd = [sys.executable, CPLLER_SCRIPT, str(port), str(action_flag), mode]
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
        
        try:
            self.log(f"Запуск cpller.pyw: {' '.join(cmd)}")
            subprocess.Popen(cmd, creationflags=creationflags)
            return True
        except Exception as e:
            self.log(f"Ошибка запуска cpller.pyw: {e}")
            return False

    def get_tun_app_path(self):
        config = config_manager.load_config()
        app_path = config.get("proxification_app", "")
        if not app_path:
            import getpass
            username = getpass.getuser()
            default_pb = rf"C:\Users\{username}\ProxyBridge\ProxyBridge_cli.exe --profile ToInet.pbprofile"
            config["proxification_app"] = default_pb
            config_manager.save_config(config)
            return default_pb
        return app_path

    def start_tun(self):
        if self.tun_process:
            return True
        
        from PyQt5.QtWidgets import QMessageBox
        import lang
        import shlex
        import getpass
        
        path_line = self.get_tun_app_path()
        if not path_line:
            return False
            
        args = shlex.split(path_line, posix=False)
        exe_path = args[0].strip('"\'')
        
        if os.path.exists(exe_path):
            try:
                self.tun_process = subprocess.Popen(args, cwd=CURRENT_DIR)
                self.log(f"TUN режим запущен: {path_line}")
                return True
            except Exception as e:
                self.log(f"Ошибка запуска TUN режима: {e}")
                QMessageBox.critical(None, "Ошибка TUN", f"Не удалось запустить проксификатор:\n{e}")
        else:
            msg = lang.T(
                f"Программа для TUN режима не найдена:\n{exe_path}\n\nСкачайте ProxyBridge v4.0.0 по ссылке:\nhttps://github.com/InterceptSuite/ProxyBridge/releases/tag/v4.0.0\nи поместите в эту папку, либо измените путь в proxification_app.txt",
                f"TUN mode application not found:\n{exe_path}\n\nDownload ProxyBridge v4.0.0 from:\nhttps://github.com/InterceptSuite/ProxyBridge/releases/tag/v4.0.0\nand place it in that folder, or change path in proxification_app.txt"
            )
            QMessageBox.warning(None, lang.T("Не настроен TUN", "TUN not configured"), msg)
            
        return False

    def stop_tun(self):
        if self.tun_process:
            try:
                self.tun_process.terminate()
                try:
                    self.tun_process.wait(timeout=2)
                except:
                    self.tun_process.kill()
                self.log("TUN режим остановлен (процесс завершен)")
            except Exception as e:
                self.log(f"Ошибка остановки TUN процесса: {e}")
            self.tun_process = None

    def tun_running(self):
        if self.tun_process:
            if self.tun_process.poll() is None:
                return True
            else:
                self.tun_process = None
        return False

    def restart_tun(self):
        self.stop_tun()
        import time
        time.sleep(1)
        self.start_tun()

    def open_proxifier_config(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
        
        config = config_manager.load_config()
        current_path = config.get("proxification_app", self.get_tun_app_path())
        
        dialog = QDialog()
        dialog.setWindowTitle("Настройка проксификатора")
        dialog.resize(500, 100)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Укажите путь до проксификатора (например, путь к ProxyBridge или Proxifier):")
        layout.addWidget(label)
        
        h_layout = QHBoxLayout()
        line_edit = QLineEdit(current_path)
        h_layout.addWidget(line_edit)
        
        browse_btn = QPushButton("Обзор...")
        def browse():
            path, _ = QFileDialog.getOpenFileName(dialog, "Выберите исполняемый файл", "", "Executables (*.exe);;All Files (*)")
            if path:
                line_edit.setText(path)
        browse_btn.clicked.connect(browse)
        h_layout.addWidget(browse_btn)
        
        layout.addLayout(h_layout)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("ОК")
        cancel_btn = QPushButton("Отмена")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            config["proxification_app"] = line_edit.text().strip()
            config_manager.save_config(config)
            QMessageBox.information(None, "Успех", "Настройки сохранены. Перезапустите проксификатор.")

    def reset_inetcpl_proxy(self):
        if self.inetcpl_tor_active:
            self.run_cpller(9853, 0)
            self.inetcpl_tor_active = False
            self.log("Отключен TOR прокси из inetcpl")
        
        if self.inetcpl_bd_active:
            self.run_cpller(1780, 0)
            self.inetcpl_bd_active = False
            self.log("Отключен BD прокси из inetcpl")
            
        if self.inetcpl_opera_active:
            self.run_cpller(1785, 0)
            self.inetcpl_opera_active = False
            self.log("Отключен Opera прокси из inetcpl")
            
        if self.inetcpl_vless_active:
            self.run_cpller(1790, 0)
            self.inetcpl_vless_active = False
            self.log("Отключен VLESS прокси из inetcpl")

_manager = ModeManager()

def get_manager():
    return _manager
