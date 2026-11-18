import os
import subprocess
from PySide6.QtWidgets import QMessageBox
from managers import config_manager
from managers.system_utils import get_base_dir

class ExtProgramsManager:
    def __init__(self):
        self.processes = []

    def _get_programs(self):
        config = config_manager.load_config()
        return config.get("ext_programs", [])

    def is_running(self):
        self.processes = [p for p in self.processes if p.poll() is None]
        return len(self.processes) > 0

    def start_all(self):
        self.processes = [p for p in self.processes if p.poll() is None]
        
        programs = self._get_programs()
        for path in programs:
            path = path.strip()
            if not path:
                continue
            if path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
            if os.path.exists(path):
                try:
                    cwd = os.path.dirname(path)
                    p = subprocess.Popen(path, cwd=cwd)
                    self.processes.append(p)
                    print(f"[Ext] Запущена программа: {path}")
                except Exception as e:
                    print(f"[Ext] Ошибка запуска {path}: {e}")
            else:
                print(f"[Ext] Программа не найдена: {path}")

    def stop_all(self):
        for p in self.processes:
            try:
                p.terminate()
                try:
                    p.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    p.kill()
            except:
                try:
                    p.kill()
                except:
                    pass
        self.processes.clear()
        print("[Ext] Все дополнительные программы остановлены")

    def restart_all(self):
        self.stop_all()
        import time
        time.sleep(1)
        self.start_all()
        print("[Ext] Дополнительные программы перезапущены")

    def open_config(self):
        CURRENT_DIR = get_base_dir()
        exe_path = os.path.join(CURRENT_DIR, "bin", "programs_settings.exe")
        if os.path.exists(exe_path):
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.Popen([exe_path], creationflags=creationflags)
        else:
            print(f"[Ext] programs_settings.exe не найден: {exe_path}")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = ExtProgramsManager()
    return _manager
