import sys
import os
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path: sys.path.insert(0, PARENT_DIR)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QGroupBox, QComboBox, QSpinBox, QTextEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from managers import system_utils as lang
from managers import config_manager

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def get_subs_path():
    candidates = [
        os.path.join(CURRENT_DIR, "evpn", "subs.txt"),
        os.path.join(CURRENT_DIR, "subs.txt"),
        os.path.join(PARENT_DIR, "evpn", "subs.txt"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

def T(ru_text, en_text):
    return en_text if lang._is_en else ru_text

class VlessSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Настройки VLESS / EVPN", "VLESS / EVPN Settings"))
        self.resize(440, 410)
        self.setMinimumSize(400, 370)
        
        icon_path = os.path.join(CURRENT_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)
        
        title_label = QLabel(T("Настройки VLESS / EVPN Proxy", "VLESS / EVPN Proxy Settings"))
        title_label.setFont(QFont("Segoe UI Variable Text", 12, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #FFFFFF; background: transparent; padding: 2px;")
        main_layout.addWidget(title_label)
        
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(8)
        mode_label = QLabel(T("Режим работы:", "Mode:"))
        mode_label.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        mode_label.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.mode_combo = QComboBox()
        self.mode_combo.setFixedHeight(27)
        self.mode_combo.addItems([T("Стандартный (Один сервер)", "Standard (Single Server)"), T("Ротация (wl_torred_vless)", "Rotation (wl_torred_vless)")])
        self.mode_combo.currentIndexChanged.connect(self.toggle_mode_ui)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo, 1)
        main_layout.addLayout(mode_layout)
        
        # Standard Mode Group (Compact)
        self.std_group = QGroupBox(T("Стандартный режим", "Standard Mode"))
        std_layout = QVBoxLayout(self.std_group)
        std_layout.setContentsMargins(10, 8, 10, 8)
        std_layout.setSpacing(4)
        
        def add_input(layout, label_text):
            h = QHBoxLayout()
            h.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(85)
            lbl.setFont(QFont("Segoe UI Variable Text", 9))
            lbl.setStyleSheet("color: #d0d0d0; background: transparent;")
            le = QLineEdit()
            le.setFixedHeight(25)
            h.addWidget(lbl)
            h.addWidget(le)
            layout.addLayout(h)
            return le
            
        self.inp_server = add_input(std_layout, "Server:")
        self.inp_port = add_input(std_layout, "Port:")
        self.inp_uuid = add_input(std_layout, "UUID:")
        self.inp_sni = add_input(std_layout, "TLS SNI:")
        self.inp_pbk = add_input(std_layout, "Reality PBK:")
        self.inp_sid = add_input(std_layout, "Short ID:")
        main_layout.addWidget(self.std_group)
        
        # Rotation Mode Group (Compact)
        self.rot_group = QGroupBox(T("Режим Ротации", "Rotation Mode"))
        rot_layout = QVBoxLayout(self.rot_group)
        rot_layout.setContentsMargins(10, 8, 10, 8)
        rot_layout.setSpacing(6)
        
        rot_lbl = QLabel(T("Ссылки на подписки (по одной на строку):", "Subscription URLs (one per line):"))
        rot_lbl.setFont(QFont("Segoe UI Variable Text", 9))
        rot_layout.addWidget(rot_lbl)
        self.subs_text = QTextEdit()
        self.subs_text.setMinimumHeight(110)
        rot_layout.addWidget(self.subs_text)
        
        int_layout = QHBoxLayout()
        int_layout.setSpacing(6)
        int_lbl = QLabel(T("Интервал ротации (сек):", "Rotation interval (sec):"))
        int_lbl.setFont(QFont("Segoe UI Variable Text", 9))
        self.inp_interval = QSpinBox()
        self.inp_interval.setFixedHeight(25)
        self.inp_interval.setRange(10, 86400)
        int_layout.addWidget(int_lbl)
        int_layout.addWidget(self.inp_interval)
        int_layout.addStretch()
        rot_layout.addLayout(int_layout)
        
        main_layout.addWidget(self.rot_group)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton(T("Отмена", "Cancel"))
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.close)
        
        save_btn = QPushButton(T("Сохранить и Применить", "Save and Apply"))
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)
        
        # Fluent Dark Theme stylesheet
        self.setStyleSheet("""
            QMainWindow, QDialog { 
                background-color: #202020; 
                color: #FFFFFF; 
                font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            }
            QLabel { 
                color: #d0d0d0; 
                background: transparent;
            }
            QGroupBox { 
                color: #0078D4; 
                border: 1px solid #383838; 
                border-radius: 6px; 
                margin-top: 6px; 
                font-weight: bold; 
                font-size: 11px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                padding: 0 4px; 
                color: #0078D4; 
            }
            QLineEdit, QComboBox, QSpinBox, QTextEdit { 
                background-color: #2b2b2b; 
                color: #ffffff; 
                border: 1px solid #383838; 
                border-radius: 4px; 
                padding: 2px 6px; 
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
                border-color: #005FB8;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #005FB8;
            }
            QPushButton { 
                background-color: #2b2b2b; 
                color: #FFFFFF; 
                border: 1px solid #383838; 
                border-radius: 4px; 
                padding: 3px 14px; 
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { 
                background-color: #383838; 
                border-color: #484848; 
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
        
        self.load_settings()
        self.toggle_mode_ui()
        
    def toggle_mode_ui(self):
        is_rot = self.mode_combo.currentIndex() == 1
        self.std_group.setVisible(not is_rot)
        self.rot_group.setVisible(is_rot)
        
    def load_settings(self):
        config = config_manager.load_config()
        mode = config.get("vless_mode", "standard")
        self.mode_combo.setCurrentIndex(1 if mode == "rotation" else 0)
        
        self.inp_server.setText(config.get("vless_server", ""))
        self.inp_port.setText(str(config.get("vless_port", 443)))
        self.inp_uuid.setText(config.get("vless_uuid", ""))
        self.inp_sni.setText(config.get("vless_sni", ""))
        self.inp_pbk.setText(config.get("vless_pbk", ""))
        self.inp_sid.setText(config.get("vless_sid", ""))
        self.inp_interval.setValue(config.get("vless_rot_interval", 300))
        
        subs_path = get_subs_path()
        if os.path.exists(subs_path):
            with open(subs_path, "r", encoding="utf-8") as f:
                self.subs_text.setPlainText(f.read())
                
    def save_settings(self):
        config = config_manager.load_config()
        config["vless_mode"] = "rotation" if self.mode_combo.currentIndex() == 1 else "standard"
        config["vless_server"] = self.inp_server.text().strip()
        
        try:
            config["vless_port"] = int(self.inp_port.text().strip() or "443")
        except:
            config["vless_port"] = 443
            
        config["vless_uuid"] = self.inp_uuid.text().strip()
        config["vless_sni"] = self.inp_sni.text().strip()
        config["vless_pbk"] = self.inp_pbk.text().strip()
        config["vless_sid"] = self.inp_sid.text().strip()
        config["vless_rot_interval"] = self.inp_interval.value()
        
        config_manager.save_config(config)
        
        subs_path = get_subs_path()
        with open(subs_path, "w", encoding="utf-8") as f:
            f.write(self.subs_text.toPlainText())
            
        QMessageBox.information(self, T("Успех", "Success"), T("Настройки сохранены.\nПерезапустите VLESS для применения.", "Settings saved.\nRestart VLESS to apply."))
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VlessSettingsWindow()
    window.show()
    sys.exit(app.exec_())
