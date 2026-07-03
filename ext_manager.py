import os
import subprocess
from PyQt5.QtWidgets import QMessageBox
import config_manager

class ExtProgramsManager:
    def __init__(self):
        self.processes = []

    def _get_programs(self):
        config = config_manager.load_config()
        return config.get("ext_programs", [])

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
        from PyQt5.QtWidgets import QInputDialog
        config = config_manager.load_config()
        ext_programs = config.get("ext_programs", [])
        
        current_text = "\n".join(ext_programs)
        
        text, ok = QInputDialog.getMultiLineText(
            None, 
            "Дополнительные программы", 
            "Укажите полные пути к программам (каждая с новой строки):", 
            current_text
        )
        
        if ok:
            lines = text.split("\n")
            programs = [line.strip() for line in lines if line.strip()]
            config["ext_programs"] = programs
            config_manager.save_config(config)
            QMessageBox.information(None, "Успех", "Настройки сохранены. Перезапустите приложения.")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = ExtProgramsManager()
    return _manager
