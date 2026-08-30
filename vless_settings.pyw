import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QGroupBox, QComboBox, QSpinBox, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
import lang
import config_manager

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def T(ru_text, en_text):
    return en_text if lang._is_en else ru_text

class VlessSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Настройки VLESS", "VLESS Settings"))
        self.setFixedSize(500, 600)
        
        icon_path = os.path.join(CURRENT_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        title_label = QLabel(T("Настройки VLESS Proxy", "VLESS Proxy Settings"))
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        mode_layout = QHBoxLayout()
        mode_label = QLabel(T("Режим работы:", "Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([T("Стандартный (Один сервер)", "Standard (Single Server)"), T("Ротация (wl_torred_vless)", "Rotation (wl_torred_vless)")])
        self.mode_combo.currentIndexChanged.connect(self.toggle_mode_ui)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        main_layout.addLayout(mode_layout)
        
        # Standard Mode Group
        self.std_group = QGroupBox(T("Стандартный режим", "Standard Mode"))
        std_layout = QVBoxLayout(self.std_group)
        
        def add_input(layout, label_text):
            h = QHBoxLayout()
            h.addWidget(QLabel(label_text))
            le = QLineEdit()
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
        
        # Rotation Mode Group
        self.rot_group = QGroupBox(T("Режим Ротации", "Rotation Mode"))
        rot_layout = QVBoxLayout(self.rot_group)
        
        rot_layout.addWidget(QLabel(T("Ссылки на подписки (по одной на строку):", "Subscription URLs (one per line):")))
        self.subs_text = QTextEdit()
        rot_layout.addWidget(self.subs_text)
        
        int_layout = QHBoxLayout()
        int_layout.addWidget(QLabel(T("Интервал ротации (сек):", "Rotation interval (sec):")))
        self.inp_interval = QSpinBox()
        self.inp_interval.setRange(10, 86400)
        int_layout.addWidget(self.inp_interval)
        rot_layout.addLayout(int_layout)
        
        main_layout.addWidget(self.rot_group)
        
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
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow, QDialog { background-color: #1e1e1e; color: #f0f0f0; }
            QLabel { color: #f0f0f0; }
            QGroupBox { color: #f0f0f0; border: 1px solid #3d3d3d; border-radius: 5px; margin-top: 10px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: #2b78e4; }
            QLineEdit, QComboBox, QSpinBox, QTextEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #3d3d3d; color: #f0f0f0; border: none; border-radius: 4px; padding: 5px 15px; }
            QPushButton:hover { background-color: #4d4d4d; }
            QComboBox::drop-down { border: none; }
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
        
        subs_path = os.path.join(CURRENT_DIR, "subs.txt")
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
        
        subs_path = os.path.join(CURRENT_DIR, "subs.txt")
        with open(subs_path, "w", encoding="utf-8") as f:
            f.write(self.subs_text.toPlainText())
            
        QMessageBox.information(self, T("Успех", "Success"), T("Настройки сохранены.\nПерезапустите VLESS для применения.", "Settings saved.\nRestart VLESS to apply."))
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VlessSettingsWindow()
    window.show()
    sys.exit(app.exec_())
