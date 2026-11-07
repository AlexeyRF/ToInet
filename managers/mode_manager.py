import os

import sys

import subprocess

import json

import time

import psutil

from PySide6.QtWidgets import QMessageBox

from managers import system_utils as lang

from managers.system_utils import AdoptedProcess

from managers import config_manager



import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CPLLER_EXE = os.path.join(CURRENT_DIR, "bin", "cpller.exe")

CPLLER_SCRIPT = os.path.join(CURRENT_DIR, "managers", "system_utils.py")



class ModeManager:

    def __init__(self):

        self.tun_process = None

        self.inetcpl_tor_active = False

        self.inetcpl_bd_active = False

        self.inetcpl_opera_active = False

        self.inetcpl_vless_active = False

        self.inetcpl_ssh_active = False

        self.tun_proxy_port = 0

        self.tun_proxy_type = "socks" # socks or http



    def log(self, msg):

        print(f"[MODE] {msg}")



    def run_cpller(self, port, action_flag):

        if os.path.exists(CPLLER_EXE):

            cmd = [CPLLER_EXE, str(port), str(action_flag)]

        else:

            cmd = [sys.executable, CPLLER_SCRIPT, "cpller", str(port), str(action_flag)]

        creationflags = 0

        if os.name == "nt":

            creationflags = subprocess.CREATE_NO_WINDOW

        

        try:

            self.log(f"Запуск cpller: {' '.join(cmd)}")

            subprocess.Popen(cmd, creationflags=creationflags)

            return True

        except Exception as e:

            self.log(f"Ошибка запуска cpller: {e}")

            return False



    def get_tun_app_path(self):

        config = config_manager.load_config()

        app_path = config.get("proxification_app", "").strip()

        if app_path and os.path.exists(app_path):

            return app_path

            

        # Автоматический поиск Proxifier.exe

        candidates = [

            os.path.join(CURRENT_DIR, "Proxifier", "Proxifier.exe"),

            r"C:\Program Files\Proxifier\Proxifier.exe",

            r"C:\Program Files (x86)\Proxifier\Proxifier.exe",

        ]

        for cand in candidates:

            if os.path.exists(cand):

                return cand

        return app_path



    def _parse_ppx(self, ppx_path=None):

        import xml.etree.ElementTree as ET

        import re

        

        if not ppx_path:

            candidates = [

                os.path.join(CURRENT_DIR, "Toinet.ppx"),

                os.path.join(os.path.dirname(CURRENT_DIR), "Toinet.ppx")

            ]

            for c in candidates:

                if os.path.exists(c):

                    ppx_path = c

                    break

                    

        if not ppx_path or not os.path.exists(ppx_path):

            self.log(f"Toinet.ppx не найден по пути: {ppx_path}")

            return [], [], {}



        cfg = config_manager.load_config()



        def parse_targets(target_str):

            if not target_str:

                return [], [], []

            target_str = re.sub(r'(\*)\s+(\*)', r'\1;\2', target_str)

            raw_targets = [t.strip() for t in target_str.replace('\n', ' ').split(';') if t.strip()]

            

            suffixes = set()

            keywords = set()

            ip_cidrs = set()

            

            for t in raw_targets:

                if t.startswith('%') and t.endswith('%'):

                    continue

                if t.lower() == 'localhost':

                    keywords.add('localhost')

                    continue

                if re.match(r'^[\d\.:/]+$', t):

                    if '/' not in t:

                        if ':' in t: t += '/128'

                        else: t += '/32'

                    ip_cidrs.add(t)

                    continue

                    

                if t.startswith('*.') and t.endswith('.*'):

                    keywords.add(t[2:-2] + '.')

                elif t.startswith('*.') and t.endswith('*'):

                    keywords.add(t[2:-1])

                elif t.startswith('*') and t.endswith('.*'):

                    keywords.add(t[1:-2] + '.')

                elif t.startswith('*') and t.endswith('*'):

                    keywords.add(t[1:-1])

                elif t.endswith('.*'):

                    keywords.add(t[:-2] + '.')

                elif t.endswith('*'):

                    keywords.add(t[:-1])

                elif t.startswith('*.'):

                    suffixes.add(t[2:].lower())

                elif t.startswith('*'):

                    sub = t[1:].lower()

                    if '*' in sub:

                        keywords.add(sub.replace('*', ''))

                    else:

                        suffixes.add(sub)

                else:

                    if '*' in t:

                        keywords.add(t.lower().replace('*', ''))

                    else:

                        suffixes.add(t.lower())

                        

            return sorted(list(suffixes)), sorted(list(keywords)), sorted(list(ip_cidrs))



        def parse_apps(app_str):

            if not app_str:

                return []

            raw = [a.strip().strip('"\'') for a in app_str.replace('\n', ' ').split(';') if a.strip()]

            names = set()

            for a in raw:

                clean = a.replace('/', '\\').split('\\')[-1].replace('*', '').strip('.').strip()

                if clean:

                    names.add(clean)

                    if not clean.endswith('.exe') and '.' not in clean:

                        names.add(clean + '.exe')

            return sorted(list(names))



        try:

            tree = ET.parse(ppx_path)

            root = tree.getroot()

            

            proxy_map = {}

            outbounds = [

                {"type": "direct", "tag": "direct"},

                {"type": "block", "tag": "block"}

            ]

            

            for proxy in root.findall('./ProxyList/Proxy'):

                p_id = proxy.get('id')

                p_port = int(proxy.find('Port').text)

                p_addr = proxy.find('Address').text

                p_label = proxy.find('Label').text if proxy.find('Label') is not None else f"Proxy_{p_id}"

                

                tag = p_label.lower().replace(' ', '_')

                if tag in ('bypass', 'byedpi', 'bd'):

                    tag = 'byedpi'

                elif tag in ('hosting', 'ssh'):

                    tag = 'ssh'

                    p_port = int(cfg.get("ssh_socks_port", p_port))

                elif 'tor' in tag:

                    tag = 'tor'

                elif 'opera' in tag:

                    tag = 'opera'

                    

                proxy_map[p_id] = tag

                

                if not any(o.get('tag') == tag for o in outbounds):

                    outbounds.append({

                        "type": "socks",

                        "tag": tag,

                        "server": p_addr,

                        "server_port": p_port

                    })

                    

            standard_tags = {

                "byedpi": 1780,

                "tor": 9853,

                "opera": 1785,

                "ssh": int(cfg.get("ssh_socks_port", 1770))

            }

            for st, sp in standard_tags.items():

                if not any(o.get('tag') == st for o in outbounds):

                    outbounds.append({

                        "type": "socks",

                        "tag": st,

                        "server": "127.0.0.1",

                        "server_port": sp

                    })

                    

            rules = []

            for r in root.findall('./RuleList/Rule'):

                if r.get('enabled') != 'true':

                    continue

                name = r.find('Name').text if r.find('Name') is not None else ''

                if name in ('Default', 'Localhost'):

                    continue

                    

                act_elem = r.find('Action')

                act_type = act_elem.get('type') if act_elem is not None else 'Direct'

                if act_type == 'Direct':

                    outbound = 'direct'

                elif act_type == 'Block':

                    outbound = 'block'

                elif act_type == 'Proxy':

                    pid = act_elem.text.strip() if act_elem.text else ''

                    outbound = proxy_map.get(pid, 'direct')

                else:

                    outbound = 'direct'

                    

                t_elem = r.find('Targets')

                a_elem = r.find('Applications')

                p_elem = r.find('Ports')

                

                t_text = t_elem.text if t_elem is not None else ''

                a_text = a_elem.text if a_elem is not None else ''

                p_text = p_elem.text if p_elem is not None else ''

                

                suffixes, keywords, cidrs = parse_targets(t_text)

                apps = parse_apps(a_text)

                ports = []

                if p_text:

                    for p in p_text.replace('\n', ' ').split(';'):

                        p = p.strip()

                        if p.isdigit():

                            ports.append(int(p))

                            

                if apps and not suffixes and not keywords and not cidrs and not ports:

                    rules.append({

                        "outbound": outbound,

                        "process_name": apps

                    })

                elif ports and not apps and not suffixes and not keywords and not cidrs:

                    rules.append({

                        "outbound": outbound,

                        "port": ports

                    })

                elif (suffixes or keywords or cidrs) and not apps and not ports:

                    r_obj = {"outbound": outbound}

                    if suffixes: r_obj["domain_suffix"] = suffixes

                    if keywords: r_obj["domain_keyword"] = keywords

                    if cidrs: r_obj["ip_cidr"] = cidrs

                    rules.append(r_obj)

                else:

                    if apps and (suffixes or keywords or cidrs):

                        rules.append({

                            "outbound": outbound,

                            "process_name": apps

                        })

                        r_obj = {"outbound": outbound}

                        if suffixes: r_obj["domain_suffix"] = suffixes

                        if keywords: r_obj["domain_keyword"] = keywords

                        if cidrs: r_obj["ip_cidr"] = cidrs

                        if ports: r_obj["port"] = ports

                        rules.append(r_obj)

                    else:

                        r_obj = {"outbound": outbound}

                        if apps: r_obj["process_name"] = apps

                        if suffixes: r_obj["domain_suffix"] = suffixes

                        if keywords: r_obj["domain_keyword"] = keywords

                        if cidrs: r_obj["ip_cidr"] = cidrs

                        if ports: r_obj["port"] = ports

                        rules.append(r_obj)

                        

            return outbounds, rules, proxy_map

        except Exception as e:

            self.log(f"Ошибка парсинга Toinet.ppx: {e}")

            return [], [], {}



    def _generate_singbox_config(self, port=None):

        import json

        cfg = config_manager.load_config()

        dns_address = cfg.get("tun_dns_address", "77.88.8.8")

        if dns_address == "local":

            dns_address = "77.88.8.8"

        dns_detour = cfg.get("tun_dns_detour", "direct")

        tun_stack = cfg.get("tun_stack", "mixed")

        proxy_dns = cfg.get("proxy_dns_tun_evpn", True)



        outbounds, ppx_rules, proxy_map = self._parse_ppx()

        

        if not outbounds:

            outbounds = [

                {"type": "direct", "tag": "direct"},

                {"type": "block", "tag": "block"},

                {"type": "socks", "tag": "byedpi", "server": "127.0.0.1", "server_port": 1780},

                {"type": "socks", "tag": "tor", "server": "127.0.0.1", "server_port": 9853},

                {"type": "socks", "tag": "opera", "server": "127.0.0.1", "server_port": 1785},

                {"type": "socks", "tag": "ssh", "server": "127.0.0.1", "server_port": int(cfg.get("ssh_socks_port", 1770))}

            ]



        primary_dns = {

            "tag": "dns-primary",

            "type": "udp",

            "server": dns_address

        }

        if dns_address.startswith("https://"):

            primary_dns["type"] = "https"

            primary_dns["server"] = dns_address.replace("https://", "")

        elif dns_address.startswith("tls://"):

            primary_dns["type"] = "tls"

            primary_dns["server"] = dns_address.replace("tls://", "")

        elif dns_address.startswith("tcp://"):

            primary_dns["type"] = "tcp"

            primary_dns["server"] = dns_address.replace("tcp://", "")

            

        if dns_detour and dns_detour != "direct":

            primary_dns["detour"] = dns_detour



        backup_dns = {

            "tag": "dns-backup",

            "type": "udp",

            "server": "1.1.1.1"

        }

        if dns_detour and dns_detour != "direct":

            backup_dns["detour"] = dns_detour



        rules = [

            {

                "action": "sniff",

                "sniffer": ["http", "tls", "quic", "dns"],

                "timeout": "300ms"

            },

            {

                "ip_version": 6,

                "action": "reject"

            },

            {

                "port": [443],

                "network": ["udp"],

                "action": "reject"

            }

        ]



        if proxy_dns:

            rules.append({

                "port": [53],

                "action": "hijack-dns"

            })

        else:

            rules.append({

                "port": [53],

                "outbound": "direct"

            })



        rules.append({

            "outbound": "direct",

            "process_name": [

                "sing-box.exe",

                "ciadpi.exe",

                "tor.exe",

                "lyrebird.exe",

                "obfs4proxy.exe",

                "opera-proxy.exe",

                "plink.exe",

                "ssh.exe",

                "python.exe",

                "pythonw.exe",

                "ToInet.exe"

            ]

        })



        rules.append({

            "outbound": "direct",

            "ip_cidr": [

                "127.0.0.0/8",

                "::1/128",

                "10.0.0.0/8",

                "172.16.0.0/12",

                "192.168.0.0/16",

                "169.254.0.0/16"

            ]

        })



        rules.extend(ppx_rules)



        # YouTube and Google CDN IPv4 CIDRs for direct-by-IP connections

        yt_cidrs_file = os.path.join(CURRENT_DIR, "data", "google_cidrs.json")

        yt_cidrs = []

        if os.path.exists(yt_cidrs_file):

            try:

                with open(yt_cidrs_file, "r", encoding="utf-8") as f:

                    raw_cidrs = json.load(f)

                    yt_cidrs = [c for c in raw_cidrs if ":" not in c]

            except Exception:

                pass

        if not yt_cidrs:

            yt_cidrs = [

                "142.250.0.0/15", "172.217.0.0/16", "173.194.0.0/16", "74.125.0.0/16",

                "108.177.0.0/17", "216.58.192.0/19", "64.233.160.0/19", "66.102.0.0/20",

                "209.85.128.0/17", "172.253.0.0/16", "192.178.0.0/15", "216.239.32.0/19"

            ]

        if yt_cidrs:

            rules.append({

                "outbound": "tor",

                "ip_cidr": yt_cidrs

            })



        final_outbound = "direct"

        if port and port != 0:

            for o in outbounds:

                if o.get("server_port") == port:

                    final_outbound = o.get("tag")

                    break

            if final_outbound == "direct":

                tag_name = f"proxy_{port}"

                outbounds.append({

                    "type": self.tun_proxy_type or "socks",

                    "tag": tag_name,

                    "server": "127.0.0.1",

                    "server_port": port

                })

                final_outbound = tag_name



        config = {

            "log": {

                "level": "info",

                "timestamp": True

            },

            "dns": {

                "servers": [primary_dns, backup_dns],

                "strategy": "ipv4_only",

                "reverse_mapping": True

            },

            "inbounds": [

                {

                    "type": "tun",

                    "tag": "tun-in",

                    "interface_name": "toinet-tun",

                    "address": [

                        "172.19.0.1/30"

                    ],

                    "mtu": 1500,

                    "auto_route": True,

                    "strict_route": False,

                    "endpoint_independent_nat": True,

                    "stack": tun_stack

                }

            ],

            "outbounds": outbounds,

            "route": {

                "default_domain_resolver": "dns-primary",

                "rules": rules,

                "auto_detect_interface": True,

                "final": final_outbound

            }

        }



        cfg_path = os.path.join(CURRENT_DIR, "data", "tun_config.json")

        with open(cfg_path, "w", encoding="utf-8") as f:

            json.dump(config, f, indent=2, ensure_ascii=False)

            

        root_cfg_path = os.path.join(CURRENT_DIR, "config.json")

        try:

            with open(root_cfg_path, "w", encoding="utf-8") as f:

                json.dump(config, f, indent=2, ensure_ascii=False)

        except Exception:

            pass

            

        return config



    def find_existing_tun_process(self):

        try:

            for proc in psutil.process_iter(['pid', 'name']):

                try:

                    name = (proc.info.get('name') or "").lower()

                    if 'sing-box' in name:

                        cmdline = proc.cmdline() or []

                        if any('tun_config.json' in arg for arg in cmdline):

                            return proc.info['pid']

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):

                    continue

        except Exception:

            pass

        return None



    def find_existing_proxifier_process(self, exe_path):

        exe_name = os.path.basename(exe_path).lower()

        try:

            for proc in psutil.process_iter(['pid', 'name']):

                try:

                    name = (proc.info.get('name') or "").lower()

                    if name == exe_name:

                        return proc.info['pid']

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):

                    continue

        except Exception:

            pass

        return None



    def start_tun(self, port=None):

        if self.tun_running():

            return True



        existing_pid = self.find_existing_tun_process()

        if existing_pid:

            self.log(f"sing-box TUN найден уже запущенным (PID {existing_pid}), используем его.")

            self.tun_process = AdoptedProcess(existing_pid)

            return True



        from PySide6.QtWidgets import QMessageBox

        from managers import system_utils as lang

        import shlex

        

        if not port:

            if self.tun_proxy_port:

                port = self.tun_proxy_port

            else:

                port = 0

            self.tun_proxy_port = port

        cfg = config_manager.load_config()

        custom_tun_cfg = cfg.get("tun_singbox_config")

        cfg_path = os.path.join(CURRENT_DIR, "data", "tun_config.json")

        if custom_tun_cfg and isinstance(custom_tun_cfg, dict):

            import json

            with open(cfg_path, "w", encoding="utf-8") as f:

                json.dump(custom_tun_cfg, f, indent=2, ensure_ascii=False)

        else:

            self._generate_singbox_config(port)

        

        import platform

        exe_name = "sing-box.exe" if platform.system() == "Windows" else "sing-box"

        sing_box_exe = os.path.join(CURRENT_DIR, "bin", "sing-box", exe_name)

        if not os.path.exists(sing_box_exe):

            QMessageBox.critical(None, "Ошибка TUN", "sing-box не найден в bin/sing-box/")

            return False

            

        cmd = [sing_box_exe, "run", "-c", cfg_path]

        kwargs = {}

        if platform.system() == "Windows":

            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW



        env = os.environ.copy()

        env["ENABLE_DEPRECATED_LEGACY_DNS_SERVERS"] = "true"

        env["ENABLE_DEPRECATED_OUTBOUND_DNS_RULE_ITEM"] = "true"

        env["ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER"] = "true"



        log_path = os.path.join(CURRENT_DIR, "data", "tun_singbox.log")

        try:

            if hasattr(self, 'tun_log_file') and self.tun_log_file:

                try:

                    self.tun_log_file.close()

                except Exception:

                    pass

            self.tun_log_file = open(log_path, "w", encoding="utf-8")

        except Exception:

            self.tun_log_file = None

            

        try:

            self.tun_process = subprocess.Popen(

                cmd,

                cwd=CURRENT_DIR,

                env=env,

                stdout=self.tun_log_file or subprocess.DEVNULL,

                stderr=subprocess.STDOUT,

                **kwargs

            )

            self.tun_proxy_port = port

            self.log(f"sing-box TUN запущен на порт {port}")

            return True

        except Exception as e:

            self.log(f"Ошибка запуска sing-box TUN: {e}")

            return False



    def start_proxifier(self):

        import shlex

        from PySide6.QtWidgets import QMessageBox

        from managers import system_utils as lang



        def _handle_missing_proxifier():

            config = config_manager.load_config()

            if config.get("proxifier_install_prompt_declined", False):

                self.log("Proxifier не настроен, пользователь ранее отказался от предложения.")

                return False



            title = lang.T("Проксификатор не найден", "Proxifier Not Found")

            msg = lang.T(

                "Для работы режима EMPTY требуется Proxifier.exe.\n\n"

                "Хотите открыть настройки и указать путь к Proxifier сейчас?\n"

                "(При выборе «Нет» это предложение больше не будет показываться)",

                "Proxifier.exe is required for EMPTY mode.\n\n"

                "Would you like to configure or specify the path to Proxifier now?\n"

                "(If you choose 'No', this message will not be shown again)"

            )

            res = QMessageBox.question(None, title, msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

            if res == QMessageBox.Yes:

                self.open_proxifier_config()

            else:

                config["proxifier_install_prompt_declined"] = True

                config_manager.save_config(config)

            return False



        path_line = self.get_tun_app_path()

        if not path_line:

            self.log("Проксификатор не настроен и не найден в стандартных путях")

            return _handle_missing_proxifier()



        args = shlex.split(path_line, posix=False)

        exe_path = args[0].strip('"\'')



        existing_pid = self.find_existing_proxifier_process(exe_path)

        if existing_pid:

            self.log(f"Проксификатор найден уже запущенным (PID {existing_pid})")

            self.proxifier_process = AdoptedProcess(existing_pid)

            return True



        if os.path.exists(exe_path):

            try:

                cmd = [exe_path]

                work_dir = os.path.dirname(exe_path) if os.path.exists(os.path.dirname(exe_path)) else CURRENT_DIR

                self.proxifier_process = subprocess.Popen(cmd, cwd=work_dir)

                self.log(f"Проксификатор запущен: {exe_path}")

                return True

            except Exception as e:

                self.log(f"Ошибка запуска проксификатора: {e}")

                QMessageBox.critical(None, "Ошибка", f"Не удалось запустить проксификатор:\n{e}")

        else:

            self.log(f"Программа для проксификатора не найдена: {exe_path}")

            return _handle_missing_proxifier()

        return False

        

    def stop_proxifier(self, force=True):

        path_line = self.get_tun_app_path()

        exe_path = ""

        exe_name = "Proxifier.exe"

        if path_line:

            import shlex

            args = shlex.split(path_line, posix=False)

            exe_path = args[0].strip('"\'')

            exe_name = os.path.basename(exe_path)



        if hasattr(self, 'proxifier_process') and self.proxifier_process:

            try:

                self.proxifier_process.terminate()

                try:

                    self.proxifier_process.wait(timeout=1.5)

                except Exception:

                    self.proxifier_process.kill()

            except Exception as e:

                self.log(f"Ошибка мягкой остановки проксификатора: {e}")

            self.proxifier_process = None



        if force or self.find_existing_proxifier_process(exe_path or exe_name):

            for _ in range(15):

                pid = self.find_existing_proxifier_process(exe_path or exe_name)

                if not pid:

                    break

                try:

                    p = psutil.Process(pid)

                    p.kill()

                    p.wait(timeout=1)

                except Exception:

                    pass

                time.sleep(0.1)



            if self.find_existing_proxifier_process(exe_path or exe_name):

                try:

                    subprocess.run(f'taskkill /F /IM "{exe_name}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                except Exception:

                    pass

                time.sleep(0.2)



        self.proxifier_process = None

        self.log("Проксификатор остановлен")

        return True



    def restart_proxifier(self):

        self.log("Перезапуск проксификатора...")

        self.stop_proxifier(force=True)

        time.sleep(0.5)

        res = self.start_proxifier()

        self.log(f"Перезапуск проксификатора: {'успешно' if res else 'не удалось'}")

        return res

    def proxifier_running(self):

        if hasattr(self, 'proxifier_process') and self.proxifier_process:

            if self.proxifier_process.poll() is None:

                return True

            else:

                self.proxifier_process = None

        else:

            import time

            now = time.time()

            if now - getattr(self, '_last_proxifier_scan_time', 0) > 15.0:

                self._last_proxifier_scan_time = now

                path_line = self.get_tun_app_path()

                if path_line:

                    import shlex

                    try:

                        args = shlex.split(path_line, posix=False)

                        exe_path = args[0].strip('"\'')

                        existing_pid = self.find_existing_proxifier_process(exe_path)

                        if existing_pid:

                            self.proxifier_process = AdoptedProcess(existing_pid)

                            return True

                    except Exception:

                        pass

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



        if hasattr(self, 'tun_log_file') and self.tun_log_file:

            try:

                self.tun_log_file.close()

            except Exception:

                pass

            self.tun_log_file = None



        existing_pid = self.find_existing_tun_process()

        if existing_pid:

            try:

                proc = psutil.Process(existing_pid)

                proc.kill()

            except Exception:

                pass



    def tun_running(self):

        if self.tun_process:

            if self.tun_process.poll() is None:

                return True

            else:

                self.tun_process = None

        else:

            existing_pid = self.find_existing_tun_process()

            if existing_pid:

                self.tun_process = AdoptedProcess(existing_pid)

                return True

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

        import sys, subprocess

        exe_path = os.path.join(CURRENT_DIR, "bin", "programs_settings.exe")

        script_path = os.path.join(CURRENT_DIR, ".dev", "programs_settings.pyw")

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        if os.path.exists(exe_path):

            subprocess.Popen([exe_path], creationflags=creationflags)

        else:

            subprocess.Popen([sys.executable, script_path], creationflags=creationflags)



    def open_advanced_tun_config(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QMessageBox
        
        config = config_manager.load_config()
        
        dialog = QDialog()
        dialog.setWindowTitle("Продвинутые настройки TUN (sing-box)")
        dialog.resize(500, 270)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #202020;
                color: #FFFFFF;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }
            QComboBox, QLineEdit {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox:hover, QLineEdit:hover {
                border-color: #555555;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #383838;
                selection-background-color: #005FB8;
                selection-color: #FFFFFF;
            }
            QCheckBox {
                color: #FFFFFF;
                background: transparent;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #555555;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover {
                border-color: #777777;
            }
            QCheckBox::indicator:checked {
                background-color: #005FB8;
                border-color: #005FB8;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #383838;
                border-color: #484848;
            }
            QPushButton#primaryBtn {
                background-color: #005FB8;
                border-color: #005FB8;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0078D4;
                border-color: #0078D4;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        
        # DNS Address
        layout.addWidget(QLabel("DNS Сервер:"))
        dns_cb = QComboBox()
        dns_cb.setEditable(True)
        dns_cb.addItems(["77.88.8.8", "1.1.1.1", "8.8.8.8", "https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query", "tcp://8.8.8.8"])
        current_dns = config.get("tun_dns_address", "77.88.8.8")
        if current_dns == "local":
            current_dns = "77.88.8.8"
        dns_cb.setCurrentText(current_dns)
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
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        edit_rules_btn = QPushButton("Редактировать правила...")
        def open_rules():
            try:
                from ui.rules_editor import RulesEditorDialog
                ed = RulesEditorDialog(parent=dialog)
                ed.exec()
            except Exception as e:
                QMessageBox.warning(dialog, "Ошибка", f"Не удалось открыть редактор правил: {e}")
        edit_rules_btn.clicked.connect(open_rules)
        btn_layout.addWidget(edit_rules_btn)
        
        btn_layout.addStretch()
        
        ok_btn = QPushButton("ОК")
        ok_btn.setObjectName("primaryBtn")
        cancel_btn = QPushButton("Отмена")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.Accepted:
            config["tun_dns_address"] = dns_cb.currentText().strip()
            config["tun_dns_detour"] = "direct" if detour_cb.currentIndex() == 0 else "proxy"
            config["tun_stack"] = stack_cb.currentText()
            config["tun_block_quic"] = quic_cb.isChecked()
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



        if getattr(self, 'inetcpl_ssh_active', False):

            cfg = config_manager.load_config()

            self.run_cpller(cfg.get("ssh_socks_port", 1770), 0)

            self.inetcpl_ssh_active = False

            self.log("Отключен SSH прокси из inetcpl")



_manager = ModeManager()



def get_manager():

    return _manager



