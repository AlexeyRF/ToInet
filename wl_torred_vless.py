import os
import sys
def safe_print(*args, **kwargs):
    with open('wl_vless.log', 'a') as f:
        f.write(' '.join(map(str, args)) + '\n')
    try:
        __builtins__.print(*args, **kwargs)
    except:
        pass

import time
import json
import socket
import urllib.request
import urllib.error
import urllib.parse
import base64
import subprocess
import threading
import psutil

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(CURRENT_DIR, "bin")
SING_BOX_DIR = os.path.join(BIN_DIR, "sing-box")
SING_BOX_EXE = os.path.join(SING_BOX_DIR, "sing-box.exe")

def load_config():
    config_path = os.path.join(CURRENT_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def b64decode_padding(s):
    s = s.strip()
    return base64.b64decode(s + '=' * (-len(s) % 4)).decode('utf-8', errors='ignore')

def fetch_subs():
    subs_path = os.path.join(CURRENT_DIR, "subs.txt")
    if not os.path.exists(subs_path):
        return []
        
    urls = []
    with open(subs_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
                
    cache_file = os.path.join(CURRENT_DIR, "subs_cache.json")
    cache_data = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except:
            pass
            
    vless_links = []
    for url in urls:
        use_cache = False
        if url in cache_data:
            cache_time = cache_data[url].get("time", 0)
            if time.time() - cache_time < 3600:
                use_cache = True
                
        content = ""
        if use_cache:
            content = cache_data[url].get("content", "")
        else:
            try:
                safe_print(f"[VLESS-Rot] Fetching {url}")
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                # Check if it's base64 encoded
                if 'vless://' not in content:
                    content = b64decode_padding(content)
                cache_data[url] = {"time": time.time(), "content": content}
            except Exception as e:
                safe_print(f"[VLESS-Rot] Error fetching {url}: {e}")
                if url in cache_data:
                    content = cache_data[url].get("content", "")
                    
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('vless://'):
                vless_links.append(line)
                
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f)
        
    return list(set(vless_links))

def parse_vless(link):
    # vless://uuid@host:port?encryption=none&security=reality&sni=...&pbk=...&sid=...#name
    try:
        if '#' in link:
            link, name = link.split('#', 1)
        else:
            name = ""
            
        parts = urllib.parse.urlparse(link)
        if parts.scheme != 'vless':
            return None
            
        uuid = parts.username
        host = parts.hostname
        port = parts.port
        
        query = urllib.parse.parse_qs(parts.query)
        security = query.get('security', [''])[0]
        sni = query.get('sni', [host])[0]
        pbk = query.get('pbk', [''])[0]
        sid = query.get('sid', [''])[0]
        
        if not uuid or not host or not port:
            return None
            
        return {
            "uuid": uuid,
            "host": host,
            "port": port,
            "security": security,
            "sni": sni,
            "pbk": pbk,
            "sid": sid,
            "name": urllib.parse.unquote(name)
        }
    except Exception as e:
        return None

def check_tcp(host, port, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
        return True
    except:
        return False

def generate_config(server_info):
    cfg = {
        "log": {"level": "fatal"},
        "inbounds": [{
            "type": "socks",
            "tag": "socks-in",
            "listen": "127.0.0.1",
            "listen_port": 1790
        }],
        "outbounds": [{
            "type": "vless",
            "tag": "vless-out",
            "server": server_info["host"],
            "server_port": server_info["port"],
            "uuid": server_info["uuid"],
            "flow": "xtls-rprx-vision" if server_info["security"] == "reality" else "",
            "tls": {
                "enabled": server_info["security"] in ["tls", "reality"],
                "server_name": server_info["sni"] if server_info["sni"] else server_info["host"],
                "insecure": not bool(server_info["sni"]),
                "utls": {"enabled": True, "fingerprint": "chrome"}
            }
        }]
    }
    
    if server_info["security"] == "reality":
        cfg["outbounds"][0]["tls"]["reality"] = {
            "enabled": True,
            "public_key": server_info["pbk"],
            "short_id": server_info["sid"]
        }
        
    config_path = os.path.join(SING_BOX_DIR, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        
    return config_path

def kill_singbox():
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == "sing-box.exe":
                p = psutil.Process(proc.info['pid'])
                p.kill()
        except:
            pass

def main():
    config = load_config()
    interval = config.get("vless_rot_interval", 300)
    
    links = fetch_subs()
    servers = []
    for link in links:
        s = parse_vless(link)
        if s:
            servers.append(s)
            
    safe_print(f"[VLESS-Rot] Loaded {len(servers)} servers")
    
    if not servers:
        safe_print("[VLESS-Rot] No servers found. Exiting.")
        return
        
    server_idx = 0
    proc = None
    
    try:
        while True:
            srv = servers[server_idx % len(servers)]
            server_idx += 1
            
            safe_print(f"[VLESS-Rot] Testing server: {srv['host']}:{srv['port']} {srv['name']}")
            if not check_tcp(srv["host"], srv["port"]):
                safe_print("[VLESS-Rot] Server offline, skipping...")
                time.sleep(1)
                continue
                
            safe_print(f"[VLESS-Rot] Starting sing-box on server {srv['host']}")
            kill_singbox()
            
            cfg_path = generate_config(srv)
            proc = subprocess.Popen(
                [SING_BOX_EXE, "run", "-c", cfg_path],
                cwd=SING_BOX_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        safe_print(f"[VLESS-Rot] Error: {e}")
    finally:
        kill_singbox()

if __name__ == "__main__":
    main()
