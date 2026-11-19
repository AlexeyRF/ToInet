import os
import sys
import time
import subprocess
import ctypes

from PySide6.QtWidgets import QMessageBox

m = None

def init(main_module):
    global m
    m = main_module

def toggle_inetcpl_rules():
    """Переключает системный прокси inetcpl с фильтрацией по правилам (Sing-box mixed inbound)."""
    if m.mode_mgr.is_inetcpl_active():
        m.mode_mgr.stop_inetcpl_proxy()
    else:
        _start_background_providers()
        m.mode_mgr.start_inetcpl_proxy()
    update_proxy_status()
    m.update_menu()

def activate_inetcpl_gateway(gw=None):
    """Подключает или отключает системный прокси inetcpl по правилам."""
    if gw == "none" or gw is False:
        m.mode_mgr.stop_inetcpl_proxy()
    else:
        _start_background_providers()
        m.mode_mgr.start_inetcpl_proxy()
    update_proxy_status()
    m.update_menu()

def connect_default_inetcpl_gateway():
    """Подключает системный прокси Windows с автофильтрацией по правилам."""
    _start_background_providers()
    m.mode_mgr.start_inetcpl_proxy()
    update_proxy_status()
    m.update_menu()

def _start_background_providers():
    try:
        from managers import config_manager
        latest = config_manager.load_config()
        if latest:
            m.config.update(latest)
            if hasattr(m.ssh_mgr, 'update_config'):
                m.ssh_mgr.update_config(m.config)
    except Exception:
        pass

    m.byedpi_manager.start()
    m.tor_manager.start()
    m.opera_mgr.start()
    if not m.lang._is_en or m.config.get("enable_ru_features", False):
        m.tgws_mgr.start()
    tools = m.config.get("autostart_tools", ["byedpi", "tor", "opera", "tgws", "ext"])
    ssh_configured = bool(m.config.get("ssh_host", "").strip() and m.config.get("ssh_user", "").strip())
    if "ssh" in tools or ssh_configured:
        if hasattr(m.ssh_mgr, 'is_running') and not m.ssh_mgr.is_running():
            m.ssh_mgr.start(silent_if_not_configured=True)
    if "vless" in tools:
        m.vless_mgr.start()

def update_proxy_status():
    if m is None:
        return
    now = time.time()
    if getattr(m.mode_mgr, '_mode_switching_until', 0) > now:
        m.proxy_enabled = True
    else:
        is_active = False
        if m.mode_type == "evpn":
            is_active = getattr(m.evpn_mgr, 'is_running', False)
        elif m.mode_type == "tun":
            is_active = m.mode_mgr.tun_running()
        elif m.mode_type == "inetcpl":
            is_active = m.mode_mgr.is_inetcpl_active()
            if not is_active:
                is_active = (
                    m.tor_manager.is_running() or
                    m.byedpi_manager.is_running() or
                    m.opera_mgr.is_running() or
                    m.ssh_mgr.is_running() or
                    m.tgws_mgr.running
                )
        elif m.mode_type == "empty":
            is_active = (
                m.mode_mgr.proxifier_running() or
                m.tor_manager.is_running() or
                m.byedpi_manager.is_running() or
                m.opera_mgr.is_running() or
                m.ssh_mgr.is_running() or
                m.tgws_mgr.running
            )
        m.proxy_enabled = is_active

    if m.main_window and hasattr(m.main_window, 'update_ui_state'):
        try:
            m.main_window.update_ui_state()
        except Exception as e:
            m.log(f"Error updating main_window UI state: {e}")

def toggle_all():
    if not m.proxy_enabled:
        if m.mode_type != "evpn":
            m.byedpi_manager.start()
            m.tor_manager.start()
            m.opera_mgr.start()
            if not m.lang._is_en or m.config.get("enable_ru_features", False):
                m.tgws_mgr.start()
            
            # Start pip proxy if enabled
            if m.config.get("byedpi_pip_enabled", False):
                if m.config.get("byedpi_pip_use_tor", False):
                    m.bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                else:
                    pip_mgr = m.bdsher.get_pip_manager(m.config)
                    pip_mgr.start()
                    m.bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
            
            m.mode_mgr.inetcpl_tor_active = False
            m.mode_mgr.inetcpl_bd_active = False
            m.mode_mgr.inetcpl_opera_active = False
            m.mode_mgr.inetcpl_vless_active = False
            m.mode_mgr.inetcpl_ssh_active = False
            if "ssh" in m.config.get("autostart_tools", []):
                m.ssh_mgr.start()
        
        if m.mode_type == "inetcpl":
            m.mode_mgr.start_inetcpl_proxy()
        elif m.mode_type == "tun":
            m.mode_mgr.start_tun()
        elif m.mode_type == "evpn":
            if m.config.get("evpn_exclusive_mode", True):
                m.tor_manager.stop()
                m.byedpi_manager.stop()
                m.opera_mgr.stop()
                m.vless_mgr.stop()
                m.ssh_mgr.stop()
                m.tgws_mgr.stop()
                m.pip_manager.stop()
                m.bdsher.clear_pip_proxy()
            m.evpn_mgr.start()
        elif m.mode_type == "empty":
            m.mode_mgr.start_proxifier()
        
        m.proxy_enabled = True
    else:
        if m.mode_type != "evpn":
            m.tor_manager.stop()
            m.byedpi_manager.stop()
            m.opera_mgr.stop()
            m.vless_mgr.stop()
            m.ssh_mgr.stop()
            m.tgws_mgr.stop()
            
            # Stop pip proxy and clear pip env
            m.pip_manager.stop()
            m.bdsher.clear_pip_proxy()
            
            m.mode_mgr.stop_inetcpl_proxy()
        
        if m.mode_type == "inetcpl":
            m.mode_mgr.stop_inetcpl_proxy()
        elif m.mode_type == "tun":
            m.mode_mgr.stop_tun()
        elif m.mode_type == "evpn":
            m.evpn_mgr.stop()
        elif m.mode_type == "empty":
            m.mode_mgr.stop_proxifier()
        
        m.proxy_enabled = False
    
    m.update_menu()

def toggle_tor():
    if not m.tor_manager.is_running():
        m.tor_manager.start()
    else:
        m.tor_manager.stop()
    update_proxy_status()
    m.update_menu()

def toggle_byedpi():
    if not m.byedpi_manager.is_running():
        m.byedpi_manager.start()
    else:
        m.byedpi_manager.stop()
    update_proxy_status()
    m.update_menu()

def toggle_vless():
    if not m.vless_mgr.is_running():
        m.vless_mgr.start()
    else:
        m.vless_mgr.stop()
    update_proxy_status()
    m.update_menu()
    
def toggle_opera():
    if not m.opera_mgr.is_running():
        m.opera_mgr.start()
    else:
        m.opera_mgr.stop()
    update_proxy_status()
    m.update_menu()

def toggle_ssh():
    if not m.ssh_mgr.is_running():
        m.ssh_mgr.start()
    else:
        m.ssh_mgr.stop()
    update_proxy_status()
    m.update_menu()

def toggle_tgws():
    if not m.tgws_mgr.running:
        m.tgws_mgr.start()
    else:
        m.tgws_mgr.stop()
    update_proxy_status()
    m.update_menu()

def toggle_tun():
    if m.mode_mgr.tun_running():
        m.mode_mgr.stop_tun()
    else:
        m.mode_mgr.start_tun()
    update_proxy_status()
    m.update_menu()

def toggle_proxifier():
    if m.mode_type == "tun":
        toggle_tun()
        return
    if not m.mode_mgr.proxifier_running():
        m.mode_mgr.start_proxifier()
    else:
        m.mode_mgr.stop_proxifier()
    update_proxy_status()
    m.update_menu()

def toggle_inetcpl_tor():
    toggle_inetcpl_rules()

def toggle_inetcpl_bd():
    toggle_inetcpl_rules()

def toggle_inetcpl_vless():
    toggle_inetcpl_rules()

def toggle_inetcpl_opera():
    toggle_inetcpl_rules()

def toggle_inetcpl_ssh():
    toggle_inetcpl_rules()

def toggle_singbox_tun(port, ptype="socks"):
    if m.mode_mgr.tun_proxy_port == port:
        m.mode_mgr.tun_proxy_port = 0
        if m.mode_type == "tun":
            m.mode_mgr.stop_tun()
    else:
        if m.mode_type == "tun":
            m.mode_mgr.set_singbox_tun_proxy(port, ptype)
        else:
            m.mode_mgr.tun_proxy_port = port
            m.mode_mgr.tun_proxy_type = ptype
    update_proxy_status()
    m.update_menu()

def toggle_singbox_tun_tor():
    toggle_singbox_tun(9853)

def toggle_singbox_tun_bd():
    toggle_singbox_tun(1780)

def toggle_singbox_tun_opera():
    toggle_singbox_tun(1785)

def toggle_singbox_tun_ssh():
    if not m.ssh_mgr.is_running():
        m.ssh_mgr.start(silent_if_not_configured=True)
    port = int(m.config.get("ssh_socks_port", 1770))
    toggle_singbox_tun(port)

def set_mode_type(mode):
    if mode == m.mode_type:
        return

    old_mode = m.mode_type
    was_connected = bool(m.proxy_enabled)

    # 1. Stop old mode proxy redirection/tunnels
    if old_mode == "inetcpl":
        m.mode_mgr.reset_inetcpl_proxy()
    elif old_mode == "tun":
        m.mode_mgr.stop_tun()
    elif old_mode == "evpn":
        m.evpn_mgr.stop()
    elif old_mode == "empty":
        m.mode_mgr.stop_proxifier()

    # Always ensure evpn is stopped if moving away from evpn
    if mode != "evpn":
        if getattr(m.evpn_mgr, 'is_running', False):
            m.evpn_mgr.stop()
        if was_connected and m.config.get("evpn_exclusive_mode", True):
            _start_background_providers()

    m.mode_type = mode
    m.config["mode_type"] = mode
    from managers import config_manager
    config_manager.save_config(m.config)

    # 2. Reconnect to new mode ONLY if previously connected
    if was_connected:
        m.proxy_enabled = True
        m.mode_mgr._mode_switching_until = time.time() + 4.0
        if mode == "tun":
            _start_background_providers()
            m.mode_mgr.start_tun()
        elif mode == "inetcpl":
            _start_background_providers()
            connect_default_inetcpl_gateway()
        elif mode == "empty":
            _start_background_providers()
            m.mode_mgr.start_proxifier()
        elif mode == "evpn":
            if m.config.get("evpn_exclusive_mode", True):
                m.tor_manager.stop()
                m.byedpi_manager.stop()
                m.opera_mgr.stop()
                m.vless_mgr.stop()
                m.ssh_mgr.stop()
                m.tgws_mgr.stop()
                m.pip_manager.stop()
                m.bdsher.clear_pip_proxy()
            m.evpn_mgr.start()
    else:
        m.proxy_enabled = False

    update_proxy_status()
    m.update_menu()

def toggle_mode():
    m.simple_mode = not m.simple_mode
    m.update_menu()

def toggle_auto_start():
    try:
        from managers import system_utils as auto_launcher_setuper
        from managers import config_manager
        current_state = m.config.get("auto_start", False)
        if not current_state:
            auto_launcher_setuper.enable_auto_start(os.path.basename(sys.argv[0]))
            m.config["auto_start"] = True
        else:
            auto_launcher_setuper.disable_auto_start()
            m.config["auto_start"] = False
        config_manager.save_config(m.config)
        m.update_menu()
    except Exception as e:
        m.log(f"Ошибка настройки автозапуска: {e}")
        QMessageBox.critical(None, m.T("Ошибка", "Error"), f"Не удалось настроить автозапуск:\n{e}")

def toggle_auto_connect_last_mode():
    from managers import config_manager
    m.config["auto_connect_last_mode"] = not m.config.get("auto_connect_last_mode", False)
    config_manager.save_config(m.config)
    m.update_menu()

def set_dns(mode):
    if mode == "comms":
        dns_primary = "195.123.209.76"
        dns_secondary = "185.112.83.4"
        msg = m.T("Comms DNS успешно установлен!\n(195.123.209.76, 185.112.83.4)", "Comms DNS successfully applied!\n(195.123.209.76, 185.112.83.4)")
    elif mode == "reset":
        dns_primary = None
        dns_secondary = None
        msg = m.T("DNS успешно сброшен на значения по умолчанию (DHCP)!", "DNS successfully reset to default (DHCP)!")
    else:
        return

    import win32com.client
    wmi = win32com.client.GetObject("winmgmts:\\\\.\\root\\cimv2")
    adapters = wmi.ExecQuery("SELECT * FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled = True")
    
    cmd = ""
    for adapter in adapters:
        alias = adapter.Description
        alias = alias.replace('"', '`"')
        if dns_primary:
            cmd += f"Get-NetAdapter | Where-Object {{ $_.InterfaceDescription -eq '{alias}' }} | Set-DnsClientServerAddress -ServerAddresses '{dns_primary}','{dns_secondary}'; "
        else:
            cmd += f"Get-NetAdapter | Where-Object {{ $_.InterfaceDescription -eq '{alias}' }} | Set-DnsClientServerAddress -ResetServerAddresses; "
            
    cmd += "; Clear-DnsClientCache"

    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", f"-NoProfile -WindowStyle Hidden -Command \"{cmd}\"", None, 0)
    
    if ret <= 32:
        QMessageBox.warning(None, m.T("Ошибка", "Error"), m.T("Не удалось получить права администратора для изменения DNS.", "Failed to get admin rights to change DNS."))
    else:
        QMessageBox.information(None, m.T("Успех", "Success"), msg)

def restart_app():
    m.tor_manager.stop()
    m.byedpi_manager.stop()
    m.opera_mgr.stop()
    m.vless_mgr.stop()
    m.ssh_mgr.stop()
    
    pip_mgr = m.bdsher.get_pip_manager()
    pip_mgr.stop()
    m.bdsher.clear_pip_proxy()
    
    m.ext_programs_manager.stop_all()
    m.mode_mgr.stop_tun()
    m.tgws_mgr.stop()
    m.evpn_mgr.stop()
    m.mode_mgr.reset_inetcpl_proxy()
    m.log("Restarting...")
    
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable] + sys.argv[1:])
    else:
        subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:])
        
    if m.tray:
        m.tray.hide()
    m.app.quit()

def exit_app():
    m.tor_manager.stop()
    m.byedpi_manager.stop()
    m.opera_mgr.stop()
    m.vless_mgr.stop()
    m.ssh_mgr.stop()
    
    pip_mgr = m.bdsher.get_pip_manager()
    pip_mgr.stop()
    m.bdsher.clear_pip_proxy()
    
    m.ext_programs_manager.stop_all()
    m.mode_mgr.stop_tun()
    m.mode_mgr.stop_proxifier()
    m.tgws_mgr.stop()
    m.evpn_mgr.stop()
    m.mode_mgr.reset_inetcpl_proxy()
    m.log("Exiting...")
    
    if hasattr(sys.stdout, "original_stream"):
        sys.stdout = sys.__stdout__
    if hasattr(sys.stderr, "original_stream"):
        sys.stderr = sys.__stderr__
    if m.tray:
        m.tray.hide()
    m.app.quit()

def run_agy_fix():
    try:
        from managers import system_utils as utils
        utils.run_script("agy_fix.pyw")
    except Exception:
        pass
