import os
import sys
import subprocess
import time
from PyQt5.QtWidgets import QMessageBox

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CPLLER_SCRIPT = os.path.join(CURRENT_DIR, "cpller.pyw")

class ModeManager:
    def __init__(self):
        self.tun_process = None
        self.inetcpl_tor_active = False
        self.inetcpl_bd_active = False

    def log(self, msg):
        print(f"[MODE] {msg}")

    def run_cpller(self, port, action_flag):
        if not os.path.exists(CPLLER_SCRIPT):
            self.log(f"cpller.pyw не найден: {CPLLER_SCRIPT}")
            return False
        
        try:
            subprocess.Popen([sys.executable, CPLLER_SCRIPT, str(port), str(action_flag)], 
                             creationflags=subprocess.CREATE_NO_WINDOW)
            self.log(f"Запущен cpller.pyw с портом {port} и флагом {action_flag}")
            return True
        except Exception as e:
            self.log(f"Ошибка запуска cpller.pyw: {e}")
            return False

    def get_tun_app_path(self):
        app_file = os.path.join(CURRENT_DIR, "proxification_app.txt")
        if not os.path.exists(app_file):
            with open(app_file, 'w', encoding='utf-8') as f:
                f.write("# Укажите путь к программе-проксификатору (например D:/Proxifier/proxifier.exe)\n")
            return None
        
        with open(app_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
        return None

    def start_tun(self):
        if self.tun_process:
            return True
        
        path = self.get_tun_app_path()
        if path and os.path.exists(path):
            try:
                self.tun_process = subprocess.Popen([path])
                self.log(f"TUN режим запущен: {path}")
                return True
            except Exception as e:
                self.log(f"Ошибка запуска TUN режима: {e}")
                QMessageBox.critical(None, "Ошибка TUN", f"Не удалось запустить проксификатор:\n{e}")
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

    def restart_tun(self):
        self.log("Перезапуск TUN режима...")
        self.stop_tun()
        time.sleep(1)
        return self.start_tun()

    def reset_inetcpl_proxy(self):
        if self.inetcpl_tor_active:
            self.run_cpller(9853, 0)
            self.inetcpl_tor_active = False
            self.log("Сброшен TOR прокси в inetcpl")
        
        if self.inetcpl_bd_active:
            self.run_cpller(1780, 0)
            self.inetcpl_bd_active = False
            self.log("Сброшен BD прокси в inetcpl")

_manager = ModeManager()

def get_manager():
    return _manager
