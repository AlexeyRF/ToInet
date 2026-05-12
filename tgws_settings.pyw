import sys
import os
import json
import socket
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QCheckBox, 
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt

# Импортируем модули TG WS Proxy
import tg_ws_proxy
import windows as tgws_windows

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CURRENT_DIR, "config.json")

def load_config():
    """Загрузка конфигурации"""
    default_config = {
        "tgws_enabled": True,
        "tgws_port": 1480,
        "tgws_host": "127.0.0.1",
        "tgws_dc_ip": ["2:149.154.167.220", "4:149.154.167.220"],
        "tgws_verbose": False
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except:
            pass
    return default_config.copy()

def save_config(config):
    """Сохранение конфигурации"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

class TGWSSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Настройки TGWS Proxy")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # IP адрес
        layout.addWidget(QLabel("IP-адрес прокси:"))
        self.host_edit = QLineEdit(self.config.get("tgws_host", "127.0.0.1"))
        layout.addWidget(self.host_edit)
        
        # Порт
        layout.addWidget(QLabel("Порт прокси:"))
        self.port_edit = QLineEdit(str(self.config.get("tgws_port", 1480)))
        layout.addWidget(self.port_edit)
        
        # DC маппинги
        layout.addWidget(QLabel("DC → IP маппинги (по одному на строку, формат DC:IP):"))
        self.dc_text = QTextEdit()
        self.dc_text.setPlainText("\n".join(self.config.get("tgws_dc_ip", ["2:149.154.167.220", "4:149.154.167.220"])))
        self.dc_text.setMaximumHeight(100)
        layout.addWidget(self.dc_text)
        
        # Verbose логирование
        self.verbose_check = QCheckBox("Подробное логирование (verbose)")
        self.verbose_check.setChecked(self.config.get("tgws_verbose", False))
        layout.addWidget(self.verbose_check)
        
        # Автозапуск
        self.auto_check = QCheckBox("Автоматически запускать при старте программы")
        self.auto_check.setChecked(self.config.get("tgws_enabled", False))
        layout.addWidget(self.auto_check)
        
        # Информация
        info_label = QLabel(
            "TGWS Proxy будет работать на указанном порту.\n"
            "В Telegram Desktop настройте SOCKS5 прокси:\n"
            f"{self.config.get('tgws_host', '127.0.0.1')}:{self.config.get('tgws_port', 1480)} (без логина/пароля)\n\n"
            "Примечание: После сохранения настроек может потребоваться\n"
            "перезапуск TGWS Proxy для применения изменений."
        )
        info_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(info_label)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.cancel_btn = QPushButton("Отмена")
        
        self.save_btn.clicked.connect(self.validate_and_save)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def validate_and_save(self):
        """Проверка и сохранение настроек"""
        host = self.host_edit.text().strip()
        
        # Проверка IP
        try:
            socket.inet_aton(host)
        except OSError:
            QMessageBox.critical(self, "Ошибка", "Некорректный IP-адрес.")
            return
        
        # Проверка порта
        try:
            port = int(self.port_edit.text().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Порт должен быть числом от 1 до 65535")
            return
        
        # Проверка DC маппингов
        lines = [l.strip() for l in self.dc_text.toPlainText().strip().splitlines() if l.strip()]
        try:
            tg_ws_proxy.parse_dc_ip_list(lines)
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        
        # Сохраняем настройки
        self.config["tgws_host"] = host
        self.config["tgws_port"] = port
        self.config["tgws_dc_ip"] = lines
        self.config["tgws_verbose"] = self.verbose_check.isChecked()
        self.config["tgws_enabled"] = self.auto_check.isChecked()
        save_config(self.config)
        
        QMessageBox.information(self, "Успех", "Настройки TGWS Proxy сохранены!")
        self.accept()

def main():
    app = QApplication(sys.argv)
    dialog = TGWSSettingsDialog()
    dialog.exec_()

if __name__ == "__main__":
    main()