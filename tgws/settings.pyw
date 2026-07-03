import sys
import os

# Добавляем родительскую директорию в sys.path
import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import lang
import json
import socket
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QCheckBox, 
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt

from tgws import config as tgws_config
import windows as tgws_windows
from lang import T

import config_manager

class TGWSSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = config_manager.load_config()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(T("Настройки TGWS Proxy", "TGWS Proxy Settings"))
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
        
        # MTProto Secret
        layout.addWidget(QLabel("MTProto Секрет (32 hex символа):"))
        self.secret_edit = QLineEdit(self.config.get("tgws_secret", ""))
        layout.addWidget(self.secret_edit)

        # Fake TLS Domain
        layout.addWidget(QLabel("Fake TLS Домен (опционально):"))
        self.fake_tls_edit = QLineEdit(self.config.get("tgws_fake_tls", ""))
        layout.addWidget(self.fake_tls_edit)
        
        # Verbose логирование
        self.verbose_check = QCheckBox("Подробное логирование (verbose)")
        self.verbose_check.setChecked(self.config.get("tgws_verbose", False))
        layout.addWidget(self.verbose_check)
        

        
        # Информация
        info_label = QLabel(
            "TGWS Proxy будет работать на указанном порту.\n"
            f"SOCKS5: {self.config.get('tgws_host', '127.0.0.1')}:{self.config.get('tgws_port', 1480)} (без логина/пароля)\n"
            f"MTProto: Секрет начинается с ee/dd и содержит ваш домен\n\n"
            "Примечание: После сохранения настроек может потребоваться\n"
            "перезапуск TGWS Proxy для применения изменений."
        )
        info_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(info_label)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(T("Сохранить", "Save"))
        self.cancel_btn = QPushButton(T("Отмена", "Cancel"))
        
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
            QMessageBox.critical(self, T("Ошибка", "Error"), "Некорректный IP-адрес.")
            return
        
        # Проверка порта
        try:
            port = int(self.port_edit.text().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, T("Ошибка", "Error"), "Порт должен быть числом от 1 до 65535")
            return
        
        # Проверка DC маппингов
        lines = [l.strip() for l in self.dc_text.toPlainText().strip().splitlines() if l.strip()]
        try:
            tgws_config.parse_dc_ip_list(lines)
        except ValueError as e:
            QMessageBox.critical(self, T("Ошибка", "Error"), str(e))
            return
            
        secret = self.secret_edit.text().strip()
        if len(secret) != 32 or not all(c in '0123456789abcdefABCDEF' for c in secret):
            QMessageBox.critical(self, T("Ошибка", "Error"), "Секрет должен состоять из 32 шестнадцатеричных символов")
            return
        
        # Сохраняем настройки
        self.config["tgws_host"] = host
        self.config["tgws_port"] = port
        self.config["tgws_dc_ip"] = lines
        self.config["tgws_secret"] = secret
        self.config["tgws_fake_tls"] = self.fake_tls_edit.text().strip()
        self.config["tgws_verbose"] = self.verbose_check.isChecked()

        config_manager.save_config(self.config)
        
        QMessageBox.information(self, T("Успех", "Success"), "Настройки TGWS Proxy сохранены!")
        self.accept()

def main():
    app = QApplication(sys.argv)
    dialog = TGWSSettingsDialog()
    dialog.exec_()

if __name__ == "__main__":
    main()

