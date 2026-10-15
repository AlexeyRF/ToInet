import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QMessageBox
from PyQt5.QtGui import QFont
from managers import config_manager

class RulesEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор конфига TUN (sing-box)")
        self.resize(850, 600)
        
        self.config = config_manager.load_config()
        
        layout = QVBoxLayout(self)
        
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        
        current_tun_config = self.config.get("tun_singbox_config", None)
        if current_tun_config and isinstance(current_tun_config, dict):
            self.editor.setPlainText(json.dumps(current_tun_config, indent=2, ensure_ascii=False))
        else:
            self.editor.setPlainText("{\n  \"log\": {\n    \"level\": \"info\"\n  },\n  \"//\": \"Вставьте сюда ваш sing-box config.json для TUN режима\"\n}")
        
        layout.addWidget(self.editor)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить и закрыть")
        save_btn.clicked.connect(self.save_and_close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
    def save_and_close(self):
        text = self.editor.toPlainText()
        try:
            parsed = json.loads(text)
            self.config["tun_singbox_config"] = parsed
            config_manager.save_config(self.config)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка JSON", f"Некорректный JSON:\n{e}")

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    d = RulesEditorDialog()
    d.exec_()
