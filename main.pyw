import sys
import os
import time
import subprocess

from managers.dependencies import ensure_dependencies
ensure_dependencies()

from managers.runtime_patch import apply_runtime_patches
apply_runtime_patches()

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QCursor
from PySide6.QtCore import Qt, QTimer

from ui.app_log_window import setup_logging, OutputLogger, AppLogWindow
from managers import config_manager
from managers import system_utils as utils
from managers import system_utils as lang
from managers.system_utils import log, T
from managers import bdsher
from managers import torchok
from managers import opera_manager
from managers import vless_manager
from managers import ssh_manager
from managers import mode_manager
from managers import evpn_manager
from managers import ext_manager
from tgws import manager as tgws_manager
from small_actions import noisy_manager
from small_actions import tester_manager

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
ICON_TITLE = "ToInet-MAX"
CACHER_SCRIPT = os.path.join(CURRENT_DIR, "managers", "system_utils.py")

# Инициализируем конфигурацию
config = config_manager.load_config()
proxy_enabled = False
simple_mode = True  
mode_type = config.get("mode_type", "inetcpl")

# Инициализируем менеджеры
byedpi_manager = bdsher.get_manager({})
tor_manager = torchok.get_manager()
noisy_manager = noisy_manager.get_manager()
tester_manager = tester_manager.get_manager()
opera_mgr = opera_manager.get_manager()
ext_programs_manager = ext_manager.get_manager()
tgws_mgr = tgws_manager.get_manager()
mode_mgr = mode_manager.get_manager()
evpn_mgr = evpn_manager.get_manager()
vless_mgr = vless_manager.get_manager(config)
ssh_mgr = ssh_manager.get_manager(config)
pip_manager = bdsher.get_pip_manager(config)

# Применяем конфигурацию к менеджерам
byedpi_manager.update_config(config)
tor_manager.update_config(config)
noisy_manager.update_config(config)
tester_manager.update_config(config)
opera_mgr.update_config(config)
tgws_mgr.update_config(config)
ssh_mgr.update_config(config)

# Глобальные переменные UI
app = None
tray = None
tray_menu = None
app_log_window = None
main_window = None

# Подключаем модули UI и контроллер действий
import ui.tray_menu as tray_menu_mod
tray_menu_mod.init(sys.modules[__name__])

MenuUpdater = tray_menu_mod.MenuUpdater
menu_updater = tray_menu_mod.menu_updater
_safe_update = tray_menu_mod._safe_update
update_menu = tray_menu_mod.update_menu
_update_menu_impl = tray_menu_mod._update_menu_impl
_update_menu_impl_unsafe = tray_menu_mod._update_menu_impl_unsafe

import managers.service_controller as service_controller
service_controller.init(sys.modules[__name__])

activate_inetcpl_gateway = service_controller.activate_inetcpl_gateway
connect_default_inetcpl_gateway = service_controller.connect_default_inetcpl_gateway
_start_background_providers = service_controller._start_background_providers
update_proxy_status = service_controller.update_proxy_status
toggle_all = service_controller.toggle_all
toggle_tor = service_controller.toggle_tor
toggle_byedpi = service_controller.toggle_byedpi
toggle_vless = service_controller.toggle_vless
toggle_opera = service_controller.toggle_opera
toggle_ssh = service_controller.toggle_ssh
toggle_tgws = service_controller.toggle_tgws
toggle_noisy = service_controller.toggle_noisy
toggle_tester = service_controller.toggle_tester
toggle_proxifier = service_controller.toggle_proxifier
toggle_inetcpl_tor = service_controller.toggle_inetcpl_tor
toggle_inetcpl_bd = service_controller.toggle_inetcpl_bd
toggle_inetcpl_vless = service_controller.toggle_inetcpl_vless
toggle_inetcpl_opera = service_controller.toggle_inetcpl_opera
toggle_inetcpl_ssh = service_controller.toggle_inetcpl_ssh
toggle_singbox_tun = service_controller.toggle_singbox_tun
toggle_singbox_tun_tor = service_controller.toggle_singbox_tun_tor
toggle_singbox_tun_bd = service_controller.toggle_singbox_tun_bd
toggle_singbox_tun_opera = service_controller.toggle_singbox_tun_opera
toggle_singbox_tun_ssh = service_controller.toggle_singbox_tun_ssh
set_mode_type = service_controller.set_mode_type
toggle_mode = service_controller.toggle_mode
toggle_auto_start = service_controller.toggle_auto_start
toggle_auto_connect_last_mode = service_controller.toggle_auto_connect_last_mode
set_dns = service_controller.set_dns
restart_app = service_controller.restart_app
exit_app = service_controller.exit_app
run_agy_fix = service_controller.run_agy_fix

def create_tray_menu():
    global app, tray, tray_menu, config, app_log_window, main_window
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app_log_window = setup_logging()

    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        import traceback
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log(f"[Unhandled Exception] {err_msg}")
        print(f"[Unhandled Exception] {err_msg}", file=sys.stderr)

    sys.excepthook = handle_unhandled_exception
    
    tray = QSystemTrayIcon()
    try:
        tray.setIcon(QIcon("icon.ico"))
    except Exception:
        pix = QPixmap(16, 16)
        pix.fill(Qt.blue)
        tray.setIcon(QIcon(pix))
    
    tray.setToolTip(ICON_TITLE)
    tray_menu = QMenu()
    tray_menu.setStyleSheet(
        "QMenu { background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 5px; } "
        "QMenu::item { padding: 5px 20px 5px 20px; } "
        "QMenu::item:selected { background-color: #3d3d3d; } "
        "QMenu::separator { height: 1px; background: #555555; margin: 5px 0px 5px 0px; }"
    )
    tray.show()
    
    import ui.window_ui as window_ui
    if main_window is None:
        main_window = window_ui.MainWindow(sys.modules[__name__])

    def on_tray_activated(reason):
        if config.get("ui_type", "tray") == "window":
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.Context, QSystemTrayIcon.DoubleClick):
                main_window.update_ui_state()
                main_window.show()
                main_window.activateWindow()
        else:
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.Context):
                update_proxy_status()
                tray_menu.popup(QCursor.pos())
    
    tray.activated.connect(on_tray_activated)
    tray_menu.aboutToShow.connect(_update_menu_impl)
    
    _update_menu_impl()
    if config.get("ui_type", "tray") == "window":
        main_window.update_ui_state()
        main_window.show()
        main_window.activateWindow()
    
    status_timer = QTimer(tray)
    status_timer.timeout.connect(update_proxy_status)
    status_timer.start(2500)
    
    def apply_autostart_tools():
        global proxy_enabled
        proxy_enabled = True
        
        tools = config.get("autostart_tools", ["byedpi", "tor", "opera", "tgws", "ext"])
        
        if mode_type == "evpn":
            if config.get("evpn_exclusive_mode", True):
                tools = [t for t in tools if t not in ["byedpi", "tor", "opera", "vless", "tgws", "proxifier"]]
            evpn_mgr.start()
        
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
            
        if "ssh" in tools:
            ssh_mgr.start()
            
        if "socks" in tools:
            subprocess.Popen([sys.executable, "small_actions/socks-reabilitator.pyw", "--silent"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            
        if "tgws" in tools and (not lang._is_en or config.get("enable_ru_features", False)):
            tgws_mgr.start()
            
        if mode_type == "inetcpl":
            connect_default_inetcpl_gateway()
        elif "proxifier" in tools and mode_type != "evpn":
            if mode_type == "empty":
                mode_mgr.start_proxifier()
            else:
                mode_mgr.start_tun()
            
        if "ext" in tools:
            ext_programs_manager.start_all()
            
        update_menu()
    
    if config.get("auto_connect_last_mode", False):
        QTimer.singleShot(500, apply_autostart_tools)
    else:
        tools = config.get("autostart_tools", ["byedpi", "tor", "opera", "tgws", "ext"])
        if "tgws" in tools and (not lang._is_en or config.get("enable_ru_features", False)):
            QTimer.singleShot(2000, lambda: tgws_mgr.start() if not tgws_mgr.running else None)
        if "socks" in tools:
            subprocess.Popen([sys.executable, "small_actions/socks-reabilitator.pyw", "--silent"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if "proxifier" in tools and mode_type != "evpn":
            if mode_type == "empty":
                mode_mgr.start_proxifier()
            else:
                mode_mgr.start_tun()
        if "ext" in tools:
            ext_programs_manager.start_all()
        
    update_proxy_status()
    return app

if __name__ == "__main__":
    app = create_tray_menu()
    ret = app.exec()
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.TerminateProcess(ctypes.windll.kernel32.GetCurrentProcess(), ret)
        sys.exit(ret)
    finally:
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.TerminateProcess(ctypes.windll.kernel32.GetCurrentProcess(), ret)
        os._exit(ret)
