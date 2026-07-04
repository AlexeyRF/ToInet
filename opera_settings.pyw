import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QGroupBox, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
import lang
import config_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
OPERA_CUSTOM_FILE = os.path.join(CURRENT_DIR, "opera_proxy_custom.txt")
DEFAULT_PARAMS = "-bind-address 127.0.0.1:1785 -socks-mode -verbosity 20 -country EU -server-selection random -proxy socks5://127.0.0.1:1787"

def T(ru_text, en_text):
    return en_text if lang._is_en else ru_text

class OperaSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Настройки Opera Proxy", "Opera Proxy Settings"))
        self.setFixedSize(500, 350)
        
        # Load icon if available
        icon_path = os.path.join(CURRENT_DIR, "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        title_label = QLabel(T("Настройки Opera Proxy", "Opera Proxy Settings"))
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        group_box = QGroupBox(T("Основные параметры", "Basic Parameters"))
        group_box.setFont(QFont("Segoe UI", 10))
        group_layout = QVBoxLayout(group_box)
        group_layout.setSpacing(10)
        
        # Region selection
        region_layout = QHBoxLayout()
        region_label = QLabel(T("Регион (Страна):", "Region (Country):"))
        self.region_combo = QComboBox()
        self.region_combo.addItems(["EU (Европа)", "AM (Америка)", "AS (Азия)", "ALL (Любой)"])
        region_layout.addWidget(region_label)
        region_layout.addWidget(self.region_combo)
        group_layout.addLayout(region_layout)
        
        # Policy selection
        policy_layout = QHBoxLayout()
        policy_label = QLabel(T("Выбор сервера:", "Server Selection:"))
        self.policy_combo = QComboBox()
        self.policy_combo.addItems(["fastest (Самый быстрый)", "random (Случайный)", "first (Первый)"])
        policy_layout.addWidget(policy_label)
        policy_layout.addWidget(self.policy_combo)
        group_layout.addLayout(policy_layout)
        
        main_layout.addWidget(group_box)
        
        # Advanced (raw parameters)
        adv_group = QGroupBox(T("Дополнительные аргументы (для продвинутых)", "Additional Arguments (Advanced)"))
        adv_group.setFont(QFont("Segoe UI", 10))
        adv_layout = QVBoxLayout(adv_group)
        self.raw_params_input = QLineEdit()
        self.raw_params_input.setPlaceholderText(T("Например: -proxy socks5://127.0.0.1:1780", "Example: -proxy socks5://127.0.0.1:1780"))
        adv_layout.addWidget(self.raw_params_input)
        main_layout.addWidget(adv_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(T("Сохранить и Применить", "Save and Apply"))
        save_btn.setMinimumHeight(35)
        save_btn.setStyleSheet("background-color: #2b78e4; color: white; border: none; border-radius: 4px; font-weight: bold;")
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton(T("Отмена", "Cancel"))
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        
        self.load_settings()
        
    def load_settings(self):
        if not os.path.exists(OPERA_CUSTOM_FILE):
            return
            
        with open(OPERA_CUSTOM_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    params = line
                    
                    # Parse region
                    if "-country EU" in params:
                        self.region_combo.setCurrentIndex(0)
                    elif "-country AM" in params:
                        self.region_combo.setCurrentIndex(1)
                    elif "-country AS" in params:
                        self.region_combo.setCurrentIndex(2)
                    elif "-country ALL" in params:
                        self.region_combo.setCurrentIndex(3)
                    
                    # Parse policy
                    if "-server-selection fastest" in params:
                        self.policy_combo.setCurrentIndex(0)
                    elif "-server-selection random" in params:
                        self.policy_combo.setCurrentIndex(1)
                    elif "-server-selection first" in params:
                        self.policy_combo.setCurrentIndex(2)
                    
                    # Extract advanced args (everything that is not standard)
                    known_args = ["-bind-address 127.0.0.1:1785", "-socks-mode", "-verbosity 20",
                                  "-country EU", "-country AM", "-country AS", "-country ALL",
                                  "-server-selection fastest", "-server-selection random", "-server-selection first"]
                    
                    adv_params = params
                    for known in known_args:
                        adv_params = adv_params.replace(known, "").strip()
                    
                    # collapse spaces
                    adv_params = " ".join(adv_params.split())
                    self.raw_params_input.setText(adv_params)
                    break # Only parse the first valid line

    def save_settings(self):
        region_map = {0: "EU", 1: "AM", 2: "AS", 3: "ALL"}
        policy_map = {0: "fastest", 1: "random", 2: "first"}
        
        region = region_map.get(self.region_combo.currentIndex(), "EU")
        policy = policy_map.get(self.policy_combo.currentIndex(), "random")
        
        adv = self.raw_params_input.text().strip()
        
        new_params = f"-bind-address 127.0.0.1:1785 -socks-mode -verbosity 20 -country {region} -server-selection {policy}"
        if adv:
            new_params += f" {adv}"
            
        config = config_manager.load_config()
        config["opera_params"] = new_params
        config_manager.save_config(config)
            
        QMessageBox.information(self, T("Успех", "Success"), T("Настройки сохранены. Если Opera Proxy запущен, пожалуйста, перезапустите его.", "Settings saved. If Opera Proxy is running, please restart it."))
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = OperaSettingsWindow()
    window.show()
    sys.exit(app.exec_())

