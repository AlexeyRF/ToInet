import sys
import platform
import subprocess
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QApplication, QStackedWidget, QScrollArea, QFrame, QComboBox, QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class SettingRow(QFrame):
    def __init__(self, title, description, control_widget, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            SettingRow {
                background-color: #2b2b2b;
                border-radius: 8px;
            }
            SettingRow:hover {
                background-color: #333333;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        text_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #aaaaaa;")
        desc_label.setWordWrap(True)
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        layout.addSpacing(10)
        
        control_layout = QVBoxLayout()
        control_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        control_layout.addWidget(control_widget)
        
        layout.addLayout(control_layout)

class MainWindow(QMainWindow):
    def __init__(self, main_module):
        super().__init__()
        self.main_module = main_module
        self.setWindowTitle("ToInet-MAX")
        self.setFixedSize(400, 600)
        self.setStyleSheet("background-color: #121212; color: #ffffff;")
        
        if platform.system() == "Windows":
            try:
                import ctypes
                hwnd = int(self.winId())
                value = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
                color = ctypes.c_int(0x00121212)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
            except Exception:
                pass

        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)
        
        self.main_view = QWidget()
        self.settings_view = QWidget()
        self.modules_view = QWidget()
        
        self.stacked.addWidget(self.main_view)
        self.stacked.addWidget(self.settings_view)
        self.stacked.addWidget(self.modules_view)
        
        self.build_main_view()
        self.build_settings_view()
        self.build_modules_view()

    def build_main_view(self):
        main_layout = QVBoxLayout(self.main_view)
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignTop)
        
        self.title_label = QLabel("ToInet-MAX")
        self.title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.title_label.setStyleSheet("color: #ffffff; letter-spacing: 2px;")
        
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setFont(QFont("Segoe UI", 18))
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #aaaaaa;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """)
        self.settings_btn.clicked.connect(self.show_settings)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.settings_btn)
        
        main_layout.addLayout(header_layout)
        
        if hasattr(self.main_module, 'evpn_mgr'):
            self.main_module.evpn_mgr.status_changed.connect(self.set_status)
            self.main_module.evpn_mgr.error_occurred.connect(self.show_error)
        
        main_layout.addSpacing(40)

        self.toggle_btn = QPushButton("OFF")
        self.toggle_btn.setFixedSize(160, 160)
        self.toggle_btn.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.set_btn_style_disconnected()
        self.toggle_btn.clicked.connect(self.toggle_vpn)
        
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(self.toggle_btn)
        main_layout.addLayout(btn_layout)
        
        main_layout.addSpacing(20)
        
        self.next_btn = QPushButton("Сменить сервер")
        self.next_btn.setFixedSize(160, 40)
        self.next_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border-radius: 20px;
                border: 2px solid #444444;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        self.next_btn.clicked.connect(self.next_server)
        self.next_btn.hide()
        
        next_btn_layout = QHBoxLayout()
        next_btn_layout.setAlignment(Qt.AlignCenter)
        next_btn_layout.addWidget(self.next_btn)
        main_layout.addLayout(next_btn_layout)
        
        main_layout.addSpacing(20)

        self.status_label = QLabel("Отключено")
        self.status_label.setFont(QFont("Segoe UI", 16))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #aaaaaa;")
        main_layout.addWidget(self.status_label)
        
        main_layout.addSpacing(20)

        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Segoe UI", 10))
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #ff5555;")
        self.error_label.setWordWrap(True)
        main_layout.addWidget(self.error_label)
        
        main_layout.addStretch()

    def build_settings_view(self):
        T = self.main_module.T
        layout = QVBoxLayout(self.settings_view)
        layout.setContentsMargins(10, 10, 10, 10)
        
        header = QHBoxLayout()
        back_btn = QPushButton("←")
        back_btn.setFixedSize(40, 40)
        back_btn.setFont(QFont("Segoe UI", 18, QFont.Bold))
        back_btn.setStyleSheet("""
            QPushButton { background: transparent; color: white; border: none; border-radius: 20px; }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.hide_settings)
        
        title = QLabel(T("Настройки", "Settings"))
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        
        header.addWidget(back_btn)
        header.addWidget(title)
        header.addStretch()
        
        layout.addLayout(header)
        layout.addSpacing(10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #555; border-radius: 4px; }
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # Mode Combo
        mode_combo = QComboBox()
        mode_combo.addItems(["EMPTY", "INETCPL", "TUN", "EVPN"])
        mode_combo.setCurrentText(self.main_module.mode_type.upper())
        mode_combo.setStyleSheet("""
            QComboBox { background: #333; border: 1px solid #555; border-radius: 4px; color: white; padding: 5px; min-width: 100px; font-family: 'Segoe UI'; font-size: 13px; }
            QComboBox::drop-down { border: none; }
        """)
        mode_combo.setCursor(Qt.PointingHandCursor)
        def on_mode_change(text):
            self.main_module.set_mode_type(text.lower())
        mode_combo.currentTextChanged.connect(on_mode_change)
        content_layout.addWidget(SettingRow(T("Режим", "Proxy Mode"), T("Способ перенаправления трафика", "How traffic is redirected"), mode_combo))
        
        # Interface Combo
        ui_combo = QComboBox()
        ui_combo.addItems([T("Окно", "Window"), T("Трей", "Tray")])
        ui_combo.setCurrentIndex(0 if self.main_module.config.get("ui_type", "tray") == "window" else 1)
        ui_combo.setStyleSheet(mode_combo.styleSheet())
        ui_combo.setCursor(Qt.PointingHandCursor)
        def on_ui_change(idx):
            self.main_module.config["ui_type"] = "window" if idx == 0 else "tray"
            self.main_module.config_manager.save_config(self.main_module.config)
            if hasattr(self.main_module, 'update_menu'):
                self.main_module.update_menu()
        ui_combo.currentIndexChanged.connect(on_ui_change)
        content_layout.addWidget(SettingRow(T("Интерфейс", "Interface"), T("Внешний вид (Окно или меню в трее)", "Window vs Tray menu"), ui_combo))
        
        # Simple Mode Button
        simple_btn = QPushButton(T("Сменить", "Toggle"))
        simple_btn.setStyleSheet("""
            QPushButton { background: #005FB8; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-family: 'Segoe UI'; }
            QPushButton:hover { background: #0078D4; }
        """)
        simple_btn.setCursor(Qt.PointingHandCursor)
        simple_btn.clicked.connect(self.main_module.toggle_mode)
        content_layout.addWidget(SettingRow(T("Вид меню", "Menu Mode"), T("Отображение расширенного меню трея", "Toggle simple/advanced tray menu"), simple_btn))
        
        # Auto Start Checkbox
        # We simulate a modern switch with a checkbox
        auto_start = QCheckBox()
        auto_start.setChecked(self.main_module.config.get("auto_start", False))
        auto_start.setStyleSheet("""
            QCheckBox::indicator { width: 40px; height: 20px; }
        """)
        auto_start.setCursor(Qt.PointingHandCursor)
        def on_auto_start():
            if hasattr(self.main_module, 'toggle_auto_start'):
                self.main_module.toggle_auto_start()
        auto_start.clicked.connect(on_auto_start)
        content_layout.addWidget(SettingRow(T("Автозапуск", "Auto Start"), T("Запускать при старте системы", "Run on system startup"), auto_start))
        
        # EVPN Encrypted DNS Checkbox
        evpn_dns = QCheckBox()
        evpn_dns.setChecked(self.main_module.config.get("evpn_encrypted_dns", False))
        evpn_dns.setStyleSheet("QCheckBox::indicator { width: 40px; height: 20px; }")
        evpn_dns.setCursor(Qt.PointingHandCursor)
        def on_evpn_dns():
            self.main_module.config["evpn_encrypted_dns"] = evpn_dns.isChecked()
            if hasattr(self.main_module, 'config_manager'):
                self.main_module.config_manager.save_config(self.main_module.config)
        evpn_dns.clicked.connect(on_evpn_dns)
        content_layout.addWidget(SettingRow(T("Шифрованный DNS (EVPN)", "Encrypted DNS (EVPN)"), T("Использовать 111.88.96.54/55 (вступит после переподключения)", "Use 111.88.96.54/55 (takes effect on reconnect)"), evpn_dns))
        
        # TUN/EVPN Proxy DNS Checkbox
        proxy_dns = QCheckBox()
        proxy_dns.setChecked(self.main_module.config.get("proxy_dns_tun_evpn", True))
        proxy_dns.setStyleSheet("QCheckBox::indicator { width: 40px; height: 20px; }")
        proxy_dns.setCursor(Qt.PointingHandCursor)
        def on_proxy_dns():
            self.main_module.config["proxy_dns_tun_evpn"] = proxy_dns.isChecked()
            if hasattr(self.main_module, 'config_manager'):
                self.main_module.config_manager.save_config(self.main_module.config)
        proxy_dns.clicked.connect(on_proxy_dns)
        content_layout.addWidget(SettingRow(T("Проксировать DNS (TUN/EVPN)", "Proxy DNS (TUN/EVPN)"), T("Направлять DNS-запросы через прокси (вступит после переподключения)", "Route DNS requests through proxy (takes effect on reconnect)"), proxy_dns))
        
        # Restart Button
        restart_btn = QPushButton(T("Перезапуск", "Restart App"))
        restart_btn.setStyleSheet("""
            QPushButton { background: #333333; color: white; border: 1px solid #555555; border-radius: 4px; padding: 6px 12px; font-family: 'Segoe UI'; font-weight: bold;}
            QPushButton:hover { background: #444444; }
        """)
        restart_btn.setCursor(Qt.PointingHandCursor)
        restart_btn.clicked.connect(self.main_module.restart_app)
        content_layout.addWidget(SettingRow(T("Перезапуск", "Restart"), T("Перезапустить все процессы", "Restart all processes"), restart_btn))
        
        # Exit Button
        exit_btn = QPushButton(T("Выйти", "Exit App"))
        exit_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #ff5555; border: 1px solid #ff5555; border-radius: 4px; padding: 6px 12px; font-family: 'Segoe UI'; font-weight: bold;}
            QPushButton:hover { background: rgba(255, 85, 85, 0.1); }
        """)
        exit_btn.setCursor(Qt.PointingHandCursor)
        exit_btn.clicked.connect(self.main_module.exit_app)
        content_layout.addWidget(SettingRow(T("Завершение", "Termination"), T("Полностью закрыть приложение", "Completely close the application"), exit_btn))
        
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def set_btn_style_disconnected(self):
        self.toggle_btn.setText("OFF")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: #888888;
                border-radius: 80px;
                border: 6px solid #333333;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #444444;
            }
            QPushButton:pressed {
                background-color: #222222;
                border-color: #2a2a2a;
            }
        """)

    def set_btn_style_connected(self):
        self.toggle_btn.setText("ON")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1abc9c;
                color: #ffffff;
                border-radius: 80px;
                border: 6px solid #16a085;
            }
            QPushButton:hover {
                background-color: #1dd2af;
                border-color: #1abc9c;
            }
            QPushButton:pressed {
                background-color: #12876f;
                border-color: #16a085;
            }
        """)
        
    def set_btn_style_transitioning(self):
        self.toggle_btn.setText("...")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: #ffffff;
                border-radius: 80px;
                border: 6px solid #d35400;
            }
            QPushButton:hover {
                background-color: #f39c12;
                border-color: #e67e22;
            }
        """)

    def toggle_vpn(self):
        self.error_label.setText("")
        self.main_module.toggle_all()
        self.update_ui_state()
            
    def next_server(self):
        if hasattr(self.main_module, 'evpn_mgr') and self.main_module.evpn_mgr.is_running:
            self.main_module.evpn_mgr.next_server()
            
    def set_status(self, text):
        if "VPN Включен" in text or "Подключено" in text:
            self.status_label.setText("Подключено")
            self.status_label.setStyleSheet("color: #1abc9c; font-weight: bold;")
            self.set_btn_style_connected()
            if hasattr(self.main_module, 'evpn_mgr') and self.main_module.evpn_mgr.is_running:
                self.next_btn.show()
            else:
                self.next_btn.hide()
        elif "VPN Выключен" in text or "Отключено" in text:
            self.status_label.setText("Отключено")
            self.status_label.setStyleSheet("color: #aaaaaa;")
            self.set_btn_style_disconnected()
            self.next_btn.hide()
        else:
            self.status_label.setText(text)
            self.status_label.setStyleSheet("color: #e67e22;")
            self.set_btn_style_transitioning()
            if "Переключение" not in text:
                self.next_btn.hide()


    def show_modules(self):
        self.update_modules_state()
        self.stacked.setCurrentWidget(self.modules_view)

    def hide_modules(self):
        self.stacked.setCurrentWidget(self.main_view)

    def update_modules_state(self):
        # Update text/colors based on running status
        if hasattr(self, 'module_btns'):
            for btn, check_func in self.module_btns:
                is_running = check_func()
                btn.setText(self.main_module.T("Остановить", "Stop") if is_running else self.main_module.T("Запустить", "Start"))
                btn.setStyleSheet(f"QPushButton {{ background: {'#ff5555' if is_running else '#1abc9c'}; color: white; font-weight: bold; border: none; border-radius: 4px; padding: 6px 12px; }} QPushButton:hover {{ background: {'#ff6666' if is_running else '#1dd2af'}; }}")

    def build_modules_view(self):
        T = getattr(self.main_module, 'T', lambda ru, en: ru)
        layout = QVBoxLayout(self.modules_view)
        layout.setContentsMargins(10, 10, 10, 10)
        
        header = QHBoxLayout()
        back_btn = QPushButton("←")
        back_btn.setFixedSize(40, 40)
        back_btn.setFont(QFont("Segoe UI", 18, QFont.Bold))
        back_btn.setStyleSheet("QPushButton { background: transparent; color: white; border: none; border-radius: 20px; } QPushButton:hover { background: rgba(255,255,255,0.1); }")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.hide_modules)
        
        title = QLabel(T("Модули и утилиты", "Modules and utilities"))
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        
        header.addWidget(back_btn)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        layout.addSpacing(10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; } QScrollBar:vertical { width: 8px; background: transparent; } QScrollBar::handle:vertical { background: #555; border-radius: 4px; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        self.module_btns = []
        
        def add_module(name, desc, toggle_func, check_func):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            def on_click():
                toggle_func()
                self.update_modules_state()
            btn.clicked.connect(on_click)
            self.module_btns.append((btn, check_func))
            content_layout.addWidget(SettingRow(name, desc, btn))
            
        m = self.main_module
        add_module("TOR", T("TOR Прокси (порт 9853)", "TOR Proxy (port 9853)"), m.toggle_tor, lambda: m.tor_manager.is_running())
        add_module("ByeDPI", T("Обход блокировок (порт 1080)", "DPI Bypass (port 1080)"), m.toggle_byedpi, lambda: m.byedpi_manager.is_running())
        add_module("Opera Proxy", T("Opera VPN (порт 1785)", "Opera VPN (port 1785)"), m.toggle_opera, lambda: m.opera_mgr.is_running())
        add_module("TG WS Proxy", T("Telegram прокси (порт 1480)", "Telegram proxy (port 1480)"), m.toggle_tgws, lambda: m.tgws_mgr.running)
        add_module("VLESS", T("VLESS прокси (порт 1790)", "VLESS proxy (port 1790)"), m.toggle_vless, lambda: m.vless_mgr.is_running())
        add_module("Noisy", T("Генератор мусорного трафика", "Traffic noise generator"), m.toggle_noisy, lambda: m.noisy_manager.is_running())
        add_module("Tester", T("Тестер прокси", "Proxy tester"), m.toggle_tester, lambda: m.tester_manager.is_running())
        add_module("Proxifier (TUN)", T("Глобальный TUN роутинг", "Global TUN routing"), m.toggle_proxifier, lambda: m.mode_mgr.proxifier_running())
        
        # EVPN Section
        evpn_label = QLabel(T("Опции EVPN", "EVPN Options"))
        evpn_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        content_layout.addWidget(evpn_label)
        
        evpn_exclusive_cb = QCheckBox()
        evpn_exclusive_cb.setChecked(m.config.get("evpn_exclusive_mode", True))
        evpn_exclusive_cb.setStyleSheet("QCheckBox::indicator { width: 40px; height: 20px; }")
        evpn_exclusive_cb.setCursor(Qt.PointingHandCursor)
        def on_evpn_exclusive():
            m.config["evpn_exclusive_mode"] = evpn_exclusive_cb.isChecked()
            if hasattr(m, 'config_manager'):
                m.config_manager.save_config(m.config)
        evpn_exclusive_cb.clicked.connect(on_evpn_exclusive)
        content_layout.addWidget(SettingRow(T("Эксклюзивный EVPN", "Exclusive EVPN"), T("Отключать TOR, BD и др. методы при запуске EVPN", "Disable TOR, BD, etc. when running EVPN"), evpn_exclusive_cb))
        
        # INETCPL section
        inetcpl_label = QLabel(T("INETCPL (Системный прокси)", "INETCPL (System Proxy)"))
        inetcpl_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        content_layout.addWidget(inetcpl_label)
        
        add_module("INETCPL -> TOR", T("Направить систему в TOR", "Route system to TOR"), m.toggle_inetcpl_tor, lambda: m.mode_mgr.inetcpl_tor_active)
        add_module("INETCPL -> ByeDPI", T("Направить систему в ByeDPI", "Route system to ByeDPI"), m.toggle_inetcpl_bd, lambda: m.mode_mgr.inetcpl_bd_active)
        add_module("INETCPL -> Opera", T("Направить систему в Opera", "Route system to Opera"), m.toggle_inetcpl_opera, lambda: m.mode_mgr.inetcpl_opera_active)
        add_module("INETCPL -> VLESS", T("Направить систему в VLESS", "Route system to VLESS"), m.toggle_inetcpl_vless, lambda: m.mode_mgr.inetcpl_vless_active)
        
        # TUN Proxy type
        tun_label = QLabel(T("TUN Направления (Sing-box)", "TUN Routes (Sing-box)"))
        tun_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        content_layout.addWidget(tun_label)
        
        add_module("TUN -> TOR", T("Завернуть TUN в TOR", "Route TUN to TOR"), m.toggle_singbox_tun_tor, lambda: m.mode_mgr.tun_proxy_port == 9853)
        add_module("TUN -> ByeDPI", T("Завернуть TUN в ByeDPI", "Route TUN to ByeDPI"), m.toggle_singbox_tun_bd, lambda: m.mode_mgr.tun_proxy_port == 1780)
        add_module("TUN -> Opera", T("Завернуть TUN в Opera", "Route TUN to Opera"), m.toggle_singbox_tun_opera, lambda: m.mode_mgr.tun_proxy_port == 1785)
        
        # DNS section

        dns_label = QLabel(T("DNS настройки (требуют прав админа)", "DNS settings (requires admin rights)"))
        dns_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        content_layout.addWidget(dns_label)
        
        def add_dns(name, mode):
            btn = QPushButton(T("Применить", "Apply"))
            btn.setStyleSheet("QPushButton { background: #005FB8; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; border: none; } QPushButton:hover { background: #0078D4; }")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda: m.set_dns(mode))
            content_layout.addWidget(SettingRow(name, T("Установить системный DNS", "Set system DNS"), btn))
            
        add_dns("Comms DNS", "comms")
        add_dns("Xbox DNS", "xbox")
        add_dns("Xbox DNS IPv6", "xbox_ipv6")
        add_dns("Сброс DNS", "reset")
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def show_settings(self):
        if hasattr(self, 'update_modules_state'): self.update_modules_state()
        self.stacked.setCurrentWidget(self.settings_view)

    def hide_settings(self):
        self.stacked.setCurrentWidget(self.main_view)

    def update_ui_state(self):
        if self.main_module.proxy_enabled:
            if getattr(self.main_module, 'mode_type', '') == 'evpn':
                pass # evpn_mgr will handle status updates
            else:
                self.set_status("Подключено")
        else:
            self.set_status("Отключено")

    def show_error(self, text):
        self.error_label.setText(text)

    def closeEvent(self, event):
        self.hide()
        event.ignore()
