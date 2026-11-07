import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QCheckBox, QPushButton, QMessageBox, QLabel, 
                             QComboBox, QHBoxLayout, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from managers import config_manager
from managers import system_utils as lang

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def T(ru, en, fr=None):
    if hasattr(lang, 'T'):
        return lang.T(ru, en, fr)
    cur = getattr(lang, '_current_lang', 'ru')
    if cur == 'fr':
        return fr or en or ru
    elif cur == 'en':
        return en or ru
    return ru

class AutostartSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Настройки автозапуска", "Autostart Settings", "Paramètres de démarrage"))
        self.setFixedSize(440, 430)
        
        # Dark Title Bar matching window background
        try:
            import ctypes
            hwnd = int(self.winId())
            val = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))
            color = ctypes.c_int(0x00181818)  # Matches #181818 background (0x00BBGGRR)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
        except Exception:
            pass
            
        icon_path = os.path.join(CURRENT_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.config = config_manager.load_config()
        self.autostart_tools = self.config.get("autostart_tools", ["byedpi", "tor", "opera", "vless", "tgws", "ext"])
        
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #181818;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #5dade2;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLabel {
                color: #cccccc;
            }
            QComboBox {
                background-color: #242424;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 3px 6px;
                color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #242424;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QCheckBox {
                color: #cccccc;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: #242424;
                border: 1px solid #444444;
                border-radius: 3px;
            }
            QCheckBox::indicator:hover {
                border-color: #666666;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        
        self.initUI()
        
    def initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(8)
        
        # 1. Tools Group (2-column compact grid)
        tools_group = QGroupBox(T("Инструменты для автозапуска", "Tools to autostart", "Outils au démarrage"))
        tools_layout = QGridLayout(tools_group)
        tools_layout.setContentsMargins(10, 8, 10, 8)
        tools_layout.setHorizontalSpacing(15)
        tools_layout.setVerticalSpacing(6)
        
        self.cb_byedpi = QCheckBox(T("ByeDPI (Обход DPI)", "ByeDPI (DPI Bypass)", "ByeDPI (Contournement DPI)"))
        self.cb_byedpi.setChecked("byedpi" in self.autostart_tools)
        tools_layout.addWidget(self.cb_byedpi, 0, 0)
        
        self.cb_tor = QCheckBox(T("Tor (Onion/Мосты)", "Tor (Onion/Bridges)", "Tor (Onion/Ponts)"))
        self.cb_tor.setChecked("tor" in self.autostart_tools)
        tools_layout.addWidget(self.cb_tor, 0, 1)
        
        self.cb_opera = QCheckBox(T("Opera Proxy (VPN)", "Opera Proxy (VPN)", "Opera Proxy (VPN)"))
        self.cb_opera.setChecked("opera" in self.autostart_tools)
        tools_layout.addWidget(self.cb_opera, 1, 0)
        
        self.cb_ssh = QCheckBox(T("SSH Туннель (SOCKS5)", "SSH Tunnel (SOCKS5)", "Tunnel SSH (SOCKS5)"))
        self.cb_ssh.setChecked("ssh" in self.autostart_tools)
        tools_layout.addWidget(self.cb_ssh, 1, 1)
        
        self.cb_tgws = QCheckBox(T("Telegram WS Proxy", "Telegram WS Proxy", "Proxy Telegram WS"))
        self.cb_tgws.setChecked("tgws" in self.autostart_tools)
        self.cb_tgws.toggled.connect(self.on_tgws_toggled)
        tools_layout.addWidget(self.cb_tgws, 2, 0)
        
        self.cb_socks = QCheckBox(T("SOCKS Реабилитатор", "SOCKS Reabilitator", "Réhabilitateur SOCKS"))
        self.cb_socks.setChecked("socks" in self.autostart_tools)
        tools_layout.addWidget(self.cb_socks, 2, 1)
        
        self.cb_proxifier = QCheckBox(T("Проксификатор (TUN)", "Proxifier (TUN)", "Proxificateur (TUN)"))
        self.cb_proxifier.setChecked("proxifier" in self.autostart_tools)
        tools_layout.addWidget(self.cb_proxifier, 3, 0)
        
        self.cb_ext = QCheckBox(T("Доп. программы", "External Programs", "Programmes additionnels"))
        self.cb_ext.setChecked("ext" in self.autostart_tools)
        tools_layout.addWidget(self.cb_ext, 3, 1)
        
        main_layout.addWidget(tools_group)
        
        # 2. General Autostart & Torrc Parameters Group
        params_group = QGroupBox(T("Параметры запуска Windows и Tor", "Startup & Tor Options", "Options de démarrage et Tor"))
        params_layout = QVBoxLayout(params_group)
        params_layout.setContentsMargins(10, 8, 10, 8)
        params_layout.setSpacing(6)
        
        self.cb_app_autostart = QCheckBox(T("Запускать ToInet-MAX при старте Windows", "Start ToInet-MAX on Windows startup", "Démarrer ToInet-MAX avec Windows"))
        self.cb_app_autostart.setChecked(self.config.get("auto_start", False))
        params_layout.addWidget(self.cb_app_autostart)
        
        self.cb_auto_last = QCheckBox(T("Подключать последний режим при запуске", "Connect last mode on start", "Reconnecter le dernier mode au démarrage"))
        self.cb_auto_last.setChecked(self.config.get("auto_connect_last_mode", False))
        params_layout.addWidget(self.cb_auto_last)
        
        torrc_row = QHBoxLayout()
        torrc_label = QLabel(T("Действие с torrc:", "Action with torrc:", "Action pour torrc :"))
        torrc_label.setFixedWidth(120)
        self.torrc_combo = QComboBox()
        self.torrc_combo.addItem(T("Не трогать (None)", "Do nothing (None)", "Ne rien faire (None)"), "none")
        self.torrc_combo.addItem(T("Обновлять мосты", "Update bridges only", "Mettre à jour les ponts"), "bridges")
        self.torrc_combo.addItem(T("Полное пересоздание", "Full recreation", "Recréation complète"), "full")
        
        val = self.config.get("recreate_torrc", "none")
        if isinstance(val, bool): val = "full" if val else "none"
        if val in ("true", "full"): self.torrc_combo.setCurrentIndex(2)
        elif val in ("false", "bridges"): self.torrc_combo.setCurrentIndex(1)
        else: self.torrc_combo.setCurrentIndex(0)
            
        torrc_row.addWidget(torrc_label)
        torrc_row.addWidget(self.torrc_combo)
        torrc_row.addStretch()
        params_layout.addLayout(torrc_row)
        
        main_layout.addWidget(params_group)
        main_layout.addStretch()
        
        # 3. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        save_btn = QPushButton(T("Сохранить", "Save", "Enregistrer"))
        save_btn.setFixedHeight(30)
        save_btn.clicked.connect(self.save_settings)
        
        close_btn = QPushButton(T("Отмена", "Cancel", "Annuler"))
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #3d3d3d;")
        close_btn.clicked.connect(self.close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        
    def on_tgws_toggled(self, checked):
        if checked:
            reply = QMessageBox.warning(self, T("Внимание", "Warning"),
                T("Павел Дуров признан в России экстремистом и не известно какие меры будут приняты в отношении телеграмма, поэтому вместо tgws стоит использовать tor или opera proxy. Включить автозапуск tgws?",
                  "Pavel Durov is recognized as an extremist in Russia and it is unknown what measures will be taken against Telegram, so instead of tgws you should use tor or opera proxy. Enable tgws autostart?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.cb_tgws.blockSignals(True)
                self.cb_tgws.setChecked(False)
                self.cb_tgws.blockSignals(False)

    def save_settings(self):
        tools = []
        if self.cb_byedpi.isChecked(): tools.append("byedpi")
        if self.cb_tor.isChecked(): tools.append("tor")
        if self.cb_opera.isChecked(): tools.append("opera")
        if self.cb_ssh.isChecked(): tools.append("ssh")
        if self.cb_socks.isChecked(): tools.append("socks")
        if self.cb_tgws.isChecked(): tools.append("tgws")
        if self.cb_proxifier.isChecked(): tools.append("proxifier")
        if self.cb_ext.isChecked(): tools.append("ext")
        
        self.config["autostart_tools"] = tools
        self.config["auto_connect_last_mode"] = self.cb_auto_last.isChecked()
        
        mode = self.torrc_combo.currentData()
        self.config["recreate_torrc"] = mode
            
        app_autostart = self.cb_app_autostart.isChecked()
        current_app_autostart = self.config.get("auto_start", False)
        
        if app_autostart != current_app_autostart:
            self.config["auto_start"] = app_autostart
            try:
                from managers import system_utils as auto_launcher_setuper
                if app_autostart:
                    auto_launcher_setuper.enable_auto_start("main.pyw")
                else:
                    auto_launcher_setuper.disable_auto_start()
            except Exception as e:
                QMessageBox.warning(self, T("Ошибка", "Error"), f"Failed to set autorun: {e}")
                
        config_manager.save_config(self.config)
        QMessageBox.information(self, T("Успех", "Success", "Succès"), T("Настройки автозапуска сохранены.", "Autostart settings saved.", "Paramètres de démarrage enregistrés."))
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutostartSettingsWindow()
    window.show()
    sys.exit(app.exec())
