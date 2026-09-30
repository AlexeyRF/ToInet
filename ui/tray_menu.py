import time, os, sys, subprocess
import system_utils as lang
from PyQt5.QtWidgets import QMenu, QAction, QWidgetAction, QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject

m = None
def init(main_module):
    global m
    m = main_module

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
        m.log('[Menu] Building simple mode menu')
        all_act = QAction(m.T("Запуск", "Start") if not m.proxy_enabled else m.T("Остановить всё", "Stop All"), m.tray_menu)
        all_act.triggered.connect(m.toggle_all)
        m.tray_menu.addAction(all_act)
        
        if m.mode_type == "inetcpl":
            tor_cpl = QAction(m.T("Подключиться к TOR", "Connect to TOR") if not m.mode_mgr.inetcpl_tor_active else m.T("Отключиться от TOR", "Disconnect from TOR"), m.tray_menu)
            tor_cpl.triggered.connect(m.toggle_inetcpl_tor)
            m.tray_menu.addAction(tor_cpl)
            
            bd_cpl = QAction(m.T("Подключиться к BD", "Connect to BD") if not m.mode_mgr.inetcpl_bd_active else m.T("Отключиться от BD", "Disconnect from BD"), m.tray_menu)
            bd_cpl.triggered.connect(m.toggle_inetcpl_bd)
            m.tray_menu.addAction(bd_cpl)
            
            opera_cpl = QAction(m.T("Подключиться к Opera", "Connect to Opera") if not m.mode_mgr.inetcpl_opera_active else m.T("Отключиться от Opera", "Disconnect from Opera"), m.tray_menu)
            opera_cpl.triggered.connect(m.toggle_inetcpl_opera)
            m.tray_menu.addAction(opera_cpl)            

        elif m.mode_type == "tun" and not m.mode_mgr.get_tun_app_path():
            tor_tun = QAction(m.T("Подключиться к TOR (TUN)", "Connect to TOR (TUN)") if m.mode_mgr.tun_proxy_port != 9853 else m.T("Отключиться от TOR (TUN)", "Disconnect from TOR (TUN)"), m.tray_menu)
            tor_tun.triggered.connect(m.toggle_singbox_tun_tor)
            m.tray_menu.addAction(tor_tun)
            
            bd_tun = QAction(m.T("Подключиться к BD (TUN)", "Connect to BD (TUN)") if m.mode_mgr.tun_proxy_port != 1780 else m.T("Отключиться от BD (TUN)", "Disconnect from BD (TUN)"), m.tray_menu)
            bd_tun.triggered.connect(m.toggle_singbox_tun_bd)
            m.tray_menu.addAction(bd_tun)
            
            opera_tun = QAction(m.T("Подключиться к Opera (TUN)", "Connect to Opera (TUN)") if m.mode_mgr.tun_proxy_port != 1785 else m.T("Отключиться от Opera (TUN)", "Disconnect from Opera (TUN)"), m.tray_menu)
            opera_tun.triggered.connect(m.toggle_singbox_tun_opera)
            m.tray_menu.addAction(opera_tun)
            
            adv_tun_simp = QAction(m.T("Продвинутые настройки TUN", "Advanced TUN Settings"), m.tray_menu)
            adv_tun_simp.triggered.connect(m.mode_mgr.open_advanced_tun_config)
            m.tray_menu.addAction(adv_tun_simp)
       
        m.tray_menu.addSeparator()
        mode_m = QMenu(m.T("Режим", "Mode"), m.tray_menu)
        for mode_val in ["empty", "inetcpl", "tun", "evpn"]:
            act = QAction(mode_val.capitalize() + (" режим" if mode_val=="tun" or mode_val=="evpn" else ""), mode_m)
            act.setCheckable(True)
            act.setChecked(m.mode_type == mode_val)
            act.triggered.connect(lambda checked, mode=mode_val: m.set_mode_type(mode))
            mode_m.addAction(act)
        m.tray_menu.addMenu(mode_m)
        m.tray_menu.addSeparator()
        
        set_act = QAction(m.T("Настройки", "Settings"), m.tray_menu); set_act.triggered.connect(m.toggle_mode); m.tray_menu.addAction(set_act)
        restart_act = QAction(m.T("Перезапуск", "Restart"), m.tray_menu); restart_act.triggered.connect(m.restart_app); m.tray_menu.addAction(restart_act)
        exit_act = QAction(m.T("Выход", "Exit"), m.tray_menu); exit_act.triggered.connect(m.exit_app); m.tray_menu.addAction(exit_act)
    else:
        m.log('[Menu] Building advanced mode menu')
        # Продвинутый режим
        
        # 1. Управление компонентами
        control_menu = QMenu(m.T("Управление компонентами", "Service Control"), m.tray_menu)
        
        tor_wa = create_service_action(control_menu, "TOR", m.tor_manager.is_running(), m.toggle_tor, m.tor_manager.restart, is_tor=True)
        control_menu.addAction(tor_wa)
        
        bd_wa = create_service_action(control_menu, "ByeDPI", m.byedpi_manager.is_running(), m.toggle_byedpi, lambda: (m.byedpi_manager.stop(), time.sleep(1), m.byedpi_manager.start()))
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
        
        if not lang._is_en or m.config.get("enable_ru_features", False):
            tg_wa = create_service_action(control_menu, "TGWS", m.tgws_mgr.running, m.toggle_tgws, lambda: (m.tgws_mgr.stop(), time.sleep(1), m.tgws_mgr.start()))
            control_menu.addAction(tg_wa)
            
        tun_wa = create_service_action(control_menu, m.T("Проксификатор", "Proxifier"), m.mode_mgr.tun_running(), m.toggle_proxifier, m.mode_mgr.restart_tun)
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
        settings_menu = QMenu(m.T("Настройки компонентов", "Component Settings"), m.tray_menu)
        settings_menu.addAction(m.T("Настройки TOR", "TOR Settings"), m.tor_manager.open_settings)
        
        settings_menu.addAction(m.T("Настройки BD", "BD Settings"), m.byedpi_manager.open_settings)
        # settings_menu.addAction(m.T("Настройки VLESS", "VLESS Settings"), lambda: m.utils.run_script("evpn/vless_settings.pyw"))
        # settings_menu.addAction(m.T("Настройки Opera Proxy", "Opera Proxy Settings"), m.opera_mgr.open_settings)
        
        

        
        if not lang._is_en or m.config.get("enable_ru_features", False):
            settings_menu.addAction(m.T("Настройки TGWS Proxy", "TGWS Proxy Settings"), lambda: m.utils.run_script("tgws/settings.pyw"))
            
        settings_menu.addAction(m.T("Настройка Проксификатора", "Configure Proxifier"), m.mode_mgr.open_proxifier_config)
        settings_menu.addAction(m.T("Настройка доп. программ", "Configure Ext. Programs"), m.ext_programs_manager.open_config)
        m.tray_menu.addMenu(settings_menu)
        
        
        # 4. Добавить в Telegram
        tg_menu = QMenu(m.T("Добавить в Telegram", "Telegram Integration"), m.tray_menu)
        if not lang._is_en or m.config.get("enable_ru_features", False):
            tg_menu.addAction(m.T("Добавить TGWS SOCKS5 (1480) в Telegram", "Add TGWS SOCKS5 (1480) to Telegram"), lambda: m.utils.add_proxy_to_telegram(m.config.get("tgws_port", 1480)))
            tg_menu.addAction(m.T("Добавить TGWS MTProto (1480) в Telegram", "Add TGWS MTProto (1480) to Telegram"), lambda: m.utils.add_mtproto_to_telegram(m.config.get("tgws_port", 1480), m.config.get("tgws_secret", "0"*32), m.config.get("tgws_fake_tls", "")))
            tg_menu.addAction(m.T("Добавить Шлюз Gatik (1777) в Telegram", "Add Smart Router (1777) to Telegram"), lambda: m.utils.add_proxy_to_telegram(1777))
        tg_menu.addAction(m.T("Добавить TOR (9853) в Telegram", "Add TOR (9853) to Telegram"), lambda: m.utils.add_proxy_to_telegram(9853))
        tg_menu.addAction(m.T("Добавить BD (1780) в Telegram", "Add BD (1780) to Telegram"), lambda: m.utils.add_proxy_to_telegram(1780))
        # tg_menu.addAction(m.T("Добавить VLESS (1790) в Telegram", "Add VLESS (1790) to Telegram"), lambda: m.utils.add_proxy_to_telegram(1790))
        m.tray_menu.addMenu(tg_menu)
        

        
        # 5. Проксирование pip
        pip_menu = QMenu(m.T("Проксирование pip (PyPI)", "pip (PyPI) Proxying"), m.tray_menu)
        
        pip_enabled_act = QAction(m.T("Включить проксирование pip", "Enable pip Proxying"), pip_menu)
        pip_enabled_act.setCheckable(True)
        pip_enabled_act.setChecked(m.config.get("byedpi_pip_enabled", False))
        
        pip_use_tor_act = QAction(m.T("Использовать TOR вместо ByeDPI", "Use TOR Instead of ByeDPI"), pip_menu)
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
        pip_menu.addAction(m.T("Настройки ByeDPI для pip", "ByeDPI Settings for pip"), lambda: m.bdsher.get_pip_manager(m.config).open_settings())
        
        # 6. Системные опции

        # Узконаправленное
        m.log('[Menu] Building narrow_menu')
        narrow_menu = QMenu(m.T("Узконаправленное", "Narrow-focused"), m.tray_menu)

        narrow_menu.addAction(m.T("Реабилитатор SOCKS", "Rehabilitate SOCKS"), lambda: m.utils.run_script("small_actions/socks-reabilitator.pyw"))

        if not lang._is_en or m.config.get("enable_ru_features", False):

            noisy_act = QAction(m.noisy_manager.get_status_text(), narrow_menu); noisy_act.triggered.connect(m.toggle_noisy); narrow_menu.addAction(noisy_act)

            tester_act = QAction(m.tester_manager.get_status_text(), narrow_menu); tester_act.triggered.connect(m.toggle_tester); narrow_menu.addAction(tester_act)

        m.tray_menu.addMenu(narrow_menu)

        m.log('[Menu] Building sys_menu')
        sys_menu = QMenu(m.T("Системные опции", "System Options"), m.tray_menu)
        sys_menu.addSeparator()
        
        inetcpl_sub = QMenu(m.T("Настройки Inetcpl", "Inetcpl Settings"), sys_menu)

        tor_cpl2 = QAction(m.T("Подключиться к TOR (Inetcpl)", "Connect to TOR (Inetcpl)") if not m.mode_mgr.inetcpl_tor_active else m.T("Отключиться от TOR (Inetcpl)", "Disconnect from TOR (Inetcpl)"), inetcpl_sub)
        tor_cpl2.triggered.connect(m.toggle_inetcpl_tor)
        inetcpl_sub.addAction(tor_cpl2)
        
        bd_cpl2 = QAction(m.T("Подключиться к BD (Inetcpl)", "Connect to BD (Inetcpl)") if not m.mode_mgr.inetcpl_bd_active else m.T("Отключиться от BD (Inetcpl)", "Disconnect from BD (Inetcpl)"), inetcpl_sub)
        bd_cpl2.triggered.connect(m.toggle_inetcpl_bd)
        inetcpl_sub.addAction(bd_cpl2)
        
        opera_cpl2 = QAction(m.T("Подключиться к Opera (Inetcpl)", "Connect to Opera (Inetcpl)") if not m.mode_mgr.inetcpl_opera_active else m.T("Отключиться от Opera (Inetcpl)", "Disconnect from Opera (Inetcpl)"), inetcpl_sub)
        opera_cpl2.triggered.connect(m.toggle_inetcpl_opera)
        inetcpl_sub.addAction(opera_cpl2)        
        # vless_cpl2 = QAction(m.T("Подключиться к VLESS (Inetcpl)", "Connect to VLESS (Inetcpl)") if not m.mode_mgr.inetcpl_vless_active else m.T("Отключиться от VLESS (Inetcpl)", "Disconnect from VLESS (Inetcpl)"), inetcpl_sub)
        # vless_cpl2.triggered.connect(toggle_inetcpl_vless)
        # inetcpl_sub.addAction(vless_cpl2)

        
        sys_menu.addMenu(inetcpl_sub)
        
        tun_sub = QMenu(m.T("Настройки TUN", "TUN Settings"), sys_menu)
        tor_tun2 = QAction(m.T("Подключиться к TOR (TUN)", "Connect to TOR (TUN)") if m.mode_mgr.tun_proxy_port != 9853 else m.T("Отключиться от TOR (TUN)", "Disconnect from TOR (TUN)"), tun_sub)
        tor_tun2.triggered.connect(m.toggle_singbox_tun_tor)
        tun_sub.addAction(tor_tun2)
        
        bd_tun2 = QAction(m.T("Подключиться к BD (TUN)", "Connect to BD (TUN)") if m.mode_mgr.tun_proxy_port != 1780 else m.T("Отключиться от BD (TUN)", "Disconnect from BD (TUN)"), tun_sub)
        bd_tun2.triggered.connect(m.toggle_singbox_tun_bd)
        tun_sub.addAction(bd_tun2)
        
        opera_tun2 = QAction(m.T("Подключиться к Opera (TUN)", "Connect to Opera (TUN)") if m.mode_mgr.tun_proxy_port != 1785 else m.T("Отключиться от Opera (TUN)", "Disconnect from Opera (TUN)"), tun_sub)
        opera_tun2.triggered.connect(m.toggle_singbox_tun_opera)
        tun_sub.addAction(opera_tun2)
        
        tun_sub.addSeparator()
        adv_tun_act = QAction(m.T("Продвинутые настройки TUN", "Advanced TUN Settings"), tun_sub)
        adv_tun_act.triggered.connect(m.mode_mgr.open_advanced_tun_config)
        tun_sub.addAction(adv_tun_act)
        
        sys_menu.addMenu(tun_sub)

        sys_menu.addSeparator()
        
        app_logs_act = QAction(m.T("Показать логи приложения", "Show Application Logs"), sys_menu)
        app_logs_act.triggered.connect(lambda: m.app_log_window.show() if m.app_log_window else None)
        sys_menu.addAction(app_logs_act)
        
        ast_act = QAction(m.T("Настройки автозапуска", "Autostart Settings"), sys_menu)
        ast_act.triggered.connect(lambda: subprocess.Popen([sys.executable, os.path.join(m.CURRENT_DIR, "ui/autostart_settings.pyw")], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        sys_menu.addAction(ast_act)
        sys_menu.addAction(m.T("Очистка кеша", "Clear Cache"), lambda: m.utils.run_script(m.CACHER_SCRIPT))
        sys_menu.addAction(m.T("Открыть папку проекта", "Open Project Folder"), lambda: m.utils.open_project_folder(m.CURRENT_DIR))
        sys_menu.addAction(m.T("Создать ярлык на рабочем столе", "Create Desktop Shortcut"), lambda: m.utils.run_script("system_utils.py", ["yarlik", os.path.basename(__file__)]))
        sys_menu.addAction(m.T("Открыть свойства браузера", "Open Browser Properties"), m.utils.open_browser_properties)
        # Управление DNS
        dns_menu = QMenu(m.T("Управление DNS (Требует прав Админа)", "DNS Management (Requires Admin)"), sys_menu)
        
        comms_dns_act = QAction(m.T("Установить Comms DNS (IPv4)", "Set Comms DNS (IPv4)"), dns_menu)
        comms_dns_act.triggered.connect(lambda: m.set_dns("comms"))
        dns_menu.addAction(comms_dns_act)

        xbox_dns_act = QAction(m.T("Установить Xbox DNS (IPv4)", "Set Xbox DNS (IPv4)"), dns_menu)
        xbox_dns_act.triggered.connect(lambda: m.set_dns("xbox"))
        dns_menu.addAction(xbox_dns_act)
        
        xbox_ipv6_dns_act = QAction(m.T("Установить Xbox DNS (с IPv6)", "Set Xbox DNS (with IPv6)"), dns_menu)
        xbox_ipv6_dns_act.triggered.connect(lambda: m.set_dns("xbox_ipv6"))
        dns_menu.addAction(xbox_ipv6_dns_act)

        dns_menu.addSeparator()

        reset_dns_act = QAction(m.T("Сбросить DNS (По умолчанию)", "Reset DNS (Default)"), dns_menu)
        reset_dns_act.triggered.connect(lambda: m.set_dns("reset"))
        dns_menu.addAction(reset_dns_act)
        
        sys_menu.addMenu(dns_menu)

        
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
            m.config["ui_type"] = "window" if current == "tray" else "tray"
            m.config_manager.save_config(m.config)
            m.update_menu()
        ui_type_act.triggered.connect(toggle_ui_type)
        sys_menu.addAction(ui_type_act)
            
        m.tray_menu.addMenu(sys_menu)
        
        m.tray_menu.addSeparator()
        
        m_act = QAction(m.T("Перейти в простой режим", "Switch to Simple Mode"), m.tray_menu); m_act.triggered.connect(m.toggle_mode); m.tray_menu.addAction(m_act)
        restart_act = QAction(m.T("Перезапуск", "Restart"), m.tray_menu); restart_act.triggered.connect(m.restart_app); m.tray_menu.addAction(restart_act)
        e_act = QAction(m.T("Выход", "Exit"), m.tray_menu); e_act.triggered.connect(m.exit_app); m.tray_menu.addAction(e_act)



