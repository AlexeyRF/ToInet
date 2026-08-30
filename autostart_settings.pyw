import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QCheckBox, QPushButton, QMessageBox, QLabel, QComboBox, QHBoxLayout
import config_manager
import lang

def T(ru, en):
    return en if lang._is_en else ru

class AutostartSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Настройки автозапуска", "Autostart Settings"))
        self.resize(600, 650)
        
        # Dark Title Bar for Windows
        try:
            import ctypes
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            hwnd = int(self.winId())
            rendering_policy = ctypes.c_int(1)
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy))
        except:
            pass
        
        self.config = config_manager.load_config()
        self.autostart_tools = self.config.get("autostart_tools", ["byedpi", "tor", "opera", "vless", "tgws", "ext"])
        
        self.initUI()
        
    def initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        label = QLabel(T("Выберите, какие инструменты будут запускаться\nавтоматически при старте приложения:", 
                         "Select which tools should be started\nautomatically when the application starts:"))
        layout.addWidget(label)
        
        self.cb_byedpi = QCheckBox(T("ByeDPI (Обход DPI)", "ByeDPI (DPI Bypass)"))
        self.cb_byedpi.setChecked("byedpi" in self.autostart_tools)
        layout.addWidget(self.cb_byedpi)
        
        self.cb_tor = QCheckBox(T("Tor (Для сайтов Onion и заблокированных)", "Tor (For Onion and blocked sites)"))
        self.cb_tor.setChecked("tor" in self.autostart_tools)
        layout.addWidget(self.cb_tor)
        
        self.cb_opera = QCheckBox(T("Opera Proxy (VPN)", "Opera Proxy (VPN)"))
        self.cb_opera.setChecked("opera" in self.autostart_tools)
        layout.addWidget(self.cb_opera)
        
        # self.cb_vless = QCheckBox(T("VLESS Proxy", "VLESS Proxy"))
        # self.cb_vless.setChecked("vless" in self.autostart_tools)
        # layout.addWidget(self.cb_vless)
        
        self.cb_socks = QCheckBox(T("SOCKS Reabilitator", "SOCKS Reabilitator"))
        self.cb_socks.setChecked("socks" in self.autostart_tools)
        layout.addWidget(self.cb_socks)
        
        self.cb_tgws = QCheckBox(T("Telegram WS Proxy", "Telegram WS Proxy"))
        self.cb_tgws.setChecked("tgws" in self.autostart_tools)
        self.cb_tgws.toggled.connect(self.on_tgws_toggled)
        layout.addWidget(self.cb_tgws)
        
        self.cb_proxifier = QCheckBox(T("Проксификатор (TUN / ProxyBridge)", "Proxifier (TUN / ProxyBridge)"))
        self.cb_proxifier.setChecked("proxifier" in self.autostart_tools)
        layout.addWidget(self.cb_proxifier)
        
        self.cb_ext = QCheckBox(T("Дополнительные программы", "External Programs"))
        self.cb_ext.setChecked("ext" in self.autostart_tools)
        layout.addWidget(self.cb_ext)
        
        # Adding a master checkbox for app autostart itself
        layout.addSpacing(15)
        
        self.cb_auto_last = QCheckBox(T("Подключать последний режим при запуске", "Connect Last Mode on Start"))
        self.cb_auto_last.setChecked(self.config.get("auto_connect_last_mode", False))
        layout.addWidget(self.cb_auto_last)
        
        layout.addSpacing(10)
        torrc_layout = QHBoxLayout()
        torrc_label = QLabel(T("Действие с torrc при запуске:", "Action with torrc on start:"))
        torrc_label.setStyleSheet("padding-bottom: 0px;")
        self.torrc_combo = QComboBox()
        self.torrc_combo.addItem(T("Не трогать (None)", "Do nothing (None)"), "none")
        self.torrc_combo.addItem(T("Обновлять мосты (Bridges Only)", "Update bridges (Bridges Only)"), "bridges")
        self.torrc_combo.addItem(T("Полное пересоздание (Full)", "Full recreation (Full)"), "full")
        
        # Read current state
        try:
            import sys
            cdir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(cdir, "recreate_torrc.txt"), "r") as f:
                val = f.read().strip().lower()
                if val == "true" or val == "full": self.torrc_combo.setCurrentIndex(2)
                elif val == "false" or val == "bridges": self.torrc_combo.setCurrentIndex(1)
                elif val == "none": self.torrc_combo.setCurrentIndex(0)
                else: self.torrc_combo.setCurrentIndex(1)
        except Exception:
            self.torrc_combo.setCurrentIndex(1)
            
        torrc_layout.addWidget(torrc_label)
        torrc_layout.addWidget(self.torrc_combo)
        torrc_layout.addStretch()
        layout.addLayout(torrc_layout)
        
        layout.addSpacing(15)
        self.cb_app_autostart = QCheckBox(T("Запускать приложение при старте Windows", "Start application on Windows startup"))
        self.cb_app_autostart.setChecked(self.config.get("auto_start", False))
        layout.addWidget(self.cb_app_autostart)
        
        layout.addStretch()
        
        save_btn = QPushButton(T("Сохранить", "Save"))
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
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
        # if self.cb_vless.isChecked(): tools.append("vless")
        if self.cb_socks.isChecked(): tools.append("socks")
        if self.cb_tgws.isChecked(): tools.append("tgws")
        if self.cb_proxifier.isChecked(): tools.append("proxifier")
        if self.cb_ext.isChecked(): tools.append("ext")
        
        self.config["autostart_tools"] = tools
        
        # Handle app autostart
        self.config["auto_connect_last_mode"] = self.cb_auto_last.isChecked()
        
        mode = self.torrc_combo.currentData()
        try:
            import sys
            cdir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(cdir, "recreate_torrc.txt"), "w") as f:
                f.write(mode)
        except:
            pass
            
        app_autostart = self.cb_app_autostart.isChecked()
        current_app_autostart = self.config.get("auto_start", False)
        
        if app_autostart != current_app_autostart:
            self.config["auto_start"] = app_autostart
            try:
                import auto_launcher_setuper
                if app_autostart:
                    auto_launcher_setuper.enable_auto_start("main.pyw")
                else:
                    auto_launcher_setuper.disable_auto_start()
            except Exception as e:
                QMessageBox.warning(self, T("Ошибка", "Error"), f"Failed to set autorun: {e}")
                
        config_manager.save_config(self.config)
        QMessageBox.information(self, T("Успех", "Success"), T("Настройки автозапуска сохранены.", "Autostart settings saved."))
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Simple dark theme
    app.setStyleSheet("""
        QWidget { 
            background-color: #1e1e1e; 
            color: #e0e0e0; 
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 13px; 
        }
        QLabel {
            font-size: 14px;
            font-weight: 500;
            padding-bottom: 10px;
            color: #ffffff;
        }
        QCheckBox { 
            padding: 8px; 
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid #555;
            background-color: #2d2d2d;
        }
        QCheckBox::indicator:hover {
            border: 2px solid #777;
        }
        QCheckBox::indicator:checked {
            background-color: #005FB8;
            border: 2px solid #005FB8;
            image: url(check.png); /* PyQt5 usually renders a check automatically if styled properly or without image, but we rely on its default check behavior by just coloring the background */
        }
        QComboBox {
            background-color: #2d2d2d;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 5px;
            color: white;
            min-width: 250px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: white;
            selection-background-color: #005FB8;
        }
        QPushButton { 
            background-color: #005FB8; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            font-weight: bold; 
            font-size: 14px;
            padding: 10px;
            margin-top: 10px;
        }
        QPushButton:hover { 
            background-color: #0078D4; 
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
    """)
    
    win = AutostartSettingsWindow()
    win.show()
    sys.exit(app.exec_())
