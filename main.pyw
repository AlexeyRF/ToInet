import lang
import sys
import os
import time
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer

# Импортируем менеджеры и утилиты
import config_manager
import tgws_manager
import mode_manager
import utils
from utils import log
from lang import T

import bdsher
import torchok
import noisy_manager
import tester_manager
import ext_manager

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_TITLE = "ToInet-MAX"
CACHER_SCRIPT = os.path.join(CURRENT_DIR, "cacher.pyw")

# Инициализируем менеджеры
byedpi_manager = bdsher.get_manager({})
tor_manager = torchok.get_manager()
noisy_manager = noisy_manager.get_manager()
tester_manager = tester_manager.get_manager()
ext_programs_manager = ext_manager.get_manager()
tgws_mgr = tgws_manager.get_manager()
mode_mgr = mode_manager.get_manager()

config = config_manager.load_config()
proxy_enabled = False
simple_mode = True  
mode_type = config.get("mode_type", "inetcpl")

# Обновляем конфигурацию для менеджеров
byedpi_manager.update_config(config)
tor_manager.update_config(config)
noisy_manager.update_config(config)
tester_manager.update_config(config)
tgws_mgr.update_config(config)

# Инициализируем менеджер для pip
pip_manager = bdsher.get_pip_manager(config)

def update_proxy_status():
    global proxy_enabled
    proxy_enabled = (tor_manager.is_running() or 
                     byedpi_manager.is_running() or 
                     tgws_mgr.running or 
                     mode_mgr.inetcpl_tor_active or 
                     mode_mgr.inetcpl_bd_active or 
                     (mode_mgr.tun_process is not None))

def toggle_all():
    global proxy_enabled
    
    if not proxy_enabled:
        byedpi_manager.start()
        tor_manager.start()
        if not lang._is_en or config.get("enable_ru_features", False):
            tgws_mgr.start()
        
        # Запускаем проксирование pip, если оно включено
        if config.get("byedpi_pip_enabled", False):
            if config.get("byedpi_pip_use_tor", False):
                bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
            else:
                pip_manager.start()
                bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
        
        if mode_type == "tun":
            mode_mgr.start_tun()
        
        proxy_enabled = True
    else:
        tor_manager.stop()
        byedpi_manager.stop()
        tgws_mgr.stop()
        
        # Останавливаем ByeDPI для pip и очищаем прокси pip
        pip_manager.stop()
        bdsher.clear_pip_proxy()
        
        if mode_mgr.inetcpl_tor_active:
            mode_mgr.run_cpller(9853, 0)
            mode_mgr.inetcpl_tor_active = False
        if mode_mgr.inetcpl_bd_active:
            mode_mgr.run_cpller(1780, 0)
            mode_mgr.inetcpl_bd_active = False
        
        if mode_type == "tun":
            mode_mgr.stop_tun()
        
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

def toggle_inetcpl_tor():
    if not mode_mgr.inetcpl_tor_active:
        if mode_mgr.inetcpl_bd_active:
            if mode_mgr.run_cpller(1780, 0):
                mode_mgr.inetcpl_bd_active = False
        
        if mode_mgr.run_cpller(9853, 1):
            mode_mgr.inetcpl_tor_active = True
    else:
        if mode_mgr.run_cpller(9853, 0):
            mode_mgr.inetcpl_tor_active = False
    
    update_proxy_status()
    update_menu()

def toggle_inetcpl_bd():
    if not mode_mgr.inetcpl_bd_active:
        if mode_mgr.inetcpl_tor_active:
            if mode_mgr.run_cpller(9853, 0):
                mode_mgr.inetcpl_tor_active = False
        
        if mode_mgr.run_cpller(1780, 1):
            mode_mgr.inetcpl_bd_active = True
    else:
        if mode_mgr.run_cpller(1780, 0):
            mode_mgr.inetcpl_bd_active = False
    
    update_proxy_status()
    update_menu()

def set_mode_type(mode):
    global mode_type, config, proxy_enabled

    if mode == mode_type:
        return

    if mode_type == "inetcpl" and mode != "inetcpl":
        mode_mgr.reset_inetcpl_proxy()

    if mode_type == "tun" and mode != "tun":
        mode_mgr.stop_tun()

    if mode == "tun":
        path = mode_mgr.get_tun_app_path()
        if not path or not os.path.exists(path):
            QMessageBox.warning(None, T("TUN режим", "TUN Mode"), T("Сначала укажите корректный путь к проксификатору в файле proxification_app.txt!", "Please specify correct path to proxifier in proxification_app.txt first!"))
            update_menu()
            return

        if proxy_enabled:
            mode_mgr.start_tun()

    mode_type = mode
    config["mode_type"] = mode
    config_manager.save_config(config)
    
    update_proxy_status()
    update_menu()

def toggle_custom_settings():
    global config
    config["use_custom_settings"] = not config.get("use_custom_settings", True)
    config_manager.save_config(config)
    byedpi_manager.update_config(config)
    update_menu()

def toggle_tor_show_window():
    config["tor_show_window"] = not config.get("tor_show_window", False)
    config_manager.save_config(config)
    tor_manager.update_config(config)
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
            auto_launcher_setuper.enable_auto_start()
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

def exit_app():
    tor_manager.stop()
    byedpi_manager.stop()
    
    # Останавливаем pip-менеджер и чистим настройки pip
    pip_mgr = bdsher.get_pip_manager()
    pip_mgr.stop()
    bdsher.clear_pip_proxy()
    
    noisy_manager.stop()
    tester_manager.stop()
    ext_programs_manager.stop_all()
    mode_mgr.stop_tun()
    tgws_mgr.stop()
    mode_mgr.reset_inetcpl_proxy()
    log("Exiting...")
    app.quit()

tray = None
tray_menu = None

def update_menu():
    global tray_menu
    if tray_menu is None: return
    tray_menu.clear()
    
    if simple_mode:
        all_act = QAction(T("Запуск", "Start") if not proxy_enabled else T("Остановить всё", "Stop All"), tray_menu)
        all_act.triggered.connect(toggle_all)
        tray_menu.addAction(all_act)
        
        if mode_type == "inetcpl":
            tor_cpl = QAction(T("Подключиться к TOR", "Connect to TOR") if not mode_mgr.inetcpl_tor_active else T("Отключиться от TOR", "Disconnect from TOR"), tray_menu)
            tor_cpl.triggered.connect(toggle_inetcpl_tor)
            tray_menu.addAction(tor_cpl)
            
            bd_cpl = QAction(T("Подключиться к BD", "Connect to BD") if not mode_mgr.inetcpl_bd_active else T("Отключиться от BD", "Disconnect from BD"), tray_menu)
            bd_cpl.triggered.connect(toggle_inetcpl_bd)
            tray_menu.addAction(bd_cpl)
       
        tray_menu.addSeparator()
        mode_m = QMenu(T("Режим", "Mode"), tray_menu)
        for m in ["empty", "inetcpl", "tun"]:
            act = QAction(m.capitalize() + (" режим" if m=="tun" else ""), mode_m)
            act.setCheckable(True)
            act.setChecked(mode_type == m)
            act.triggered.connect(lambda checked, mode=m: set_mode_type(mode))
            mode_m.addAction(act)
        tray_menu.addMenu(mode_m)
        tray_menu.addSeparator()
        
        set_act = QAction(T("Настройки", "Settings"), tray_menu); set_act.triggered.connect(toggle_mode); tray_menu.addAction(set_act)
        exit_act = QAction(T("Выход", "Exit"), tray_menu); exit_act.triggered.connect(exit_app); tray_menu.addAction(exit_act)
    else:
        # Продвинутый режим
        tor_act = QAction(T("Ручной запуск TOR", "Manual Start TOR") if not tor_manager.is_running() else T("Остановить TOR", "Stop TOR"), tray_menu)
        tor_act.triggered.connect(toggle_tor); tray_menu.addAction(tor_act)
        
        if tor_manager.is_running():
            nc_act = QAction(T("Запросить новую цепочку TOR", "Request New TOR Circuit"), tray_menu); nc_act.triggered.connect(tor_manager.new_circuit); tray_menu.addAction(nc_act)
            rt_act = QAction(T("Перезапустить TOR", "Restart TOR"), tray_menu); rt_act.triggered.connect(tor_manager.restart); tray_menu.addAction(rt_act)
        
        bd_act = QAction(byedpi_manager.get_status_text(), tray_menu); bd_act.triggered.connect(toggle_byedpi); tray_menu.addAction(bd_act)
        if byedpi_manager.is_running():
            rb_act = QAction(T("Перезапустить ByeDPI", "Restart ByeDPI"), tray_menu); rb_act.triggered.connect(lambda: (byedpi_manager.stop(), time.sleep(1), byedpi_manager.start())); tray_menu.addAction(rb_act)
        
        if not lang._is_en or config.get("enable_ru_features", False):
            noisy_act = QAction(noisy_manager.get_status_text(), tray_menu); noisy_act.triggered.connect(toggle_noisy); tray_menu.addAction(noisy_act)
            tester_act = QAction(tester_manager.get_status_text(), tray_menu); tester_act.triggered.connect(toggle_tester); tray_menu.addAction(tester_act)
            tg_act = QAction(T("Ручной запуск TGWS", "Manual Start TGWS") if not tgws_mgr.running else T("Остановить TGWS", "Stop TGWS"), tray_menu); tg_act.triggered.connect(toggle_tgws); tray_menu.addAction(tg_act)
        
        if mode_type == "tun" and mode_mgr.tun_process:
            rtun_act = QAction(T("Перезапустить проксификатор", "Restart Proxifier"), tray_menu); rtun_act.triggered.connect(mode_mgr.restart_tun); tray_menu.addAction(rtun_act)
        
        tray_menu.addSeparator()
        rec_act = QAction(T("Отключить пересоздание torrc", "Disable torrc Recreation") if tor_manager.get_recreate_status() else T("Включить пересоздание torrc", "Enable torrc Recreation"), tray_menu)
        rec_act.triggered.connect(lambda: (tor_manager.toggle_recreate(), update_menu())); tray_menu.addAction(rec_act)
        
        cust_txt = T("Использовать предустановленные настройки", "Use Preset Settings") if config.get("use_custom_settings", True) else T("Использовать кастомные настройки ByeDPI", "Use Custom ByeDPI Settings")
        cust_act = QAction(cust_txt, tray_menu); cust_act.triggered.connect(toggle_custom_settings); tray_menu.addAction(cust_act)
        
        tshow_act = QAction(T("Показывать окно TOR при запуске", "Show TOR Window on Start"), tray_menu); tshow_act.setCheckable(True); tshow_act.setChecked(config.get("tor_show_window", False)); tshow_act.triggered.connect(toggle_tor_show_window); tray_menu.addAction(tshow_act)
        
        tray_menu.addSeparator()
        tray_menu.addAction(T("Настройки TOR", "TOR Settings"), tor_manager.open_settings)
        tray_menu.addAction(T("Настройки BD", "BD Settings"), byedpi_manager.open_settings)
        
        if lang._is_en:
            ru_feat_act = QAction("Enable unsupported features (for RU region)", tray_menu)
            ru_feat_act.setCheckable(True)
            ru_feat_act.setChecked(config.get("enable_ru_features", False))
            def toggle_ru_features():
                config["enable_ru_features"] = not config.get("enable_ru_features", False)
                config_manager.save_config(config)
                update_menu()
            ru_feat_act.triggered.connect(toggle_ru_features)
            tray_menu.addAction(ru_feat_act)
            
        if not lang._is_en or config.get("enable_ru_features", False):
            tray_menu.addAction(T("VK Turn Proxy", "VK Turn Proxy Launcher"), lambda: utils.run_script("vk_turn_proxy_gui.pyw"))
            
        tray_menu.addAction(T("Реабилитировать SOCKS", "Rehabilitate SOCKS"), lambda: utils.run_script("socks-reabilitator.pyw"))
        if not lang._is_en or config.get("enable_ru_features", False):
            tray_menu.addAction(T("Тестер стратегий ByeDPI", "ByeDPI Strategies Tester"), lambda: utils.run_script("byedpi_tester_gui.pyw"))
            tray_menu.addAction(T("Настройки TGWS Proxy", "TGWS Proxy Settings"), lambda: utils.run_script("tgws_settings.pyw"))
        
        # Настройки проксирования pip
        pip_menu = QMenu(T("Проксирование pip (PyPI)", "pip (PyPI) Proxying"), tray_menu)
        
        pip_enabled_act = QAction(T("Включить проксирование pip", "Enable pip Proxying"), pip_menu)
        pip_enabled_act.setCheckable(True)
        pip_enabled_act.setChecked(config.get("byedpi_pip_enabled", False))
        
        pip_use_tor_act = QAction(T("Использовать TOR вместо ByeDPI", "Use TOR Instead of ByeDPI"), pip_menu)
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
        pip_menu.addAction(T("Настройки ByeDPI для pip", "ByeDPI Settings for pip"), lambda: bdsher.get_pip_manager(config).open_settings())
        
        tray_menu.addMenu(pip_menu)
        
        tray_menu.addSeparator()
        tray_menu.addAction(T("Очистить кэш", "Clear Cache"), lambda: utils.run_script(CACHER_SCRIPT))
        tray_menu.addAction(T("Открыть папку проекта", "Open Project Folder"), lambda: utils.open_project_folder(CURRENT_DIR))
        
        tray_menu.addSeparator()
        ast_act = QAction(T("Автозапуск приложения", "Auto Start Application"), tray_menu); ast_act.setCheckable(True); ast_act.setChecked(config.get("auto_start", False)); ast_act.triggered.connect(toggle_auto_start); tray_menu.addAction(ast_act)
        acl_act = QAction(T("Подключать последний режим при запуске", "Connect Last Mode on Start"), tray_menu); acl_act.setCheckable(True); acl_act.setChecked(config.get("auto_connect_last_mode", False)); acl_act.setEnabled(config.get("auto_start", False)); acl_act.triggered.connect(toggle_auto_connect_last_mode); tray_menu.addAction(acl_act)
        
        tray_menu.addSeparator()
        tray_menu.addAction(T("Создать ярлык на рабочем столе", "Create Desktop Shortcut"), lambda: utils.run_script("yarlik.pyw"))
        
        tray_menu.addSeparator()
        tray_menu.addAction(T("Перезапустить доп. программы", "Restart Ext. Programs"), ext_programs_manager.restart_all)
        tray_menu.addAction(T("Настроить доп. программы", "Configure Ext. Programs"), ext_programs_manager.open_config)
        
        tray_menu.addSeparator()
        if not lang._is_en or config.get("enable_ru_features", False):
            tray_menu.addAction(T("Добавить TGWS (1480) в Telegram", "Add TGWS (1480) to Telegram"), lambda: utils.add_proxy_to_telegram(1480))
            tray_menu.addAction(T("Добавить Шлюз Gatik (1777) в Telegram", "Add Smart Router (1777) to Telegram"), lambda: utils.add_proxy_to_telegram(1777))
        tray_menu.addAction(T("Добавить TOR (9853) в Telegram", "Add TOR (9853) to Telegram"), lambda: utils.add_proxy_to_telegram(9853))
        tray_menu.addAction(T("Добавить BD (1780) в Telegram", "Add BD (1780) to Telegram"), lambda: utils.add_proxy_to_telegram(1780))
        tray_menu.addAction(T("Добавить реаб. SOCKS (1788) в Telegram", "Add Rehab. SOCKS (1788) to Telegram"), lambda: utils.add_proxy_to_telegram(1788))
        
        tray_menu.addSeparator()
        tray_menu.addAction(T("Изменить мосты", "Edit Bridges"), lambda: utils.run_script("edit_bridges.pyw"))
        tray_menu.addAction(T("Удалить конфигурацию TOR", "Delete TOR Config"), tor_manager.delete_config)
        
        tray_menu.addSeparator()
        tray_menu.addAction(T("Открыть свойства браузера", "Open Browser Properties"), utils.open_browser_properties)
        
        tray_menu.addSeparator()
        m_act = QAction(T("Перейти в простой режим", "Switch to Simple Mode"), tray_menu); m_act.triggered.connect(toggle_mode); tray_menu.addAction(m_act)
        e_act = QAction(T("Выход", "Exit"), tray_menu); e_act.triggered.connect(exit_app); tray_menu.addAction(e_act)

def create_tray_menu():
    global tray, tray_menu, config
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    if not config.get("auto_connect_last_mode", False) and (not lang._is_en or config.get("enable_ru_features", False)):
        QTimer.singleShot(2000, lambda: tgws_mgr.start() if not tgws_mgr.running else None)
    
    tray = QSystemTrayIcon()
    try: tray.setIcon(QIcon("icon.ico"))
    except:
        pix = QPixmap(16, 16); pix.fill(Qt.blue); tray.setIcon(QIcon(pix))
    
    tray.setToolTip(ICON_TITLE)
    tray_menu = QMenu()
    tray_menu.setStyleSheet("QMenu { background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 5px; } QMenu::item { padding: 5px 20px 5px 20px; } QMenu::item:selected { background-color: #3d3d3d; } QMenu::separator { height: 1px; background: #555555; margin: 5px 0px 5px 0px; }")
    tray.setContextMenu(tray_menu)
    tray.show()
    
    update_menu()
    
    if config.get("auto_connect_last_mode", False):
        QTimer.singleShot(500, toggle_all)
    
    ext_programs_manager.start_all()
    return app

if __name__ == "__main__":
    app = create_tray_menu()
    sys.exit(app.exec_())
