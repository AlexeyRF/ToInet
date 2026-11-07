import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QGroupBox, QComboBox, QCheckBox, QSpinBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from managers import system_utils as lang
from managers import config_manager

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
DEFAULT_PARAMS = "-bind-address 127.0.0.1:1785 -verbosity 20 -country EU -server-selection random -proxy socks5://127.0.0.1:1787"

def T(ru_text, en_text, fr_text=None, fr=None):
    if hasattr(lang, 'T'):
        return lang.T(ru_text, en_text, fr_text, fr)
    cur = getattr(lang, '_current_lang', 'ru')
    if cur == 'fr':
        return fr or fr_text or en_text or ru_text
    elif cur == 'en':
        return en_text or ru_text
    return ru_text

class OperaSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Настройки Opera Proxy", "Opera Proxy Settings", "Paramètres Opera Proxy"))
        # Increased window length/height for comfortable spacing and scaling
        self.resize(520, 450)
        self.setMinimumSize(480, 420)
        
        # Dark Title Bar matching window background
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                val = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))
                color = ctypes.c_int(0x00202020)  # Matches #202020 background (0x00BBGGRR)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
            except Exception:
                pass

        # Load icon if available
        for p in [os.path.join(CURRENT_DIR, "icon.ico"), 
                  os.path.join(os.path.dirname(CURRENT_DIR), "icon.ico")]:
            if os.path.exists(p):
                self.setWindowIcon(QIcon(p))
                break

        self.setStyleSheet("""
            QMainWindow, QWidget { 
                background-color: #202020; 
                color: #FFFFFF; 
                font-family: 'Segoe UI Variable Text', 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
            }
            QLabel { 
                color: #d0d0d0; 
                background: transparent;
            }
            QGroupBox { 
                color: #0078D4; 
                border: 1px solid #383838; 
                border-radius: 6px; 
                margin-top: 10px; 
                padding-top: 10px;
                font-weight: bold; 
                font-size: 11px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                left: 10px;
                padding: 0 4px; 
                color: #0078D4; 
            }
            QLineEdit, QComboBox, QSpinBox { 
                background-color: #2b2b2b; 
                color: #ffffff; 
                border: 1px solid #383838; 
                border-radius: 4px; 
                padding: 4px 8px; 
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #0078D4;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #005FB8;
            }
            QCheckBox {
                color: #cccccc;
                spacing: 6px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 3px;
            }
            QCheckBox::indicator:hover {
                border-color: #666666;
            }
            QCheckBox::indicator:checked {
                background-color: #0078D4;
                border-color: #0078D4;
            }
            QPushButton { 
                background-color: #2b2b2b; 
                color: #FFFFFF; 
                border: 1px solid #383838; 
                border-radius: 4px; 
                padding: 6px 14px; 
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { 
                background-color: #383838; 
                border-color: #484848; 
            }
            QPushButton:pressed { 
                background-color: #1e1e1e; 
            }
            QPushButton#primaryBtn {
                background-color: #005FB8;
                border-color: #005FB8;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0078D4;
                border-color: #0078D4;
            }
        """)
            
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)
        
        title_label = QLabel(T("Настройки Opera Proxy", "Opera Proxy Settings", "Paramètres Opera Proxy"))
        title_label.setFont(QFont("Segoe UI Variable Text", 13, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #FFFFFF; background: transparent; padding: 2px;")
        main_layout.addWidget(title_label)
        
        # 1. Basic Parameters Group
        group_box = QGroupBox(T("Основные параметры", "Basic Parameters", "Paramètres de base"))
        group_box.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(12, 12, 12, 12)
        group_layout.setSpacing(10)
        
        # Region selection
        region_layout = QHBoxLayout()
        region_label = QLabel(T("Регион (Страна):", "Region (Country):", "Région (Pays):"))
        region_label.setFont(QFont("Segoe UI Variable Text", 9))
        self.region_combo = QComboBox()
        self.region_combo.setFixedHeight(28)
        self.region_combo.addItems(["EU (Европа)", "AM (Америка)", "AS (Азия)", "ALL (Любой)"])
        region_layout.addWidget(region_label)
        region_layout.addWidget(self.region_combo, 1)
        group_layout.addLayout(region_layout)
        
        # Policy selection
        policy_layout = QHBoxLayout()
        policy_label = QLabel(T("Выбор сервера:", "Server Selection:", "Sélection du serveur:"))
        policy_label.setFont(QFont("Segoe UI Variable Text", 9))
        self.policy_combo = QComboBox()
        self.policy_combo.setFixedHeight(28)
        self.policy_combo.addItems(["fastest (Самый быстрый)", "random (Случайный)", "first (Первый)"])
        policy_layout.addWidget(policy_label)
        policy_layout.addWidget(self.policy_combo, 1)
        group_layout.addLayout(policy_layout)
        
        main_layout.addWidget(group_box)
        
        # 2. Advanced (raw parameters) Group
        adv_group = QGroupBox(T("Дополнительные аргументы (для продвинутых)", "Additional Arguments (Advanced)", "Arguments additionnels (Avancé)"))
        adv_group.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        adv_layout = QVBoxLayout(adv_group)
        adv_layout.setContentsMargins(12, 12, 12, 12)
        adv_layout.setSpacing(8)
        self.raw_params_input = QLineEdit()
        self.raw_params_input.setFixedHeight(28)
        self.raw_params_input.setPlaceholderText(T("Например: -proxy socks5://127.0.0.1:1780", "Example: -proxy socks5://127.0.0.1:1780", "Exemple: -proxy socks5://127.0.0.1:1780"))
        adv_layout.addWidget(self.raw_params_input)
        main_layout.addWidget(adv_group)

        # 3. Proxy Pool Group
        pool_group = QGroupBox(T("Пул прокси (Load Balancing)", "Proxy Pool (Load Balancing)", "Pool de proxies (Équilibrage de charge)"))
        pool_group.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        pool_layout = QHBoxLayout(pool_group)
        pool_layout.setContentsMargins(12, 12, 12, 12)
        pool_layout.setSpacing(10)
        self.pool_checkbox = QCheckBox(T("Включить пул (запуск нескольких экземпляров)", "Enable Pool (Run multiple instances)", "Activer le pool (plusieurs instances)"))
        self.pool_checkbox.setFont(QFont("Segoe UI Variable Text", 9))
        self.pool_spinbox = QSpinBox()
        self.pool_spinbox.setFixedHeight(28)
        self.pool_spinbox.setRange(2, 10)
        self.pool_spinbox.setValue(3)
        self.pool_spinbox.setEnabled(False)
        self.pool_checkbox.toggled.connect(self.pool_spinbox.setEnabled)
        pool_layout.addWidget(self.pool_checkbox, 1)
        lbl_count = QLabel(T("Количество:", "Count:", "Nombre:"))
        lbl_count.setFont(QFont("Segoe UI Variable Text", 9))
        pool_layout.addWidget(lbl_count)
        pool_layout.addWidget(self.pool_spinbox)
        main_layout.addWidget(pool_group)
        
        main_layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton(T("Отмена", "Cancel", "Annuler"))
        cancel_btn.setFixedHeight(30)
        cancel_btn.clicked.connect(self.close)
        
        save_btn = QPushButton(T("Сохранить и Применить", "Save and Apply", "Enregistrer et appliquer"))
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(30)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
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
            
        QMessageBox.information(self, T("Успех", "Success", "Succès"), 
                                T("Настройки сохранены. Если Opera Proxy запущен, пожалуйста, перезапустите его.", 
                                  "Settings saved. If Opera Proxy is running, please restart it.",
                                  "Paramètres enregistrés. Si Opera Proxy est en cours d'exécution, veuillez le redémarrer."))
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = OperaSettingsWindow()
    window.show()
    sys.exit(app.exec_())
