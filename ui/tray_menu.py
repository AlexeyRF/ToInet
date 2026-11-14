import time, os, sys, subprocess
from managers import system_utils as lang
from PySide6.QtWidgets import QMenu, QWidgetAction, QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer, Signal, QObject

m = None
def init(main_module):
    global m
    m = main_module

class MenuUpdater(QObject):
    update_signal = Signal()

menu_updater = MenuUpdater()

_debounce_timer = None

def _safe_update():
    global _debounce_timer
    if _debounce_timer is None:
        _debounce_timer = QTimer()
        _debounce_timer.setSingleShot(True)
        _debounce_timer.timeout.connect(_update_menu_impl)
    _debounce_timer.start(50)

menu_updater.update_signal.connect(_safe_update, Qt.QueuedConnection)

def update_menu():
    menu_updater.update_signal.emit()

def _update_menu_impl():
    try:
        _update_menu_impl_unsafe()
    except Exception as e:
        m.log(f"[Menu] FATAL ERROR in menu generation: {e}")
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
                m.update_menu()
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
            m.update_menu()
        btn.clicked.connect(on_click)
        return btn

    if is_running and restart_func:
        if is_tor:
            def tor_restart_handler():
                mods = QApplication.keyboardModifiers()
                if mods & Qt.ControlModifier:
                    m.tor_manager.new_circuit()
                else:
                    restart_func()
            btn_restart = make_btn("↻", m.T("Перезапуск (Ctrl + Клик = Новая цепь)", "Restart (Ctrl + Click = New Circuit)"), tor_restart_handler)
        else:
            btn_restart = make_btn("↻", m.T("Перезапустить", "Restart"), restart_func)
        l.addWidget(btn_restart)
        
    play_stop_text = "■" if is_running else "▶"
    play_stop_color = "#ff5555" if is_running else "#55ff55"
    
    btn_play = make_btn(play_stop_text, m.T("Остановить", "Stop") if is_running else m.T("Запустить", "Start"), toggle_func)
    btn_play.setStyleSheet(f"QPushButton {{ color: {play_stop_color}; }} QPushButton:hover {{ background: rgba(255, 255, 255, 0.1); }}")
    l.addWidget(btn_play)
    
    wa.setDefaultWidget(w)
    return wa

def _update_menu_impl_unsafe():
    
    if m.tray_menu is None: return
    m.tray_menu.clear()
    
    if m.simple_mode:
        all_act = QAction(m.T("Запуск", "Start") if not m.proxy_enabled else m.T("Остановить всё", "Stop All"), m.tray_menu)
        all_act.triggered.connect(m.toggle_all)
        m.tray_menu.addAction(all_act)
        
        if m.mode_type == "inetcpl":
            cpl_active = m.mode_mgr.is_inetcpl_active()
            cpl_act = QAction(
                m.T("Отключить inetcpl (по правилам)", "Disconnect inetcpl (by rules)") if cpl_active else m.T("Подключить inetcpl (по правилам)", "Connect inetcpl (by rules)"),
                m.tray_menu
            )
            cpl_act.triggered.connect(m.toggle_inetcpl_rules)
            m.tray_menu.addAction(cpl_act)            

        elif m.mode_type == "tun":
            tun_act = QAction(m.T("Отключить TUN (по правилам)", "Disconnect TUN (by rules)") if m.mode_mgr.tun_running() else m.T("Подключить TUN (по правилам)", "Connect TUN (by rules)"), m.tray_menu)
            def toggle_tun_rules():
                if m.mode_mgr.tun_running():
                    m.mode_mgr.stop_tun()
                else:
                    m.mode_mgr.start_tun()
                m.update_proxy_status()
                m.update_menu()
            tun_act.triggered.connect(toggle_tun_rules)
            m.tray_menu.addAction(tun_act)

            adv_tun_simp = QAction(m.T("Продвинутые настройки TUN", "Advanced TUN Settings"), m.tray_menu)
            adv_tun_simp.triggered.connect(m.mode_mgr.open_advanced_tun_config)
            m.tray_menu.addAction(adv_tun_simp)
        elif m.mode_type == "evpn":
            evpn_next = QAction(m.T("Сменить сервер", "Change server"), m.tray_menu)
            evpn_next.triggered.connect(m.evpn_mgr.next_server)
            m.tray_menu.addAction(evpn_next)
        elif m.mode_type == "empty":
            proxi_act = QAction(m.T("Отключить Проксификатор", "Disconnect Proxifier") if m.mode_mgr.proxifier_running() else m.T("Подключить Проксификатор", "Connect Proxifier"), m.tray_menu)
            proxi_act.triggered.connect(m.toggle_proxifier)
            m.tray_menu.addAction(proxi_act)
       
        m.tray_menu.addSeparator()
        mode_m = QMenu(m.T("Режим", "Mode", "Mode"), m.tray_menu)
        for mode_val in ["empty", "inetcpl", "tun", "evpn"]:
            act = QAction(mode_val.capitalize() + (" режим" if mode_val=="tun" or mode_val=="evpn" else ""), mode_m)
            act.setCheckable(True)
            act.setChecked(m.mode_type == mode_val)
            act.triggered.connect(lambda checked, mode=mode_val: m.set_mode_type(mode))
            mode_m.addAction(act)
        m.tray_menu.addMenu(mode_m)
        m.tray_menu.addSeparator()
        
        set_act = QAction(m.T("Настройки", "Settings"), m.tray_menu); set_act.triggered.connect(m.toggle_mode); m.tray_menu.addAction(set_act)
        restart_act = QAction(m.T("Перезапуск", "Restart", "Redémarrer"), m.tray_menu); restart_act.triggered.connect(m.restart_app); m.tray_menu.addAction(restart_act)
        exit_act = QAction(m.T("Выход", "Exit", "Quitter"), m.tray_menu); exit_act.triggered.connect(m.exit_app); m.tray_menu.addAction(exit_act)
    else:
        # Продвинутый режим (дублёры простого режима убраны)

        # 1. Управление компонентами
        control_menu = QMenu(m.T("Управление компонентами", "Service Control", "Contrôle des services"), m.tray_menu)
        
        tor_wa = create_service_action(control_menu, "TOR", m.tor_manager.is_running(), m.toggle_tor, m.tor_manager.restart, is_tor=True)
        control_menu.addAction(tor_wa)
        
        bd_wa = create_service_action(control_menu, "zDPI", m.byedpi_manager.is_running(), m.toggle_byedpi, lambda: (m.byedpi_manager.stop(), time.sleep(1), m.byedpi_manager.start()))
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
        #     m.update_menu()
        # 
        # vless_wa = create_service_action(control_menu, "VLESS Proxy", vless_mgr.is_running(), vless_toggle_handler, vless_restart_handler)
        # control_menu.addAction(vless_wa)
        
        opera_wa = create_service_action(control_menu, "Opera Proxy", m.opera_mgr.is_running(), m.toggle_opera, lambda: (m.opera_mgr.stop(), time.sleep(1), m.opera_mgr.start()))
        control_menu.addAction(opera_wa)

        ssh_wa = create_service_action(control_menu, "SSH Tunnel", m.ssh_mgr.is_running(), m.toggle_ssh, m.ssh_mgr.restart)
        control_menu.addAction(ssh_wa)
        
        if not lang._is_en or m.config.get("enable_ru_features", False):
            tg_wa = create_service_action(control_menu, "TGWS", m.tgws_mgr.running, m.toggle_tgws, lambda: (m.tgws_mgr.stop(), time.sleep(1), m.tgws_mgr.start()))
            control_menu.addAction(tg_wa)
            
        tun_wa = create_service_action(control_menu, m.T("Проксификатор", "Proxifier"), m.mode_mgr.proxifier_running(), m.toggle_proxifier, m.mode_mgr.restart_proxifier)
        control_menu.addAction(tun_wa)
        
        def toggle_ext():
            if m.ext_programs_manager.is_running():
                m.ext_programs_manager.stop_all()
            else:
                m.ext_programs_manager.start_all()
        ext_wa = create_service_action(control_menu, m.T("Доп. Программы", "Ext. Programs"), m.ext_programs_manager.is_running(), toggle_ext, m.ext_programs_manager.restart_all)
        control_menu.addAction(ext_wa)
        m.tray_menu.addMenu(control_menu)
        
        # 2. Настройки Компонентов
        settings_menu = QMenu(m.T("Настройки компонентов", "Component Settings", "Paramètres des composants"), m.tray_menu)
        settings_menu.addAction(m.T("Настройки TOR", "TOR Settings", "Paramètres TOR"), m.tor_manager.open_settings)
        
        settings_menu.addAction(m.T("Настройки zDPI", "zDPI Settings", "Paramètres zDPI"), m.byedpi_manager.open_settings)
        settings_menu.addAction(m.T("Настройки SSH Туннеля", "SSH Tunnel Settings", "Paramètres du tunnel SSH"), m.ssh_mgr.open_settings)
        # settings_menu.addAction(m.T("Настройки VLESS", "VLESS Settings"), lambda: m.utils.run_script("evpn/vless_settings.pyw"))
        # settings_menu.addAction(m.T("Настройки Opera Proxy", "Opera Proxy Settings"), m.opera_mgr.open_settings)
        
        

        
        if not lang._is_en or m.config.get("enable_ru_features", False):
            settings_menu.addAction(m.T("Настройки TGWS Proxy", "TGWS Proxy Settings"), lambda: m.utils.run_script("ui/tgws_settings.pyw"))
            
        settings_menu.addAction(m.T("Настройки TUN", "TUN Settings", "Paramètres TUN"), m.mode_mgr.open_advanced_tun_config)
        settings_menu.addAction(m.T("Пути программ", "Program Paths", "Chemins des programmes"), m.mode_mgr.open_proxifier_config)
        m.tray_menu.addMenu(settings_menu)
        
        
        # 4. Добавить в Telegram
        tg_menu = QMenu(m.T("Добавить в Telegram", "Telegram Integration", "Intégration Telegram"), m.tray_menu)
        if not lang._is_en or m.config.get("enable_ru_features", False):
            tg_menu.addAction(m.T("Добавить TGWS MTProto (1480) в Telegram", "Add TGWS MTProto (1480) to Telegram"), lambda: m.utils.add_mtproto_to_telegram(m.config.get("tgws_port", 1480), m.config.get("tgws_secret", "0"*32), m.config.get("tgws_fake_tls", "")))
            tg_menu.addAction(m.T("Добавить Шлюз Gatik (1777) в Telegram", "Add Smart Router (1777) to Telegram"), lambda: m.utils.add_proxy_to_telegram(1777))
        tg_menu.addAction(m.T("Добавить TOR (9853) в Telegram", "Add TOR (9853) to Telegram"), lambda: m.utils.add_proxy_to_telegram(9853))
        ssh_port_val = int(m.config.get("ssh_socks_port", 1770))
        tg_menu.addAction(m.T(f"Добавить SSH ({ssh_port_val}) в Telegram", f"Add SSH ({ssh_port_val}) to Telegram"), lambda: m.utils.add_proxy_to_telegram(int(m.config.get("ssh_socks_port", 1770))))
        # tg_menu.addAction(m.T("Добавить VLESS (1790) в Telegram", "Add VLESS (1790) to Telegram"), lambda: m.utils.add_proxy_to_telegram(1790))
        m.tray_menu.addMenu(tg_menu)
        

        
        # 5. Проксирование pip
        pip_menu = QMenu(m.T("Проксирование pip (PyPI)", "pip (PyPI) Proxying"), m.tray_menu)
        
        pip_enabled_act = QAction(m.T("Включить проксирование pip", "Enable pip Proxying"), pip_menu)
        pip_enabled_act.setCheckable(True)
        pip_enabled_act.setChecked(m.config.get("byedpi_pip_enabled", False))
        
        pip_use_tor_act = QAction(m.T("Использовать TOR вместо zDPI", "Use TOR Instead of zDPI"), pip_menu)
        pip_use_tor_act.setCheckable(True)
        pip_use_tor_act.setChecked(m.config.get("byedpi_pip_use_tor", False))
        pip_use_tor_act.setEnabled(m.config.get("byedpi_pip_enabled", False))
        
        def toggle_pip_enabled():
            m.config["byedpi_pip_enabled"] = not m.config.get("byedpi_pip_enabled", False)
            m.config_manager.save_config(m.config)
            
            if m.proxy_enabled:
                pip_mgr = m.bdsher.get_pip_manager(m.config)
                if m.config["byedpi_pip_enabled"]:
                    if m.config.get("byedpi_pip_use_tor", False):
                        pip_mgr.stop()
                        m.bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                    else:
                        pip_mgr.start()
                        m.bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
                else:
                    pip_mgr.stop()
                    m.bdsher.clear_pip_proxy()
            m.update_menu()
            
        def toggle_pip_use_tor():
            m.config["byedpi_pip_use_tor"] = not m.config.get("byedpi_pip_use_tor", False)
            m.config_manager.save_config(m.config)
            
            if m.proxy_enabled and m.config.get("byedpi_pip_enabled", False):
                pip_mgr = m.bdsher.get_pip_manager(m.config)
                if m.config["byedpi_pip_use_tor"]:
                    pip_mgr.stop()
                    m.bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                else:
                    pip_mgr.start()
                    m.bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
            m.update_menu()
            
        pip_enabled_act.triggered.connect(toggle_pip_enabled)
        pip_use_tor_act.triggered.connect(toggle_pip_use_tor)
        
        pip_menu.addAction(pip_enabled_act)
        pip_menu.addAction(pip_use_tor_act)
        pip_menu.addAction(m.T("Настройки zDPI для pip", "zDPI Settings for pip"), lambda: m.bdsher.get_pip_manager(m.config).open_settings())
        
        # 6. Системные опции

        sys_menu = QMenu(m.T("Системные опции", "System Options"), m.tray_menu)
        sys_menu.addSeparator()
        
        app_logs_act = QAction(m.T("Показать логи приложения", "Show Application Logs"), sys_menu)
        app_logs_act.triggered.connect(lambda: m.app_log_window.show() if m.app_log_window else None)
        sys_menu.addAction(app_logs_act)
        
        ast_act = QAction(m.T("Настройки автозапуска", "Autostart Settings", "Paramètres de démarrage"), sys_menu)
        ast_act.triggered.connect(lambda: subprocess.Popen([sys.executable, os.path.join(m.CURRENT_DIR, "ui/autostart_settings.pyw")], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        sys_menu.addAction(ast_act)
        sys_menu.addAction(m.T("Очистка кеша", "Clear Cache", "Vider le cache"), lambda: m.utils.clean_data_directory())
        sys_menu.addAction(m.T("Открыть папку проекта", "Open Project Folder", "Ouvrir le dossier du projet"), lambda: m.utils.open_project_folder(m.CURRENT_DIR))
        sys_menu.addAction(m.T("Создать ярлык на рабочем столе", "Create Desktop Shortcut", "Créer un raccourci sur le bureau"), lambda: m.utils.create_shortcut("ToInet.exe" if getattr(sys, 'frozen', False) else "main.pyw"))
        sys_menu.addAction(m.T("Открыть свойства браузера", "Open Browser Properties"), m.utils.open_browser_properties)
        # Управление DNS
        dns_menu = QMenu(m.T("Управление DNS (Требует прав Админа)", "DNS Management (Requires Admin)"), sys_menu)
        
        comms_dns_act = QAction(m.T("Установить Comms DNS (IPv4)", "Set Comms DNS (IPv4)"), dns_menu)
        comms_dns_act.triggered.connect(lambda: m.set_dns("comms"))
        dns_menu.addAction(comms_dns_act)

        dns_menu.addSeparator()

        reset_dns_act = QAction(m.T("Сбросить DNS (По умолчанию)", "Reset DNS (Default)"), dns_menu)
        reset_dns_act.triggered.connect(lambda: m.set_dns("reset"))
        dns_menu.addAction(reset_dns_act)
        
        sys_menu.addMenu(dns_menu)
        # Language submenu
        lang_menu = QMenu(m.T("Язык интерфейса", "Language", "Langue"), sys_menu)
        cur_lang = m.config.get("language", "auto")
        for l_code, l_name in [("auto", m.T("Авто (Система)", "Auto (System)", "Auto (Système)")),
                                ("ru", "Русский"),
                                ("en", "English"),
                                ("fr", "Français")]:
            l_act = QAction(l_name, lang_menu)
            l_act.setCheckable(True)
            l_act.setChecked(cur_lang == l_code)
            def _make_lang_cb(c):
                def _apply():
                    m.config["language"] = c
                    m.config_manager.save_config(m.config)
                    m.update_menu()
                return _apply
            l_act.triggered.connect(_make_lang_cb(l_code))
            lang_menu.addAction(l_act)
        sys_menu.addMenu(lang_menu)


        
        if lang._is_en:
            ru_feat_act = QAction("Enable unsupported features (for RU region)", sys_menu)
            ru_feat_act.setCheckable(True)
            ru_feat_act.setChecked(m.config.get("enable_ru_features", False))
            def toggle_ru_features():
                m.config["enable_ru_features"] = not m.config.get("enable_ru_features", False)
                m.config_manager.save_config(m.config)
                m.update_menu()
            ru_feat_act.triggered.connect(toggle_ru_features)
            sys_menu.addAction(ru_feat_act)
            
        sys_menu.addSeparator()
        
        ui_type_act = QAction(m.T("Интерфейс: Окно (Приложение)", "Interface: Window (App)") if m.config.get("ui_type", "tray") == "window" else m.T("Интерфейс: Трей (По умолчанию)", "Interface: Tray (Default)"), sys_menu)
        def toggle_ui_type():
            current = m.config.get("ui_type", "tray")
            new_type = "window" if current == "tray" else "tray"
            m.config["ui_type"] = new_type
            m.config_manager.save_config(m.config)
            m.update_menu()
            if new_type == "window" and getattr(m, "main_window", None):
                m.main_window.update_ui_state()
                m.main_window.show()
                m.main_window.activateWindow()
            elif new_type == "tray" and getattr(m, "main_window", None):
                m.main_window.hide()
        ui_type_act.triggered.connect(toggle_ui_type)
        sys_menu.addAction(ui_type_act)
            
        m.tray_menu.addMenu(sys_menu)
        
        m.tray_menu.addSeparator()
        
        m_act = QAction(m.T("Перейти в простой режим", "Switch to Simple Mode"), m.tray_menu); m_act.triggered.connect(m.toggle_mode); m.tray_menu.addAction(m_act)
        restart_act = QAction(m.T("Перезапуск", "Restart", "Redémarrer"), m.tray_menu); restart_act.triggered.connect(m.restart_app); m.tray_menu.addAction(restart_act)
        e_act = QAction(m.T("Выход", "Exit"), m.tray_menu); e_act.triggered.connect(m.exit_app); m.tray_menu.addAction(e_act)



