import system_utils as lang
import sys
import os
def _ensure_dependencies():
    import sys, os
    if getattr(sys, 'frozen', False):
        return
    required = {
        'PyQt5': 'pyqt5',
        'psutil': 'psutil',
        'requests': 'requests',
        'cryptography': 'cryptography==46.0.5',
        'win32com': 'pywin32',
        'pyperclip': 'pyperclip==1.9.0',
        'socks': 'pysocks'
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing dependencies found: {', '.join(missing)}")
        print("Starting auto-installation...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("Successfully installed dependencies! Restarting application...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"Failed to install dependencies: {e}")
            sys.exit(1)
_ensure_dependencies()

if getattr(sys, 'frozen', False):
    import runpy
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
        
        # Если передан абсолютный путь, который начинается с папки программы,
        # преобразуем его в относительный, чтобы найти внутри _MEIPASS
        if os.path.isabs(script_path) and script_path.startswith(exe_dir):
            rel_path = os.path.relpath(script_path, exe_dir)
            full_path = os.path.join(getattr(sys, '_MEIPASS', exe_dir), rel_path)
        else:
            # Иначе просто склеиваем (сработает для относительных путей)
            # или берем только имя файла как запасной вариант
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

from ui.app_log_window import setup_logging, OutputLogger, AppLogWindow
from managers import config_manager
from tgws import manager as tgws_manager
from managers import opera_manager
from managers import vless_manager
from managers import mode_manager
import system_utils as utils
from utils import log
from system_utils import T
import subprocess
from managers import bdsher
from managers import torchok
from small_actions import noisy_manager
from small_actions import tester_manager
from managers import ext_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
ICON_TITLE = "ToInet-MAX"
CACHER_SCRIPT = os.path.join(CURRENT_DIR, "system_utils.py")

# Инициализируем менеджеры
byedpi_manager = bdsher.get_manager({})
tor_manager = torchok.get_manager()
noisy_manager = noisy_manager.get_manager()
tester_manager = tester_manager.get_manager()
opera_mgr = opera_manager.get_manager()
ext_programs_manager = ext_manager.get_manager()
tgws_mgr = tgws_manager.get_manager()
mode_mgr = mode_manager.get_manager()

from managers import evpn_manager
evpn_mgr = evpn_manager.get_manager()
import ui.window_ui as window_ui
main_window = None

config = config_manager.load_config()
vless_mgr = vless_manager.get_manager(config)
proxy_enabled = False
simple_mode = True  
mode_type = config.get("mode_type", "inetcpl")

# Обновляем конфигурацию для менеджеров
byedpi_manager.update_config(config)
tor_manager.update_config(config)
noisy_manager.update_config(config)
tester_manager.update_config(config)
opera_mgr.update_config(config)
tgws_mgr.update_config(config)

# Инициализируем менеджер для pip
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
            
            # Запускаем pip прокси если включено
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
        
        # Остановка pip-прокси и очистка глобального pip
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
            QMessageBox.warning(None, T("TUN режим", "TUN Mode"), T("Сначала укажите корректный путь к проксификатору в файле proxification_app.txt!", "Please specify correct path to proxifier in proxification_app.txt first!"))
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
        log(f"Ошибка настройки автозапуска: {e}")
        QMessageBox.critical(None, T("Ошибка", "Error"), f"Не удалось настроить автозапуск:\n{e}")

def toggle_auto_connect_last_mode():
    config["auto_connect_last_mode"] = not config.get("auto_connect_last_mode", False)
    config_manager.save_config(config)
    update_menu()

def set_dns(mode):
    import ctypes
    
    if mode == "comms":
        cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('83.220.169.155', '212.109.195.93')"
        msg = T("Запрос на установку Comms DNS отправлен. Подтвердите права администратора.", "Request to set Comms DNS sent. Please confirm admin rights.")
    elif mode == "xbox":
        if not lang._is_en or config.get("enable_ru_features", False):
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.54', '111.88.96.55')"
        else:
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.50', '111.88.96.51')"
        msg = T("Запрос на установку Xbox DNS отправлен. Подтвердите права администратора.", "Request to set Xbox DNS sent. Please confirm admin rights.")
    elif mode == "xbox_ipv6":
        if not lang._is_en or config.get("enable_ru_features", False):
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.54', '111.88.96.55', '2a00:ab00:1233:26::54', '2a00:ab00:1233:26::55')"
        else:
            cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.50', '111.88.96.51', '2a00:ab00:1233:26::50', '2a00:ab00:1233:26::51')"
        msg = T("Запрос на установку Xbox DNS (с IPv6) отправлен. Подтвердите права администратора.", "Request to set Xbox DNS (with IPv6) sent. Please confirm admin rights.")
    elif mode == "reset":
        cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ResetServerAddresses"
        msg = T("Запрос на сброс DNS отправлен. Подтвердите права администратора.", "Request to reset DNS sent. Please confirm admin rights.")
    else:
        return
        
    cmd += "; Clear-DnsClientCache"

    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", f"-NoProfile -WindowStyle Hidden -Command \"{cmd}\"", None, 0)
    
    if ret <= 32:
        QMessageBox.warning(None, T("Ошибка", "Error"), T("Не удалось получить права администратора для изменения DNS.", "Failed to get admin rights to change DNS."))
    else:
        QMessageBox.information(None, T("Успех", "Success"), msg)

def restart_app():
    tor_manager.stop()
    byedpi_manager.stop()
    opera_mgr.stop()
    vless_mgr.stop()
    
    # Остановка pip-прокси и очистка глобального pip
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
    
    # Остановка pip-прокси и очистка глобального pip
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
        import system_utils as utils
        utils.run_script("agy_fix.pyw")
    except:
        pass

import ui.tray_menu
ui.tray_menu.init(sys.modules[__name__])
MenuUpdater = ui.tray_menu.MenuUpdater
menu_updater = ui.tray_menu.menu_updater
_safe_update = ui.tray_menu._safe_update
update_menu = ui.tray_menu.update_menu
_update_menu_impl = ui.tray_menu._update_menu_impl
_update_menu_impl_unsafe = ui.tray_menu._update_menu_impl_unsafe
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
    import ui.window_ui as window_ui
    import ui.window_ui as window_ui
    
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
            subprocess.Popen([sys.executable, "small_actions/socks-reabilitator.pyw", "--silent"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            
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
            subprocess.Popen([sys.executable, "small_actions/socks-reabilitator.pyw", "--silent"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if "proxifier" in tools and mode_type != "evpn":
            mode_mgr.start_tun()
        if "ext" in tools:
            ext_programs_manager.start_all()
        
    return app

if __name__ == "__main__":
    app = create_tray_menu()
    sys.exit(app.exec_())




