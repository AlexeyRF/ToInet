import re

with open(r'D:\Documents\ToInet-MAX\main.pyw', 'r', encoding='utf-8') as f:
    text = f.read()

new_update_menu = """def update_menu():
    global tray_menu
    if tray_menu is None: return
    tray_menu.clear()
    
    if simple_mode:
        all_act = QAction(T("Запустить", "Start") if not proxy_enabled else T("Остановить всё", "Stop All"), tray_menu)
        all_act.triggered.connect(toggle_all)
        tray_menu.addAction(all_act)
        
        if mode_type == "inetcpl":
            tor_cpl = QAction(T("Включить TOR", "Connect to TOR") if not mode_mgr.inetcpl_tor_active else T("Отключить TOR", "Disconnect from TOR"), tray_menu)
            tor_cpl.triggered.connect(toggle_inetcpl_tor)
            tray_menu.addAction(tor_cpl)
            
            bd_cpl = QAction(T("Включить BD", "Connect to BD") if not mode_mgr.inetcpl_bd_active else T("Отключить BD", "Disconnect from BD"), tray_menu)
            bd_cpl.triggered.connect(toggle_inetcpl_bd)
            tray_menu.addAction(bd_cpl)
            
            opera_cpl = QAction(T("Включить Opera", "Connect to Opera") if not mode_mgr.inetcpl_opera_active else T("Отключить Opera", "Disconnect from Opera"), tray_menu)
            opera_cpl.triggered.connect(toggle_inetcpl_opera)
            tray_menu.addAction(opera_cpl)
       
        tray_menu.addSeparator()
        mode_m = QMenu(T("Режим", "Mode"), tray_menu)
        for m in ["empty", "inetcpl", "tun"]:
            act = QAction(m.capitalize() + (" (Proxy)" if m=="tun" else ""), mode_m)
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
        def create_service_action(menu, name, is_running, toggle_func, restart_func=None, extra_btn_func=None, extra_btn_text=None, extra_btn_tooltip=None):
            from PyQt5.QtWidgets import QWidgetAction, QWidget, QHBoxLayout, QLabel, QApplication, QSizePolicy, QPushButton
            from PyQt5.QtCore import Qt
            
            wa = QWidgetAction(menu)
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(15, 2, 10, 2)
            l.setSpacing(5)
            
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #E0E0E0; font-size: 14px;")
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            l.addWidget(lbl)
            
            def make_btn(text, tooltip, callback):
                btn = QPushButton(text)
                btn.setToolTip(tooltip)
                btn.setFixedSize(22, 22)
                btn.setStyleSheet(\"\"\"
                    QPushButton {
                        color: #E0E0E0;
                        background: rgba(255, 255, 255, 0.05);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 4px;
                        font-size: 14px;
                        padding-bottom: 2px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.15);
                        border: 1px solid rgba(255, 255, 255, 0.3);
                    }
                    QPushButton:pressed {
                        background: rgba(255, 255, 255, 0.02);
                    }
                \"\"\")
                btn.setCursor(Qt.PointingHandCursor)
                if callback:
                    btn.clicked.connect(callback)
                    btn.clicked.connect(menu.hide)
                return btn
            
            btn_play = make_btn("■" if is_running else "▶", T("Остановить", "Stop") if is_running else T("Запустить", "Start"), toggle_func)
            if is_running:
                btn_play.setStyleSheet(btn_play.styleSheet().replace("color: #E0E0E0;", "color: #ff5555;"))
            else:
                btn_play.setStyleSheet(btn_play.styleSheet().replace("color: #E0E0E0;", "color: #55ff55;"))
            l.addWidget(btn_play)
            
            if is_running and restart_func:
                btn_restart = make_btn("↻", T("Перезапустить", "Restart"), restart_func)
                l.addWidget(btn_restart)
                
            if is_running and extra_btn_func and extra_btn_text:
                btn_extra = make_btn(extra_btn_text, extra_btn_tooltip, extra_btn_func)
                l.addWidget(btn_extra)
                
            w.setStyleSheet("QWidget:hover { background: rgba(255, 255, 255, 0.05); }")
            wa.setDefaultWidget(w)
            return wa

        control_menu = QMenu(T("Управление компонентами", "Service Control"), tray_menu)
        
        tor_wa = create_service_action(
            control_menu, "TOR", tor_manager.is_running(), toggle_tor, tor_manager.restart,
            extra_btn_func=tor_manager.new_circuit, extra_btn_text="✦", extra_btn_tooltip=T("Новая цепь", "New Circuit")
        )
        control_menu.addAction(tor_wa)
        
        bd_wa = create_service_action(
            control_menu, "ByeDPI", byedpi_manager.is_running(), toggle_byedpi,
            lambda: (byedpi_manager.stop(), time.sleep(1), byedpi_manager.start())
        )
        control_menu.addAction(bd_wa)
        
        opera_wa = create_service_action(
            control_menu, "Opera Proxy", opera_mgr.is_running(), toggle_opera,
            lambda: (opera_mgr.stop(), time.sleep(1), opera_mgr.start())
        )
        control_menu.addAction(opera_wa)
        
        if 'vless_mgr' in globals():
            vless_wa = create_service_action(
                control_menu, "VLESS Proxy", vless_mgr.is_running(), toggle_vless,
                lambda: (vless_mgr.stop(), time.sleep(1), vless_mgr.start())
            )
            control_menu.addAction(vless_wa)
        
        if not lang._is_en or config.get("enable_ru_features", False):
            tgws_wa = create_service_action(
                control_menu, "TGWS Proxy", tgws_mgr.running, toggle_tgws,
                lambda: (tgws_mgr.stop(), time.sleep(1), tgws_mgr.start())
            )
            control_menu.addAction(tgws_wa)
            
        if 'ext_programs_manager' in globals():
            def toggle_ext():
                if ext_programs_manager.is_running(): ext_programs_manager.stop_all()
                else: ext_programs_manager.start_all()
                update_menu()
            ext_wa = create_service_action(
                control_menu, T("Доп. программы", "Ext. Programs"), ext_programs_manager.is_running(), toggle_ext,
                ext_programs_manager.restart_all
            )
            control_menu.addAction(ext_wa)
        
        control_menu.addSeparator()
        
        tun_wa = create_service_action(
            control_menu, T("Проксификатор", "Proxifier"), mode_mgr.tun_running(), toggle_proxifier, mode_mgr.restart_tun
        )
        control_menu.addAction(tun_wa)
        
        tray_menu.addMenu(control_menu)
        
        # 2. Настройки Компонентов
        settings_menu = QMenu(T("Настройки Компонентов", "Component Settings"), tray_menu)
        settings_menu.addAction(T("Настройки BD", "BD Settings"), lambda: mode_mgr.open_bd_config())
        if not lang._is_en or config.get("enable_ru_features", False):
            settings_menu.addAction(T("Настройки TGWS", "TGWS Settings"), lambda: utils.run_script("tgws/settings.pyw"))
        settings_menu.addAction(T("Настройки Opera Proxy", "Opera Proxy Settings"), lambda: utils.run_script("opera_settings.pyw"))
        settings_menu.addAction(T("Настройки VLESS Proxy", "VLESS Proxy Settings"), lambda: utils.run_script("vless_settings.pyw"))
        if 'ext_programs_manager' in globals():
            settings_menu.addAction(T("Настройки Доп. Программ", "Ext. Programs Settings"), ext_programs_manager.open_config)
        
        settings_menu.addSeparator()
        settings_menu.addAction(T("Настройки Проксификатора", "Configure Proxifier"), mode_mgr.open_proxifier_config)
        tray_menu.addMenu(settings_menu)
        
        # 3. Инструменты и Утилиты
        tools_menu = QMenu(T("Инструменты и Утилиты", "Tools & Utilities"), tray_menu)
        tools_menu.addAction(T("Очистить кэш", "Clear Cache"), lambda: utils.run_script(CACHER_SCRIPT))
        tools_menu.addAction(T("Открыть папку проекта", "Open Project Folder"), lambda: utils.open_project_folder(CURRENT_DIR))
        tools_menu.addAction(T("Создать ярлык на рабочем столе", "Create Desktop Shortcut"), lambda: utils.run_script("yarlik.pyw", [os.path.basename(__file__)]))
        tools_menu.addAction(T("Редактировать мосты", "Edit Bridges"), lambda: utils.run_script("edit_bridges.pyw"))
        tools_menu.addAction(T("Удалить конфиг TOR", "Delete TOR Config"), tor_manager.delete_config)
        tray_menu.addMenu(tools_menu)
        
        narrow_menu = QMenu(T("Узконаправленные программы", "Narrow-focused Programs"), tray_menu)
        
        narrow_menu.addAction(T("Восстановить SOCKS", "Rehabilitate SOCKS"), lambda: utils.run_script("socks-reabilitator.pyw"))
        narrow_menu.addAction(T("VK Turn Proxy", "VK Turn Proxy Launcher"), lambda: utils.run_script("vk_turn_proxy_gui.pyw"))
        narrow_menu.addAction(T("Agy Фикс (Agy Fix)", "Agy Fix"), lambda: utils.run_console_script("gemini_fixik.py") if 'run_agy_fix' not in globals() else run_agy_fix)
        if not lang._is_en or config.get("enable_ru_features", False):
            narrow_menu.addAction(T("Тест стратегий ByeDPI", "ByeDPI Strategies Tester"), lambda: utils.run_script("byedpi_tester_gui.pyw"))
            narrow_menu.addAction(T("Тест стратегий TGWS", "TGWS Strategies Tester"), lambda: utils.run_script("tgws/tester_gui.pyw"))
            if 'noisy_manager' in globals():
                noisy_act = QAction(noisy_manager.get_status_text(), narrow_menu)
                noisy_act.triggered.connect(toggle_noisy)
                narrow_menu.addAction(noisy_act)
            if 'tester_manager' in globals():
                tester_act = QAction(tester_manager.get_status_text(), narrow_menu)
                tester_act.triggered.connect(toggle_tester)
                narrow_menu.addAction(tester_act)
                
        # DNS
        dns_menu = QMenu(T("Управление DNS (Требует админа)", "DNS Management (Requires Admin)"), tray_menu)
        comms_dns_act = QAction(T("Поставить Comms DNS (IPv4)", "Set Comms DNS (IPv4)"), dns_menu)
        comms_dns_act.triggered.connect(lambda: set_dns("comms"))
        dns_menu.addAction(comms_dns_act)

        xbox_dns_act = QAction(T("Поставить Xbox DNS (IPv4)", "Set Xbox DNS (IPv4)"), dns_menu)
        xbox_dns_act.triggered.connect(lambda: set_dns("xbox"))
        dns_menu.addAction(xbox_dns_act)
        
        xbox_ipv6_dns_act = QAction(T("Поставить Xbox DNS (с IPv6)", "Set Xbox DNS (with IPv6)"), dns_menu)
        xbox_ipv6_dns_act.triggered.connect(lambda: set_dns("xbox_ipv6"))
        dns_menu.addAction(xbox_ipv6_dns_act)

        dns_menu.addSeparator()

        reset_dns_act = QAction(T("Сбросить DNS (По умолчанию)", "Reset DNS (Default)"), dns_menu)
        reset_dns_act.triggered.connect(lambda: set_dns("reset"))
        dns_menu.addAction(reset_dns_act)
        
        narrow_menu.addMenu(dns_menu)
        tray_menu.addMenu(narrow_menu)
        
        # 4. Интеграция с Telegram
        tg_menu = QMenu(T("Интеграция с Telegram", "Telegram Integration"), tray_menu)
        if not lang._is_en or config.get("enable_ru_features", False):
            tg_menu.addAction(T("Добавить TGWS SOCKS5 (1480) в Telegram", "Add TGWS SOCKS5 (1480) to Telegram"), lambda: utils.add_proxy_to_telegram(config.get("tgws_port", 1480)))
            tg_menu.addAction(T("Добавить TGWS MTProto (1480) в Telegram", "Add TGWS MTProto (1480) to Telegram"), lambda: utils.add_mtproto_to_telegram(config.get("tgws_port", 1480), config.get("tgws_secret", "0"*32), config.get("tgws_fake_tls", "")))
            tg_menu.addAction(T("Добавить Роутер Gatik (1777) в Telegram", "Add Smart Router (1777) to Telegram"), lambda: utils.add_proxy_to_telegram(1777))
        tg_menu.addAction(T("Добавить TOR (9853) в Telegram", "Add TOR (9853) to Telegram"), lambda: utils.add_proxy_to_telegram(9853))
        tg_menu.addAction(T("Добавить BD (1780) в Telegram", "Add BD (1780) to Telegram"), lambda: utils.add_proxy_to_telegram(1780))
        tg_menu.addAction(T("Добавить Opera SOCKS5 (1786) в Telegram", "Add Opera SOCKS5 (1786) to Telegram"), lambda: utils.add_proxy_to_telegram(1786))
        tg_menu.addAction(T("Добавить Восстан. SOCKS (1788) в Telegram", "Add Rehab. SOCKS (1788) to Telegram"), lambda: utils.add_proxy_to_telegram(1788))
        tray_menu.addMenu(tg_menu)
        
        # 5. pip-запросы
        pip_menu = QMenu(T("Настройки pip", "pip Settings"), tray_menu)
        pip_menu.addAction(T("Установить глобально (HTTP_PROXY)", "Set Global (HTTP_PROXY)"), lambda: utils.run_script("pip-global.pyw"))
        pip_menu.addAction(T("Сбросить глобальные настройки", "Reset Global Settings"), lambda: utils.run_script("pip-reset.pyw"))
        pip_menu.addAction(T("Настройки ByeDPI для pip", "ByeDPI Settings for pip"), lambda: bdsher.get_pip_manager(config).open_settings())
        tray_menu.addMenu(pip_menu)
        
        tray_menu.addSeparator()
        
        # 6. Режим работы
        mode_m = QMenu(T("Режим работы", "Operation Mode"), tray_menu)
        for m in ["empty", "inetcpl", "tun"]:
            act = QAction(m.capitalize() + (" (Proxy)" if m=="tun" else ""), mode_m)
            act.setCheckable(True)
            act.setChecked(mode_type == m)
            act.triggered.connect(lambda checked, mode=m: set_mode_type(mode))
            mode_m.addAction(act)
        tray_menu.addMenu(mode_m)
        
        # Системные опции
        sys_menu = QMenu(T("Системные опции", "System Options"), tray_menu)
        
        app_logs_act = QAction(T("Показать логи приложения", "Show Application Logs"), sys_menu)
        app_logs_act.triggered.connect(lambda: app_log_window.show() if app_log_window else None)
        sys_menu.addAction(app_logs_act)
        
        ast_act = QAction(T("Настройки автозапуска", "Autostart Settings"), sys_menu)
        ast_act.triggered.connect(lambda: subprocess.Popen([sys.executable, os.path.join(CURRENT_DIR, "autostart_settings.pyw")], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        sys_menu.addAction(ast_act)
        
        acl_act = QAction(T("Подключать прошлый режим при запуске", "Connect Last Mode on Start"), sys_menu); acl_act.setCheckable(True); acl_act.setChecked(config.get("auto_connect_last_mode", False)); acl_act.triggered.connect(toggle_auto_connect_last_mode); sys_menu.addAction(acl_act)
        
        rec_act = QAction(T("Отключить пересоздание torrc", "Disable torrc Recreation") if tor_manager.get_recreate_status() else T("Включить пересоздание torrc", "Enable torrc Recreation"), sys_menu)
        rec_act.triggered.connect(lambda: (tor_manager.toggle_recreate(), update_menu())); sys_menu.addAction(rec_act)
        
        tshow_act = QAction(T("Показывать окно TOR при старте", "Show TOR Window on Start"), sys_menu); tshow_act.setCheckable(True); tshow_act.setChecked(config.get("tor_show_window", False)); tshow_act.triggered.connect(toggle_tor_show_window); sys_menu.addAction(tshow_act)
        
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
        
        set_act = QAction(T("Настройки приложения", "Application Settings"), tray_menu)
        set_act.triggered.connect(toggle_mode)
        tray_menu.addAction(set_act)
        
        restart_act = QAction(T("Перезапуск", "Restart"), tray_menu)
        restart_act.triggered.connect(restart_app)
        tray_menu.addAction(restart_act)
        
        exit_act = QAction(T("Выход", "Exit"), tray_menu)
        exit_act.triggered.connect(exit_app)
        tray_menu.addAction(exit_act)
"""

text = re.sub(r'def update_menu\(\):.*?(?=    def apply_autostart_tools\(\):)', new_update_menu + '\n', text, flags=re.DOTALL)

with open(r'D:\Documents\ToInet-MAX\main.pyw', 'w', encoding='utf-8') as f:
    f.write(text)
