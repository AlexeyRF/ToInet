#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ByeByeDPI Strategy Tester (Python Analog)
=========================================
This script is a Python equivalent of the strategy selector implemented in ByeByeDPI Android.
It loads a list of strategies and site lists, then for each strategy:
1. Launches the `byedpi` (or `ciadpi`) daemon as a subprocess.
2. Sends HTTP/HTTPS requests to the target domains through the SOCKS5 proxy.
3. Checks if the connection succeeded and the response size matches the expectations (detecting DPI blocks).
4. Records, sorts, and displays the most effective strategies.

No third-party dependencies are required (runs on pure standard library).
"""

import os
import sys
import time
import socket
import ssl
import http.client
import urllib.parse
import subprocess
import argparse
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- ANSI Colors ---
def init_colors():
    if os.name == 'nt':
        os.system('')  # Enable ANSI terminal colors on Windows 10+

def color_text(text, color):
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'bold': '\033[1m',
        'underline': '\033[4m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

# --- Embedded Default Strategies (80 strategies from proxytest_strategies.list) ---
DEFAULT_STRATEGIES = [
    '-l:"\\xC2\\x00\\x00\\x00\\x01\\x14\\x2E\\xE3\\xE3\\x5F\\x6B\\xBB\\x23\\xA8\\xE6\\x5D\\xA9\\x78\\x21\\xCF\\xC2\\x72\\x4C\\x8F\\xC4\\x5E\\x14\\x00\\x00\\x00\\x00\\xC5\\x00\\x00\\x00\\x00\\x4C\\x00\\xA7\\x00\\x00\\x00\\x00\\x00\\x00\\x44\\x00\\x00\\x80\\x00\\x00\\x00\\x0D\\xFC\\xFA\\x1D\\xCD\\x73\\xBA\\x2A\\x90\\x93\\xB3\\xEE\\xF7\\x43\\xC5\\x85\\xDA\\xFF\\x45\\x3C\\x00\\x00\\x00\\x00\\x00\\x00\\x7C\\x00\\x9B\\x00\\xF6\\x00\\x00\\xDD\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x59\\xA8\\xE4\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x7B\\x00\\x0F\\x00\\x00\\x00\\x48\\x4E\\x00\\x00\\x00\\x06\\xF3\\x00\\x00\\x00\\x00\\xD9\\x5A\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00" -a3 -t12 -d1 -s0+h -d3+s -s6+s -d5+s -s8+s -d7+s -s10+s -d3 -At,s -r3',
    '-f-200 -Qr -s3:5+sm -a1 -As -d1 -s4+sm -s8+sh -f-300 -d6+sh -a1 -At,r,s -o2 -f-30 -As -r5 -Mh -r6+sh -f-250 -s2:7+s -s3:6+sm -a1 -At,r,s -s3:5+sm -s6+s -s7:9+s -q30+sm -a1',
    '-d1 -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -r1+s -S -a1 -As -d1 -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -S -a1',
    '-q2 -s2 -s3+s -r3 -s4 -r4 -s5+s -r5+s -s6 -s7+s -r8 -s9+s -Qr -Mh,d,r -a1 -At,r -s2+s -r2 -d2 -s3 -r3 -r4 -s4 -d5+s -r5 -d6 -s7+s -d7 -a1',
    '-Ku -l:"\\xe3\\x00\\x06\\xec\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00" -a3 -An -f64+se -n {sni} -t5',
    '-o1 -d1 -a1 -At,r,s -s1 -d1 -s5+s -s10+s -s15+s -s20+s -r1+s -S -a1 -As -s1 -d1 -s5+s -s10+s -s15+s -s20+s -S -a1',
    '-n {sni} -Qr -f-204 -s1:5+sm -a1 -As -d1 -s3+s -s5+s -q7 -a1 -As -o2 -f-43 -a1 -As -r5 -Mh -s1:5+s -s3:7+sm -a1',
    '-n {sni} -Qr -f-205 -a1 -As -s1:3+sm -a1 -As -s5:8+sm -a1 -As -d3 -q7 -o2 -f-43 -f-85 -f-165 -r5 -Mh -a1',
    '-d1+s -s50+s -a1 -As -f20 -r2+s -a1 -At -d2 -s1+s -s5+s -s10+s -s15+s -s25+s -s35+s -s50+s -s60+s -a1',
    '-o1 -a1 -At,r,s -f-1 -a1 -At,r,s -d1:11+sm -S -a1 -At,r,s -n {sni} -Qr -f1 -d1:11+sm -s1:11+sm -S -a1',
    '-d1 -s1 -q1 -Y -a1 -Ar -s5 -o1+s -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -a1',
    '-f1+nme -t6 -a1 -As -n {sni} -Qr -s1:6+sm -a1 -As -s5:12+sm -a1 -As -d3 -q7 -r6 -Mh -a1',
    '-s1 -o1 -a1 -Y -Ar -s5 -o1+s -a1 -At -f-1 -r1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-s1 -d1 -a1 -Y -Ar -d5 -o1+s -a1 -At -f-1 -r1+s -a1 -As -d1 -o1+s -s-1 -a1',
    '-d1 -s1+s -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -a1',
    '-s1 -q1 -a1 -Y -Ar -a1 -s5 -o2 -At -f-1 -r1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-s1 -q1 -a1 -Ar -s5 -o1+s -a1 -At -f-1 -d1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-s1 -q1 -a1 -Ar -s5 -o2 -a1 -At -f-1 -r1+s -a1 -As -s1 -o1+s -s-1 -a1',
    '-d1 -s1+s -d1+s -s3+s -d6+s -s12+s -d14+s -s20+s -d24+s -s30+s -a1',
    '-s1 -q1 -a1 -Y -At -a1 -S -f-1 -r1+s -a1 -As -d1+s -O1 -s29+s -a1',
    '-o1 -a1 -At,r,s -f-1 -a1 -Ar,s -o1 -a1 -At -r1+s -f-1 -t6 -a1',
    '-d1 -s1+s -s3+s -s6+s -s9+s -s12+s -s15+s -s20+s -s30+s -a1',
    '-f1 -t5 -n {sni} -q3+h -Qr -f2 -q1 -r1+s -t15 -q1 -o2 -a1',
    '-n {sni} -d2:5:2+h -f-3 -r2+sm -o2 -o50+s -r2+s -f-4 -a1',
    '-r-1+s -o20+sm -s3:7+sm -d5:3+sm -f300+s -Qr -Y -f-1 -a1',
    '-f-1 -Qr -s1+sm -d3+s -s5+sm -o2 -a1 -As -r1+s -d8+s -a1',
    '-s25 -r5+s -s25+s -a1 -At,r,s -s50 -r5+s -s50+s -a1',
    '-o2 -O4 -s1 -q1 -a2 -Ar -s5 -o1+s -f1+s -r20+s -a2',
    '-o1 -r-5+se -a1 -At,r,s -d1 -n {sni} -Qr -f-1 -a1',
    '--fake -1 --ttl 8 --split 1+s --disorder 3+s -a1',
    '-s1 -d1 -r1+s -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s1 -q1 -r1+s -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s1 -o1 -r1+s -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-n {sni} -Qr -f6+nr -d2 -d11 -f9+hm -o3 -t7 -a1',
    '-d1 -d3+s -s6+s -d9+s -s20+s -d25+s -s30+s -a1',
    '-s1 -d1 -o1 -a1 -Ar -o3 -a1 -At -f-1 -r1+s -a1',
    '-d9+s -q20+s -s25+s -t5 -a1 -At,r,s -r1+h -a1',
    '-q1+s -s29+s -s30+s -s14+s -o5+s -f-1 -S -a1',
    '-d1 -s1+s -r1+s -e1 -m1 -o1+s -f-1 -t2 -a1',
    '-d9+s -q20+s -s 25+s -t5 -At,r,s -r1+h -a1',
    '-s1 -o1 -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-d1 -o1 -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-d1 -s4 -d8 -s1+s -d5+s -s10+s -d20+s -a1',
    '-f-1 -n {sni} -Qr -s2+s -r3 -o20 -t4 -a7',
    '-n {sni} -Qr -d5+sm -f3+sm -o2 -t4 -a1',
    '-o1 -a1 -Ar -q1 -a1 -At -f-1 -r1+s -a1',
    '-q1 -a1 -Ar -o1 -a1 -At -f-1 -r1+s -a1',
    '-s1 -q1 -Y -a1 -At,r,s -f-1 -r1+s -a1',
    '-s1 -o1 -Y -a1 -At,r,s -f-1 -r1+s -a1',
    '-s1 -d1 -Y -a1 -At,r,s -f-1 -r1+s -a1',
    '-n {sni} -Qr -f209 -s1+sm -R1-3 -a1',
    '-s1 -q1 -a1 -At,r,s -f-1 -r1+s -a1',
    '-s1 -o1 -a1 -At,r,s -f-1 -r1+s -a1',
    '-s1 -d1 -a1 -At,r,s -f-1 -r1+s -a1',
    '-s4+sn -r9+s -Qr -n {sni} -S -a1',
    '-o1 -d1 -r1+s -S -s1+s -d3+s -a1',
    '-d1 -r1+s -f-1 -S -t8 -o3+s -a1',
    '-q1+s -s29+s -o5+s -f-1 -S -a1',
    '-n {sni} -Qr -m2 -f-1 -d7 -a1',
    '-d1 -s1+s -r1+s -f-1 -t8 -a1',
    '-o1 -a1 -An -f1+nme -t6 -a1',
    '-n {sni} -Qr -f-1 -r1+s -a1',
    '-n {sni} -Qr -d1:3 -f-1 -a1',
    '-s1 -d3+s -a1 -At -r1+s -a1',
    '-f-1 -t8 -n {sni} -s1+s -a5',
    '-o1 -a1 -At,r,s -d1 -a1',
    '-n {sni} -Qr -d1 -f-1',
    '-d1+s -o2 -s5 -r5 -a1',
    '-r8 -o2 -s7 -q4+s -a1',
    '-d6+s -q4+hm -o2 -a1',
    '-f-1+sm -t7 -a5 -m2',
    '-o1 -a1 -r-5+se',
    '-s1+s -d3+s -a1',
    '-s1 -f-1 -S -a1',
    '-o1+s -d3+s -a1',
    '-o1 -s4 -s6 -a1',
    '-q1 -r25+s -a1',
    '-d1 -s3+s -a1',
    '-o3 -d7 -a1',
    '-d7 -s2 -a1'
]

# --- Embedded Default Site Lists ---
DEFAULT_SITES = [
    # General sites
    'rutracker.org',
    'nyaa.si',
    'rutor.org',
    'nnmclub.to',
    'speedtest.net',
    # YouTube / Google Video sites
    'youtube.com',
    'youtu.be',
    'i.ytimg.com',
    'googleapis.com',
    'googleusercontent.com',
    'manifest.googlevideo.com'
]

# --- Shell Argument Parser (Direct Kotlin translation of shellSplit) ---
def shell_split(string: str) -> list[str]:
    tokens = []
    quote_char = ' '
    escaping = False
    quoting = False
    last_close_quote_index = -999999
    current = []

    for i in range(len(string)):
        c = string[i]

        if escaping:
            current.append(c)
            escaping = False
        elif c == '\\' and quoting:
            if i + 1 < len(string) and string[i + 1] == quote_char:
                escaping = True
            else:
                current.append(c)
        elif quoting and c == quote_char:
            quoting = False
            last_close_quote_index = i
        elif not quoting and (c == "'" or c == '"'):
            quoting = True
            quote_char = c
        elif not quoting and c.isspace():
            if current or last_close_quote_index == i - 1:
                tokens.append("".join(current))
                current = []
        else:
            current.append(c)

    if current or last_close_quote_index == len(string) - 1:
        tokens.append("".join(current))

    return tokens

# --- IP and Port detection logic (Direct Kotlin translation of checkIpAndPortInCmd) ---
def check_ip_and_port_in_cmd(cmd_args: list[str]) -> tuple[str | None, str | None]:
    def get_arg_value(keys: list[str]) -> str | None:
        for i in range(len(cmd_args)):
            arg = cmd_args[i]
            for key in keys:
                if key.startswith("--"):
                    if arg == key and i + 1 < len(cmd_args):
                        return cmd_args[i + 1]
                    elif arg.startswith(key + "="):
                        return arg.split('=', 1)[1]
                elif key.startswith("-"):
                    if arg.startswith(key) and len(arg) > len(key):
                        return arg[len(key):]
                    elif arg == key and i + 1 < len(cmd_args):
                        return cmd_args[i + 1]
        return None

    cmd_ip = get_arg_value(["--ip", "-i"])
    cmd_port = get_arg_value(["--port", "-p"])
    return cmd_ip, cmd_port

# --- SOCKS5 Client ---
def connect_socks5(proxy_host, proxy_port, dest_host, dest_port, timeout=5):
    """Establishes a raw connection to SOCKS5 proxy and performs handshake."""
    s = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
    
    # Handshake: version 5, 1 auth method, no authentication
    s.sendall(b'\x05\x01\x00')
    resp = s.recv(2)
    if len(resp) != 2 or resp[0] != 5 or resp[1] != 0:
        s.close()
        raise Exception("SOCKS5 negotiation failed")
    
    # Request connect
    try:
        # IPv4
        ip_bytes = socket.inet_aton(dest_host)
        addr_type = 1
        addr_bytes = ip_bytes
    except socket.error:
        try:
            # IPv6
            ip_bytes = socket.inet_pton(socket.AF_INET6, dest_host)
            addr_type = 4
            addr_bytes = ip_bytes
        except socket.error:
            # Domain Name
            addr_type = 3
            host_bytes = dest_host.encode('utf-8')
            addr_bytes = bytes([len(host_bytes)]) + host_bytes
            
    req = struct.pack('!BBBB', 5, 1, 0, addr_type) + addr_bytes + struct.pack('!H', dest_port)
    s.sendall(req)
    
    resp = s.recv(4)
    if len(resp) < 4 or resp[0] != 5 or resp[1] != 0:
        s.close()
        raise Exception(f"SOCKS5 connection failed: code {resp[1] if len(resp) >= 2 else 'unknown'}")
        
    # Read remaining address and port
    bnd_addr_type = resp[3]
    if bnd_addr_type == 1:
        s.recv(6)  # 4 bytes IP + 2 bytes Port
    elif bnd_addr_type == 3:
        len_byte = s.recv(1)
        if len_byte:
            s.recv(ord(len_byte) + 2)
    elif bnd_addr_type == 4:
        s.recv(18)  # 16 bytes IP + 2 bytes Port
        
    return s

# --- HTTP / HTTPS custom connection subclasses over SOCKS5 ---
class SOCKS5HTTPConnection(http.client.HTTPConnection):
    def __init__(self, proxy_host, proxy_port, host, port=None, timeout=5, **kwargs):
        super().__init__(host, port, timeout=timeout, **kwargs)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def connect(self):
        self.sock = connect_socks5(self.proxy_host, self.proxy_port, self.host, self.port or 80, self.timeout)

class SOCKS5HTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, proxy_host, proxy_port, host, port=None, timeout=5, context=None, **kwargs):
        super().__init__(host, port, timeout=timeout, context=context, **kwargs)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def connect(self):
        self.sock = connect_socks5(self.proxy_host, self.proxy_port, self.host, self.port or 443, self.timeout)
        if self._tunnel_host:
            self._tunnel()
        
        if self._context is None:
            # Tolerant SSL configuration (similar to check bypasses)
            self._context = ssl.create_default_context()
            self._context.check_hostname = False
            self._context.verify_mode = ssl.CERT_NONE
            
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)

# --- Probing function ---
def check_url(proxy_host, proxy_port, url_str, timeout=5):
    """Sends a GET request to a url through SOCKS5 proxy and verifies content length."""
    parsed = urllib.parse.urlparse(url_str)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
        
    redirects_limit = 5
    current_url = url_str
    
    for _ in range(redirects_limit):
        if scheme == 'https':
            conn = SOCKS5HTTPSConnection(proxy_host, proxy_port, host, port or 443, timeout=timeout)
        elif scheme == 'http':
            conn = SOCKS5HTTPConnection(proxy_host, proxy_port, host, port or 80, timeout=timeout)
        else:
            return False, f"Unsupported scheme {scheme}"
            
        try:
            # Probing request: mimics a simple web browser
            conn.request("GET", path, headers={
                "Connection": "close",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp = conn.getresponse()
            
            declared_len = resp.getheader('content-length')
            declared_len = int(declared_len) if declared_len is not None else -1
            
            actual_len = 0
            limit = declared_len if declared_len > 0 else 1024 * 1024  # Cap body read to 1MB if no content-length
            
            while actual_len < limit:
                chunk = resp.read(min(8192, limit - actual_len))
                if not chunk:
                    break
                actual_len += len(chunk)
                
            # Follow redirects (301, 302, etc.)
            if resp.status in (301, 302, 303, 307, 308):
                loc = resp.getheader('Location')
                if loc:
                    current_url = urllib.parse.urljoin(current_url, loc)
                    parsed = urllib.parse.urlparse(current_url)
                    scheme = parsed.scheme.lower()
                    host = parsed.hostname
                    port = parsed.port
                    path = parsed.path or "/"
                    if parsed.query:
                        path += "?" + parsed.query
                    conn.close()
                    continue
            
            # Successful connection and matched payload content size checks
            if declared_len <= 0 or actual_len >= declared_len:
                return True, f"Success ({resp.status})"
            else:
                return False, f"Block detected (read {actual_len} bytes, declared {declared_len})"
                
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
            
    return False, "Too many redirects"

# --- Subprocess Management ---
def start_byedpi(executable, strategy_args):
    """Launches the byedpi subprocess with given arguments."""
    try:
        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
        proc = subprocess.Popen(
            [executable] + strategy_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            text=True
        )
        return proc
    except Exception as e:
        print(color_text(f"Error starting byedpi: {e}", 'red'))
        return None

def stop_byedpi(proc):
    """Stops the running byedpi subprocess."""
    if proc is None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    except Exception:
        pass

def wait_for_proxy_port(ip, port, timeout=3.0):
    """Waits until the proxy opens and listens on the specified port."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            s = socket.create_connection((ip, port), timeout=0.3)
            s.close()
            return True
        except Exception:
            time.sleep(0.1)
    return False

# --- Testing Loop ---
def run_test(args):
    init_colors()
    
    # 1. Setup Executable Path
    byedpi_path = args.byedpi
    if not os.path.exists(byedpi_path):
        # Try to search in system PATH
        import shutil
        found_path = shutil.which(byedpi_path)
        if found_path:
            byedpi_path = found_path
        else:
            print(color_text(f"Error: byedpi executable '{args.byedpi}' was not found.", 'red'))
            print("Please place the byedpi/ciadpi binary in this directory or provide the absolute path using --byedpi")
            sys.exit(1)
            
    print(color_text("=== ByeByeDPI Python Strategy Tester ===", 'bold'))
    print(f"Byedpi Executable: {color_text(byedpi_path, 'cyan')}")
    print(f"Target SNI for replace: {color_text(args.sni, 'cyan')}")
    print(f"Proxy Bind IP/Port: {color_text(f'{args.ip}:{args.port}', 'cyan')}\n")

    # 2. Setup strategies list
    strategies = []
    if args.strategies_file and os.path.exists(args.strategies_file):
        print(f"Loading custom strategies from: {args.strategies_file}")
        with open(args.strategies_file, 'r', encoding='utf-8') as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith("#"):
                    strategies.append(l)
    else:
        # Check if assets exist locally in workspace
        local_assets_strategies = os.path.join("app", "src", "main", "assets", "proxytest_strategies.list")
        if os.path.exists(local_assets_strategies):
            print(f"Loading strategies from local assets: {local_assets_strategies}")
            with open(local_assets_strategies, 'r', encoding='utf-8') as f:
                for line in f:
                    l = line.strip()
                    if l and not l.startswith("#"):
                        strategies.append(l)
        else:
            print(f"Loading embedded default strategies ({len(DEFAULT_STRATEGIES)} configurations)")
            strategies = list(DEFAULT_STRATEGIES)
            
    # 3. Setup sites list
    sites = []
    if args.sites:
        sites = [s.strip() for s in args.sites.split(',') if s.strip()]
    elif args.sites_file and os.path.exists(args.sites_file):
        print(f"Loading custom sites from: {args.sites_file}")
        with open(args.sites_file, 'r', encoding='utf-8') as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith("#"):
                    sites.append(l)
    else:
        local_assets_general = os.path.join("app", "src", "main", "assets", "proxytest_general.sites")
        if os.path.exists(local_assets_general):
            print(f"Loading sites from local assets: {local_assets_general}")
            with open(local_assets_general, 'r', encoding='utf-8') as f:
                for line in f:
                    l = line.strip()
                    if l and not l.startswith("#"):
                        sites.append(l)
        else:
            print(f"Loading embedded default sites ({len(DEFAULT_SITES)} domains)")
            sites = list(DEFAULT_SITES)

    print(f"Successfully loaded {color_text(len(strategies), 'bold')} strategies and {color_text(len(sites), 'bold')} sites.\n")
    print(color_text("Starting strategy selection loop...", 'bold'))
    print("-" * 70)

    # 4. Strategy Testing Loop
    results = []
    
    for idx, strategy_template in enumerate(strategies):
        # Format SNI in the strategy
        strategy_cmd = strategy_template.replace("{sni}", f'"{args.sni}"')
        
        print(f"Strategy [{idx + 1}/{len(strategies)}]: {color_text(strategy_cmd, 'yellow')}")
        
        # Parse command line to list of args
        parsed_args = shell_split(strategy_cmd)
        
        # Detect if ip/port already defined in the command
        cmd_ip, cmd_port = check_ip_and_port_in_cmd(parsed_args)
        
        proxy_ip = cmd_ip or args.ip
        proxy_port = int(cmd_port or args.port)
        
        # Prepend IP and Port if not defined in the cmd
        final_args = []
        if cmd_ip is None:
            final_args.extend(["--ip", proxy_ip])
        if cmd_port is None:
            final_args.extend(["--port", str(proxy_port)])
            
        final_args.extend(parsed_args)
        
        # Start daemon
        proc = start_byedpi(byedpi_path, final_args)
        if not proc:
            print(color_text(" -> FAILED to spawn byedpi process.", 'red'))
            results.append((strategy_template, 0.0, 0, len(sites)))
            print("-" * 70)
            continue
            
        # Wait for port to open
        if not wait_for_proxy_port(proxy_ip, proxy_port, timeout=3.0):
            print(color_text(f" -> ERROR: SOCKS5 proxy port {proxy_ip}:{proxy_port} did not open.", 'red'))
            stop_byedpi(proc)
            results.append((strategy_template, 0.0, 0, len(sites)))
            print("-" * 70)
            continue
            
        # Give daemon 200ms additional breathing room
        time.sleep(args.delay)
        
        # Parallel test sites
        success_count = 0
        checked_details = {}
        
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = {
                executor.submit(
                    check_url, 
                    proxy_ip, 
                    proxy_port, 
                    f"https://{site}", 
                    timeout=args.timeout
                ): site
                for site in sites
            }
            
            for future in as_completed(futures):
                site = futures[future]
                try:
                    success, msg = future.result()
                    checked_details[site] = (success, msg)
                    if success:
                        success_count += 1
                except Exception as e:
                    checked_details[site] = (False, str(e))
                    
        # Stop daemon
        stop_byedpi(proc)
        time.sleep(0.3)  # wait for port to completely unbind
        
        # Calculate success percentage
        pct = (success_count / len(sites)) * 100
        results.append((strategy_template, pct, success_count, len(sites)))
        
        # Print summary for this strategy
        color = 'green' if pct >= 80 else 'yellow' if pct >= 40 else 'red'
        pct_str = f"{pct:.1f}% ({success_count}/{len(sites)})"
        print(f" -> Result: {color_text(pct_str, color)}")
        
        # Show verbose logs if requested
        if args.verbose:
            for s, (ok, m) in checked_details.items():
                s_color = 'green' if ok else 'red'
                symbol = '✔' if ok else '✘'
                print(f"    {color_text(symbol, s_color)} {s:<25} : {m}")
        print("-" * 70)

    # 5. Output sorted results
    print(color_text("\n=== FINAL RESULTS SUMMARY (Sorted by Success Rate) ===", 'bold'))
    
    # Sort strategies by success percentage (descending)
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Print nice table
    print(f"{'#':<3} | {'Success Rate':<18} | {'Strategy Command'}")
    print("-" * 80)
    for r_idx, (strat, pct, succ, tot) in enumerate(results):
        color = 'green' if pct >= 80 else 'yellow' if pct >= 40 else 'red'
        pct_str = f"{pct:.1f}% ({succ}/{tot})"
        print(f"{r_idx+1:<3} | {color_text(pct_str, color):<27} | {strat}")
        
    print("\nBest strategy: ", end="")
    if results and results[0][1] > 0:
        print(color_text(results[0][0], 'green'))
    else:
        print(color_text("None of the tested strategies worked.", 'red'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ByeByeDPI Strategy Tester (Python Analog)")
    
    parser.add_argument('-b', '--byedpi', type=str, default='ciadpi',
                        help="Path to the byedpi/ciadpi executable (default: 'ciadpi')")
    parser.add_argument('-s', '--sni', type=str, default='google.com',
                        help="SNI value to replace {sni} in strategies (default: 'google.com')")
    parser.add_argument('--ip', type=str, default='127.0.0.1',
                        help="Default proxy SOCKS5 IP (default: 127.0.0.1)")
    parser.add_argument('--port', type=str, default='1080',
                        help="Default proxy SOCKS5 Port (default: 1080)")
    parser.add_argument('-c', '--concurrency', type=int, default=10,
                        help="Max concurrent site check requests (default: 10)")
    parser.add_argument('-t', '--timeout', type=float, default=4.0,
                        help="Request connect/read timeout in seconds (default: 4.0)")
    parser.add_argument('-d', '--delay', type=float, default=0.2,
                        help="Delay in seconds to wait after starting daemon before probing (default: 0.2)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Show detailed access probe logs for each site")
    parser.add_argument('--strategies-file', type=str, default=None,
                        help="Path to custom strategies.list file")
    parser.add_argument('--sites-file', type=str, default=None,
                        help="Path to custom sites.list file")
    parser.add_argument('--sites', type=str, default=None,
                        help="Comma-separated list of custom target sites to test")
                        
    args = parser.parse_args()
    
    try:
        run_test(args)
    except KeyboardInterrupt:
        print(color_text("\nTest cancelled by user.", 'red'))
        sys.exit(0)
