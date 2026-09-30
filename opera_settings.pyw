import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QGroupBox, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
import lang
from managers import config_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
DEFAULT_PARAMS = "-bind-address 127.0.0.1:1785 -verbosity 20 -country EU -server-selection random -proxy socks5://127.0.0.1:1787"

def T(ru_text, en_text):
    return en_text if lang._is_en else ru_text

class OperaSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Р СњР В°РЎРѓРЎвЂљРЎР‚Р С•Р в„–Р С”Р С‘ Opera Proxy", "Opera Proxy Settings"))
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
        
        title_label = QLabel(T("Р СњР В°РЎРѓРЎвЂљРЎР‚Р С•Р в„–Р С”Р С‘ Opera Proxy", "Opera Proxy Settings"))
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        group_box = QGroupBox(T("Р С›РЎРѓР Р…Р С•Р Р†Р Р…РЎвЂ№Р Вµ Р С—Р В°РЎР‚Р В°Р СР ВµРЎвЂљРЎР‚РЎвЂ№", "Basic Parameters"))
        group_box.setFont(QFont("Segoe UI", 10))
        group_layout = QVBoxLayout(group_box)
        group_layout.setSpacing(10)
        
        # Region selection
        region_layout = QHBoxLayout()
        region_label = QLabel(T("Р В Р ВµР С–Р С‘Р С•Р Р… (Р РЋРЎвЂљРЎР‚Р В°Р Р…Р В°):", "Region (Country):"))
        self.region_combo = QComboBox()
        self.region_combo.addItems(["EU (Р вЂўР Р†РЎР‚Р С•Р С—Р В°)", "AM (Р С’Р СР ВµРЎР‚Р С‘Р С”Р В°)", "AS (Р С’Р В·Р С‘РЎРЏ)", "ALL (Р вЂєРЎР‹Р В±Р С•Р в„–)"])
        region_layout.addWidget(region_label)
        region_layout.addWidget(self.region_combo)
        group_layout.addLayout(region_layout)
        
        # Policy selection
        policy_layout = QHBoxLayout()
        policy_label = QLabel(T("Р вЂ™РЎвЂ№Р В±Р С•РЎР‚ РЎРѓР ВµРЎР‚Р Р†Р ВµРЎР‚Р В°:", "Server Selection:"))
        self.policy_combo = QComboBox()
        self.policy_combo.addItems(["fastest (Р РЋР В°Р СРЎвЂ№Р в„– Р В±РЎвЂ№РЎРѓРЎвЂљРЎР‚РЎвЂ№Р в„–)", "random (Р РЋР В»РЎС“РЎвЂЎР В°Р в„–Р Р…РЎвЂ№Р в„–)", "first (Р СџР ВµРЎР‚Р Р†РЎвЂ№Р в„–)"])
        policy_layout.addWidget(policy_label)
        policy_layout.addWidget(self.policy_combo)
        group_layout.addLayout(policy_layout)
        
        main_layout.addWidget(group_box)
        
        # Advanced (raw parameters)
        adv_group = QGroupBox(T("Р вЂќР С•Р С—Р С•Р В»Р Р…Р С‘РЎвЂљР ВµР В»РЎРЉР Р…РЎвЂ№Р Вµ Р В°РЎР‚Р С–РЎС“Р СР ВµР Р…РЎвЂљРЎвЂ№ (Р Т‘Р В»РЎРЏ Р С—РЎР‚Р С•Р Т‘Р Р†Р С‘Р Р…РЎС“РЎвЂљРЎвЂ№РЎвЂ¦)", "Additional Arguments (Advanced)"))
        adv_group.setFont(QFont("Segoe UI", 10))
        adv_layout = QVBoxLayout(adv_group)
        self.raw_params_input = QLineEdit()
        self.raw_params_input.setPlaceholderText(T("Р СњР В°Р С—РЎР‚Р С‘Р СР ВµРЎР‚: -proxy socks5://127.0.0.1:1780", "Example: -proxy socks5://127.0.0.1:1780"))
        adv_layout.addWidget(self.raw_params_input)
        main_layout.addWidget(adv_group)

        # Proxy Pool
        from PyQt5.QtWidgets import QCheckBox, QSpinBox
        pool_group = QGroupBox(T("Р СџРЎС“Р В» Р С—РЎР‚Р С•Р С”РЎРѓР С‘ (Load Balancing)", "Proxy Pool (Load Balancing)"))
        pool_group.setFont(QFont("Segoe UI", 10))
        pool_layout = QHBoxLayout(pool_group)
        self.pool_checkbox = QCheckBox(T("Р вЂ™Р С”Р В»РЎР‹РЎвЂЎР С‘РЎвЂљРЎРЉ Р С—РЎС“Р В» (Р В·Р В°Р С—РЎС“РЎРѓР С” Р Р…Р ВµРЎРѓР С”Р С•Р В»РЎРЉР С”Р С‘РЎвЂ¦ РЎРЊР С”Р В·Р ВµР СР С—Р В»РЎРЏРЎР‚Р С•Р Р†)", "Enable Pool (Run multiple instances)"))
        self.pool_spinbox = QSpinBox()
        self.pool_spinbox.setRange(2, 10)
        self.pool_spinbox.setValue(3)
        self.pool_spinbox.setEnabled(False)
        self.pool_checkbox.toggled.connect(self.pool_spinbox.setEnabled)
        pool_layout.addWidget(self.pool_checkbox)
        pool_layout.addWidget(QLabel(T("Р С™Р С•Р В»Р С‘РЎвЂЎР ВµРЎРѓРЎвЂљР Р†Р С•:", "Count:")))
        pool_layout.addWidget(self.pool_spinbox)
        main_layout.addWidget(pool_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(T("Р РЋР С•РЎвЂ¦РЎР‚Р В°Р Р…Р С‘РЎвЂљРЎРЉ Р С‘ Р СџРЎР‚Р С‘Р СР ВµР Р…Р С‘РЎвЂљРЎРЉ", "Save and Apply"))
        save_btn.setMinimumHeight(35)
        save_btn.setStyleSheet("background-color: #2b78e4; color: white; border: none; border-radius: 4px; font-weight: bold;")
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton(T("Р С›РЎвЂљР СР ВµР Р…Р В°", "Cancel"))
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        
        self.load_settings()
        
    def load_settings(self):
        config = config_manager.load_config()
        pool_enabled = config.get("opera_pool_enabled", False)
        pool_size = config.get("opera_pool_size", 3)
        self.pool_checkbox.setChecked(pool_enabled)
        self.pool_spinbox.setValue(pool_size)

        params = config.get("opera_params", "")
        if params:
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

    def save_settings(self):
        region_map = {0: "EU", 1: "AM", 2: "AS", 3: "ALL"}
        policy_map = {0: "fastest", 1: "random", 2: "first"}
        
        region = region_map.get(self.region_combo.currentIndex(), "EU")
        policy = policy_map.get(self.policy_combo.currentIndex(), "random")
        
        adv = self.raw_params_input.text().strip()
        
        new_params = f"-bind-address 127.0.0.1:1785 -verbosity 20 -country {region} -server-selection {policy}"
        if adv:
            new_params += f" {adv}"
            
        config = config_manager.load_config()
        config["opera_params"] = new_params
        config["opera_pool_enabled"] = self.pool_checkbox.isChecked()
        config["opera_pool_size"] = self.pool_spinbox.value()
        config_manager.save_config(config)
            
        QMessageBox.information(self, T("Р Р€РЎРѓР С—Р ВµРЎвЂ¦", "Success"), T("Р СњР В°РЎРѓРЎвЂљРЎР‚Р С•Р в„–Р С”Р С‘ РЎРѓР С•РЎвЂ¦РЎР‚Р В°Р Р…Р ВµР Р…РЎвЂ№. Р вЂўРЎРѓР В»Р С‘ Opera Proxy Р В·Р В°Р С—РЎС“РЎвЂ°Р ВµР Р…, Р С—Р С•Р В¶Р В°Р В»РЎС“Р в„–РЎРѓРЎвЂљР В°, Р С—Р ВµРЎР‚Р ВµР В·Р В°Р С—РЎС“РЎРѓРЎвЂљР С‘РЎвЂљР Вµ Р ВµР С–Р С•.", "Settings saved. If Opera Proxy is running, please restart it."))
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = OperaSettingsWindow()
    window.show()
    sys.exit(app.exec_())



