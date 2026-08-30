import lang
import sys
import os

if getattr(sys, 'frozen', False):
    import runpy
    
    # --- Монкипатч для os.path.exists и os.path.isfile ---
    # Так как мы подменили CURRENT_DIR на папку с EXE, стандартные проверки
    # наличия Python-скриптов будут падать, потому что скрипты лежат в _MEIPASS.
    # Этот патч глобально чинит все вызовы os.path.exists для .py и .pyw файлов.
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
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox, QFileDialog, QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt5.QtGui import QIcon, QPixmap
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
    def __init__(self, title="Логи приложения", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)
        
        self.clear_btn = QPushButton("Очистить", self)
        self.clear_btn.clicked.connect(self.text_edit.clear)
        self.layout.addWidget(self.clear_btn)
        
    def append_log(self, text):
        self.text_edit.moveCursor(self.text_edit.textCursor().End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(self.text_edit.textCursor().End)

app_log_window = None

def setup_logging():
    global app_log_window
    app_log_window = AppLogWindow("Логи приложения")
    
    sys.stdout = OutputLogger(sys.stdout)
    sys.stderr = OutputLogger(sys.stderr)
    
    sys.stdout.log_signal.connect(app_log_window.append_log)
    sys.stderr.log_signal.connect(app_log_window.append_log)
    
    print("[LOG] Система логирования инициализирована.")

# Импортируем менеджеры и утилиты
import config_manager
from tgws import manager as tgws_manager
import opera_manager
import converter_manager
import mode_manager
import utils
from utils import log
from lang import T
import subprocess
import bdsher
import torchok
import noisy_manager
import tester_manager
import ext_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
ICON_TITLE = "ToInet-MAX"
CACHER_SCRIPT = os.path.join(CURRENT_DIR, "cacher.pyw")

# Инициализируем менеджеры
byedpi_manager = bdsher.get_manager({})
tor_manager = torchok.get_manager()
noisy_manager = noisy_manager.get_manager()
tester_manager = tester_manager.get_manager()
opera_mgr = opera_manager.get_manager()
ext_programs_manager = ext_manager.get_manager()
tgws_mgr = tgws_manager.get_manager()
conv_mgr = converter_manager.get_manager()
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
                     (mode_mgr.tun_process is not None))

def toggle_all():
    global proxy_enabled
    
    if not proxy_enabled:
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
        
        if mode_type == "tun":
            mode_mgr.start_tun()
        
        proxy_enabled = True
    else:
        tor_manager.stop()
        byedpi_manager.stop()
        opera_mgr.stop()
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

def toggle_inetcpl_opera():
    if not mode_mgr.inetcpl_opera_active:
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

def toggle_inetcpl_mode():
    global config
    current = config.get("inetcpl_mode", "classic")
    config["inetcpl_mode"] = "modern" if current == "classic" else "classic"
    config_manager.save_config(config)
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
        cmd = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Set-DnsClientServerAddress -ServerAddresses ('111.88.96.50', '111.88.96.51')"
        msg = T("Запрос на установку Xbox DNS отправлен. Подтвердите права администратора.", "Request to set Xbox DNS sent. Please confirm admin rights.")
    elif mode == "xbox_ipv6":
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
    
    # Остановка pip-прокси и очистка глобального pip
    pip_mgr = bdsher.get_pip_manager()
    pip_mgr.stop()
    bdsher.clear_pip_proxy()
    
    noisy_manager.stop()
    tester_manager.stop()
    ext_programs_manager.stop_all()
    mode_mgr.stop_tun()
    tgws_mgr.stop()
    conv_mgr.stop()
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
    
    # Остановка pip-прокси и очистка глобального pip
    pip_mgr = bdsher.get_pip_manager()
    pip_mgr.stop()
    bdsher.clear_pip_proxy()
    
    noisy_manager.stop()
    tester_manager.stop()
    ext_programs_manager.stop_all()
    mode_mgr.stop_tun()
    tgws_mgr.stop()
    conv_mgr.stop()
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

def _update_menu_impl_unsafe():
    global tray_menu
    if tray_menu is None: return
    tray_menu.clear()
    
    if simple_mode:
        log('[Menu] Building simple mode menu')
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
            
            opera_cpl = QAction(T("Подключиться к Opera", "Connect to Opera") if not mode_mgr.inetcpl_opera_active else T("Отключиться от Opera", "Disconnect from Opera"), tray_menu)
            opera_cpl.triggered.connect(toggle_inetcpl_opera)
            tray_menu.addAction(opera_cpl)
       
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
        restart_act = QAction(T("Перезапуск", "Restart"), tray_menu); restart_act.triggered.connect(restart_app); tray_menu.addAction(restart_act)
        exit_act = QAction(T("Выход", "Exit"), tray_menu); exit_act.triggered.connect(exit_app); tray_menu.addAction(exit_act)
    else:
        log('[Menu] Building advanced mode menu')
        # Продвинутый режим
        
        # 1. Управление компонентами
        control_menu = QMenu(T("Управление компонентами", "Service Control"), tray_menu)
        
        tor_act = QAction(T("Ручной запуск TOR", "Manual Start TOR") if not tor_manager.is_running() else T("Остановить TOR", "Stop TOR"), control_menu)
        tor_act.triggered.connect(toggle_tor); control_menu.addAction(tor_act)
        
        if tor_manager.is_running():
            nc_act = QAction(T("Запросить новую цепочку TOR", "Request New TOR Circuit"), control_menu); nc_act.triggered.connect(tor_manager.new_circuit); control_menu.addAction(nc_act)
            rt_act = QAction(T("Перезапустить TOR", "Restart TOR"), control_menu); rt_act.triggered.connect(tor_manager.restart); control_menu.addAction(rt_act)
        
        bd_act = QAction(byedpi_manager.get_status_text(), control_menu); bd_act.triggered.connect(toggle_byedpi); control_menu.addAction(bd_act)
        if byedpi_manager.is_running():
            rb_act = QAction(T("Перезапуск ByeDPI", "Restart ByeDPI"), control_menu); rb_act.triggered.connect(lambda: (byedpi_manager.stop(), time.sleep(1), byedpi_manager.start())); control_menu.addAction(rb_act)
            
        opera_act = QAction(opera_mgr.get_status_text(), control_menu); opera_act.triggered.connect(toggle_opera); control_menu.addAction(opera_act)
        if opera_mgr.is_running():
            ro_act = QAction(T("Перезапуск Opera Proxy", "Restart Opera Proxy"), control_menu); ro_act.triggered.connect(lambda: (opera_mgr.stop(), time.sleep(1), opera_mgr.start())); control_menu.addAction(ro_act)
        
        if not lang._is_en or config.get("enable_ru_features", False):
            noisy_act = QAction(noisy_manager.get_status_text(), control_menu); noisy_act.triggered.connect(toggle_noisy); control_menu.addAction(noisy_act)
            tester_act = QAction(tester_manager.get_status_text(), control_menu); tester_act.triggered.connect(toggle_tester); control_menu.addAction(tester_act)
            tg_act = QAction(T("Ручной запуск TGWS", "Manual Start TGWS") if not tgws_mgr.running else T("Остановить TGWS", "Stop TGWS"), control_menu); tg_act.triggered.connect(toggle_tgws); control_menu.addAction(tg_act)
        
            
        tun_status = T("Запустить Проксификатор", "Start Proxifier") if not mode_mgr.tun_running() else T("Остановить Проксификатор", "Stop Proxifier")
        tun_act = QAction(tun_status, control_menu); tun_act.triggered.connect(toggle_proxifier); control_menu.addAction(tun_act)
        
        if mode_mgr.tun_running():
            rtun_act = QAction(T("Перезапустить проксификатор", "Restart Proxifier"), control_menu); rtun_act.triggered.connect(mode_mgr.restart_tun); control_menu.addAction(rtun_act)
            
        control_menu.addAction(T("Перезапустить Доп. Программы", "Restart Ext. Programs"), ext_programs_manager.restart_all)
        tray_menu.addMenu(control_menu)
        
        # 2. Настройки Компонентов
        settings_menu = QMenu(T("Настройки компонентов", "Component Settings"), tray_menu)
        settings_menu.addAction(T("Настройки TOR", "TOR Settings"), tor_manager.open_settings)
        
        tor_win_txt = T("Скрывать окно TOR", "Hide TOR Window") if config.get("tor_show_window", False) else T("Показывать окно TOR", "Show TOR Window")
        tor_win_act = QAction(tor_win_txt, settings_menu); tor_win_act.triggered.connect(toggle_tor_show_window); settings_menu.addAction(tor_win_act)
        
        settings_menu.addAction(T("Настройки BD", "BD Settings"), byedpi_manager.open_settings)
        # settings_menu.addAction(T("Настройки Opera Proxy", "Opera Proxy Settings"), opera_mgr.open_settings)
        
        

        
        if not lang._is_en or config.get("enable_ru_features", False):
            settings_menu.addAction(T("Настройки TGWS Proxy", "TGWS Proxy Settings"), lambda: utils.run_script("tgws/settings.pyw"))
            
        settings_menu.addAction(T("Настройка Проксификатора", "Configure Proxifier"), mode_mgr.open_proxifier_config)
        settings_menu.addAction(T("Настройка доп. программ", "Configure Ext. Programs"), ext_programs_manager.open_config)
        tray_menu.addMenu(settings_menu)
        
        # 3. Инструменты и Утилиты
        tools_menu = QMenu(T("Инструменты и Утилиты", "Tools & Utilities"), tray_menu)
        tools_menu.addAction(T("Реабилитатор SOCKS", "Rehabilitate SOCKS"), lambda: utils.run_script("socks-reabilitator.pyw"))
        if not lang._is_en or config.get("enable_ru_features", False):
            tools_menu.addAction(T("Тест стратегий TGWS", "TGWS Strategies Tester"), lambda: utils.run_script("tgws/tester_gui.pyw"))
        
        tools_menu.addAction(T("Очистить кэш", "Clear Cache"), lambda: utils.run_script(CACHER_SCRIPT))
        tools_menu.addAction(T("Открыть папку проекта", "Open Project Folder"), lambda: utils.open_project_folder(CURRENT_DIR))
        tools_menu.addAction(T("Создать ярлык на рабочем столе", "Create Desktop Shortcut"), lambda: utils.run_script("yarlik.pyw", [os.path.basename(__file__)]))
        tools_menu.addAction(T("Изменить мосты", "Edit Bridges"), lambda: utils.run_script("edit_bridges.pyw"))
        tools_menu.addAction(T("Удалить конфигурацию TOR", "Delete TOR Config"), tor_manager.delete_config)
        tools_menu.addAction(T("Открыть свойства браузера", "Open Browser Properties"), utils.open_browser_properties)
        tray_menu.addMenu(tools_menu)
        
        # 4. Добавить в Telegram
        tg_menu = QMenu(T("Добавить в Telegram", "Telegram Integration"), tray_menu)
        if not lang._is_en or config.get("enable_ru_features", False):
            tg_menu.addAction(T("Добавить TGWS SOCKS5 (1480) в Telegram", "Add TGWS SOCKS5 (1480) to Telegram"), lambda: utils.add_proxy_to_telegram(config.get("tgws_port", 1480)))
            tg_menu.addAction(T("Добавить TGWS MTProto (1480) в Telegram", "Add TGWS MTProto (1480) to Telegram"), lambda: utils.add_mtproto_to_telegram(config.get("tgws_port", 1480), config.get("tgws_secret", "0"*32), config.get("tgws_fake_tls", "")))
            tg_menu.addAction(T("Добавить Шлюз Gatik (1777) в Telegram", "Add Smart Router (1777) to Telegram"), lambda: utils.add_proxy_to_telegram(1777))
        tg_menu.addAction(T("Добавить TOR (9853) в Telegram", "Add TOR (9853) to Telegram"), lambda: utils.add_proxy_to_telegram(9853))
        tg_menu.addAction(T("Добавить BD (1780) в Telegram", "Add BD (1780) to Telegram"), lambda: utils.add_proxy_to_telegram(1780))
        tg_menu.addAction(T("Добавить Opera SOCKS5 (1786) в Telegram", "Add Opera SOCKS5 (1786) to Telegram"), lambda: utils.add_proxy_to_telegram(1786))
        tg_menu.addAction(T("Добавить Реаб. SOCKS (1788) в Telegram", "Add Rehab. SOCKS (1788) to Telegram"), lambda: utils.add_proxy_to_telegram(1788))
        tray_menu.addMenu(tg_menu)
        
        # Управление DNS
        dns_menu = QMenu(T("Управление DNS (Требует прав Админа)", "DNS Management (Requires Admin)"), tray_menu)
        
        comms_dns_act = QAction(T("Установить Comms DNS (IPv4)", "Set Comms DNS (IPv4)"), dns_menu)
        comms_dns_act.triggered.connect(lambda: set_dns("comms"))
        dns_menu.addAction(comms_dns_act)

        xbox_dns_act = QAction(T("Установить Xbox DNS (IPv4)", "Set Xbox DNS (IPv4)"), dns_menu)
        xbox_dns_act.triggered.connect(lambda: set_dns("xbox"))
        dns_menu.addAction(xbox_dns_act)
        
        xbox_ipv6_dns_act = QAction(T("Установить Xbox DNS (с IPv6)", "Set Xbox DNS (with IPv6)"), dns_menu)
        xbox_ipv6_dns_act.triggered.connect(lambda: set_dns("xbox_ipv6"))
        dns_menu.addAction(xbox_ipv6_dns_act)

        dns_menu.addSeparator()

        reset_dns_act = QAction(T("Сбросить DNS (По умолчанию)", "Reset DNS (Default)"), dns_menu)
        reset_dns_act.triggered.connect(lambda: set_dns("reset"))
        dns_menu.addAction(reset_dns_act)
        
        tray_menu.addMenu(dns_menu)
        
        # 5. Проксирование pip
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
        
        # 6. Системные опции
        log('[Menu] Building sys_menu')
        sys_menu = QMenu(T("Системные опции", "System Options"), tray_menu)
        sys_menu.addSeparator()
        
        tor_cpl2 = QAction(T("Подключиться к TOR (Inetcpl)", "Connect to TOR (Inetcpl)") if not mode_mgr.inetcpl_tor_active else T("Отключиться от TOR (Inetcpl)", "Disconnect from TOR (Inetcpl)"), sys_menu)
        tor_cpl2.triggered.connect(toggle_inetcpl_tor)
        sys_menu.addAction(tor_cpl2)
        
        bd_cpl2 = QAction(T("Подключиться к BD (Inetcpl)", "Connect to BD (Inetcpl)") if not mode_mgr.inetcpl_bd_active else T("Отключиться от BD (Inetcpl)", "Disconnect from BD (Inetcpl)"), sys_menu)
        bd_cpl2.triggered.connect(toggle_inetcpl_bd)
        sys_menu.addAction(bd_cpl2)
        
        opera_cpl2 = QAction(T("Подключиться к Opera (Inetcpl)", "Connect to Opera (Inetcpl)") if not mode_mgr.inetcpl_opera_active else T("Отключиться от Opera (Inetcpl)", "Disconnect from Opera (Inetcpl)"), sys_menu)
        opera_cpl2.triggered.connect(toggle_inetcpl_opera)
        sys_menu.addAction(opera_cpl2)

        inetcpl_mode = config.get("inetcpl_mode", "classic")
        inetcpl_mode_txt = T("Inetcpl: Режим Classic (По умолчанию)", "Inetcpl: Classic Mode (Default)") if inetcpl_mode == "classic" else T("Inetcpl: Режим Modern (Мосты)", "Inetcpl: Modern Mode (Bridges)")
        inetcpl_mode_act = QAction(inetcpl_mode_txt, sys_menu); inetcpl_mode_act.triggered.connect(toggle_inetcpl_mode); sys_menu.addAction(inetcpl_mode_act)

        sys_menu.addSeparator()
        
        app_logs_act = QAction(T("Показать логи приложения", "Show Application Logs"), sys_menu)
        app_logs_act.triggered.connect(lambda: app_log_window.show() if app_log_window else None)
        sys_menu.addAction(app_logs_act)
        
        ast_act = QAction(T("Настройки автозапуска", "Autostart Settings"), sys_menu)
        ast_act.triggered.connect(lambda: subprocess.Popen([sys.executable, os.path.join(CURRENT_DIR, "autostart_settings.pyw")], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        sys_menu.addAction(ast_act)
        
        acl_act = QAction(T("Запускать обход при старте приложения", "Connect Last Mode on Start"), sys_menu); acl_act.setCheckable(True); acl_act.setChecked(config.get("auto_connect_last_mode", False)); acl_act.triggered.connect(toggle_auto_connect_last_mode); sys_menu.addAction(acl_act)
        
        rec_act = QAction(T("Отключить пересоздание torrc", "Disable torrc Recreation") if tor_manager.get_recreate_status() else T("Включить пересоздание torrc", "Enable torrc Recreation"), sys_menu)
        rec_act.triggered.connect(lambda: (tor_manager.toggle_recreate(), update_menu())); sys_menu.addAction(rec_act)
        
        tshow_act = QAction(T("Показывать окно TOR при запуске", "Show TOR Window on Start"), sys_menu); tshow_act.setCheckable(True); tshow_act.setChecked(config.get("tor_show_window", False)); tshow_act.triggered.connect(toggle_tor_show_window); sys_menu.addAction(tshow_act)
        
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
            
        tray_menu.addMenu(sys_menu)
        
        tray_menu.addSeparator()
        
        m_act = QAction(T("Перейти в простой режим", "Switch to Simple Mode"), tray_menu); m_act.triggered.connect(toggle_mode); tray_menu.addAction(m_act)
        restart_act = QAction(T("Перезапуск", "Restart"), tray_menu); restart_act.triggered.connect(restart_app); tray_menu.addAction(restart_act)
        e_act = QAction(T("Выход", "Exit"), tray_menu); e_act.triggered.connect(exit_app); tray_menu.addAction(e_act)

def create_tray_menu():
    global tray, tray_menu, config
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    setup_logging()
    conv_mgr.start()
    
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
            
        if "opera" in tools:
            opera_mgr.start()
            
        if "socks" in tools:
            import subprocess
            subprocess.Popen([sys.executable, "socks-reabilitator.pyw", "--silent"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            
        if "tgws" in tools and (not lang._is_en or config.get("enable_ru_features", False)):
            tgws_mgr.start()
            
        if "proxifier" in tools:
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
        if "proxifier" in tools:
            mode_mgr.start_tun()
        if "ext" in tools:
            ext_programs_manager.start_all()
        
    return app

if __name__ == "__main__":
    app = create_tray_menu()
    sys.exit(app.exec_())

