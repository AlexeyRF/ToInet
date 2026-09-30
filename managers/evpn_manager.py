import os
import subprocess
import urllib.request
import urllib.parse
import json
import platform
import socket
import base64
import concurrent.futures
from PyQt5.QtCore import pyqtSignal, QObject, QThread
import sys

def build_singbox_config(nodes):
    outbounds = [
        {
            "type": "direct",
            "tag": "direct"
        }
    ]
    
    proxy_tags = []
    
    for i, link in enumerate(nodes[:200]):
        try:
            parsed = urllib.parse.urlparse(link)
            uuid = parsed.username
            server = parsed.hostname
            port = parsed.port or 443
            qs = urllib.parse.parse_qs(parsed.query)
            
            tag = f"proxy-{i}"
            
            security = qs.get("security", ["none"])[0]
            type_ = qs.get("type", ["tcp"])[0]
            flow = qs.get("flow", [""])[0]
            sni = qs.get("sni", [""])[0]
            fp = qs.get("fp", ["chrome"])[0]
            pbk = qs.get("pbk", [""])[0]
            sid = qs.get("sid", [""])[0]
            
            outbound = {
                "type": "vless",
                "tag": tag,
                "server": server,
                "server_port": int(port),
                "uuid": uuid,
                "packet_encoding": "xudp"
            }
            
            if flow:
                outbound["flow"] = flow
                
            if security in ["tls", "reality"]:
                tls_config = {
                    "enabled": True,
                    "server_name": sni or server,
                    "utls": {
                        "enabled": True,
                        "fingerprint": fp
                    }
                }
                if security == "reality":
                    tls_config["reality"] = {
                        "enabled": True,
                        "public_key": pbk,
                        "short_id": sid
                    }
                outbound["tls"] = tls_config
                
            if type_ == "ws":
                path = qs.get("path", ["/"])[0]
                host = qs.get("host", [""])[0]
                outbound["transport"] = {
                    "type": "ws",
                    "path": path,
                    "headers": {"Host": host} if host else {}
                }
            elif type_ == "grpc":
                serviceName = qs.get("serviceName", [""])[0]
                outbound["transport"] = {
                    "type": "grpc",
                    "service_name": serviceName
                }
                
            outbounds.append(outbound)
            proxy_tags.append(tag)
        except Exception:
            continue
            
    outbounds.insert(0, {
        "type": "urltest",
        "tag": "auto",
        "outbounds": proxy_tags,
        "url": "http://cp.cloudflare.com/generate_204",
        "interval": "3m",
        "tolerance": 5000
    })

    config = {
        "log": {
            "level": "info"
        },
        "dns": {
            "servers": [
                {"tag": "local", "address": "local", "detour": "direct"}
            ]
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "easy-vpn-tun",
                "address": [
                    "172.19.0.1/30"
                ],
                "auto_route": True,
                "strict_route": True,
                "stack": "mixed"
            }
        ],
        "outbounds": outbounds,
        "route": {
            "rules": [
                {"port": 53, "action": "hijack-dns"},
                {"inbound": "tun-in", "outbound": "auto"}
            ],
            "auto_detect_interface": True,
            "final": "auto"
        }
    }
    return config

class ProxyTester(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, list)

    def run(self):
        try:
            self.progress.emit("Загрузка подписок...")
            subs_file = "evpn/subs.txt"
            if not os.path.exists(subs_file):
                self.finished.emit(False, ["Файл evpn/subs.txt не найден в папке"])
                return
                
            with open(subs_file, "r") as f:
                urls = [line.strip() for line in f if line.strip()]
                
            nodes = []
            for u in urls:
                try:
                    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
                    data = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
                    try:
                        if "vless://" not in data:
                            data = base64.b64decode(data).decode('utf-8')
                    except Exception:
                        pass
                    for line in data.splitlines():
                        if line.startswith('vless://'):
                            nodes.append(line.strip())
                except Exception as e:
                    pass
            
            if not nodes:
                self.finished.emit(False, ["Не найдено ни одного vless конфига"])
                return
                
            self.progress.emit(f"Проверка серверов (найдено {len(nodes)})...")
            
            working_nodes = []
            checked = 0
            
            def check_node(link):
                try:
                    parsed = urllib.parse.urlparse(link)
                    host = parsed.hostname
                    port = parsed.port or 443
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1.5)
                    sock.connect((host, int(port)))
                    sock.close()
                    return link
                except:
                    return None
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                futures = {executor.submit(check_node, n): n for n in nodes}
                for future in concurrent.futures.as_completed(futures):
                    checked += 1
                    if checked % 20 == 0:
                        self.progress.emit(f"Проверка: {checked}/{len(nodes)} (Рабочих: {len(working_nodes)})")
                    res = future.result()
                    if res:
                        working_nodes.append(res)
            
            if not working_nodes:
                self.finished.emit(False, ["Нет доступных серверов"])
                return
                
            self.finished.emit(True, working_nodes)
        except Exception as e:
            self.finished.emit(False, [f"Ошибка: {e}"])


class EvpnManager(QObject):
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.sb_process = None
        self.is_running = False
        self.tester = None
        self.working_nodes = []

    def start(self):
        if self.is_running:
            return
        
        self.is_running = True
        
        self.tester = ProxyTester()
        self.tester.progress.connect(self.status_changed.emit)
        self.tester.finished.connect(self._on_test_finished)
        self.tester.start()

    def _on_test_finished(self, success, result):
        if not success:
            self.error_occurred.emit(result[0])
            self.is_running = False
            self.status_changed.emit("VPN Выключен")
            return
            
        self.working_nodes = result
        self._start_singbox_with_nodes()

    def _start_singbox_with_nodes(self):
        if not self.working_nodes:
            self.error_occurred.emit("Нет доступных серверов!")
            self.is_running = False
            self.status_changed.emit("VPN Выключен")
            return
            
        self.status_changed.emit(f"Генерация конфига (сохранено {len(self.working_nodes[:200])} серверов)...")
        
        try:
            config = build_singbox_config(self.working_nodes)
            with open("evpn/evpn_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
                
            self.status_changed.emit("Запуск sing-box...")
            
            current_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sing_box_exe = os.path.join(current_dir, "bin", "sing-box", "sing-box.exe")
            if not os.path.exists(sing_box_exe) and platform.system() != "Windows":
                sing_box_exe = os.path.join(current_dir, "bin", "sing-box", "sing-box")

            cmd = [
                sing_box_exe,
                "run",
                "-c", "evpn/evpn_config.json"
            ]
            
            kwargs = {}
            if platform.system() == "Windows":
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            env = os.environ.copy()
            env["ENABLE_DEPRECATED_LEGACY_DNS_SERVERS"] = "true"
            env["ENABLE_DEPRECATED_OUTBOUND_DNS_RULE_ITEM"] = "true"
            env["ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER"] = "true"
            
            self.sb_process = subprocess.Popen(cmd, env=env, **kwargs)
            self.status_changed.emit("VPN Включен")
            
        except Exception as e:
            self.error_occurred.emit(f"Ошибка запуска sing-box:\n{e}")
            self.is_running = False
            self.status_changed.emit("VPN Выключен")

    def next_server(self):
        if not self.is_running or not self.working_nodes:
            return
        
        self.status_changed.emit("Переключение сервера...")
        if self.sb_process:
            self.sb_process.terminate()
            try:
                self.sb_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.sb_process.kill()
            self.sb_process = None
            
        top_node = self.working_nodes.pop(0)
        self.working_nodes.append(top_node)
        
        self._start_singbox_with_nodes()

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.status_changed.emit("Выключение...")
        
        if self.sb_process:
            self.sb_process.terminate()
            try:
                self.sb_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.sb_process.kill()
            self.sb_process = None
            
        self.status_changed.emit("VPN Выключен")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = EvpnManager()
    return _manager

