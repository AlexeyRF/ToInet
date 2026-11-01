from managers import system_utils as lang
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
        'socks': 'pysocks',
        'h2': 'h2',
        'certifi': 'certifi'
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
            norm_p = os.path.normpath(path)
            norm_exe = os.path.normpath(exe_dir)
            if norm_p.lower().startswith(norm_exe.lower()):
                rel = os.path.relpath(norm_p, norm_exe)
                meipass_path = os.path.join(sys._MEIPASS, rel)
                if original_func(meipass_path):
                    return True
            meipass_rel = os.path.join(sys._MEIPASS, norm_p)
            if original_func(meipass_rel):
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
        norm_script = os.path.normcase(os.path.normpath(script_path))
        norm_exe = os.path.normcase(os.path.normpath(exe_dir))
        base_path = getattr(sys, '_MEIPASS', exe_dir)
        if os.path.isabs(script_path) and norm_script.startswith(norm_exe):
            rel_path = os.path.relpath(script_path, exe_dir)
            full_path = os.path.join(base_path, rel_path)
        else:
            full_path = os.path.join(base_path, os.path.normpath(script_path))
            if not original_exists(full_path):
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
from managers import ssh_manager
from managers import mode_manager
from managers import system_utils as utils
from managers.system_utils import log
from managers.system_utils import T
import subprocess
from managers import bdsher
from managers import torchok
from small_actions import noisy_manager
from small_actions import tester_manager
from managers import ext_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
ICON_TITLE = "ToInet-MAX"
CACHER_SCRIPT = os.path.join(CURRENT_DIR, "managers", "system_utils.py")

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
ssh_mgr = ssh_manager.get_manager(config)
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
ssh_mgr.update_config(config)

# Инициализируем менеджер для pip
pip_manager = bdsher.get_pip_manager(config)

def activate_inetcpl_gateway(gw):
    """Explicitly connects the specified inetcpl gateway without toggling off."""
    if gw != "tor" and mode_mgr.inetcpl_tor_active:
        if mode_mgr.run_cpller(9853, 0):
            mode_mgr.inetcpl_tor_active = False
    if gw != "byedpi" and mode_mgr.inetcpl_bd_active:
        if mode_mgr.run_cpller(1780, 0):
            mode_mgr.inetcpl_bd_active = False
    if gw != "opera" and mode_mgr.inetcpl_opera_active:
        if mode_mgr.run_cpller(1785, 0):
            mode_mgr.inetcpl_opera_active = False
    if gw != "vless" and mode_mgr.inetcpl_vless_active:
        if mode_mgr.run_cpller(1790, 0):
            mode_mgr.inetcpl_vless_active = False
    if gw != "ssh" and getattr(mode_mgr, 'inetcpl_ssh_active', False):
        ssh_port = int(config.get("ssh_socks_port", 1770))
        if mode_mgr.run_cpller(ssh_port, 0):
            mode_mgr.inetcpl_ssh_active = False

    if gw == "tor":
        if not tor_manager.is_running():
            tor_manager.start()
        if mode_mgr.run_cpller(9853, 1):
            mode_mgr.inetcpl_tor_active = True
    elif gw == "opera":
        if not opera_mgr.is_running():
            opera_mgr.start()
        if mode_mgr.run_cpller(1785, 1):
            mode_mgr.inetcpl_opera_active = True
    elif gw == "ssh":
        if not ssh_mgr.is_running():
            ssh_mgr.start(silent_if_not_configured=True)
        ssh_port = int(config.get("ssh_socks_port", 1770))
        if mode_mgr.run_cpller(ssh_port, 1):
            mode_mgr.inetcpl_ssh_active = True
    elif gw == "vless":
        if not vless_mgr.is_running():
            vless_mgr.start()
        if mode_mgr.run_cpller(1790, 1):
            mode_mgr.inetcpl_vless_active = True
    else:  # byedpi
        if not byedpi_manager.is_running():
            byedpi_manager.start()
        if mode_mgr.run_cpller(1780, 1):
            mode_mgr.inetcpl_bd_active = True

    update_proxy_status()
    update_menu()

def connect_default_inetcpl_gateway():
    """Connects the user-selected default gateway when in inetcpl mode."""
    gw = config.get("inetcpl_default_gateway", "byedpi")
    activate_inetcpl_gateway(gw)

def _start_background_providers():
    try:
        from managers import config_manager
        latest = config_manager.load_config()
        if latest:
            config.update(latest)
            if hasattr(ssh_mgr, 'update_config'):
                ssh_mgr.update_config(config)
    except Exception:
        pass

    byedpi_manager.start()
    tor_manager.start()
    opera_mgr.start()
    if not lang._is_en or config.get("enable_ru_features", False):
        tgws_mgr.start()
    tools = config.get("autostart_tools", ["byedpi", "tor", "opera", "tgws", "ext"])
    ssh_configured = bool(config.get("ssh_host", "").strip() and config.get("ssh_user", "").strip())
    if "ssh" in tools or ssh_configured:
        if hasattr(ssh_mgr, 'is_running') and not ssh_mgr.is_running():
            ssh_mgr.start(silent_if_not_configured=True)
    if "vless" in tools:
        vless_mgr.start()

def update_proxy_status():
    global proxy_enabled
    now = time.time()
    if getattr(mode_mgr, '_mode_switching_until', 0) > now:
        proxy_enabled = True
    else:
        is_active = False
        if mode_type == "evpn":
            is_active = getattr(evpn_mgr, 'is_running', False)
        elif mode_type == "tun":
            is_active = mode_mgr.tun_running()
        elif mode_type == "inetcpl":
            is_active = (
                getattr(mode_mgr, 'inetcpl_bd_active', False) or
                getattr(mode_mgr, 'inetcpl_tor_active', False) or
                getattr(mode_mgr, 'inetcpl_opera_active', False) or
                getattr(mode_mgr, 'inetcpl_ssh_active', False) or
                getattr(mode_mgr, 'inetcpl_vless_active', False)
            )
        elif mode_type == "empty":
            is_active = (
                mode_mgr.proxifier_running() or
                tor_manager.is_running() or
                byedpi_manager.is_running() or
                opera_mgr.is_running() or
                ssh_mgr.is_running() or
                tgws_mgr.running
            )
        proxy_enabled = is_active

    if main_window and hasattr(main_window, 'update_ui_state'):
        try:
            main_window.update_ui_state()
        except Exception as e:
            log(f"Error updating main_window UI state: {e}")

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
            mode_mgr.inetcpl_ssh_active = False
            if "ssh" in config.get("autostart_tools", []):
                ssh_mgr.start()
        
        if mode_type == "inetcpl":
            connect_default_inetcpl_gateway()
        elif mode_type == "tun":
            mode_mgr.start_tun()
        elif mode_type == "evpn":
            if config.get("evpn_exclusive_mode", True):
                tor_manager.stop()
                byedpi_manager.stop()
                opera_mgr.stop()
                vless_mgr.stop()
                ssh_mgr.stop()
                tgws_mgr.stop()
                pip_manager.stop()
                bdsher.clear_pip_proxy()
            evpn_mgr.start()
        elif mode_type == "empty":
            mode_mgr.start_proxifier()
        
        proxy_enabled = True
    else:
        if mode_type != "evpn":
            tor_manager.stop()
            byedpi_manager.stop()
            opera_mgr.stop()
            vless_mgr.stop()
            ssh_mgr.stop()
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
            if getattr(mode_mgr, 'inetcpl_ssh_active', False):
                mode_mgr.run_cpller(config.get("ssh_socks_port", 1770), 0)
                mode_mgr.inetcpl_ssh_active = False
        
        if mode_type == "tun":
            mode_mgr.stop_tun()
        elif mode_type == "evpn":
            evpn_mgr.stop()
        elif mode_type == "empty":
            mode_mgr.stop_proxifier()
        
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

def toggle_ssh():
    if not ssh_mgr.is_running():
        ssh_mgr.start()
    else:
        ssh_mgr.stop()
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
    if not mode_mgr.proxifier_running():
        mode_mgr.start_proxifier()
    else:
        mode_mgr.stop_proxifier()
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

def toggle_inetcpl_ssh():
    port = int(config.get("ssh_socks_port", 1770))
    if not getattr(mode_mgr, 'inetcpl_ssh_active', False):
        if mode_mgr.inetcpl_vless_active:
            if mode_mgr.run_cpller(1790, 0):
                mode_mgr.inetcpl_vless_active = False
        if mode_mgr.inetcpl_tor_active:
            if mode_mgr.run_cpller(9853, 0):
                mode_mgr.inetcpl_tor_active = False
        if mode_mgr.inetcpl_bd_active:
            if mode_mgr.run_cpller(1780, 0):
                mode_mgr.inetcpl_bd_active = False
        if mode_mgr.inetcpl_opera_active:
            if mode_mgr.run_cpller(1785, 0):
                mode_mgr.inetcpl_opera_active = False
        
        if not ssh_mgr.is_running():
            ssh_mgr.start()
        if mode_mgr.run_cpller(port, 1):
            mode_mgr.inetcpl_ssh_active = True
    else:
        if mode_mgr.run_cpller(port, 0):
            mode_mgr.inetcpl_ssh_active = False
    
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

def toggle_singbox_tun_ssh():
    if not ssh_mgr.is_running():
        ssh_mgr.start(silent_if_not_configured=True)
    port = int(config.get("ssh_socks_port", 1770))
    toggle_singbox_tun(port)

def set_mode_type(mode):
    global mode_type, config, proxy_enabled

    if mode == mode_type:
        return

    old_mode = mode_type
    # Switching modes via top UI buttons always auto-connects to the chosen mode
    was_connected = True

    # 1. Stop old mode proxy redirection/tunnels
    if old_mode == "inetcpl":
        mode_mgr.reset_inetcpl_proxy()
    elif old_mode == "tun":
        mode_mgr.stop_tun()
    elif old_mode == "evpn":
        evpn_mgr.stop()
    elif old_mode == "empty":
        mode_mgr.stop_proxifier()

    # Always ensure evpn is stopped if moving away from evpn
    if mode != "evpn":
        if getattr(evpn_mgr, 'is_running', False):
            evpn_mgr.stop()
        if config.get("evpn_exclusive_mode", True):
            _start_background_providers()

    mode_type = mode
    config["mode_type"] = mode
    config_manager.save_config(config)

    # 2. Reconnect to new mode
    proxy_enabled = True
    mode_mgr._mode_switching_until = time.time() + 4.0
    if mode == "tun":
        _start_background_providers()
        mode_mgr.start_tun()
    elif mode == "inetcpl":
        _start_background_providers()
        connect_default_inetcpl_gateway()
    elif mode == "empty":
        _start_background_providers()
        mode_mgr.start_proxifier()
    elif mode == "evpn":
        if config.get("evpn_exclusive_mode", True):
            tor_manager.stop()
            byedpi_manager.stop()
            opera_mgr.stop()
            vless_mgr.stop()
            ssh_mgr.stop()
            tgws_mgr.stop()
            pip_manager.stop()
            bdsher.clear_pip_proxy()
        evpn_mgr.start()

    update_proxy_status()
    update_menu()




def toggle_mode():
    global simple_mode
    simple_mode = not simple_mode
    update_menu()

def toggle_auto_start():
    try:
        from managers import system_utils as auto_launcher_setuper
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
    ssh_mgr.stop()
    
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
        
    if tray: tray.hide()
    app.quit()

def exit_app():
    tor_manager.stop()
    byedpi_manager.stop()
    opera_mgr.stop()
    vless_mgr.stop()
    ssh_mgr.stop()
    
    # Остановка pip-прокси и очистка глобального pip
    pip_mgr = bdsher.get_pip_manager()
    pip_mgr.stop()
    bdsher.clear_pip_proxy()
    
    noisy_manager.stop()
    tester_manager.stop()
    ext_programs_manager.stop_all()
    mode_mgr.stop_tun()
    mode_mgr.stop_proxifier()
    tgws_mgr.stop()
    evpn_mgr.stop()
    # conv_mgr.stop()
    mode_mgr.reset_inetcpl_proxy()
    log("Exiting...")
    import sys
    if hasattr(sys.stdout, "original_stream"): sys.stdout = sys.__stdout__
    if hasattr(sys.stderr, "original_stream"): sys.stderr = sys.__stderr__
    if tray: tray.hide()
    app.quit()

tray = None
app_log_window = None
tray_menu = None

def run_agy_fix():
    try:
        from managers import system_utils as utils
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
    global tray, tray_menu, config, app_log_window
    
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
    try: tray.setIcon(QIcon("icon.ico"))
    except:
        pix = QPixmap(16, 16); pix.fill(Qt.blue); tray.setIcon(QIcon(pix))
    
    tray.setToolTip(ICON_TITLE)
    tray_menu = QMenu()
    tray_menu.setStyleSheet("QMenu { background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 5px; } QMenu::item { padding: 5px 20px 5px 20px; } QMenu::item:selected { background-color: #3d3d3d; } QMenu::separator { height: 1px; background: #555555; margin: 5px 0px 5px 0px; }")
    tray.show()
    
    global main_window
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
                _update_menu_impl()
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
            import subprocess
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
        # If no proxy autostart, maybe just start what is needed individually (like tgws and ext in previous logic)
        tools = config.get("autostart_tools", ["byedpi", "tor", "opera", "tgws", "ext"])
        if "tgws" in tools and (not lang._is_en or config.get("enable_ru_features", False)):
            QTimer.singleShot(2000, lambda: tgws_mgr.start() if not tgws_mgr.running else None)
        if "socks" in tools:
            import subprocess
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
    ret = app.exec_()
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




