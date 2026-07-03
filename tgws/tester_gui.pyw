import sys
import os
import json
import time
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
                             QMessageBox, QInputDialog, QDialog, QSpinBox, QDialogButtonBox, QGroupBox)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import config_manager

ALL_IPS = [
    "1:149.154.175.50", "1:149.154.175.53", 
    "2:149.154.167.51", "2:149.154.167.50", "2:149.154.167.220", "2:91.108.56.114", "2:91.108.12.18", 
    "3:149.154.175.100", 
    "4:149.154.167.91", "4:149.154.167.92", "4:149.154.167.220", "4:91.108.56.164", "4:91.108.12.15", "4:91.108.16.14", 
    "5:91.108.56.184", "5:91.108.56.185", "5:91.108.56.140", "5:91.108.56.141", "5:91.108.56.142"
]

DARK_STYLESHEET = """
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3d3d3d;
    border-color: #555555;
}
QListWidget {
    background-color: #222222;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    padding: 5px;
}
QListWidget::item:selected {
    background-color: #333333;
    color: #ffffff;
    border-radius: 4px;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px;
    background-color: #222222;
}
QSpinBox {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}
"""

class RatingDialog(QDialog):
    def __init__(self, parent=None, ip_str=""):
        super().__init__(parent)
        self.setWindowTitle(f"Оценка для {ip_str}")
        self.setFixedSize(400, 250)
        self.setStyleSheet(DARK_STYLESHEET)
        
        layout = QVBoxLayout(self)
        info = QLabel(f"Пожалуйста, зайдите в Telegram и попробуйте:\n1. Загрузить картинку/файл в 'Избранное'\n2. Скачать картинку/файл.\n\nТекущий IP: {ip_str}")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        hbox_up = QHBoxLayout()
        hbox_up.addWidget(QLabel("Скорость отправки (1-10):"))
        self.spin_up = QSpinBox()
        self.spin_up.setRange(1, 10)
        self.spin_up.setValue(5)
        hbox_up.addWidget(self.spin_up)
        layout.addLayout(hbox_up)
        
        hbox_down = QHBoxLayout()
        hbox_down.addWidget(QLabel("Скорость скачивания (1-10):"))
        self.spin_down = QSpinBox()
        self.spin_down.setRange(1, 10)
        self.spin_down.setValue(5)
        hbox_down.addWidget(self.spin_down)
        layout.addLayout(hbox_down)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def get_ratings(self):
        return self.spin_up.value(), self.spin_down.value()

class TGWSTesterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGWS Strategies Tester")
        self.setFixedSize(650, 500)
        self.setStyleSheet(DARK_STYLESHEET)
        
        self.config = config_manager.load_config()
        self.original_ips = self.config.get("tgws_dc_ip", [])
        self.results = {}  # ip -> (up_score, down_score, avg)
        
        self.tgws_process = None
        
        self.init_ui()
        
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        lbl = QLabel("Тестирование стратегий TGWS (Telegram WebSocket)")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(lbl)
        
        desc = QLabel("Этот инструмент поможет вам перебрать различные конфигурации IP-адресов датацентров Telegram и найти ту, которая обеспечит наилучшую скорость отправки и скачивания медиафайлов. Для теста вам нужно будет загружать и скачивать файлы в клиенте.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        hbox = QHBoxLayout()
        
        # Left - IPS
        left_group = QGroupBox("Доступные IP")
        l_layout = QVBoxLayout()
        self.ip_list = QListWidget()
        for ip in ALL_IPS:
            self.ip_list.addItem(ip)
        l_layout.addWidget(self.ip_list)
        
        btn_test_one = QPushButton("Протестировать выбранный IP")
        btn_test_one.clicked.connect(self.test_selected_ip)
        l_layout.addWidget(btn_test_one)
        
        left_group.setLayout(l_layout)
        hbox.addWidget(left_group)
        
        # Right - Results
        right_group = QGroupBox("Результаты (Баллы из 10)")
        r_layout = QVBoxLayout()
        self.res_list = QListWidget()
        r_layout.addWidget(self.res_list)
        
        btn_combine = QPushButton("Объединить лучшие IP")
        btn_combine.clicked.connect(self.combine_best)
        r_layout.addWidget(btn_combine)
        
        btn_save = QPushButton("Сохранить и выйти")
        btn_save.clicked.connect(self.save_and_exit)
        r_layout.addWidget(btn_save)
        
        right_group.setLayout(r_layout)
        hbox.addWidget(right_group)
        
        layout.addLayout(hbox)
        
    def stop_existing_tgws(self):
        # We try to cleanly stop any running TGWS processes to free the port 1480
        if self.tgws_process:
            try:
                self.tgws_process.kill()
            except:
                pass
            self.tgws_process = None
            
        # We can also modify config and let tgws_manager handle it if we want, but since we are a separate GUI,
        # it's better to launch the script separately and kill it.
        # But wait! If main.pyw is running, its background thread holds the port!
        # So we'll have to warn the user or edit the config directly and tell them to wait.
        pass

    def test_selected_ip(self):
        items = self.ip_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "Ошибка", "Выберите IP из списка слева.")
            return
            
        ip_str = items[0].text()
        
        # Modify config.json
        self.config["tgws_dc_ip"] = [ip_str]
        config_manager.save_config(self.config)
        
        QMessageBox.information(self, "Внимание", "Настройки обновлены! Если у вас открыто основное приложение ToInet-MAX, пожалуйста, ПЕРЕЗАПУСТИТЕ TGWS в меню 'Управление компонентами' перед тестированием.\n\nЗатем нажмите OK для выставления оценки.")
        
        dlg = RatingDialog(self, ip_str)
        if dlg.exec_():
            up, down = dlg.get_ratings()
            avg = (up + down) / 2.0
            self.results[ip_str] = (up, down, avg)
            self.update_results()
            
    def update_results(self):
        self.res_list.clear()
        sorted_res = sorted(self.results.items(), key=lambda x: x[1][2], reverse=True)
        for ip, scores in sorted_res:
            self.res_list.addItem(f"{ip} | Отправка: {scores[0]} | Загрузка: {scores[1]} | Среднее: {scores[2]}")

    def combine_best(self):
        if not self.results:
            QMessageBox.warning(self, "Ошибка", "Сначала протестируйте хотя бы один IP.")
            return
            
        # Pick best from each DC if available, or just top 3-5
        sorted_res = sorted(self.results.items(), key=lambda x: x[1][2], reverse=True)
        best_ips = [k for k, v in sorted_res[:5]]
        
        self.config["tgws_dc_ip"] = best_ips
        config_manager.save_config(self.config)
        
        QMessageBox.information(self, "Комбинация", f"Лучшие IP были объединены и сохранены:\n{', '.join(best_ips)}\n\nПерезапустите TGWS в основном приложении для применения.")
        
    def save_and_exit(self):
        if self.results:
            sorted_res = sorted(self.results.items(), key=lambda x: x[1][2], reverse=True)
            best_ips = [k for k, v in sorted_res[:5]]
            self.config["tgws_dc_ip"] = best_ips
            config_manager.save_config(self.config)
            QMessageBox.information(self, "Сохранено", "Конфигурация успешно сохранена.")
        else:
            self.config["tgws_dc_ip"] = self.original_ips
            config_manager.save_config(self.config)
            
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = TGWSTesterGUI()
    win.show()
    sys.exit(app.exec_())

