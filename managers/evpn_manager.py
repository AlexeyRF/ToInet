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

from PySide6.QtCore import Signal, QObject, QThread

import sys
CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_evpn_dir():
    d = os.path.join(CURRENT_DIR, "evpn")
    os.makedirs(d, exist_ok=True)
    return d

def get_subs_file_path():
    candidates = [
        os.path.join(CURRENT_DIR, "evpn", "subs.txt"),
        os.path.join(CURRENT_DIR, "subs.txt"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evpn", "subs.txt"),
        os.path.abspath("evpn/subs.txt"),
        "evpn/subs.txt"
    ]
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            candidates.insert(0, os.path.join(meipass, "evpn", "subs.txt"))
            candidates.insert(1, os.path.join(meipass, "subs.txt"))

    for c in candidates:
        if c and os.path.exists(c):
            return c

    default_path = os.path.join(CURRENT_DIR, "evpn", "subs.txt")
    try:
        os.makedirs(os.path.dirname(default_path), exist_ok=True)
        default_subs = (
            "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_universal.txt\n"
            "https://gitverse.ru/api/repos/zieng2/wl/raw/branch/master/list_lite.txt\n"
        )
        with open(default_path, "w", encoding="utf-8") as f:
            f.write(default_subs)
        return default_path
    except Exception:
        return candidates[0]

def get_blacklist_file():
    return os.path.join(get_evpn_dir(), "blacklist.json")

def load_blacklist():
    path = get_blacklist_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception:
            pass
    return set()

def save_blacklist(bl_set):
    path = get_blacklist_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sorted(list(bl_set)), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[EVPN] Error saving blacklist: {e}")

def get_node_key(link):
    if not link:
        return ""
    try:
        parsed = urllib.parse.urlparse(link.strip())
        host = parsed.hostname or ""
        port = parsed.port or 443
        return f"{host}:{port}".lower()
    except Exception:
        return link.strip().lower()

def is_node_blacklisted(link, bl_set=None):
    if not link:
        return False
    if bl_set is None:
        bl_set = load_blacklist()
    if not bl_set:
        return False
    clean = link.strip()
    if clean in bl_set:
        return True
    key = get_node_key(clean)
    if key and key in bl_set:
        return True
    try:
        parsed = urllib.parse.urlparse(clean)
        if parsed.hostname and parsed.hostname.lower() in bl_set:
            return True
    except Exception:
        pass
    return False

def add_to_blacklist(link):
    if not link:
        return set()
    bl = load_blacklist()
    clean = link.strip()
    bl.add(clean)
    key = get_node_key(clean)
    if key:
        bl.add(key)
    try:
        parsed = urllib.parse.urlparse(clean)
        if parsed.hostname:
            bl.add(parsed.hostname.lower())
    except Exception:
        pass
    save_blacklist(bl)
    return bl




def build_singbox_config(nodes):
    bl = load_blacklist()
    if bl:
        nodes = [n for n in nodes if not is_node_blacklisted(n, bl)]

    outbounds = [
        {
            "type": "block",
            "tag": "block"
        },
        {
            "type": "direct",
            "tag": "direct"
        }
    ]

    

    proxy_tags = []

    

    for i, link in enumerate(nodes[:30]):

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

            

    if proxy_tags:
        urltest_group = {
            "type": "urltest",
            "tag": "urltest-auto",
            "outbounds": proxy_tags,
            "url": "http://cp.cloudflare.com/generate_204",
            "interval": "3m",
            "tolerance": 5000
        }
        outbounds.insert(0, urltest_group)
        outbounds.insert(0, {
            "type": "selector",
            "tag": "auto",
            "outbounds": [proxy_tags[0], "urltest-auto"] + [t for t in proxy_tags[1:]],
            "default": proxy_tags[0]
        })
    else:
        outbounds.insert(0, {
            "type": "block",
            "tag": "auto"
        })



    from managers import config_manager
    cfg = config_manager.load_config() if hasattr(config_manager, 'load_config') else {}
    proxy_dns = cfg.get("proxy_dns_tun_evpn", True)

    config = {
        "log": {
            "level": "warn"
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
                {"port": 53, "action": "hijack-dns"} if proxy_dns else {"port": 53, "outbound": "direct"},
                {"inbound": ["tun-in"], "outbound": "auto"},
                {"inbound": ["tun-in"], "outbound": "block"}
            ],

            "auto_detect_interface": True,

            "final": "block"

        }

    }

    return config



class ProxyTester(QThread):

    progress = Signal(str)

    finished = Signal(bool, list)



    def emit_progress(self, msg):
        self.progress.emit(msg)

    def run(self):

        try:

            nodes = []

            use_cache = False

            cache_file = os.path.join(get_evpn_dir(), "working_nodes.json")

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

                subs_file = get_subs_file_path()

                if not os.path.exists(subs_file):

                    self.finished.emit(False, [f"Файл evpn/subs.txt не найден ({subs_file or 'evpn/subs.txt'})"])

                    return

                    

                with open(subs_file, "r", encoding="utf-8", errors="ignore") as f:

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
            bl = load_blacklist()
            if nodes and bl:
                nodes = [n for n in nodes if not is_node_blacklisted(n, bl)]


            

            if not nodes:

                self.finished.emit(False, ["Не найдено ни одного vless конфига"])

                return

                

            self.emit_progress(f"Проверка серверов (найдено {len(nodes)})...")

            

            working_nodes = []

            checked = 0
            def check_node(link):
                if is_node_blacklisted(link, bl):
                    return None
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

            

            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:

                futures = {executor.submit(check_node, n): n for n in nodes}

                for future in concurrent.futures.as_completed(futures):

                    checked += 1

                    res = future.result()

                    if res:

                        working_nodes.append(res)

                    if checked % 30 == 0 or len(working_nodes) >= 25:

                        self.emit_progress(f"Проверка: {checked}/{len(nodes)} (Рабочих: {len(working_nodes)})")

                    if len(working_nodes) >= 25:

                        break

            

            if not working_nodes:

                self.finished.emit(False, ["Нет доступных серверов"])

                return

                
            
            try:

                os.makedirs("evpn", exist_ok=True)

                with open(cache_file, "w", encoding="utf-8") as f:

                    json.dump({"timestamp": time.time(), "nodes": working_nodes}, f)

            except Exception:

                pass

            self.finished.emit(True, working_nodes)

        except Exception as e:

            self.finished.emit(False, [f"Ошибка: {e}"])





class EvpnManager(QObject):
    status_changed = Signal(str)
    error_occurred = Signal(str)

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
            if self.sb_process:
                try:
                    self.sb_process.terminate()
                    self.sb_process.wait(timeout=1.5)
                except Exception:
                    try:
                        self.sb_process.kill()
                    except Exception:
                        pass
                self.sb_process = None

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
        top_node = self.working_nodes.pop(0)
        self.working_nodes.append(top_node)

        # Skip any blacklisted nodes
        bl = load_blacklist()
        if bl:
            self.working_nodes = [n for n in self.working_nodes if not is_node_blacklisted(n, bl)]

        if not self.working_nodes:
            self.emit_error("Нет доступных серверов!")
            self.stop()
            return

        self._start_singbox_with_nodes()

    def blacklist_current_server(self):
        if not self.working_nodes:
            self.emit_error("Нет активного сервера для добавления в Ч/С")
            return None
        
        banned_node = self.working_nodes.pop(0)
        add_to_blacklist(banned_node)
        
        bl = load_blacklist()
        self.working_nodes = [n for n in self.working_nodes if not is_node_blacklisted(n, bl)]
        
        banned_key = get_node_key(banned_node) or "сервер"
        self.emit_status(f"Сервер {banned_key} добавлен в Ч/С. Переключение...")
        print(f"[EVPN] Added to blacklist: {banned_key}. Remaining active nodes: {len(self.working_nodes)}")

        try:
            cache_file = os.path.join(get_evpn_dir(), "working_nodes.json")
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"timestamp": time.time(), "nodes": self.working_nodes}, f)
        except Exception:
            pass

        if not self.working_nodes:
            self.emit_error("Все доступные серверы в Ч/С. Запустите обновление подписок.")
            self.stop()
            return banned_node

        self._start_singbox_with_nodes()
        return banned_node

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



