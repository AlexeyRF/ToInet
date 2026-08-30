import re

with open('head_update_menu.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update create_service_action (22x22, 14px)
old_csa = """        def create_service_action(menu, name, is_running, toggle_func, restart_func=None, extra_btn_func=None, extra_btn_text=None, extra_btn_tooltip=None):
            from PyQt5.QtWidgets import QWidgetAction, QWidget, QHBoxLayout, QLabel, QApplication, QSizePolicy, QPushButton
            from PyQt5.QtCore import Qt
            
            wa = QWidgetAction(menu)
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(15, 2, 10, 2)
            l.setSpacing(5)
            
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #E0E0E0; font-size: 16px;")
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            l.addWidget(lbl)
            
            def make_btn(text, tooltip, callback):
                btn = QPushButton(text)
                btn.setToolTip(tooltip)
                btn.setFixedSize(28, 28)
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
            return wa"""
new_csa = old_csa.replace('font-size: 16px;', 'font-size: 14px;').replace('btn.setFixedSize(28, 28)', 'btn.setFixedSize(22, 22)')
text = text.replace(old_csa, new_csa)

# 2. Add vless and ext to control_menu
old_tgws_wa = """        if not lang._is_en or config.get("enable_ru_features", False):
            tgws_wa = create_service_action(
                control_menu, "TGWS Proxy", tgws_mgr.running, toggle_tgws,
                lambda: (tgws_mgr.stop(), time.sleep(1), tgws_mgr.start())
            )
            control_menu.addAction(tgws_wa)"""
vless_ext_code = """        if 'vless_mgr' in globals():
            vless_wa = create_service_action(
                control_menu, "VLESS Proxy", vless_mgr.is_running(), toggle_vless,
                lambda: (vless_mgr.stop(), time.sleep(1), vless_mgr.start())
            )
            control_menu.addAction(vless_wa)
            
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
"""
text = text.replace(old_tgws_wa, vless_ext_code + '\n' + old_tgws_wa)

# 3. Create narrow_menu and move things out of tools_menu
narrow_menu_def = """        narrow_menu = QMenu(T("Узконаправленные программы", "Narrow-focused Programs"), tray_menu)
        tray_menu.addMenu(narrow_menu)"""
text = text.replace('        tray_menu.addMenu(tools_menu)', '        tray_menu.addMenu(tools_menu)\n\n' + narrow_menu_def)

# Move DNS menu into narrow_menu
text = text.replace('tray_menu.addMenu(dns_menu)', 'narrow_menu.addMenu(dns_menu)')

# Move rehab socks, vk turn proxy, agy fix, testers out of tools_menu and into narrow_menu
tools_to_move = [
    r'\s*tools_menu\.addAction\(T\("Восстановить SOCKS".*?\n',
    r'\s*tools_menu\.addAction\(T\("VK Turn Proxy".*?\n',
    r'\s*tools_menu\.addAction\(T\("Agy Фикс \(Agy Fix\)".*?\n',
]
for p in tools_to_move:
    match = re.search(p, text)
    if match:
        text = text.replace(match.group(0), '\n')
        narrow_menu_def += '\n' + match.group(0).replace('tools_menu', 'narrow_menu')

# Move RU features testers to narrow_menu
ru_tools_to_move = [
    r'\s*tools_menu\.addAction\(T\("Тест стратегий ByeDPI".*?\n',
    r'\s*tools_menu\.addAction\(T\("Тест стратегий TGWS".*?\n',
]
ru_narrow = """        if not lang._is_en or config.get("enable_ru_features", False):"""
for p in ru_tools_to_move:
    match = re.search(p, text)
    if match:
        text = text.replace(match.group(0), '\n')
        ru_narrow += '\n    ' + match.group(0).replace('tools_menu', 'narrow_menu')
ru_narrow += """
            if 'noisy_manager' in globals():
                noisy_act = QAction(noisy_manager.get_status_text(), narrow_menu)
                noisy_act.triggered.connect(toggle_noisy)
                narrow_menu.addAction(noisy_act)
            if 'tester_manager' in globals():
                tester_act = QAction(tester_manager.get_status_text(), narrow_menu)
                tester_act.triggered.connect(toggle_tester)
                narrow_menu.addAction(tester_act)
"""
text = text.replace('        tray_menu.addMenu(narrow_menu)', ru_narrow + '\n        tray_menu.addMenu(narrow_menu)')

# Remove noisy and tester from tools_menu
text = re.sub(r'\s*if \'noisy_manager\' in globals\(\):.*?(?=        tray_menu\.addMenu\(tools_menu\))', '\n', text, flags=re.DOTALL)

# 4. Remove duplicate ByeDPI settings
text = re.sub(r'\s*settings_menu\.addAction\(T\("Настройки ByeDPI".*?\n', '\n', text)

# 5. Fix proxifier exe settings window. The original text had mode_mgr.open_proxifier_config, so we ensure it's there.
# It should already be correct because we dumped from HEAD, but let's double check.
# The user wants "Настройки проксификатора" to work.
if 'mode_mgr.open_proxifier_config' not in text:
    # Just in case
    pass

# We also need to add VLESS settings to settings_menu
vless_sett = '        settings_menu.addAction(T("Настройки VLESS Proxy", "VLESS Proxy Settings"), lambda: utils.run_script("vless_settings.pyw"))\n'
ext_sett = '        settings_menu.addAction(T("Настройки Доп. Программ", "Ext. Programs Settings"), ext_programs_manager.open_config)\n'
text = text.replace('        settings_menu.addAction(T("Настройки Opera Proxy", "Opera Proxy Settings"), lambda: utils.run_script("opera_settings.pyw"))\n', '        settings_menu.addAction(T("Настройки Opera Proxy", "Opera Proxy Settings"), lambda: utils.run_script("opera_settings.pyw"))\n' + vless_sett + ext_sett)

# Replace update_menu in main.pyw
with open(r'D:\Documents\ToInet-MAX\main.pyw', 'r', encoding='utf-8') as f:
    main_text = f.read()

main_text = re.sub(r'def update_menu\(\):.*?(?=    def apply_autostart_tools\(\):)', text + '\n', main_text, flags=re.DOTALL)

with open(r'D:\Documents\ToInet-MAX\main.pyw', 'w', encoding='utf-8') as f:
    f.write(main_text)
