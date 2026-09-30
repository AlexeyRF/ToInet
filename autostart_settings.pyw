import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QCheckBox, QPushButton, QMessageBox, QLabel, QComboBox, QHBoxLayout
from managers import config_manager
import lang

def T(ru, en):
    return en if lang._is_en else ru

class AutostartSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("РќР°СЃС‚СЂРѕР№РєРё Р°РІС‚РѕР·Р°РїСѓСЃРєР°", "Autostart Settings"))
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
        
        label = QLabel(T("Р’С‹Р±РµСЂРёС‚Рµ, РєР°РєРёРµ РёРЅСЃС‚СЂСѓРјРµРЅС‚С‹ Р±СѓРґСѓС‚ Р·Р°РїСѓСЃРєР°С‚СЊСЃСЏ\nР°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё РїСЂРё СЃС‚Р°СЂС‚Рµ РїСЂРёР»РѕР¶РµРЅРёСЏ:", 
                         "Select which tools should be started\nautomatically when the application starts:"))
        layout.addWidget(label)
        
        self.cb_byedpi = QCheckBox(T("ByeDPI (РћР±С…РѕРґ DPI)", "ByeDPI (DPI Bypass)"))
        self.cb_byedpi.setChecked("byedpi" in self.autostart_tools)
        layout.addWidget(self.cb_byedpi)
        
        self.cb_tor = QCheckBox(T("Tor (Р”Р»СЏ СЃР°Р№С‚РѕРІ Onion Рё Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅРЅС‹С…)", "Tor (For Onion and blocked sites)"))
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
        
        self.cb_proxifier = QCheckBox(T("РџСЂРѕРєСЃРёС„РёРєР°С‚РѕСЂ (TUN / ProxyBridge)", "Proxifier (TUN / ProxyBridge)"))
        self.cb_proxifier.setChecked("proxifier" in self.autostart_tools)
        layout.addWidget(self.cb_proxifier)
        
        self.cb_ext = QCheckBox(T("Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РїСЂРѕРіСЂР°РјРјС‹", "External Programs"))
        self.cb_ext.setChecked("ext" in self.autostart_tools)
        layout.addWidget(self.cb_ext)
        
        # Adding a master checkbox for app autostart itself
        layout.addSpacing(15)
        
        self.cb_auto_last = QCheckBox(T("РџРѕРґРєР»СЋС‡Р°С‚СЊ РїРѕСЃР»РµРґРЅРёР№ СЂРµР¶РёРј РїСЂРё Р·Р°РїСѓСЃРєРµ", "Connect Last Mode on Start"))
        self.cb_auto_last.setChecked(self.config.get("auto_connect_last_mode", False))
        layout.addWidget(self.cb_auto_last)
        
        layout.addSpacing(10)
        torrc_layout = QHBoxLayout()
        torrc_label = QLabel(T("Р”РµР№СЃС‚РІРёРµ СЃ torrc РїСЂРё Р·Р°РїСѓСЃРєРµ:", "Action with torrc on start:"))
        torrc_label.setStyleSheet("padding-bottom: 0px;")
        self.torrc_combo = QComboBox()
        self.torrc_combo.addItem(T("РќРµ С‚СЂРѕРіР°С‚СЊ (None)", "Do nothing (None)"), "none")
        self.torrc_combo.addItem(T("РћР±РЅРѕРІР»СЏС‚СЊ РјРѕСЃС‚С‹ (Bridges Only)", "Update bridges (Bridges Only)"), "bridges")
        self.torrc_combo.addItem(T("РџРѕР»РЅРѕРµ РїРµСЂРµСЃРѕР·РґР°РЅРёРµ (Full)", "Full recreation (Full)"), "full")
        
        # Read current state
        self.config["recreate_torrc"] = mode
            
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
                QMessageBox.warning(self, T("РћС€РёР±РєР°", "Error"), f"Failed to set autorun: {e}")
                
        config_manager.save_config(self.config)
        QMessageBox.information(self, T("РЈСЃРїРµС…", "Success"), T("РќР°СЃС‚СЂРѕР№РєРё Р°РІС‚РѕР·Р°РїСѓСЃРєР° СЃРѕС…СЂР°РЅРµРЅС‹.", "Autostart settings saved."))
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

