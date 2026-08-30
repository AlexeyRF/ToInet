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
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog
        
        config = config_manager.load_config()
        ext_programs = config.get("ext_programs", [])
        current_text = "\n".join(ext_programs)
        
        dialog = QDialog()
        dialog.setWindowTitle("Дополнительные программы")
        dialog.resize(500, 300)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Укажите полные пути к программам (по одной на строку):")
        layout.addWidget(label)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(current_text)
        layout.addWidget(text_edit)
        
        h_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить файл...")
        def add_file():
            path, _ = QFileDialog.getOpenFileName(dialog, "Выберите исполняемый файл", "", "Executables (*.exe *.bat *.cmd);;All Files (*)")
            if path:
                current = text_edit.toPlainText()
                if current and not current.endswith("\n"):
                    current += "\n"
                text_edit.setPlainText(current + path + "\n")
        add_btn.clicked.connect(add_file)
        
        h_layout.addWidget(add_btn)
        h_layout.addStretch()
        
        ok_btn = QPushButton("ОК")
        cancel_btn = QPushButton("Отмена")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        h_layout.addWidget(ok_btn)
        h_layout.addWidget(cancel_btn)
        
        layout.addLayout(h_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            lines = text_edit.toPlainText().split("\n")
            programs = [line.strip() for line in lines if line.strip()]
            config["ext_programs"] = programs
            config_manager.save_config(config)
            QMessageBox.information(None, "Успех", "Настройки сохранены. Перезапустите доп. программы.")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = ExtProgramsManager()
    return _manager
