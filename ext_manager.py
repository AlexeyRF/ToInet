import os
import subprocess
from PyQt5.QtWidgets import QMessageBox

EXT_PROGRAMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ext_programs.txt")

class ExtProgramsManager:
    def __init__(self):
        self.processes = []

    def _get_programs(self):
        programs = []
        if not os.path.exists(EXT_PROGRAMS_FILE):
            with open(EXT_PROGRAMS_FILE, 'w', encoding='utf-8') as f:
                f.write("# Укажите полные пути к программам, которые нужно запускать вместе с приложением\n")
                f.write("# Каждая программа с новой строки\n")
                f.write("# Пример: C:\\Program Files\\My App\\app.exe\n")
            return programs
            
        with open(EXT_PROGRAMS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Удаляем кавычки, если они есть
                    if line.startswith('"') and line.endswith('"'):
                        line = line[1:-1]
                    programs.append(line)
        return programs

    def start_all(self):
        # Очищаем список от уже завершенных процессов
        self.processes = [p for p in self.processes if p.poll() is None]
        
        programs = self._get_programs()
        for path in programs:
            if os.path.exists(path):
                try:
                    # Устанавливаем рабочую директорию как папку программы
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
                p.wait(timeout=3)
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
        print("[Ext] Программы перезапущены")
        
    def open_config(self):
        if not os.path.exists(EXT_PROGRAMS_FILE):
            self._get_programs() # создает файл с шаблоном
        try:
            os.startfile(EXT_PROGRAMS_FILE)
        except Exception as e:
            print(f"[Ext] Ошибка открытия конфига: {e}")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = ExtProgramsManager()
    return _manager