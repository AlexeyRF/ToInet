import lang
import sys
import os

if getattr(sys, 'frozen', False):
    import runpy
    
    # --- РњРѕРЅРєРёРїР°С‚С‡ РґР»СЏ os.path.exists Рё os.path.isfile ---
    # РўР°Рє РєР°Рє РјС‹ РїРѕРґРјРµРЅРёР»Рё CURRENT_DIR РЅР° РїР°РїРєСѓ СЃ EXE, СЃС‚Р°РЅРґР°СЂС‚РЅС‹Рµ РїСЂРѕРІРµСЂРєРё
    # РЅР°Р»РёС‡РёСЏ Python-СЃРєСЂРёРїС‚РѕРІ Р±СѓРґСѓС‚ РїР°РґР°С‚СЊ, РїРѕС‚РѕРјСѓ С‡С‚Рѕ СЃРєСЂРёРїС‚С‹ Р»РµР¶Р°С‚ РІ _MEIPASS.
    # Р­С‚РѕС‚ РїР°С‚С‡ РіР»РѕР±Р°Р»СЊРЅРѕ С‡РёРЅРёС‚ РІСЃРµ РІС‹Р·РѕРІС‹ os.path.exists РґР»СЏ .py Рё .pyw С„Р°Р№Р»РѕРІ.
    original_exists = os.path.exists
    original_isfile = os.path.isfile
    exe_dir = os.path.dirname(sys.executable)
    
    def smart_check(path, original_func):
        if original_func(path):
            return True
        if isinstance(path, str) and path.endswith(('.py', '.pyw')):
            if path.startswith(exe_dir):
                rel = os.path.relpath(path, exe_dir)
                meipass_path = os.path.join(sys._MEIPASS, rel)
                if original_func(meipass_path):
                    return True
            meipass_path = os.path.join(sys._MEIPASS, os.path.basename(path))
            if original_func(meipass_path):
                return True
        return False

    os.path.exists = lambda p: smart_check(p, original_exists)
    os.path.isfile = lambda p: smart_check(p, original_isfile)
    # ----------------------------------------------------

    if len(sys.argv) >= 2 and sys.argv[1].endswith(('.py', '.pyw')):
        script_path = sys.argv[1]
        
        # Р•СЃР»Рё РїРµСЂРµРґР°РЅ Р°Р±СЃРѕР»СЋС‚РЅС‹Р№ РїСѓС‚СЊ, РєРѕС‚РѕСЂС‹Р№ РЅР°С‡РёРЅР°РµС‚СЃСЏ СЃ РїР°РїРєРё РїСЂРѕРіСЂР°РјРјС‹,
        # РїСЂРµРѕР±СЂР°Р·СѓРµРј РµРіРѕ РІ РѕС‚РЅРѕСЃРёС‚РµР»СЊРЅС‹Р№, С‡С‚РѕР±С‹ РЅР°Р№С‚Рё РІРЅСѓС‚СЂРё _MEIPASS
        if os.path.isabs(script_path) and script_path.startswith(exe_dir):
            rel_path = os.path.relpath(script_path, exe_dir)
            full_path = os.path.join(getattr(sys, '_MEIPASS', exe_dir), rel_path)
        else:
            # РРЅР°С‡Рµ РїСЂРѕСЃС‚Рѕ СЃРєР»РµРёРІР°РµРј (СЃСЂР°Р±РѕС‚Р°РµС‚ РґР»СЏ РѕС‚РЅРѕСЃРёС‚РµР»СЊРЅС‹С… РїСѓС‚РµР№)
            # РёР»Рё Р±РµСЂРµРј С‚РѕР»СЊРєРѕ РёРјСЏ С„Р°Р№Р»Р° РєР°Рє Р·Р°РїР°СЃРЅРѕР№ РІР°СЂРёР°РЅС‚
            base_path = getattr(sys, '_MEIPASS', exe_dir)
            full_path = os.path.join(base_path, script_path)
            if not original_exists(full_path) and os.path.isabs(script_path):
                full_path = os.path.join(base_path, os.path.basename(script_path))
                
        if not original_exists(full_path):
            full_path = script_path
            
        sys.argv = [full_path] + sys.argv[2:]
        runpy.run_path(full_path, run_name="__main__")
        sys.exit(0)
    elif len(sys.argv) >= 3 and sys.argv[1] == '-m':
        sys.exit(1)

import time
import subprocess
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton, QWidget, QWidgetAction, QHBoxLayout, QLabel, QCheckBox
from PyQt5.QtGui import QIcon, QPixmap, QCursor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject

class OutputLogger(QObject):
    log_signal = pyqtSignal(str)
    def __init__(self, original_stream):
        super().__init__()
        self.original_stream = original_stream

    def write(self, text):
        if self.original_stream:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except: pass
        self.log_signal.emit(text)

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except: pass

class AppLogWindow(QDialog):
    def __init__(self, title="Р›РѕРіРё РїСЂРёР»РѕР¶РµРЅРёСЏ", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)
        
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
        
        # Dark Theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #555;
                font-family: Consolas, monospace;
            }
            QPushButton {
                background-color: #005FB8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #0078D4;
            }
            QCheckBox {
                color: #e0e0e0;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        
        # Checkboxes for categories
        self.filter_layout = QHBoxLayout()
        self.categories = {}
        # Pre-populate known categories
        for pre_cat in ["LOG", "TOR Manager", "ByeDPI", "OperaProxy", "TGWS", "MODE"]:
            self._add_category_checkbox(pre_cat)
        self.layout.addLayout(self.filter_layout)
        
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)
        
        self.clear_btn = QPushButton(T("РћС‡РёСЃС‚РёС‚СЊ", "Clear"), self)
        self.clear_btn.clicked.connect(self.clear_logs)
        self.layout.addWidget(self.clear_btn)
        
        self.all_logs = []  # Store raw tuples of (category, text)
        self.current_category = "Other"

    def clear_logs(self):
        self.all_logs = []
        self.text_edit.clear()
        
    def _get_category(self, text):
        import re
        match = re.search(r'^\[(.*?)\]', text.strip())
        if match:
            return match.group(1)
        return None

    def _add_category_checkbox(self, cat):
        if cat not in self.categories:
            cb = QCheckBox(cat)
            cb.setChecked(True)
            cb.stateChanged.connect(self.refresh_logs)
            self.filter_layout.addWidget(cb)
            self.categories[cat] = cb

    def refresh_logs(self):
        self.text_edit.clear()
        for cat, text in self.all_logs:
            if cat == "Other" or (cat in self.categories and self.categories[cat].isChecked()):
                self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(self.text_edit.textCursor().End)

    def append_log(self, text):
        cat = self._get_category(text)
        if cat:
            self.current_category = cat
            self._add_category_checkbox(cat)
        else:
            cat = self.current_category
            
        self.all_logs.append((cat, text))
        
        # If the category is checked (or it's "Other"), append to text edit
        if cat == "Other" or (cat in self.categories and self.categories[cat].isChecked()):
            self.text_edit.moveCursor(self.text_edit.textCursor().End)
            self.text_edit.insertPlainText(text)
            self.text_edit.moveCursor(self.text_edit.textCursor().End)

app_log_window = None

def setup_logging():
    global app_log_window
    app_log_window = AppLogWindow("Р›РѕРіРё РїСЂРёР»РѕР¶РµРЅРёСЏ")
    
    sys.stdout = OutputLogger(sys.stdout)
    sys.stderr = OutputLogger(sys.stderr)
    
    sys.stdout.log_signal.connect(app_log_window.append_log)
    sys.stderr.log_signal.connect(app_log_window.append_log)
    
    print("[LOG] РЎРёСЃС‚РµРјР° Р»РѕРіРёСЂРѕРІР°РЅРёСЏ РёРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°РЅР°.")

# РРјРїРѕСЂС‚РёСЂСѓРµРј РјРµРЅРµРґР¶РµСЂС‹ Рё СѓС‚РёР»РёС‚С‹
from managers import config_manager
from tgws import manager as tgws_manager
from managers import opera_manager
from managers import vless_manager
from managers import converter_manager
from managers import mode_manager
import utils
from utils import log
from lang import T
import subprocess
from managers import bdsher
from managers import torchok
from managers import noisy_manager
from managers import tester_manager
from managers import ext_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
ICON_TITLE = "ToInet-MAX"
CACHER_SCRIPT = os.path.join(CURRENT_DIR, "cacher.pyw")

# РРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј РјРµРЅРµРґР¶РµСЂС‹
byedpi_manager = bdsher.get_manager({})
tor_manager = torchok.get_manager()
noisy_manager = noisy_manager.get_manager()
tester_manager = tester_manager.get_manager()
opera_mgr = opera_manager.get_manager()
ext_programs_manager = ext_manager.get_manager()
tgws_mgr = tgws_manager.get_manager()
conv_mgr = converter_manager.get_manager()
mode_mgr = mode_manager.get_manager()

from managers import evpn_manager
evpn_mgr = evpn_manager.get_manager()
import window_ui
main_window = None

config = config_manager.load_config()
vless_mgr = vless_manager.get_manager(config)
proxy_enabled = False
simple_mode = True  
mode_type = config.get("mode_type", "inetcpl")

# РћР±РЅРѕРІР»СЏРµРј РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ РґР»СЏ РјРµРЅРµРґР¶РµСЂРѕРІ
byedpi_manager.update_config(config)
tor_manager.update_config(config)
noisy_manager.update_config(config)
tester_manager.update_config(config)
opera_mgr.update_config(config)
tgws_mgr.update_config(config)

# РРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј РјРµРЅРµРґР¶РµСЂ РґР»СЏ pip
pip_manager = bdsher.get_pip_manager(config)

def update_proxy_status():
    global proxy_enabled
    proxy_enabled = (tor_manager.is_running() or 
                     byedpi_manager.is_running() or 
                     tgws_mgr.running or 
                     opera_mgr.is_running() or
                     mode_mgr.inetcpl_tor_active or 
                     mode_mgr.inetcpl_bd_active or 
                     evpn_mgr.is_running or
                     (mode_mgr.tun_process is not None))
    if main_window:
        main_window.update_ui_state()

def toggle_all():
    global proxy_enabled
    
    if not proxy_enabled:
        if mode_type != "evpn":
            byedpi_manager.start()
            tor_manager.start()
            opera_mgr.start()
            if not lang._is_en or config.get("enable_ru_features", False):
                tgws_mgr.start()
            
            # Р—Р°РїСѓСЃРєР°РµРј pip РїСЂРѕРєСЃРё РµСЃР»Рё РІРєР»СЋС‡РµРЅРѕ
            if config.get("byedpi_pip_enabled", False):
                if config.get("byedpi_pip_use_tor", False):
                    bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                else:
                    pip_mgr = bdsher.get_pip_manager(config)
                    pip_mgr.start()
                    bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
        
        mode_mgr.inetcpl_tor_active = False
        mode_mgr.inetcpl_bd_active = False
        mode_mgr.inetcpl_opera_active = False
        mode_mgr.inetcpl_vless_active = False
        
        if mode_type == "tun":
            mode_mgr.start_tun()
        elif mode_type == "evpn":
            tor_manager.stop()
            byedpi_manager.stop()
            opera_mgr.stop()
            vless_mgr.stop()
            tgws_mgr.stop()
            pip_manager.stop()
            bdsher.clear_pip_proxy()
            evpn_mgr.start()
        
        proxy_enabled = True
    else:
        tor_manager.stop()
        byedpi_manager.stop()
        opera_mgr.stop()
        vless_mgr.stop()
        tgws_mgr.stop()
        
        # РћСЃС‚Р°РЅРѕРІРєР° pip-РїСЂРѕРєСЃРё Рё РѕС‡РёСЃС‚РєР° РіР»РѕР±Р°Р»СЊРЅРѕРіРѕ pip
        pip_manager.stop()
        bdsher.clear_pip_proxy()
        
        if mode_mgr.inetcpl_tor_active:
            mode_mgr.run_cpller(9853, 0)
            mode_mgr.inetcpl_tor_active = False
        if mode_mgr.inetcpl_bd_active:
            mode_mgr.run_cpller(1780, 0)
            mode_mgr.inetcpl_bd_active = False
        if mode_mgr.inetcpl_opera_active:
            mode_mgr.run_cpller(1785, 0)
            mode_mgr.inetcpl_opera_active = False
        if mode_mgr.inetcpl_vless_active:
            mode_mgr.run_cpller(1790, 0)
            mode_mgr.inetcpl_vless_active = False
        
        if mode_type == "tun":
            mode_mgr.stop_tun()
        elif mode_type == "evpn":
            evpn_mgr.stop()
        
        proxy_enabled = False
    
    update_menu()

def toggle_tor():
    if not tor_manager.is_running():
        tor_manager.start()
    else:
        tor_manager.stop()
    update_proxy_status()
    update_menu()

def toggle_byedpi():
    if not byedpi_manager.is_running():
        byedpi_manager.start()
    else:
        byedpi_manager.stop()
    update_proxy_status()
    update_menu()

def toggle_vless():
    if not vless_mgr.is_running():
        vless_mgr.start()
    else:
        vless_mgr.stop()
    update_proxy_status()
    update_menu()
    
def toggle_opera():
    if not opera_mgr.is_running():
        opera_mgr.start()
    else:
        opera_mgr.stop()
    update_proxy_status()
    update_menu()

def toggle_tgws():
    if not tgws_mgr.running:
        tgws_mgr.start()
    else:
        tgws_mgr.stop()
    update_proxy_status()
    update_menu()

def toggle_noisy():
    if not noisy_manager.is_running():
        noisy_manager.start()
    else:
        noisy_manager.stop()
    update_menu()

def toggle_tester():
    if not tester_manager.is_running():
        tester_manager.start()
    else:
        tester_manager.stop()
    update_menu()

def toggle_proxifier():
    if not mode_mgr.tun_running():
        mode_mgr.start_tun()
    else:
        mode_mgr.stop_tun()
    update_proxy_status()
    update_menu()

def toggle_inetcpl_tor():
    if not mode_mgr.inetcpl_tor_active:

        if mode_mgr.inetcpl_vless_active:
            if mode_mgr.run_cpller(1790, 0):
                mode_mgr.inetcpl_vless_active = False
        if mode_mgr.inetcpl_bd_active:
            if mode_mgr.run_cpller(1780, 0):
                mode_mgr.inetcpl_bd_active = False
        if mode_mgr.inetcpl_opera_active:
            if mode_mgr.run_cpller(1785, 0):
                mode_mgr.inetcpl_opera_active = False
        
        if mode_mgr.run_cpller(9853, 1):
            mode_mgr.inetcpl_tor_active = True
    else:
        if mode_mgr.run_cpller(9853, 0):
            mode_mgr.inetcpl_tor_active = False
    
    update_proxy_status()
    update_menu()

def toggle_inetcpl_bd():
    if not mode_mgr.inetcpl_bd_active:

        if mode_mgr.inetcpl_vless_active:
            if mode_mgr.run_cpller(1790, 0):
                mode_mgr.inetcpl_vless_active = False
        if mode_mgr.inetcpl_tor_active:
            if mode_mgr.run_cpller(9853, 0):
                mode_mgr.inetcpl_tor_active = False
        if mode_mgr.inetcpl_opera_active:
            if mode_mgr.run_cpller(1785, 0):
                mode_mgr.inetcpl_opera_active = False
        
        if mode_mgr.run_cpller(1780, 1):
            mode_mgr.inetcpl_bd_active = True
    else:
        if mode_mgr.run_cpller(1780, 0):
            mode_mgr.inetcpl_bd_active = False
    
    update_proxy_status()
    update_menu()

def toggle_inetcpl_vless():
    if not mode_mgr.inetcpl_vless_active:
        if mode_mgr.inetcpl_tor_active:
            if mode_mgr.run_cpller(9853, 0):
                mode_mgr.inetcpl_tor_active = False
        if mode_mgr.inetcpl_bd_active:
            if mode_mgr.run_cpller(1780, 0):
                mode_mgr.inetcpl_bd_active = False
        if mode_mgr.inetcpl_opera_active:
            if mode_mgr.run_cpller(1785, 0):
                mode_mgr.inetcpl_opera_active = False
        
        if mode_mgr.run_cpller(1790, 1):
            mode_mgr.inetcpl_vless_active = True
    else:
        if mode_mgr.run_cpller(1790, 0):
            mode_mgr.inetcpl_vless_active = False
    
    update_proxy_status()
    update_menu()

def toggle_inetcpl_opera():
    if not mode_mgr.inetcpl_opera_active:

        if mode_mgr.inetcpl_vless_active:
            if mode_mgr.run_cpller(1790, 0):
                mode_mgr.inetcpl_vless_active = False
        if mode_mgr.inetcpl_tor_active:
            if mode_mgr.run_cpller(9853, 0):
                mode_mgr.inetcpl_tor_active = False
        if mode_mgr.inetcpl_bd_active:
            if mode_mgr.run_cpller(1780, 0):
                mode_mgr.inetcpl_bd_active = False
        
        if mode_mgr.run_cpller(1785, 1):
            mode_mgr.inetcpl_opera_active = True
    else:
        if mode_mgr.run_cpller(1785, 0):
            mode_mgr.inetcpl_opera_active = False
    
    update_proxy_status()
    update_menu()

def toggle_singbox_tun(port, ptype="socks"):
    if mode_mgr.tun_proxy_port == port:
        mode_mgr.tun_proxy_port = 0
        if mode_type == "tun":
            mode_mgr.stop_tun()
    else:
        if mode_type == "tun":
            mode_mgr.set_singbox_tun_proxy(port, ptype)
        else:
            mode_mgr.tun_proxy_port = port
            mode_mgr.tun_proxy_type = ptype
    update_proxy_status()
    update_menu()

def toggle_singbox_tun_tor():
    toggle_singbox_tun(9853)

def toggle_singbox_tun_bd():
    toggle_singbox_tun(1780)

def toggle_singbox_tun_opera():
    toggle_singbox_tun(1785)

def set_mode_type(mode):
    global mode_type, config, proxy_enabled

    if mode == mode_type:
        return

    if mode_type == "inetcpl" and mode != "inetcpl":
        mode_mgr.reset_inetcpl_proxy()

    if mode_type == "tun" and mode != "tun":
        mode_mgr.stop_tun()
        
    if mode_type == "evpn" and mode != "evpn":
        evpn_mgr.stop()

    if mode == "tun":
        path = mode_mgr.get_tun_app_path()
        if not path or not os.path.exists(path):
            QMessageBox.warning(None, T("TUN СЂРµР¶РёРј", "TUN Mode"), T("РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ РєРѕСЂСЂРµРєС‚РЅС‹Р№ РїСѓС‚СЊ Рє РїСЂРѕРєСЃРёС„РёРєР°С‚РѕСЂСѓ РІ С„Р°Р№Р»Рµ proxification_app.txt!", "Please specify correct path to proxifier in proxification_app.txt first!"))
            update_menu()
            return
        if proxy_enabled:
            mode_mgr.start_tun()
            
    if mode == "evpn":
        if proxy_enabled:
            tor_manager.stop()
            byedpi_manager.stop()
            opera_mgr.stop()
            vless_mgr.stop()
            tgws_mgr.stop()
            pip_manager.stop()
            bdsher.clear_pip_proxy()
            evpn_mgr.start()

    mode_type = mode
    config["mode_type"] = mode
    config_manager.save_config(config)
    
    update_proxy_status()
    update_menu()

def toggle_inetcpl_mode():
    global config
    current = config.get("inetcpl_mode", "classic")
    config["inetcpl_mode"] = "modern" if current == "classic" else "classic"
    config_manager.save_config(config)
    update_menu()


def toggle_mode():
    global simple_mode
    simple_mode = not simple_mode
    update_menu()

def toggle_auto_start():
    try:
        import auto_launcher_setuper
        current_state = config.get("auto_start", False)
        if not current_state:
            auto_launcher_setuper.enable_auto_start(os.path.basename(__file__))
            config["auto_start"] = True
        else:
            auto_launcher_setuper.disable_auto_start()
            config["auto_start"] = False
        config_manager.save_config(config)
        update_menu()
    except Exception as e:
        log(f"РћС€РёР±РєР° РЅР°СЃС‚СЂРѕР№РєРё Р°РІС‚РѕР·Р°РїСѓСЃРєР°: {e}")
        QMessageBox.critical(None, T("РћС€РёР±РєР°", "Error"), f"РќРµ СѓРґР°Р»РѕСЃСЊ РЅР°СЃС‚СЂРѕРёС‚СЊ Р°РІС‚РѕР·Р°РїСѓСЃРє:\n{e}")

def toggle_auto_connect_last_mode():
    config["auto_connect_last_mode"] = not config.get("auto_connect_last_mode", False)
    config_manager.save_config(config)
    update_menu()

def set_dns(mode):
    import ctypes
    
    if mode == "comms":
        cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('83.220.169.155', '212.109.195.93')"
        msg = T("Р—Р°РїСЂРѕСЃ РЅР° СѓСЃС‚Р°РЅРѕРІРєСѓ Comms DNS РѕС‚РїСЂР°РІР»РµРЅ. РџРѕРґС‚РІРµСЂРґРёС‚Рµ РїСЂР°РІР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°.", "Request to set Comms DNS sent. Please confirm admin rights.")
    elif mode == "xbox":
        if not lang._is_en or config.get("enable_ru_features", False):
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.54', '111.88.96.55')"
        else:
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.50', '111.88.96.51')"
        msg = T("Р—Р°РїСЂРѕСЃ РЅР° СѓСЃС‚Р°РЅРѕРІРєСѓ Xbox DNS РѕС‚РїСЂР°РІР»РµРЅ. РџРѕРґС‚РІРµСЂРґРёС‚Рµ РїСЂР°РІР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°.", "Request to set Xbox DNS sent. Please confirm admin rights.")
    elif mode == "xbox_ipv6":
        if not lang._is_en or config.get("enable_ru_features", False):
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.54', '111.88.96.55', '2a00:ab00:1233:26::54', '2a00:ab00:1233:26::55')"
        else:
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.50', '111.88.96.51', '2a00:ab00:1233:26::50', '2a00:ab00:1233:26::51')"
        msg = T("Р—Р°РїСЂРѕСЃ РЅР° СѓСЃС‚Р°РЅРѕРІРєСѓ Xbox DNS (СЃ IPv6) РѕС‚РїСЂР°РІР»РµРЅ. РџРѕРґС‚РІРµСЂРґРёС‚Рµ РїСЂР°РІР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°.", "Request to set Xbox DNS (with IPv6) sent. Please confirm admin rights.")
    elif mode == "reset":
        cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ResetServerAddresses"
        msg = T("Р—Р°РїСЂРѕСЃ РЅР° СЃР±СЂРѕСЃ DNS РѕС‚РїСЂР°РІР»РµРЅ. РџРѕРґС‚РІРµСЂРґРёС‚Рµ РїСЂР°РІР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°.", "Request to reset DNS sent. Please confirm admin rights.")
    else:
        return
        
    cmd += "; Clear-DnsClientCache"

    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", f"-NoProfile -WindowStyle Hidden -Command \"{cmd}\"", None, 0)
    
    if ret <= 32:
        QMessageBox.warning(None, T("РћС€РёР±РєР°", "Error"), T("РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ РїСЂР°РІР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР° РґР»СЏ РёР·РјРµРЅРµРЅРёСЏ DNS.", "Failed to get admin rights to change DNS."))
    else:
        QMessageBox.information(None, T("РЈСЃРїРµС…", "Success"), msg)

def restart_app():
    tor_manager.stop()
    byedpi_manager.stop()
    opera_mgr.stop()
    vless_mgr.stop()
    
    # РћСЃС‚Р°РЅРѕРІРєР° pip-РїСЂРѕРєСЃРё Рё РѕС‡РёСЃС‚РєР° РіР»РѕР±Р°Р»СЊРЅРѕРіРѕ pip
    pip_mgr = bdsher.get_pip_manager()
    pip_mgr.stop()
    bdsher.clear_pip_proxy()
    
    noisy_manager.stop()
    tester_manager.stop()
    ext_programs_manager.stop_all()
    mode_mgr.stop_tun()
    tgws_mgr.stop()
    evpn_mgr.stop()
    # conv_mgr.stop()
    mode_mgr.reset_inetcpl_proxy()
    log("Restarting...")
    
    import subprocess
    import os
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable] + sys.argv[1:])
    else:
        subprocess.Popen([sys.executable, os.path.abspath(__file__)] + sys.argv[1:])
        
    app.quit()

def exit_app():
    tor_manager.stop()
    byedpi_manager.stop()
    opera_mgr.stop()
    vless_mgr.stop()
    
    # РћСЃС‚Р°РЅРѕРІРєР° pip-РїСЂРѕРєСЃРё Рё РѕС‡РёСЃС‚РєР° РіР»РѕР±Р°Р»СЊРЅРѕРіРѕ pip
    pip_mgr = bdsher.get_pip_manager()
    pip_mgr.stop()
    bdsher.clear_pip_proxy()
    
    noisy_manager.stop()
    tester_manager.stop()
    ext_programs_manager.stop_all()
    mode_mgr.stop_tun()
    tgws_mgr.stop()
    evpn_mgr.stop()
    # conv_mgr.stop()
    mode_mgr.reset_inetcpl_proxy()
    log("Exiting...")
    app.quit()

tray = None
tray_menu = None

def run_agy_fix():
    try:
        import utils
        utils.run_script("agy_fix.pyw")
    except:
        pass

class MenuUpdater(QObject):
    update_signal = pyqtSignal()

menu_updater = MenuUpdater()

def _safe_update():
    QTimer.singleShot(0, _update_menu_impl)

menu_updater.update_signal.connect(_safe_update, Qt.QueuedConnection)

def update_menu():
    menu_updater.update_signal.emit()

def _update_menu_impl():
    try:
        _update_menu_impl_unsafe()
    except Exception as e:
        log(f"[Menu] FATAL ERROR in menu generation: {e}")
        import traceback
        traceback.print_exc()


class MenuServiceWidget(QWidget):
    def __init__(self, toggle_func, menu):
        super().__init__()
        self.toggle_func = toggle_func
        self.menu = menu
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if not isinstance(child, QPushButton):
                self.menu.hide()
                self.toggle_func()
                update_menu()
        super().mouseReleaseEvent(event)

def create_service_action(menu, name, is_running, toggle_func, restart_func=None, is_tor=False):
    wa = QWidgetAction(menu)
    w = MenuServiceWidget(toggle_func, menu)
    w.setStyleSheet("""
        QWidget { background: transparent; }
        QWidget:hover { background: rgba(255, 255, 255, 0.05); }
        QLabel { padding-left: 5px; font-size: 14px; color: white; }
        QPushButton { 
            background: transparent; 
            border: none; 
            font-size: 16px; 
            font-weight: bold;
            color: white;
        }
        QPushButton:hover { background: rgba(255, 255, 255, 0.1); border-radius: 3px; }
    """)
    
    l = QHBoxLayout(w)
    l.setContentsMargins(5, 2, 5, 2)
    l.setSpacing(5)
    
    lbl = QLabel(name)
    l.addWidget(lbl)
    
    l.addStretch()
    
    def make_btn(text, tooltip, callback):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(24, 24)
        btn.setCursor(Qt.PointingHandCursor)
        def on_click():
            menu.hide()
            callback()
            update_menu()
        btn.clicked.connect(on_click)
        return btn

    if is_running and restart_func:
        if is_tor:
            def tor_restart_handler():
                mods = QApplication.keyboardModifiers()
                if mods & Qt.ControlModifier:
                    tor_manager.new_circuit()
                else:
                    restart_func()
            btn_restart = make_btn("в†»", T("РџРµСЂРµР·Р°РїСѓСЃРє (Ctrl + РљР»РёРє = РќРѕРІР°СЏ С†РµРїСЊ)", "Restart (Ctrl + Click = New Circuit)"), tor_restart_handler)
        else:
            btn_restart = make_btn("в†»", T("РџРµСЂРµР·Р°РїСѓСЃС‚РёС‚СЊ", "Restart"), restart_func)
        l.addWidget(btn_restart)
        
    play_stop_text = "в– " if is_running else "в–¶"
    play_stop_color = "#ff5555" if is_running else "#55ff55"
    
    btn_play = make_btn(play_stop_text, T("РћСЃС‚Р°РЅРѕРІРёС‚СЊ", "Stop") if is_running else T("Р—Р°РїСѓСЃС‚РёС‚СЊ", "Start"), toggle_func)
    btn_play.setStyleSheet(f"QPushButton {{ color: {play_stop_color}; }} QPushButton:hover {{ background: rgba(255, 255, 255, 0.1); }}")
    l.addWidget(btn_play)
    
    wa.setDefaultWidget(w)
    return wa

def _update_menu_impl_unsafe():
    global tray_menu
    if tray_menu is None: return
    tray_menu.clear()
    
    if simple_mode:
        log('[Menu] Building simple mode menu')
        all_act = QAction(T("Р—Р°РїСѓСЃРє", "Start") if not proxy_enabled else T("РћСЃС‚Р°РЅРѕРІРёС‚СЊ РІСЃС‘", "Stop All"), tray_menu)
        all_act.triggered.connect(toggle_all)
        tray_menu.addAction(all_act)
        
        if mode_type == "inetcpl":
            tor_cpl = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє TOR", "Connect to TOR") if not mode_mgr.inetcpl_tor_active else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ TOR", "Disconnect from TOR"), tray_menu)
            tor_cpl.triggered.connect(toggle_inetcpl_tor)
            tray_menu.addAction(tor_cpl)
            
            bd_cpl = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє BD", "Connect to BD") if not mode_mgr.inetcpl_bd_active else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ BD", "Disconnect from BD"), tray_menu)
            bd_cpl.triggered.connect(toggle_inetcpl_bd)
            tray_menu.addAction(bd_cpl)
            
            opera_cpl = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє Opera", "Connect to Opera") if not mode_mgr.inetcpl_opera_active else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ Opera", "Disconnect from Opera"), tray_menu)
            opera_cpl.triggered.connect(toggle_inetcpl_opera)
            tray_menu.addAction(opera_cpl)            

        elif mode_type == "tun" and not mode_mgr.get_tun_app_path():
            tor_tun = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє TOR (TUN)", "Connect to TOR (TUN)") if mode_mgr.tun_proxy_port != 9853 else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ TOR (TUN)", "Disconnect from TOR (TUN)"), tray_menu)
            tor_tun.triggered.connect(toggle_singbox_tun_tor)
            tray_menu.addAction(tor_tun)
            
            bd_tun = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє BD (TUN)", "Connect to BD (TUN)") if mode_mgr.tun_proxy_port != 1780 else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ BD (TUN)", "Disconnect from BD (TUN)"), tray_menu)
            bd_tun.triggered.connect(toggle_singbox_tun_bd)
            tray_menu.addAction(bd_tun)
            
            opera_tun = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє Opera (TUN)", "Connect to Opera (TUN)") if mode_mgr.tun_proxy_port != 1785 else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ Opera (TUN)", "Disconnect from Opera (TUN)"), tray_menu)
            opera_tun.triggered.connect(toggle_singbox_tun_opera)
            tray_menu.addAction(opera_tun)
            
            adv_tun_simp = QAction(T("РџСЂРѕРґРІРёРЅСѓС‚С‹Рµ РЅР°СЃС‚СЂРѕР№РєРё TUN", "Advanced TUN Settings"), tray_menu)
            adv_tun_simp.triggered.connect(mode_mgr.open_advanced_tun_config)
            tray_menu.addAction(adv_tun_simp)
       
        tray_menu.addSeparator()
        mode_m = QMenu(T("Р РµР¶РёРј", "Mode"), tray_menu)
        for m in ["empty", "inetcpl", "tun", "evpn"]:
            act = QAction(m.capitalize() + (" СЂРµР¶РёРј" if m=="tun" or m=="evpn" else ""), mode_m)
            act.setCheckable(True)
            act.setChecked(mode_type == m)
            act.triggered.connect(lambda checked, mode=m: set_mode_type(mode))
            mode_m.addAction(act)
        tray_menu.addMenu(mode_m)
        tray_menu.addSeparator()
        
        set_act = QAction(T("РќР°СЃС‚СЂРѕР№РєРё", "Settings"), tray_menu); set_act.triggered.connect(toggle_mode); tray_menu.addAction(set_act)
        restart_act = QAction(T("РџРµСЂРµР·Р°РїСѓСЃРє", "Restart"), tray_menu); restart_act.triggered.connect(restart_app); tray_menu.addAction(restart_act)
        exit_act = QAction(T("Р’С‹С…РѕРґ", "Exit"), tray_menu); exit_act.triggered.connect(exit_app); tray_menu.addAction(exit_act)
    else:
        log('[Menu] Building advanced mode menu')
        # РџСЂРѕРґРІРёРЅСѓС‚С‹Р№ СЂРµР¶РёРј
        
        # 1. РЈРїСЂР°РІР»РµРЅРёРµ РєРѕРјРїРѕРЅРµРЅС‚Р°РјРё
        control_menu = QMenu(T("РЈРїСЂР°РІР»РµРЅРёРµ РєРѕРјРїРѕРЅРµРЅС‚Р°РјРё", "Service Control"), tray_menu)
        
        tor_wa = create_service_action(control_menu, "TOR", tor_manager.is_running(), toggle_tor, tor_manager.restart, is_tor=True)
        control_menu.addAction(tor_wa)
        
        bd_wa = create_service_action(control_menu, "ByeDPI", byedpi_manager.is_running(), toggle_byedpi, lambda: (byedpi_manager.stop(), time.sleep(1), byedpi_manager.start()))
        control_menu.addAction(bd_wa)
        
        # def vless_restart_handler():
        #     mods = QApplication.keyboardModifiers()
        #     if mods & Qt.ControlModifier:
        #         vless_mgr.rot_cmd = "keep"
        #     elif mods & Qt.ShiftModifier:
        #         vless_mgr.rot_cmd = "prev"
        #     else:
        #         vless_mgr.rot_cmd = "next"
        #     vless_mgr.stop()
        #     time.sleep(1)
        #     vless_mgr.start()
        #     
        # def vless_toggle_handler():
        #     mods = QApplication.keyboardModifiers()
        #     if not vless_mgr.is_running():
        #         if mods & Qt.ControlModifier:
        #             vless_mgr.rot_cmd = "keep"
        #         elif mods & Qt.ShiftModifier:
        #             vless_mgr.rot_cmd = "prev"
        #         else:
        #             vless_mgr.rot_cmd = "next"
        #         vless_mgr.start()
        #     else:
        #         vless_mgr.stop()
        #     update_proxy_status()
        #     update_menu()
        # 
        # vless_wa = create_service_action(control_menu, "VLESS Proxy", vless_mgr.is_running(), vless_toggle_handler, vless_restart_handler)
        # control_menu.addAction(vless_wa)
        
        opera_wa = create_service_action(control_menu, "Opera Proxy", opera_mgr.is_running(), toggle_opera, lambda: (opera_mgr.stop(), time.sleep(1), opera_mgr.start()))
        control_menu.addAction(opera_wa)
        
        if not lang._is_en or config.get("enable_ru_features", False):
            tg_wa = create_service_action(control_menu, "TGWS", tgws_mgr.running, toggle_tgws, lambda: (tgws_mgr.stop(), time.sleep(1), tgws_mgr.start()))
            control_menu.addAction(tg_wa)
            
        tun_wa = create_service_action(control_menu, T("РџСЂРѕРєСЃРёС„РёРєР°С‚РѕСЂ", "Proxifier"), mode_mgr.tun_running(), toggle_proxifier, mode_mgr.restart_tun)
        control_menu.addAction(tun_wa)
        
        def toggle_ext():
            if ext_programs_manager.is_running():
                ext_programs_manager.stop_all()
            else:
                ext_programs_manager.start_all()
        ext_wa = create_service_action(control_menu, T("Р”РѕРї. РџСЂРѕРіСЂР°РјРјС‹", "Ext. Programs"), ext_programs_manager.is_running(), toggle_ext, ext_programs_manager.restart_all)
        control_menu.addAction(ext_wa)
        tray_menu.addMenu(control_menu)
        
        # 2. РќР°СЃС‚СЂРѕР№РєРё РљРѕРјРїРѕРЅРµРЅС‚РѕРІ
        settings_menu = QMenu(T("РќР°СЃС‚СЂРѕР№РєРё РєРѕРјРїРѕРЅРµРЅС‚РѕРІ", "Component Settings"), tray_menu)
        settings_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєРё TOR", "TOR Settings"), tor_manager.open_settings)
        
        settings_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєРё BD", "BD Settings"), byedpi_manager.open_settings)
        # settings_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєРё VLESS", "VLESS Settings"), lambda: utils.run_script("evpn/vless_settings.pyw"))
        # settings_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєРё Opera Proxy", "Opera Proxy Settings"), opera_mgr.open_settings)
        
        

        
        if not lang._is_en or config.get("enable_ru_features", False):
            settings_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєРё TGWS Proxy", "TGWS Proxy Settings"), lambda: utils.run_script("tgws/settings.pyw"))
            
        settings_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєР° РџСЂРѕРєСЃРёС„РёРєР°С‚РѕСЂР°", "Configure Proxifier"), mode_mgr.open_proxifier_config)
        settings_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєР° РґРѕРї. РїСЂРѕРіСЂР°РјРј", "Configure Ext. Programs"), ext_programs_manager.open_config)
        tray_menu.addMenu(settings_menu)
        
        
        # 4. Р”РѕР±Р°РІРёС‚СЊ РІ Telegram
        tg_menu = QMenu(T("Р”РѕР±Р°РІРёС‚СЊ РІ Telegram", "Telegram Integration"), tray_menu)
        if not lang._is_en or config.get("enable_ru_features", False):
            tg_menu.addAction(T("Р”РѕР±Р°РІРёС‚СЊ TGWS SOCKS5 (1480) РІ Telegram", "Add TGWS SOCKS5 (1480) to Telegram"), lambda: utils.add_proxy_to_telegram(config.get("tgws_port", 1480)))
            tg_menu.addAction(T("Р”РѕР±Р°РІРёС‚СЊ TGWS MTProto (1480) РІ Telegram", "Add TGWS MTProto (1480) to Telegram"), lambda: utils.add_mtproto_to_telegram(config.get("tgws_port", 1480), config.get("tgws_secret", "0"*32), config.get("tgws_fake_tls", "")))
            tg_menu.addAction(T("Р”РѕР±Р°РІРёС‚СЊ РЁР»СЋР· Gatik (1777) РІ Telegram", "Add Smart Router (1777) to Telegram"), lambda: utils.add_proxy_to_telegram(1777))
        tg_menu.addAction(T("Р”РѕР±Р°РІРёС‚СЊ TOR (9853) РІ Telegram", "Add TOR (9853) to Telegram"), lambda: utils.add_proxy_to_telegram(9853))
        tg_menu.addAction(T("Р”РѕР±Р°РІРёС‚СЊ BD (1780) РІ Telegram", "Add BD (1780) to Telegram"), lambda: utils.add_proxy_to_telegram(1780))
        # tg_menu.addAction(T("Р”РѕР±Р°РІРёС‚СЊ VLESS (1790) РІ Telegram", "Add VLESS (1790) to Telegram"), lambda: utils.add_proxy_to_telegram(1790))
        tray_menu.addMenu(tg_menu)
        

        
        # 5. РџСЂРѕРєСЃРёСЂРѕРІР°РЅРёРµ pip
        pip_menu = QMenu(T("РџСЂРѕРєСЃРёСЂРѕРІР°РЅРёРµ pip (PyPI)", "pip (PyPI) Proxying"), tray_menu)
        
        pip_enabled_act = QAction(T("Р’РєР»СЋС‡РёС‚СЊ РїСЂРѕРєСЃРёСЂРѕРІР°РЅРёРµ pip", "Enable pip Proxying"), pip_menu)
        pip_enabled_act.setCheckable(True)
        pip_enabled_act.setChecked(config.get("byedpi_pip_enabled", False))
        
        pip_use_tor_act = QAction(T("РСЃРїРѕР»СЊР·РѕРІР°С‚СЊ TOR РІРјРµСЃС‚Рѕ ByeDPI", "Use TOR Instead of ByeDPI"), pip_menu)
        pip_use_tor_act.setCheckable(True)
        pip_use_tor_act.setChecked(config.get("byedpi_pip_use_tor", False))
        pip_use_tor_act.setEnabled(config.get("byedpi_pip_enabled", False))
        
        def toggle_pip_enabled():
            config["byedpi_pip_enabled"] = not config.get("byedpi_pip_enabled", False)
            config_manager.save_config(config)
            
            if proxy_enabled:
                pip_mgr = bdsher.get_pip_manager(config)
                if config["byedpi_pip_enabled"]:
                    if config.get("byedpi_pip_use_tor", False):
                        pip_mgr.stop()
                        bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                    else:
                        pip_mgr.start()
                        bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
                else:
                    pip_mgr.stop()
                    bdsher.clear_pip_proxy()
            update_menu()
            
        def toggle_pip_use_tor():
            config["byedpi_pip_use_tor"] = not config.get("byedpi_pip_use_tor", False)
            config_manager.save_config(config)
            
            if proxy_enabled and config.get("byedpi_pip_enabled", False):
                pip_mgr = bdsher.get_pip_manager(config)
                if config["byedpi_pip_use_tor"]:
                    pip_mgr.stop()
                    bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                else:
                    pip_mgr.start()
                    bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
            update_menu()
            
        pip_enabled_act.triggered.connect(toggle_pip_enabled)
        pip_use_tor_act.triggered.connect(toggle_pip_use_tor)
        
        pip_menu.addAction(pip_enabled_act)
        pip_menu.addAction(pip_use_tor_act)
        pip_menu.addAction(T("РќР°СЃС‚СЂРѕР№РєРё ByeDPI РґР»СЏ pip", "ByeDPI Settings for pip"), lambda: bdsher.get_pip_manager(config).open_settings())
        
        # 6. РЎРёСЃС‚РµРјРЅС‹Рµ РѕРїС†РёРё

        # РЈР·РєРѕРЅР°РїСЂР°РІР»РµРЅРЅРѕРµ
        log('[Menu] Building narrow_menu')
        narrow_menu = QMenu(T("РЈР·РєРѕРЅР°РїСЂР°РІР»РµРЅРЅРѕРµ", "Narrow-focused"), tray_menu)

        narrow_menu.addAction(T("Р РµР°Р±РёР»РёС‚Р°С‚РѕСЂ SOCKS", "Rehabilitate SOCKS"), lambda: utils.run_script("socks-reabilitator.pyw"))

        if not lang._is_en or config.get("enable_ru_features", False):

            noisy_act = QAction(noisy_manager.get_status_text(), narrow_menu); noisy_act.triggered.connect(toggle_noisy); narrow_menu.addAction(noisy_act)

            tester_act = QAction(tester_manager.get_status_text(), narrow_menu); tester_act.triggered.connect(toggle_tester); narrow_menu.addAction(tester_act)

        tray_menu.addMenu(narrow_menu)

        log('[Menu] Building sys_menu')
        sys_menu = QMenu(T("РЎРёСЃС‚РµРјРЅС‹Рµ РѕРїС†РёРё", "System Options"), tray_menu)
        sys_menu.addSeparator()
        
        inetcpl_sub = QMenu(T("РќР°СЃС‚СЂРѕР№РєРё Inetcpl", "Inetcpl Settings"), sys_menu)

        tor_cpl2 = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє TOR (Inetcpl)", "Connect to TOR (Inetcpl)") if not mode_mgr.inetcpl_tor_active else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ TOR (Inetcpl)", "Disconnect from TOR (Inetcpl)"), inetcpl_sub)
        tor_cpl2.triggered.connect(toggle_inetcpl_tor)
        inetcpl_sub.addAction(tor_cpl2)
        
        bd_cpl2 = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє BD (Inetcpl)", "Connect to BD (Inetcpl)") if not mode_mgr.inetcpl_bd_active else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ BD (Inetcpl)", "Disconnect from BD (Inetcpl)"), inetcpl_sub)
        bd_cpl2.triggered.connect(toggle_inetcpl_bd)
        inetcpl_sub.addAction(bd_cpl2)
        
        opera_cpl2 = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє Opera (Inetcpl)", "Connect to Opera (Inetcpl)") if not mode_mgr.inetcpl_opera_active else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ Opera (Inetcpl)", "Disconnect from Opera (Inetcpl)"), inetcpl_sub)
        opera_cpl2.triggered.connect(toggle_inetcpl_opera)
        inetcpl_sub.addAction(opera_cpl2)        
        # vless_cpl2 = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє VLESS (Inetcpl)", "Connect to VLESS (Inetcpl)") if not mode_mgr.inetcpl_vless_active else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ VLESS (Inetcpl)", "Disconnect from VLESS (Inetcpl)"), inetcpl_sub)
        # vless_cpl2.triggered.connect(toggle_inetcpl_vless)
        # inetcpl_sub.addAction(vless_cpl2)

        inetcpl_mode = config.get("inetcpl_mode", "classic")
        inetcpl_mode_txt = T("Inetcpl: Р РµР¶РёРј Classic (РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ)", "Inetcpl: Classic Mode (Default)") if inetcpl_mode == "classic" else T("Inetcpl: Р РµР¶РёРј Modern (РњРѕСЃС‚С‹)", "Inetcpl: Modern Mode (Bridges)")
        inetcpl_mode_act = QAction(inetcpl_mode_txt, inetcpl_sub); inetcpl_mode_act.triggered.connect(toggle_inetcpl_mode); inetcpl_sub.addAction(inetcpl_mode_act)
        
        sys_menu.addMenu(inetcpl_sub)
        
        tun_sub = QMenu(T("РќР°СЃС‚СЂРѕР№РєРё TUN", "TUN Settings"), sys_menu)
        tor_tun2 = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє TOR (TUN)", "Connect to TOR (TUN)") if mode_mgr.tun_proxy_port != 9853 else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ TOR (TUN)", "Disconnect from TOR (TUN)"), tun_sub)
        tor_tun2.triggered.connect(toggle_singbox_tun_tor)
        tun_sub.addAction(tor_tun2)
        
        bd_tun2 = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє BD (TUN)", "Connect to BD (TUN)") if mode_mgr.tun_proxy_port != 1780 else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ BD (TUN)", "Disconnect from BD (TUN)"), tun_sub)
        bd_tun2.triggered.connect(toggle_singbox_tun_bd)
        tun_sub.addAction(bd_tun2)
        
        opera_tun2 = QAction(T("РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє Opera (TUN)", "Connect to Opera (TUN)") if mode_mgr.tun_proxy_port != 1785 else T("РћС‚РєР»СЋС‡РёС‚СЊСЃСЏ РѕС‚ Opera (TUN)", "Disconnect from Opera (TUN)"), tun_sub)
        opera_tun2.triggered.connect(toggle_singbox_tun_opera)
        tun_sub.addAction(opera_tun2)
        
        tun_sub.addSeparator()
        adv_tun_act = QAction(T("РџСЂРѕРґРІРёРЅСѓС‚С‹Рµ РЅР°СЃС‚СЂРѕР№РєРё TUN", "Advanced TUN Settings"), tun_sub)
        adv_tun_act.triggered.connect(mode_mgr.open_advanced_tun_config)
        tun_sub.addAction(adv_tun_act)
        
        sys_menu.addMenu(tun_sub)

        sys_menu.addSeparator()
        
        app_logs_act = QAction(T("РџРѕРєР°Р·Р°С‚СЊ Р»РѕРіРё РїСЂРёР»РѕР¶РµРЅРёСЏ", "Show Application Logs"), sys_menu)
        app_logs_act.triggered.connect(lambda: app_log_window.show() if app_log_window else None)
        sys_menu.addAction(app_logs_act)
        
        ast_act = QAction(T("РќР°СЃС‚СЂРѕР№РєРё Р°РІС‚РѕР·Р°РїСѓСЃРєР°", "Autostart Settings"), sys_menu)
        ast_act.triggered.connect(lambda: subprocess.Popen([sys.executable, os.path.join(CURRENT_DIR, "autostart_settings.pyw")], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        sys_menu.addAction(ast_act)
        sys_menu.addAction(T("РћС‡РёСЃС‚РєР° РєРµС€Р°", "Clear Cache"), lambda: utils.run_script(CACHER_SCRIPT))
        sys_menu.addAction(T("РћС‚РєСЂС‹С‚СЊ РїР°РїРєСѓ РїСЂРѕРµРєС‚Р°", "Open Project Folder"), lambda: utils.open_project_folder(CURRENT_DIR))
        sys_menu.addAction(T("РЎРѕР·РґР°С‚СЊ СЏСЂР»С‹Рє РЅР° СЂР°Р±РѕС‡РµРј СЃС‚РѕР»Рµ", "Create Desktop Shortcut"), lambda: utils.run_script("yarlik.pyw", [os.path.basename(__file__)]))
        sys_menu.addAction(T("РћС‚РєСЂС‹С‚СЊ СЃРІРѕР№СЃС‚РІР° Р±СЂР°СѓР·РµСЂР°", "Open Browser Properties"), utils.open_browser_properties)
        # РЈРїСЂР°РІР»РµРЅРёРµ DNS
        dns_menu = QMenu(T("РЈРїСЂР°РІР»РµРЅРёРµ DNS (РўСЂРµР±СѓРµС‚ РїСЂР°РІ РђРґРјРёРЅР°)", "DNS Management (Requires Admin)"), sys_menu)
        
        comms_dns_act = QAction(T("РЈСЃС‚Р°РЅРѕРІРёС‚СЊ Comms DNS (IPv4)", "Set Comms DNS (IPv4)"), dns_menu)
        comms_dns_act.triggered.connect(lambda: set_dns("comms"))
        dns_menu.addAction(comms_dns_act)

        xbox_dns_act = QAction(T("РЈСЃС‚Р°РЅРѕРІРёС‚СЊ Xbox DNS (IPv4)", "Set Xbox DNS (IPv4)"), dns_menu)
        xbox_dns_act.triggered.connect(lambda: set_dns("xbox"))
        dns_menu.addAction(xbox_dns_act)
        
        xbox_ipv6_dns_act = QAction(T("РЈСЃС‚Р°РЅРѕРІРёС‚СЊ Xbox DNS (СЃ IPv6)", "Set Xbox DNS (with IPv6)"), dns_menu)
        xbox_ipv6_dns_act.triggered.connect(lambda: set_dns("xbox_ipv6"))
        dns_menu.addAction(xbox_ipv6_dns_act)

        dns_menu.addSeparator()

        reset_dns_act = QAction(T("РЎР±СЂРѕСЃРёС‚СЊ DNS (РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ)", "Reset DNS (Default)"), dns_menu)
        reset_dns_act.triggered.connect(lambda: set_dns("reset"))
        dns_menu.addAction(reset_dns_act)
        
        sys_menu.addMenu(dns_menu)

        
        if lang._is_en:
            ru_feat_act = QAction("Enable unsupported features (for RU region)", sys_menu)
            ru_feat_act.setCheckable(True)
            ru_feat_act.setChecked(config.get("enable_ru_features", False))
            def toggle_ru_features():
                config["enable_ru_features"] = not config.get("enable_ru_features", False)
                config_manager.save_config(config)
                update_menu()
            ru_feat_act.triggered.connect(toggle_ru_features)
            sys_menu.addAction(ru_feat_act)
            
        sys_menu.addSeparator()
        
        ui_type_act = QAction(T("РРЅС‚РµСЂС„РµР№СЃ: РћРєРЅРѕ (РџСЂРёР»РѕР¶РµРЅРёРµ)", "Interface: Window (App)") if config.get("ui_type", "tray") == "window" else T("РРЅС‚РµСЂС„РµР№СЃ: РўСЂРµР№ (РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ)", "Interface: Tray (Default)"), sys_menu)
        def toggle_ui_type():
            current = config.get("ui_type", "tray")
            config["ui_type"] = "window" if current == "tray" else "tray"
            config_manager.save_config(config)
            update_menu()
        ui_type_act.triggered.connect(toggle_ui_type)
        sys_menu.addAction(ui_type_act)
            
        tray_menu.addMenu(sys_menu)
        
        tray_menu.addSeparator()
        
        m_act = QAction(T("РџРµСЂРµР№С‚Рё РІ РїСЂРѕСЃС‚РѕР№ СЂРµР¶РёРј", "Switch to Simple Mode"), tray_menu); m_act.triggered.connect(toggle_mode); tray_menu.addAction(m_act)
        restart_act = QAction(T("РџРµСЂРµР·Р°РїСѓСЃРє", "Restart"), tray_menu); restart_act.triggered.connect(restart_app); tray_menu.addAction(restart_act)
        e_act = QAction(T("Р’С‹С…РѕРґ", "Exit"), tray_menu); e_act.triggered.connect(exit_app); tray_menu.addAction(e_act)

def create_tray_menu():
    global tray, tray_menu, config
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    setup_logging()
    # conv_mgr.start()
    
    tray = QSystemTrayIcon()
    try: tray.setIcon(QIcon("icon.ico"))
    except:
        pix = QPixmap(16, 16); pix.fill(Qt.blue); tray.setIcon(QIcon(pix))
    
    tray.setToolTip(ICON_TITLE)
    tray_menu = QMenu()
    tray_menu.setStyleSheet("QMenu { background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 5px; } QMenu::item { padding: 5px 20px 5px 20px; } QMenu::item:selected { background-color: #3d3d3d; } QMenu::separator { height: 1px; background: #555555; margin: 5px 0px 5px 0px; }")
    tray.show()
    
    global main_window
    import window_ui
    main_window = window_ui.MainWindow(sys.modules[__name__])
    
    def on_tray_activated(reason):
        if config.get("ui_type", "tray") == "window":
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.Context, QSystemTrayIcon.DoubleClick):
                main_window.update_ui_state()
                main_window.show()
                main_window.activateWindow()
        else:
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.Context):
                tray_menu.popup(QCursor.pos())
    
    tray.activated.connect(on_tray_activated)
    
    update_menu()
    
    def apply_autostart_tools():
        global proxy_enabled
        proxy_enabled = True
        
        tools = config.get("autostart_tools", ["byedpi", "tor", "opera", "tgws", "ext"])
        
        if "byedpi" in tools:
            byedpi_manager.start()
            if config.get("byedpi_pip_enabled", False):
                if config.get("byedpi_pip_use_tor", False):
                    bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                else:
                    pip_mgr = bdsher.get_pip_manager(config)
                    pip_mgr.start()
                    bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
        
        if "tor" in tools:
            tor_manager.start()
            
        if "vless" in tools:
            vless_mgr.start()
            
        if "opera" in tools:
            opera_mgr.start()
            
        if "socks" in tools:
            import subprocess
            subprocess.Popen([sys.executable, "socks-reabilitator.pyw", "--silent"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            
        if "tgws" in tools and (not lang._is_en or config.get("enable_ru_features", False)):
            tgws_mgr.start()
            
        if "proxifier" in tools and mode_type != "evpn":
            mode_mgr.start_tun()
            
        if "ext" in tools:
            ext_programs_manager.start_all()
            
        update_menu()
    
    if config.get("auto_connect_last_mode", False):
        QTimer.singleShot(500, apply_autostart_tools)
    else:
        # If no proxy autostart, maybe just start what is needed individually (like tgws and ext in previous logic)
        tools = config.get("autostart_tools", ["byedpi", "tor", "opera", "tgws", "ext"])
        if "tgws" in tools and (not lang._is_en or config.get("enable_ru_features", False)):
            QTimer.singleShot(2000, lambda: tgws_mgr.start() if not tgws_mgr.running else None)
        if "socks" in tools:
            import subprocess
            subprocess.Popen([sys.executable, "socks-reabilitator.pyw", "--silent"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if "proxifier" in tools and mode_type != "evpn":
            mode_mgr.start_tun()
        if "ext" in tools:
            ext_programs_manager.start_all()
        
    return app

if __name__ == "__main__":
    app = create_tray_menu()
    sys.exit(app.exec_())


