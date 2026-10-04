import os

import subprocess

import time

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

                {"inbound": ["tun-in"], "outbound": "auto"}

            ],

            "auto_detect_interface": True,

            "final": "auto"

        }

    }

    return config



class ProxyTester(QThread):

    progress = pyqtSignal(str)

    finished = pyqtSignal(bool, list)



    def emit_progress(self, msg):
        self.progress.emit(msg)

    def run(self):

        try:

            nodes = []

            use_cache = False

            cache_file = "evpn/working_nodes.json"

            if os.path.exists(cache_file):

                try:

                    with open(cache_file, "r", encoding="utf-8") as f:

                        cache_data = json.load(f)

                    if time.time() - cache_data.get("timestamp", 0) < 1800:

                        nodes = cache_data.get("nodes", [])

                        if nodes:

                            use_cache = True

                            self.emit_progress("Проверка сохраненных ранее серверов...")

                except Exception:

                    pass

            if not use_cache:

                self.emit_progress("Загрузка подписок...")

                subs_file = "evpn/subs.txt"

                if not os.path.exists(subs_file):

                    self.finished.emit(False, ["Файл evpn/subs.txt не найден в папке"])

                    return

                    

                with open(subs_file, "r") as f:

                    urls = [line.strip() for line in f if line.strip()]

                    

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

                

            self.emit_progress(f"Проверка серверов (найдено {len(nodes)})...")

            

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

                        self.emit_progress(f"Проверка: {checked}/{len(nodes)} (Рабочих: {len(working_nodes)})")

                    res = future.result()

                    if res:

                        working_nodes.append(res)

            

            if not working_nodes:

                self.finished.emit(False, ["Нет доступных серверов"])

                return

                
            
            try:

                os.makedirs("evpn", exist_ok=True)

                with open("evpn/working_nodes.json", "w", encoding="utf-8") as f:

                    json.dump({"timestamp": time.time(), "nodes": working_nodes}, f)

            except Exception:

                pass

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
        self.log_file = None

    def log(self, msg):
        print(f"[EVPN] {msg}")

    def emit_status(self, msg):
        self.log(msg)
        self.status_changed.emit(msg)

    def emit_error(self, msg):
        self.log(f"ERROR: {msg}")
        self.error_occurred.emit(msg)

    def start(self):
        if self.is_running:
            return
        
        self.is_running = True
        
        self.tester = ProxyTester()
        self.tester.progress.connect(self.emit_status)
        self.tester.finished.connect(self._on_test_finished)
        self.tester.start()

    def _on_test_finished(self, success, result):
        if not self.is_running:
            return
        if not success:
            self.emit_error(result[0])
            self.is_running = False
            self.emit_status("VPN Выключен")
            return
            
        self.working_nodes = result
        self._start_singbox_with_nodes()

    def _start_singbox_with_nodes(self):
        if not self.working_nodes:
            self.emit_error("Нет доступных серверов!")
            self.is_running = False
            self.emit_status("VPN Выключен")
            return
            
        self.emit_status(f"Генерация конфига (сохранено {len(self.working_nodes[:200])} серверов)...")
        
        try:
            current_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config = build_singbox_config(self.working_nodes)
            
            evpn_dir = os.path.join(current_dir, "evpn")
            if not os.path.exists(evpn_dir):
                os.makedirs(evpn_dir)
            cfg_path = os.path.join(evpn_dir, "evpn_config.json")
            
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
                
            self.emit_status("Запуск sing-box...")
            
            sing_box_exe = os.path.join(current_dir, "bin", "sing-box", "sing-box.exe")
            if not os.path.exists(sing_box_exe) and platform.system() != "Windows":
                sing_box_exe = os.path.join(current_dir, "bin", "sing-box", "sing-box")

            cmd = [
                sing_box_exe,
                "run",
                "-c", cfg_path
            ]
            
            kwargs = {}
            if platform.system() == "Windows":
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            env = os.environ.copy()
            env["ENABLE_DEPRECATED_LEGACY_DNS_SERVERS"] = "true"
            env["ENABLE_DEPRECATED_OUTBOUND_DNS_RULE_ITEM"] = "true"
            env["ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER"] = "true"
            
            if self.log_file:
                try:
                    self.log_file.close()
                except:
                    pass
            log_path = os.path.join(evpn_dir, "evpn.log")
            self.log_file = open(log_path, "w", encoding="utf-8")
            
            self.sb_process = subprocess.Popen(cmd, env=env, cwd=current_dir, stdout=self.log_file, stderr=subprocess.STDOUT, **kwargs)
            self.emit_status("VPN Включен")
            
        except Exception as e:
            self.emit_error(f"Ошибка запуска sing-box:\n{e}")
            self.is_running = False
            self.emit_status("VPN Выключен")

    def next_server(self):
        if not self.is_running or not self.working_nodes:
            return
        
        self.emit_status("Переключение сервера...")
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
        self.emit_status("Выключение...")
        
        if self.sb_process:
            self.sb_process.terminate()
            try:
                self.sb_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.sb_process.kill()
            self.sb_process = None
            
            if self.log_file:
                try:
                    self.log_file.close()
                except:
                    pass
                self.log_file = None
            
        self.emit_status("VPN Выключен")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = EvpnManager()
    return _manager



