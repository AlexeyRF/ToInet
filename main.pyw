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
        tgws_mgr.start()
        
        if mode_type == "tun":
            mode_mgr.start_tun()
        
        proxy_enabled = True
    else:
        tor_manager.stop()
        byedpi_manager.stop()
        tgws_mgr.stop()
        
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
            QMessageBox.warning(None, "TUN режим", "Сначала укажите корректный путь к проксификатору в файле proxification_app.txt!")
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
        QMessageBox.critical(None, "Ошибка", f"Не удалось настроить автозапуск:\n{e}")

def toggle_auto_connect_last_mode():
    config["auto_connect_last_mode"] = not config.get("auto_connect_last_mode", False)
    config_manager.save_config(config)
    update_menu()

def exit_app():
    tor_manager.stop()
    byedpi_manager.stop()
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
        all_act = QAction("Запуск" if not proxy_enabled else "Остановить всё", tray_menu)
        all_act.triggered.connect(toggle_all)
        tray_menu.addAction(all_act)
        
        if mode_type == "inetcpl":
            tor_cpl = QAction("Подключиться к TOR" if not mode_mgr.inetcpl_tor_active else "Отключиться от TOR", tray_menu)
            tor_cpl.triggered.connect(toggle_inetcpl_tor)
            tray_menu.addAction(tor_cpl)
            
            bd_cpl = QAction("Подключиться к BD" if not mode_mgr.inetcpl_bd_active else "Отключиться от BD", tray_menu)
            bd_cpl.triggered.connect(toggle_inetcpl_bd)
            tray_menu.addAction(bd_cpl)
       
        tray_menu.addSeparator()
        mode_m = QMenu("Режим", tray_menu)
        for m in ["empty", "inetcpl", "tun"]:
            act = QAction(m.capitalize() + (" режим" if m=="tun" else ""), mode_m)
            act.setCheckable(True)
            act.setChecked(mode_type == m)
            act.triggered.connect(lambda checked, mode=m: set_mode_type(mode))
            mode_m.addAction(act)
        tray_menu.addMenu(mode_m)
        tray_menu.addSeparator()
        
        set_act = QAction("Настройки", tray_menu); set_act.triggered.connect(toggle_mode); tray_menu.addAction(set_act)
        exit_act = QAction("Выход", tray_menu); exit_act.triggered.connect(exit_app); tray_menu.addAction(exit_act)
    else:
        # Продвинутый режим
        tor_act = QAction("Ручной запуск TOR" if not tor_manager.is_running() else "Остановить TOR", tray_menu)
        tor_act.triggered.connect(toggle_tor); tray_menu.addAction(tor_act)
        
        if tor_manager.is_running():
            nc_act = QAction("Запросить новую цепочку TOR", tray_menu); nc_act.triggered.connect(tor_manager.new_circuit); tray_menu.addAction(nc_act)
            rt_act = QAction("Перезапустить TOR", tray_menu); rt_act.triggered.connect(tor_manager.restart); tray_menu.addAction(rt_act)
        
        bd_act = QAction(byedpi_manager.get_status_text(), tray_menu); bd_act.triggered.connect(toggle_byedpi); tray_menu.addAction(bd_act)
        if byedpi_manager.is_running():
            rb_act = QAction("Перезапустить ByeDPI", tray_menu); rb_act.triggered.connect(lambda: (byedpi_manager.stop(), time.sleep(1), byedpi_manager.start())); tray_menu.addAction(rb_act)
        
        noisy_act = QAction(noisy_manager.get_status_text(), tray_menu); noisy_act.triggered.connect(toggle_noisy); tray_menu.addAction(noisy_act)
        tester_act = QAction(tester_manager.get_status_text(), tray_menu); tester_act.triggered.connect(toggle_tester); tray_menu.addAction(tester_act)
        tg_act = QAction("Ручной запуск TGWS" if not tgws_mgr.running else "Остановить TGWS", tray_menu); tg_act.triggered.connect(toggle_tgws); tray_menu.addAction(tg_act)
        
        if mode_type == "tun" and mode_mgr.tun_process:
            rtun_act = QAction("Перезапустить проксификатор", tray_menu); rtun_act.triggered.connect(mode_mgr.restart_tun); tray_menu.addAction(rtun_act)
        
        tray_menu.addSeparator()
        rec_act = QAction("Отключить пересоздание torrc" if tor_manager.get_recreate_status() else "Включить пересоздание torrc", tray_menu)
        rec_act.triggered.connect(lambda: (tor_manager.toggle_recreate(), update_menu())); tray_menu.addAction(rec_act)
        
        cust_txt = "Использовать предустановленные настройки" if config.get("use_custom_settings", True) else "Использовать кастомные настройки ByeDPI"
        cust_act = QAction(cust_txt, tray_menu); cust_act.triggered.connect(toggle_custom_settings); tray_menu.addAction(cust_act)
        
        tshow_act = QAction("Показывать окно TOR при запуске", tray_menu); tshow_act.setCheckable(True); tshow_act.setChecked(config.get("tor_show_window", False)); tshow_act.triggered.connect(toggle_tor_show_window); tray_menu.addAction(tshow_act)
        
        tray_menu.addSeparator()
        tray_menu.addAction("Настройки TOR", tor_manager.open_settings)
        tray_menu.addAction("Настройки BD", byedpi_manager.open_settings)
        tray_menu.addAction("Настройки TGWS Proxy", lambda: utils.run_script("tgws_settings.pyw"))
        
        tray_menu.addSeparator()
        tray_menu.addAction("Очистить кэш", lambda: utils.run_script(CACHER_SCRIPT))
        tray_menu.addAction("Открыть папку проекта", lambda: utils.open_project_folder(CURRENT_DIR))
        
        tray_menu.addSeparator()
        ast_act = QAction("Автозапуск приложения", tray_menu); ast_act.setCheckable(True); ast_act.setChecked(config.get("auto_start", False)); ast_act.triggered.connect(toggle_auto_start); tray_menu.addAction(ast_act)
        acl_act = QAction("Подключать последний режим при запуске", tray_menu); acl_act.setCheckable(True); acl_act.setChecked(config.get("auto_connect_last_mode", False)); acl_act.setEnabled(config.get("auto_start", False)); acl_act.triggered.connect(toggle_auto_connect_last_mode); tray_menu.addAction(acl_act)
        
        tray_menu.addSeparator()
        tray_menu.addAction("Создать ярлык на рабочем столе", lambda: utils.run_script("yarlik.pyw"))
        
        tray_menu.addSeparator()
        tray_menu.addAction("Перезапустить доп. программы", ext_programs_manager.restart_all)
        tray_menu.addAction("Настроить доп. программы", ext_programs_manager.open_config)
        
        tray_menu.addSeparator()
        tray_menu.addAction("Добавить TGWS (1480) в Telegram", lambda: utils.add_proxy_to_telegram(1480))
        tray_menu.addAction("Добавить TOR (9853) в Telegram", lambda: utils.add_proxy_to_telegram(9853))
        tray_menu.addAction("Добавить BD (1780) в Telegram", lambda: utils.add_proxy_to_telegram(1780))
        
        tray_menu.addSeparator()
        tray_menu.addAction("Изменить мосты", lambda: utils.run_script("edit_bridges.pyw"))
        tray_menu.addAction("Удалить конфигурацию TOR", tor_manager.delete_config)
        
        tray_menu.addSeparator()
        tray_menu.addAction("Открыть свойства браузера", utils.open_browser_properties)
        
        tray_menu.addSeparator()
        m_act = QAction("Перейти в простой режим", tray_menu); m_act.triggered.connect(toggle_mode); tray_menu.addAction(m_act)
        e_act = QAction("Выход", tray_menu); e_act.triggered.connect(exit_app); tray_menu.addAction(e_act)

def create_tray_menu():
    global tray, tray_menu, config
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    if not config.get("auto_connect_last_mode", False):
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
