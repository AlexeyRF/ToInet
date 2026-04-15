import sys
import os
import subprocess
import json
import socket
import threading
import time
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox, QFileDialog, QCheckBox
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer

# Импортируем модули
import tg_ws_proxy
import windows as tgws_windows
import bdsher
import torchok

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

TORRC_FILE = "torrc"
CONFIG_FILE = os.path.join(CURRENT_DIR, "config.json")
PROXY_CFG = os.path.join(CURRENT_DIR, r"3proxy\bin64\3proxy.cfg")
ICON_TITLE = "ToInet-MAX"
CPLLER_SCRIPT = os.path.join(CURRENT_DIR, "cpller.pyw")
CACHER_SCRIPT = os.path.join(CURRENT_DIR, "cacher.pyw")

# TG WS Proxy конфигурация
TGWS_CONFIG_FILE = tgws_windows.CONFIG_FILE
TGWS_APP_DIR = tgws_windows.APP_DIR
TGWS_DEFAULT_CONFIG = tgws_windows.DEFAULT_CONFIG

# Инициализируем менеджеры
byedpi_manager = bdsher.get_manager({})
tor_manager = torchok.get_manager()

proxy_enabled = False
tgws_running = False
inetcpl_tor_active = False
inetcpl_bd_active = False
simple_mode = True  
mode_type = "inetcpl"  # Возможные значения: "empty", "inetcpl"
mode_change_pending = False

tor_process = None
universal_process = None
tgws_thread = None
tgws_stop_event = None

DEFAULT_CONFIG = {
    "use_custom_settings": True,
    "byedpi_params": "--split 1 --disorder 3+s --mod-http=h,d --auto=torst --tlsrec 1+s",
    "tgws_enabled": True,
    "tgws_port": 1081,
    "tgws_host": "127.0.0.1",
    "tgws_dc_ip": ["2:149.154.167.220", "4:149.154.167.220"],
    "tgws_verbose": False,
    "mode_type": "inetcpl",
    "auto_start": False,
    "auto_connect_last_mode": False,
    "tor_show_window": False  # Новый параметр: показывать окно TOR или нет
}

def log(msg):
    print(f"[LOG] {msg}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except:
            pass
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()
mode_type = config.get("mode_type", "inetcpl")

# Обновляем конфигурацию для менеджеров
byedpi_manager.update_config(config)
tor_manager.update_config(config)  # Обновляем конфигурацию TOR менеджера

def run_script(script_name):
    if os.path.exists(script_name):
        subprocess.Popen([sys.executable, script_name], creationflags=subprocess.CREATE_NO_WINDOW)
        log(f"Started: {script_name}")
        return True
    else:
        log(f"Script not found: {script_name}")
        return False

def run_script_blocking(script_name):
    if os.path.exists(script_name):
        subprocess.call([sys.executable, script_name])
        log(f"Ran (blocking): {script_name}")
        return True
    else:
        log(f"Script not found: {script_name}")
        return False

def run_cpller(port, action_flag):
    """Запускает cpller.pyw с указанным портом и флагом"""
    if not os.path.exists(CPLLER_SCRIPT):
        log(f"cpller.pyw не найден: {CPLLER_SCRIPT}")
        return False
    
    try:
        subprocess.Popen([sys.executable, CPLLER_SCRIPT, str(port), str(action_flag)], 
                         creationflags=subprocess.CREATE_NO_WINDOW)
        log(f"Запущен cpller.pyw с портом {port} и флагом {action_flag}")
        return True
    except Exception as e:
        log(f"Ошибка запуска cpller.pyw: {e}")
        return False

def clear_cache():
    """Очистка кэша через cacher.py"""
    log("Очистка кэша...")
    
    if not os.path.exists(CACHER_SCRIPT):
        return False
    
    try:
        subprocess.Popen([sys.executable, CACHER_SCRIPT], 
                        creationflags=subprocess.CREATE_NO_WINDOW)
        log("Запущен cacher.pyw для очистки кэша")
        return True
    except Exception as e:
        log(f"Ошибка запуска cacher.pyw: {e}")
        return False

def open_project_folder():
    """Открытие папки проекта в проводнике"""
    log(f"Открытие папки проекта: {CURRENT_DIR}")
    try:
        if os.path.exists(CURRENT_DIR):
            os.startfile(CURRENT_DIR)
            log("Папка проекта открыта")
            return True
        else:
            log("Папка проекта не найдена")
            return False
    except Exception as e:
        log(f"Ошибка открытия папки проекта: {e}")
        QMessageBox.critical(None, "Ошибка", f"Не удалось открыть папку проекта:\n{e}")
        return False

def run_tgws_thread():
    global tgws_stop_event
    loop = tgws_windows._asyncio.new_event_loop()
    tgws_windows._asyncio.set_event_loop(loop)
    
    stop_ev = tgws_windows._asyncio.Event()
    tgws_stop_event = (loop, stop_ev)
    
    try:
        port = config.get("tgws_port", 1081)
        host = config.get("tgws_host", "127.0.0.1")
        dc_ip_list = config.get("tgws_dc_ip", ["2:149.154.167.220", "4:149.154.167.220"])
        
        dc_opt = tg_ws_proxy.parse_dc_ip_list(dc_ip_list)
        
        loop.run_until_complete(
            tg_ws_proxy._run(port, dc_opt, stop_event=stop_ev, host=host))
    except Exception as exc:
        log(f"TG WS Proxy thread crashed: {exc}")
        if "10048" in str(exc) or "Address already in use" in str(exc):
            QMessageBox.critical(None, "Ошибка TG WS Proxy", 
                               f"Не удалось запустить TG WS Proxy:\nПорт {port} уже используется другим приложением.")
    finally:
        loop.close()
        tgws_stop_event = None

def start_tgws():
    global tgws_running, tgws_thread, config
    
    if tgws_running:
        return True
    
    port = config.get("tgws_port", 1081)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    
    if result == 0:
        QMessageBox.critical(None, "Ошибка", 
                           f"Порт {port} уже используется.\nИзмените порт в настройках.")
        return False
    
    tgws_windows._ensure_dirs()
    tgws_windows.setup_logging(config.get("tgws_verbose", False))
    
    tgws_thread = threading.Thread(target=run_tgws_thread, daemon=True, name="tgws-proxy")
    tgws_thread.start()
    
    time.sleep(2)
    
    if tgws_thread.is_alive():
        tgws_running = True
        config["tgws_enabled"] = True
        save_config(config)
        log("TG WS Proxy запущен")
        return True
    else:
        log("Ошибка: поток TG WS Proxy не запустился")
        return False

def stop_tgws():
    global tgws_running, tgws_thread, tgws_stop_event, config
    
    if tgws_stop_event:
        loop, stop_ev = tgws_stop_event
        loop.call_soon_threadsafe(stop_ev.set)
        if tgws_thread:
            tgws_thread.join(timeout=3)
    
    tgws_thread = None
    tgws_stop_event = None
    tgws_running = False
    config["tgws_enabled"] = False
    save_config(config)
    log("TG WS Proxy остановлен")

def reset_inetcpl_proxy():
    """Сброс прокси в Internet Explorer при смене режима"""
    global inetcpl_tor_active, inetcpl_bd_active
    
    if inetcpl_tor_active:
        run_cpller(9051, 0)
        inetcpl_tor_active = False
        log("Сброшен TOR прокси в inetcpl")
    
    if inetcpl_bd_active:
        run_cpller(1080, 0)
        inetcpl_bd_active = False
        log("Сброшен BD прокси в inetcpl")

def set_mode_type(mode):
    global mode_type, config, mode_change_pending, proxy_enabled
    
    if mode == mode_type:
        return
    
    if mode_type == "inetcpl" and mode == "empty":
        reset_inetcpl_proxy()
    
    mode_type = mode
    config["mode_type"] = mode
    save_config(config)
    mode_change_pending = False
    
    proxy_enabled = tor_manager.is_running() or byedpi_manager.is_running() or tgws_running or inetcpl_tor_active or inetcpl_bd_active
    
    update_menu()

def toggle_all():
    global proxy_enabled, tgws_running
    global inetcpl_tor_active, inetcpl_bd_active
    
    if not proxy_enabled:
        if mode_type == "empty":
            byedpi_manager.start()
            tor_manager.start()
            if config.get("tgws_enabled", True):
                start_tgws()
        
        elif mode_type == "inetcpl":
            byedpi_manager.start()
            tor_manager.start()
            if config.get("tgws_enabled", True):
                start_tgws()
        
        proxy_enabled = True
    else:
        tor_manager.stop()
        byedpi_manager.stop()
        
        if tgws_running:
            stop_tgws()
        
        if inetcpl_tor_active:
            run_cpller(9051, 0)
            inetcpl_tor_active = False
        if inetcpl_bd_active:
            run_cpller(1080, 0)
            inetcpl_bd_active = False
        
        proxy_enabled = False
    
    update_menu()

def toggle_tor():
    global proxy_enabled
    
    if not tor_manager.is_running():
        if tor_manager.start():
            proxy_enabled = True
    else:
        tor_manager.stop()
        if not byedpi_manager.is_running() and not tgws_running and not inetcpl_tor_active and not inetcpl_bd_active:
            proxy_enabled = False
    
    update_menu()

def toggle_byedpi():
    global proxy_enabled
    
    if not byedpi_manager.is_running():
        if byedpi_manager.start():
            if tor_manager.is_running() or tgws_running or inetcpl_tor_active or inetcpl_bd_active:
                proxy_enabled = True
    else:
        byedpi_manager.stop()
        if not tor_manager.is_running() and not tgws_running and not inetcpl_tor_active and not inetcpl_bd_active:
            proxy_enabled = False
    
    update_menu()

def toggle_tgws():
    global tgws_running, proxy_enabled, config
    
    if not tgws_running:
        if start_tgws():
            if tor_manager.is_running() or byedpi_manager.is_running() or inetcpl_tor_active or inetcpl_bd_active:
                proxy_enabled = True
    else:
        stop_tgws()
        if not tor_manager.is_running() and not byedpi_manager.is_running() and not inetcpl_tor_active and not inetcpl_bd_active:
            proxy_enabled = False
    
    update_menu()

def restart_byedpi():
    """Перезапуск ByeDPI"""
    log("Перезапуск ByeDPI...")
    if byedpi_manager.is_running():
        byedpi_manager.stop()
        time.sleep(1)
        
    if byedpi_manager.start():
        log("ByeDPI перезапущен")
    else:
        log("Ошибка перезапуска ByeDPI")

def toggle_inetcpl_tor():
    global inetcpl_tor_active, inetcpl_bd_active, proxy_enabled
    
    if not inetcpl_tor_active:
        if inetcpl_bd_active:
            if run_cpller(1080, 0):
                inetcpl_bd_active = False
        
        if run_cpller(9051, 1):
            inetcpl_tor_active = True
            if not proxy_enabled and (byedpi_manager.is_running() or tgws_running or tor_manager.is_running()):
                proxy_enabled = True
    else:
        if run_cpller(9051, 0):
            inetcpl_tor_active = False
            if not byedpi_manager.is_running() and not tgws_running and not tor_manager.is_running() and not inetcpl_bd_active:
                proxy_enabled = False
    
    update_menu()

def toggle_inetcpl_bd():
    global inetcpl_bd_active, inetcpl_tor_active, proxy_enabled
    
    if not inetcpl_bd_active:
        if inetcpl_tor_active:
            if run_cpller(9051, 0):
                inetcpl_tor_active = False
        
        if run_cpller(1080, 1):
            inetcpl_bd_active = True
            if not proxy_enabled and (byedpi_manager.is_running() or tgws_running or tor_manager.is_running()):
                proxy_enabled = True
    else:
        if run_cpller(1080, 0):
            inetcpl_bd_active = False
            if not byedpi_manager.is_running() and not tgws_running and not tor_manager.is_running() and not inetcpl_tor_active:
                proxy_enabled = False
    
    update_menu()

def toggle_recreate_torrc():
    tor_manager.toggle_recreate()
    update_menu()

def toggle_custom_settings():
    global config
    current_state = config.get("use_custom_settings", True)
    config["use_custom_settings"] = not current_state
    save_config(config)
    byedpi_manager.update_config(config)
    update_menu()

def toggle_tor_show_window():
    """Переключение режима отображения окна TOR"""
    current_state = config.get("tor_show_window", False)
    config["tor_show_window"] = not current_state
    save_config(config)
    tor_manager.update_config(config)
    update_menu()
    status = "показывать" if config["tor_show_window"] else "не показывать"
    log(f"Режим запуска TOR изменен: {status} окно")

def toggle_mode():
    global simple_mode
    simple_mode = not simple_mode
    update_menu()

def open_tor_settings():
    tor_manager.open_settings()

def open_byedpi_settings():
    byedpi_manager.open_settings()

def open_tgws_settings():
    """Открытие настроек TGWS Proxy в отдельном окне"""
    try:
        import tgws_settings
        dialog = tgws_settings.TGWSSettingsDialog()
        dialog.exec_()
    except ImportError as e:
        log(f"Ошибка импорта tgws_settings: {e}")
        QMessageBox.critical(None, "Ошибка", 
                           f"Не удалось открыть настройки TGWS Proxy:\nМодуль tgws_settings.py не найден.")
    except Exception as e:
        log(f"Ошибка открытия настроек TGWS: {e}")
        QMessageBox.critical(None, "Ошибка", f"Не удалось открыть настройки TGWS Proxy:\n{e}")

def add_proxy_to_telegram(port):
    """Добавить прокси в Telegram по указанному порту"""
    host = "127.0.0.1"
    url = f"tg://socks?server={host}&port={port}"
    
    log(f"Adding proxy with port {port} to Telegram")
    try:
        import webbrowser
        result = webbrowser.open(url)
        if not result:
            raise RuntimeError("webbrowser.open returned False")
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(url)
            QMessageBox.information(None, "Telegram Proxy", 
                                   f"Не удалось открыть Telegram автоматически.\n\n"
                                   f"Ссылка для порта {port} скопирована в буфер обмена:\n{url}")
        except:
            QMessageBox.information(None, "Telegram Proxy", 
                                   f"Ссылка для настройки прокси (порт {port}) в Telegram:\n{url}")

def edit_bridges():
    run_script("edit_bridges.pyw")

def open_browser_properties():
    try:
        subprocess.run(['inetcpl.cpl'], shell=True)
    except Exception as e:
        QMessageBox.warning(None, "Ошибка", f"Не удалось открыть свойства браузера:\n{e}")

def create_desktop_shortcut():
    """Создание ярлыка на рабочем столе"""
    try:
        import yarlik
        yarlik.create_shortcut()
    except ImportError as e:
        log(f"Ошибка импорта yarlik: {e}")
        QMessageBox.critical(None, "Ошибка", f"Не удалось создать ярлык:\nМодуль yarlik.py не найден.")
    except Exception as e:
        log(f"Ошибка создания ярлыка: {e}")
        QMessageBox.critical(None, "Ошибка", f"Не удалось создать ярлык:\n{e}")

def toggle_auto_start():
    """Включение/выключение автозапуска приложения"""
    try:
        import auto_launcher_setuper
        current_state = config.get("auto_start", False)
        if not current_state:
            auto_launcher_setuper.enable_auto_start()
            config["auto_start"] = True
        else:
            auto_launcher_setuper.disable_auto_start()
            config["auto_start"] = False
        save_config(config)
        update_menu()
    except ImportError as e:
        log(f"Ошибка импорта auto_launcher_setuper: {e}")
        QMessageBox.critical(None, "Ошибка", 
                            f"Не удалось настроить автозапуск:\nМодуль auto_launcher_setuper.py не найден.")
    except Exception as e:
        log(f"Ошибка настройки автозапуска: {e}")
        QMessageBox.critical(None, "Ошибка", f"Не удалось настроить автозапуск:\n{e}")

def toggle_auto_connect_last_mode():
    """Включение/выключение автоматического подключения последнего режима"""
    current_state = config.get("auto_connect_last_mode", False)
    config["auto_connect_last_mode"] = not current_state
    save_config(config)
    update_menu()

def auto_connect_last_mode():
    """Автоматическое подключение последнего режима при запуске"""
    if config.get("auto_connect_last_mode", False):
        log("Автоматическое подключение последнего режима...")
        toggle_all()

def exit_app():
    tor_manager.stop()
    byedpi_manager.stop()
    if tgws_running:
        stop_tgws()
    
    if inetcpl_tor_active:
        run_cpller(9051, 0)
    if inetcpl_bd_active:
        run_cpller(1080, 0)
    
    log("Exiting...")
    app.quit()


tray = None
tray_menu = None
all_action = None
tor_action = None
byedpi_action = None
tgws_action = None
recreate_action = None
custom_settings_action = None
mode_action = None
settings_action = None
inetcpl_tor_action = None
inetcpl_bd_action = None
restart_tor_action = None
clear_cache_action = None
open_folder_action = None
auto_start_action = None
auto_connect_action = None
create_shortcut_action = None
tor_show_window_action = None
restart_byedpi_action = None

def update_menu():
    global tray_menu, all_action, tor_action, byedpi_action, tgws_action
    global recreate_action, custom_settings_action, mode_action, settings_action
    global inetcpl_tor_action, inetcpl_bd_action, restart_tor_action, clear_cache_action, open_folder_action
    global auto_start_action, auto_connect_action, create_shortcut_action, tor_show_window_action
    global restart_byedpi_action
    
    if tray_menu is None:
        return
    
    tray_menu.clear()
    
    if simple_mode:
        all_action = QAction("Запуск" if not proxy_enabled else "Остановить всё", tray_menu)
        all_action.triggered.connect(toggle_all)
        tray_menu.addAction(all_action)
        
        if mode_type == "inetcpl":
            inetcpl_tor_action = QAction("Подключиться к TOR" if not inetcpl_tor_active else "Отключиться от TOR", tray_menu)
            inetcpl_tor_action.triggered.connect(toggle_inetcpl_tor)
            tray_menu.addAction(inetcpl_tor_action)
            
            inetcpl_bd_action = QAction("Подключиться к BD" if not inetcpl_bd_active else "Отключиться от BD", tray_menu)
            inetcpl_bd_action.triggered.connect(toggle_inetcpl_bd)
            tray_menu.addAction(inetcpl_bd_action)
        
        tray_menu.addSeparator()
        
        mode_menu = QMenu("Режим", tray_menu)
        
        empty_mode_action = QAction("Empty", mode_menu)
        empty_mode_action.setCheckable(True)
        empty_mode_action.setChecked(mode_type == "empty")
        empty_mode_action.triggered.connect(lambda: set_mode_type("empty"))
        mode_menu.addAction(empty_mode_action)
        
        inetcpl_mode_action = QAction("inetcpl", mode_menu)
        inetcpl_mode_action.setCheckable(True)
        inetcpl_mode_action.setChecked(mode_type == "inetcpl")
        inetcpl_mode_action.triggered.connect(lambda: set_mode_type("inetcpl"))
        mode_menu.addAction(inetcpl_mode_action)
        
        tray_menu.addMenu(mode_menu)
        
        tray_menu.addSeparator()
        
        settings_action = QAction("Настройки", tray_menu)
        settings_action.triggered.connect(toggle_mode)
        tray_menu.addAction(settings_action)
        
        exit_action = QAction("Выход", tray_menu)
        exit_action.triggered.connect(exit_app)
        tray_menu.addAction(exit_action)
    else:
        tor_action = QAction("Ручной запуск TOR" if not tor_manager.is_running() else "Остановить TOR", tray_menu)
        tor_action.triggered.connect(toggle_tor)
        tray_menu.addAction(tor_action)
        
        if tor_manager.is_running():
            restart_tor_action = QAction("Перезапустить TOR", tray_menu)
            restart_tor_action.triggered.connect(lambda: tor_manager.restart())
            tray_menu.addAction(restart_tor_action)
        
        byedpi_action = QAction(byedpi_manager.get_status_text(), tray_menu)
        byedpi_action.triggered.connect(toggle_byedpi)
        tray_menu.addAction(byedpi_action)
        
        if byedpi_manager.is_running():
            restart_byedpi_action = QAction("Перезапустить ByeDPI", tray_menu)
            restart_byedpi_action.triggered.connect(restart_byedpi)
            tray_menu.addAction(restart_byedpi_action)
        
        tgws_action = QAction("Ручной запуск TGWS" if not tgws_running else "Остановить TGWS", tray_menu)
        tgws_action.triggered.connect(toggle_tgws)
        tray_menu.addAction(tgws_action)
        
        tray_menu.addSeparator()
        
        recreate_action = QAction("Отключить пересоздание torrc" if tor_manager.get_recreate_status() else "Включить пересоздание torrc", tray_menu)
        recreate_action.triggered.connect(toggle_recreate_torrc)
        tray_menu.addAction(recreate_action)
        
        if config.get("use_custom_settings", True):
            custom_text = "Использовать предустановленные настройки"
        else:
            custom_text = "Использовать кастомные настройки ByeDPI"
        
        custom_settings_action = QAction(custom_text, tray_menu)
        custom_settings_action.triggered.connect(toggle_custom_settings)
        tray_menu.addAction(custom_settings_action)
        
        # Добавляем настройку отображения окна TOR
        tor_show_window_action = QAction("Показывать окно TOR при запуске", tray_menu)
        tor_show_window_action.setCheckable(True)
        tor_show_window_action.setChecked(config.get("tor_show_window", False))
        tor_show_window_action.triggered.connect(toggle_tor_show_window)
        tray_menu.addAction(tor_show_window_action)
        
        tray_menu.addSeparator()
        
        tor_settings_action = QAction("Настройки TOR", tray_menu)
        tor_settings_action.triggered.connect(open_tor_settings)
        tray_menu.addAction(tor_settings_action)
        
        byedpi_settings_action = QAction("Настройки BD", tray_menu)
        byedpi_settings_action.triggered.connect(open_byedpi_settings)
        tray_menu.addAction(byedpi_settings_action)
        
        tgws_settings_action = QAction("Настройки TGWS Proxy", tray_menu)
        tgws_settings_action.triggered.connect(open_tgws_settings)
        tray_menu.addAction(tgws_settings_action)
        
        tray_menu.addSeparator()
        
        clear_cache_action = QAction("Очистить кэш", tray_menu)
        clear_cache_action.triggered.connect(clear_cache)
        tray_menu.addAction(clear_cache_action)
        
        open_folder_action = QAction("Открыть папку проекта", tray_menu)
        open_folder_action.triggered.connect(open_project_folder)
        tray_menu.addAction(open_folder_action)
        
        tray_menu.addSeparator()
        
        auto_start_action = QAction("Автозапуск приложения", tray_menu)
        auto_start_action.setCheckable(True)
        auto_start_action.setChecked(config.get("auto_start", False))
        auto_start_action.triggered.connect(toggle_auto_start)
        tray_menu.addAction(auto_start_action)
        
        auto_connect_action = QAction("Подключать последний режим при запуске", tray_menu)
        auto_connect_action.setCheckable(True)
        auto_connect_action.setChecked(config.get("auto_connect_last_mode", False))
        auto_connect_action.setEnabled(config.get("auto_start", False))
        auto_connect_action.triggered.connect(toggle_auto_connect_last_mode)
        tray_menu.addAction(auto_connect_action)
        
        tray_menu.addSeparator()
        
        create_shortcut_action = QAction("Создать ярлык на рабочем столе", tray_menu)
        create_shortcut_action.triggered.connect(create_desktop_shortcut)
        tray_menu.addAction(create_shortcut_action)
        
        tray_menu.addSeparator()
        
        add_tgws_proxy_action = QAction("Добавить TGWS (1081) в Telegram", tray_menu)
        add_tgws_proxy_action.triggered.connect(lambda: add_proxy_to_telegram(1081))
        tray_menu.addAction(add_tgws_proxy_action)
        
        add_tor_proxy_action = QAction("Добавить TOR (9051) в Telegram", tray_menu)
        add_tor_proxy_action.triggered.connect(lambda: add_proxy_to_telegram(9051))
        tray_menu.addAction(add_tor_proxy_action)
        
        add_bd_proxy_action = QAction("Добавить BD (1080) в Telegram", tray_menu)
        add_bd_proxy_action.triggered.connect(lambda: add_proxy_to_telegram(1080))
        tray_menu.addAction(add_bd_proxy_action)
        
        tray_menu.addSeparator()
           
        edit_bridges_action = QAction("Изменить мосты", tray_menu)
        edit_bridges_action.triggered.connect(edit_bridges)
        tray_menu.addAction(edit_bridges_action)
        
        delete_config_action = QAction("Удалить конфигурацию TOR", tray_menu)
        delete_config_action.triggered.connect(tor_manager.delete_config)
        tray_menu.addAction(delete_config_action)
        
        tray_menu.addSeparator()
        
        browser_props_action = QAction("Открыть свойства браузера", tray_menu)
        browser_props_action.triggered.connect(open_browser_properties)
        tray_menu.addAction(browser_props_action)
        
        tray_menu.addSeparator()
        
        mode_action = QAction("Перейти в простой режим", tray_menu)
        mode_action.triggered.connect(toggle_mode)
        tray_menu.addAction(mode_action)
        
        exit_action = QAction("Выход", tray_menu)
        exit_action.triggered.connect(exit_app)
        tray_menu.addAction(exit_action)

def create_tray_menu():
    global tray, tray_menu
    global config, tgws_running
    
    config = load_config()
    # Обновляем конфигурацию для менеджеров
    byedpi_manager.update_config(config)
    tor_manager.update_config(config)
    
    if config.get("tgws_enabled", False) and not tgws_running:
        log("Запланирован автозапуск TGWS Proxy через 2 секунды")
        
        def delayed_tgws_start():
            if not tgws_running:
                log("Выполняется автозапуск TGWS Proxy...")
                success = start_tgws()
                if success:
                    log("TGWS Proxy успешно запущен автоматически")
                else:
                    log("Не удалось запустить TGWS Proxy автоматически")
                    QTimer.singleShot(3000, lambda: start_tgws() if not tgws_running else None)
        
        QTimer.singleShot(2000, delayed_tgws_start)
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    tray = QSystemTrayIcon()
   
    try:
        tray.setIcon(QIcon("icon.ico"))
    except:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.blue)
        tray.setIcon(QIcon(pixmap))
    
    tray.setToolTip(ICON_TITLE)
    
    tray_menu = QMenu()
    tray_menu.setStyleSheet("""
        QMenu {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
        }
        QMenu::item {
            padding: 5px 20px 5px 20px;
        }
        QMenu::item:selected {
            background-color: #3d3d3d;
        }
        QMenu::separator {
            height: 1px;
            background: #555555;
            margin: 5px 0px 5px 0px;
        }
    """)
    
    tray.setContextMenu(tray_menu)
    tray.show()
    
    update_menu()
    
    log("Иконка трея запущена. Нажмите ПКМ на иконке для отображения меню.")
    
    auto_connect_last_mode()
    
    return app

if __name__ == "__main__":
    app = create_tray_menu()
    sys.exit(app.exec_())