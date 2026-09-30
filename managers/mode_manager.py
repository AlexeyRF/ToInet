import os
import sys
import subprocess
import time
from PyQt5.QtWidgets import QMessageBox
from managers import system_utils as lang
from managers import config_manager

import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPLLER_SCRIPT = os.path.join(CURRENT_DIR, "managers", "system_utils.py")

class ModeManager:
    def __init__(self):
        self.tun_process = None
        self.inetcpl_tor_active = False
        self.inetcpl_bd_active = False
        self.inetcpl_opera_active = False
        self.inetcpl_vless_active = False
        self.tun_proxy_port = 0
        self.tun_proxy_type = "socks" # socks or http

    def log(self, msg):
        print(f"[MODE] {msg}")

    def run_cpller(self, port, action_flag):
        cmd = [sys.executable, CPLLER_SCRIPT, "cpller", str(port), str(action_flag)]
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
        
        try:
            self.log(f"Запуск cpller.pyw: {' '.join(cmd)}")
            subprocess.Popen(cmd, creationflags=creationflags)
            return True
        except Exception as e:
            self.log(f"Ошибка запуска cpller.pyw: {e}")
            return False

    def get_tun_app_path(self):
        config = config_manager.load_config()
        # Default is empty, meaning we use sing-box
        app_path = config.get("proxification_app", "")
        return app_path

    def _parse_custom_rules(self):
        import json
        import re
        rules_path = os.path.join(CURRENT_DIR, "tun_rules.json")
        if not os.path.exists(rules_path):
            return []
            
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                gui_rules = json.load(f)
                
            rules = []
            
            for gr in gui_rules:
                if not gr.get("enabled", True): continue
                if gr.get("name") == "Default": continue # Default is handled via final route
                
                action = gr.get("action", "Direct")
                outbound = "direct"
                if action == "Block": outbound = "block"
                elif action == "Proxy TOR": outbound = "tor"
                elif action == "Proxy BD": outbound = "bd"
                elif action == "Proxy Opera": outbound = "opera"
                elif action == "Proxy VLESS": outbound = "vless"
                
                sing_rule = {"outbound": outbound}
                has_cond = False
                
                apps = gr.get("applications", "Any").strip()
                if apps.lower() != "any" and apps:
                    process_name = []
                    for a in apps.split(';'):
                        a = a.strip().strip('"\'')
                        if not a: continue
                        a = a.replace('*', '').replace('\\', '')
                        process_name.append(a)
                    if process_name:
                        sing_rule["process_name"] = process_name
                        has_cond = True
                        
                hosts = gr.get("hosts", "Any").strip()
                if hosts.lower() != "any" and hosts:
                    domain_suffix = []
                    domain_keyword = []
                    domain = []
                    ip_cidr = []
                    for t in hosts.split(';'):
                        t = t.strip()
                        if not t or "%" in t: continue
                        if re.match(r'^[\d\./]+$', t) or ":" in t:
                            ip_cidr.append(t)
                            continue
                        if t.startswith('*.'): domain_suffix.append(t[2:])
                        elif t.startswith('*') and t.endswith('*'): domain_keyword.append(t[1:-1])
                        elif t.startswith('*'): domain_keyword.append(t[1:])
                        elif t.endswith('*'): domain_keyword.append(t[:-1])
                        else: domain.append(t)
                    if domain_suffix: sing_rule["domain_suffix"] = domain_suffix
                    if domain_keyword: sing_rule["domain_keyword"] = domain_keyword
                    if domain: sing_rule["domain"] = domain
                    if ip_cidr: sing_rule["ip_cidr"] = ip_cidr
                    has_cond = True
                    
                ports = gr.get("ports", "Any").strip()
                if ports.lower() != "any" and ports:
                    port_list = []
                    for p in ports.split(';'):
                        p = p.strip()
                        if p.isdigit(): port_list.append(int(p))
                    if port_list:
                        sing_rule["port"] = port_list
                        has_cond = True
                        
                if has_cond:
                    rules.append(sing_rule)
                    
            return rules
        except Exception as e:
            self.log(f"Ошибка парсинга tun_rules.json: {e}")
            return []

    def _generate_singbox_config(self, port):
        cfg = config_manager.load_config()
        dns_address = cfg.get("tun_dns_address", "local")
        dns_detour = cfg.get("tun_dns_detour", "direct")
        tun_stack = cfg.get("tun_stack", "mixed")
        block_quic = cfg.get("tun_block_quic", False)
        smart_route = cfg.get("tun_smart_route", False)
        
        config = {
            "log": {"level": "info"},
            "dns": {
                "servers": [{"tag": "primary-dns", "address": dns_address, "detour": dns_detour}]
            },
            "inbounds": [{
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "toinet-tun",
                "address": ["172.19.0.1/30"],
                "auto_route": True,
                "strict_route": True,
                "stack": tun_stack
            }],
            "outbounds": [
                {
                    "type": "socks",
                    "tag": "proxy",
                    "server": "127.0.0.1",
                    "server_port": port
                },
                {"type": "direct", "tag": "direct"},
                {"type": "block", "tag": "block"}
            ],
            "route": {
                "rules": [
                    {"port": 53, "action": "hijack-dns"}
                ],
                "auto_detect_interface": True,
                "final": "proxy"
            }
        }
        
        if smart_route:
            config["outbounds"].extend([
                {"type": "socks", "tag": "tor", "server": "127.0.0.1", "server_port": 9853},
                {"type": "socks", "tag": "bd", "server": "127.0.0.1", "server_port": 1780},
                {"type": "socks", "tag": "opera", "server": "127.0.0.1", "server_port": 1785},
                {"type": "socks", "tag": "vless", "server": "127.0.0.1", "server_port": 1790}
            ])
            rules = self._parse_custom_rules()
            for r in rules:
                r["inbound"] = ["tun-in"]
                config["route"]["rules"].append(r)
        
        if block_quic:
            config["route"]["rules"].append({"port": 443, "network": "udp", "outbound": "block"})
            
        config["route"]["rules"].append({"inbound": "tun-in", "outbound": "proxy"})
        
        if self.tun_proxy_type == "http":
            config["outbounds"][0]["type"] = "http"
            
        import json
        with open("data/tun_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def start_tun(self, port=None):
        if self.tun_process:
            return True
        
        from PyQt5.QtWidgets import QMessageBox
        from managers import system_utils as lang
        import shlex
        
        path_line = self.get_tun_app_path()
        if not path_line:
            # Use sing-box
            if not port:
                if self.tun_proxy_port:
                    port = self.tun_proxy_port
                else:
                    cfg = config_manager.load_config()
                    if cfg.get("tun_smart_route", False):
                        port = 1780 # Default fallback for smart route
                    else:
                        return False # No proxy selected yet
            
            self._generate_singbox_config(port)
            
            import platform
            exe_name = "sing-box.exe" if platform.system() == "Windows" else "sing-box"
            sing_box_exe = os.path.join(CURRENT_DIR, "bin", "sing-box", exe_name)
            if not os.path.exists(sing_box_exe):
                QMessageBox.critical(None, "Ошибка TUN", "sing-box не найден в bin/sing-box/")
                return False
                
            cmd = [sing_box_exe, "run", "-c", "data/tun_config.json"]
            kwargs = {}
            if platform.system() == "Windows":
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                
            try:
                self.tun_process = subprocess.Popen(cmd, cwd=CURRENT_DIR, **kwargs)
                self.log(f"sing-box TUN запущен на порт {port}")
                return True
            except Exception as e:
                self.log(f"Ошибка запуска sing-box TUN: {e}")
                return False
        else:
            args = shlex.split(path_line, posix=False)
            exe_path = args[0].strip('"\'')
            if os.path.exists(exe_path):
                try:
                    self.tun_process = subprocess.Popen(args, cwd=CURRENT_DIR)
                    self.log(f"TUN режим запущен: {path_line}")
                    return True
                except Exception as e:
                    self.log(f"Ошибка запуска TUN режима: {e}")
                    QMessageBox.critical(None, "Ошибка TUN", f"Не удалось запустить проксификатор:\n{e}")
            else:
                msg = lang.T(f"Программа для TUN режима не найдена:\n{exe_path}", f"TUN mode application not found:\n{exe_path}")
                QMessageBox.warning(None, lang.T("Не настроен TUN", "TUN not configured"), msg)
        return False

    def stop_tun(self):
        if self.tun_process:
            try:
                self.tun_process.terminate()
                try:
                    self.tun_process.wait(timeout=2)
                except:
                    self.tun_process.kill()
                self.log("TUN режим остановлен (процесс завершен)")
            except Exception as e:
                self.log(f"Ошибка остановки TUN процесса: {e}")
            self.tun_process = None

    def tun_running(self):
        if self.tun_process:
            if self.tun_process.poll() is None:
                return True
            else:
                self.tun_process = None
        return False

    def restart_tun(self):
        self.stop_tun()
        import time
        time.sleep(1)
        self.start_tun()

    def set_singbox_tun_proxy(self, port, ptype="socks"):
        self.tun_proxy_port = port
        self.tun_proxy_type = ptype
        if self.tun_process:
            self.restart_tun()
        else:
            self.start_tun(port)

    def open_proxifier_config(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
        
        config = config_manager.load_config()
        current_path = config.get("proxification_app", self.get_tun_app_path())
        
        dialog = QDialog()
        dialog.setWindowTitle("Настройка проксификатора")
        dialog.resize(500, 100)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Укажите путь до проксификатора (например, путь к Proxifier).\nОставьте пустым, чтобы использовать встроенный sing-box для TUN:")
        layout.addWidget(label)
        
        h_layout = QHBoxLayout()
        line_edit = QLineEdit(current_path)
        h_layout.addWidget(line_edit)
        
        browse_btn = QPushButton("Обзор...")
        def browse():
            path, _ = QFileDialog.getOpenFileName(dialog, "Выберите исполняемый файл", "", "Executables (*.exe);;All Files (*)")
            if path:
                line_edit.setText(path)
        browse_btn.clicked.connect(browse)
        h_layout.addWidget(browse_btn)
        
        layout.addLayout(h_layout)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("ОК")
        cancel_btn = QPushButton("Отмена")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            config["proxification_app"] = line_edit.text().strip()
            config_manager.save_config(config)
            QMessageBox.information(None, "Успех", "Настройки сохранены. Перезапустите проксификатор.")

    def open_advanced_tun_config(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QMessageBox
        
        config = config_manager.load_config()
        
        dialog = QDialog()
        dialog.setWindowTitle("Продвинутые настройки TUN (sing-box)")
        dialog.resize(500, 250)
        
        layout = QVBoxLayout(dialog)
        
        # DNS Address
        layout.addWidget(QLabel("DNS Сервер:"))
        dns_cb = QComboBox()
        dns_cb.setEditable(True)
        dns_cb.addItems(["local", "https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query", "8.8.8.8", "1.1.1.1", "tcp://8.8.8.8"])
        dns_cb.setCurrentText(config.get("tun_dns_address", "local"))
        layout.addWidget(dns_cb)
        
        # DNS Detour
        layout.addWidget(QLabel("Маршрут DNS:"))
        detour_cb = QComboBox()
        detour_cb.addItems(["direct (напрямую)", "proxy (через прокси)"])
        current_detour = config.get("tun_dns_detour", "direct")
        detour_cb.setCurrentIndex(0 if current_detour == "direct" else 1)
        layout.addWidget(detour_cb)
        
        # Stack
        layout.addWidget(QLabel("Сетевой стек TUN:"))
        stack_cb = QComboBox()
        stack_cb.addItems(["mixed", "system", "gvisor"])
        current_stack = config.get("tun_stack", "mixed")
        stack_cb.setCurrentText(current_stack)
        layout.addWidget(stack_cb)
        
        # Block QUIC
        quic_cb = QCheckBox("Блокировать QUIC (UDP 443)")
        quic_cb.setToolTip("Полезно для обхода замедления YouTube, заставляет браузеры использовать TCP")
        quic_cb.setChecked(config.get("tun_block_quic", False))
        layout.addWidget(quic_cb)
        
        # Smart Routing
        smart_cb = QCheckBox("Умная маршрутизация (по правилам)")
        smart_cb.setToolTip("Использовать кастомные правила маршрутизации трафика")
        smart_cb.setChecked(config.get("tun_smart_route", False))
        
        edit_rules_btn = QPushButton("Редактировать правила")
        def open_rules_file():
            # We run rules_editor.py in a separate process
            subprocess.Popen([sys.executable, os.path.join(CURRENT_DIR, "ui/rules_editor.py")], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            
        edit_rules_btn.clicked.connect(open_rules_file)
        
        smart_layout = QHBoxLayout()
        smart_layout.addWidget(smart_cb)
        smart_layout.addWidget(edit_rules_btn)
        layout.addLayout(smart_layout)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("ОК")
        cancel_btn = QPushButton("Отмена")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            config["tun_dns_address"] = dns_cb.currentText().strip()
            config["tun_dns_detour"] = "direct" if detour_cb.currentIndex() == 0 else "proxy"
            config["tun_stack"] = stack_cb.currentText()
            config["tun_block_quic"] = quic_cb.isChecked()
            config["tun_smart_route"] = smart_cb.isChecked()
            config_manager.save_config(config)
            QMessageBox.information(None, "Успех", "Настройки сохранены. Если TUN запущен, переподключитесь, чтобы применить.")

    def reset_inetcpl_proxy(self):
        if self.inetcpl_tor_active:
            self.run_cpller(9853, 0)
            self.inetcpl_tor_active = False
            self.log("Отключен TOR прокси из inetcpl")
        
        if self.inetcpl_bd_active:
            self.run_cpller(1780, 0)
            self.inetcpl_bd_active = False
            self.log("Отключен BD прокси из inetcpl")
            
        if self.inetcpl_opera_active:
            self.run_cpller(1785, 0)
            self.inetcpl_opera_active = False
            self.log("Отключен Opera прокси из inetcpl")
            
        if self.inetcpl_vless_active:
            self.run_cpller(1790, 0)
            self.inetcpl_vless_active = False
            self.log("Отключен VLESS прокси из inetcpl")

_manager = ModeManager()

def get_manager():
    return _manager

