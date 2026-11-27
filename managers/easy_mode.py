import os
import sys
import time
import socket
import ssl
import struct
import threading
import subprocess
import ctypes

from PySide6.QtCore import QObject, Signal

from managers import config_manager
from managers import system_utils as utils
from managers.system_utils import log, get_base_dir

CURRENT_DIR = get_base_dir()
COMMS_DNS_PRIMARY = "195.123.209.76"
COMMS_DNS_SECONDARY = "185.112.83.4"
EASY_EVPN_PORT = 1788
ZDPI_TEST_PORT = 1789


def ping_1111(timeout_ms=1200):
    """Returns True if 1.1.1.1 responds to ICMP ping."""
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        res = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), "1.1.1.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            timeout=(timeout_ms / 1000.0) + 2.0,
        )
        return res.returncode == 0
    except Exception:
        return False


def set_comms_dns_silent(enable=True):
    """Silently sets Comms DNS (195.123.209.76, 185.112.83.4) or resets to DHCP."""
    if os.name != "nt":
        return False
    try:
        import win32com.client
        wmi = win32com.client.GetObject("winmgmts:\\\\.\\root\\cimv2")
        adapters = wmi.ExecQuery("SELECT * FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled = True")
        cmds = []
        for adapter in adapters:
            alias = str(adapter.Description or "").replace("'", "''")
            if not alias:
                continue
            if enable:
                cmds.append(
                    f"Get-NetAdapter | Where-Object {{ $_.InterfaceDescription -eq '{alias}' }} | "
                    f"Set-DnsClientServerAddress -ServerAddresses '{COMMS_DNS_PRIMARY}','{COMMS_DNS_SECONDARY}'"
                )
            else:
                cmds.append(
                    f"Get-NetAdapter | Where-Object {{ $_.InterfaceDescription -eq '{alias}' }} | "
                    f"Set-DnsClientServerAddress -ResetServerAddresses"
                )
        if not cmds:
            return False
        cmds.append("Clear-DnsClientCache")
        ps_cmd = "; ".join(cmds)

        # Try directly first (works without UAC if already elevated)
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10,
        )
        if res.returncode == 0:
            return True

        # Fallback to UAC elevation if not elevated
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "powershell.exe",
            f'-NoProfile -WindowStyle Hidden -Command "{ps_cmd}"', None, 0
        )
        return ret > 32
    except Exception as e:
        log(f"[EasyMode] DNS update error: {e}")
        return False


def check_socks5_connectivity(port, test_host="cp.cloudflare.com", test_port=80, timeout=4.0):
    """Checks if a local SOCKS5 proxy can actually connect out."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", int(port)))
        # Greeting: VER=5, NMETHODS=1, NO_AUTH=0
        s.sendall(b"\x05\x01\x00")
        resp = s.recv(2)
        if len(resp) < 2 or resp[0] != 5 or resp[1] != 0:
            return False
        # CONNECT domain
        host_b = test_host.encode("ascii")
        req = b"\x05\x01\x00\x03" + bytes([len(host_b)]) + host_b + struct.pack(">H", test_port)
        s.sendall(req)
        rep = s.recv(10)
        return len(rep) >= 2 and rep[1] == 0x00
    except Exception:
        return False
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


def create_easy_desktop_shortcut():
    """Creates a desktop shortcut 'ToInet-MAX (Easy).lnk' launching with -easy."""
    try:
        import pythoncom
        from win32com.client import Dispatch

        desktop_path = utils.get_desktop_path()
        app_dir = utils.get_app_directory()
        is_frozen = getattr(sys, "frozen", False)

        if is_frozen:
            target_path = sys.executable
            args = "-easy"
        else:
            pyw_exe = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(pyw_exe):
                pyw_exe = sys.executable
            target_path = pyw_exe
            args = f'"{os.path.join(app_dir, "main.pyw")}" -easy'

        icon_path = None
        for cand in [
            os.path.join(app_dir, "icon.ico"),
            os.path.join(getattr(sys, "_MEIPASS", ""), "icon.ico"),
            sys.executable,
        ]:
            if cand and os.path.exists(cand):
                icon_path = os.path.abspath(cand)
                break

        shortcut_path = os.path.join(desktop_path, "ToInet-MAX (Easy).lnk")
        pythoncom.CoInitialize()
        try:
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target_path
            shortcut.Arguments = args
            shortcut.WorkingDirectory = app_dir
            if icon_path:
                shortcut.IconLocation = f"{icon_path},0" if (icon_path.endswith(".ico") or icon_path.endswith(".exe")) else icon_path
            shortcut.save()
        finally:
            pythoncom.CoUninitialize()
        return True
    except Exception as e:
        log(f"[EasyMode] Shortcut creation failed: {e}")
        return False


def _test_zdpi_strategy(zdpi_exe, strategy_args, test_sites, port=ZDPI_TEST_PORT):
    """Launches zdpi on a temporary port and scores how many test_sites connect over TLS."""
    proc = None
    try:
        args = strategy_args.split()
        cmd = [zdpi_exe, "-p", str(port)] + args
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)

        # Wait briefly for port to bind
        ready = False
        for _ in range(15):
            if proc.poll() is not None:
                return 0
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    ready = True
                    break
            except Exception:
                time.sleep(0.1)
        if not ready:
            return 0

        score = 0
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for domain in test_sites:
            s = None
            ss = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.5)
                s.connect(("127.0.0.1", port))
                s.sendall(b"\x05\x01\x00")
                if len(s.recv(2)) < 2:
                    continue
                db = domain.encode("ascii")
                s.sendall(b"\x05\x01\x00\x03" + bytes([len(db)]) + db + struct.pack(">H", 443))
                rep = s.recv(10)
                if len(rep) < 2 or rep[1] != 0:
                    continue
                ss = ctx.wrap_socket(s, server_hostname=domain)
                ss.sendall(f"HEAD / HTTP/1.1\r\nHost: {domain}\r\nConnection: close\r\n\r\n".encode("ascii"))
                data = ss.recv(64)
                if data:
                    score += 1
            except Exception:
                pass
            finally:
                for sock_obj in (ss, s):
                    if sock_obj:
                        try:
                            sock_obj.close()
                        except Exception:
                            pass
        return score
    except Exception:
        return 0
    finally:
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


class EasyModeController(QObject):
    status_updated = Signal(str)
    state_changed = Signal(bool)
    zdpi_status_updated = Signal(str)

    def __init__(self, main_mod):
        super().__init__()
        self.m = main_mod
        self.active = False
        self.connecting = False
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._optimizer_thread = None
        self._watchdog_thread = None
        self._dns_applied = False

    def start_easy(self):
        if self.active or self.connecting:
            return
        self.connecting = True
        self._stop_event.clear()
        self.status_updated.emit("Проверка сети (1.1.1.1) и запуск...")
        self._worker_thread = threading.Thread(target=self._start_sequence, daemon=True)
        self._worker_thread.start()

    def _start_sequence(self):
        try:
            m = self.m
            m.mode_mgr.easy_mode = True
            m.mode_mgr.easy_evpn_port = EASY_EVPN_PORT

            # Ensure tgws, gatik, ssh are stopped
            for mgr_attr in ("tgws_mgr", "ssh_mgr"):
                mgr = getattr(m, mgr_attr, None)
                if mgr:
                    try:
                        mgr.stop()
                    except Exception:
                        pass

            ping_ok = ping_1111()
            use_evpn = not ping_ok
            m.mode_mgr.easy_use_evpn_upstream = use_evpn
            m.mode_mgr.easy_foreign_tag = "opera"

            if self._stop_event.is_set():
                self.connecting = False
                return

            # Start core providers
            m.byedpi_manager.start()
            m.tor_manager.start()

            if use_evpn:
                self.status_updated.emit("1.1.1.1 не пингуется — запуск easy-vpn как upstream...")
                m.evpn_mgr.start(socks_port=EASY_EVPN_PORT)
                # Wait briefly for easy-vpn SOCKS port
                for _ in range(40):
                    if self._stop_event.is_set():
                        self.connecting = False
                        return
                    if check_socks5_connectivity(EASY_EVPN_PORT, timeout=1.0):
                        break
                    time.sleep(0.5)
            else:
                self.status_updated.emit("Запуск Opera Proxy (резерв: Tor)...")
                m.opera_mgr.start()

            if self._stop_event.is_set():
                self.connecting = False
                return

            # Start sing-box TUN and inetcpl simultaneously
            m.mode_mgr.start_tun()
            m.mode_mgr.start_inetcpl_proxy()

            # Apply Comms DNS
            set_comms_dns_silent(True)
            self._dns_applied = True

            self.active = True
            self.connecting = False
            m.proxy_enabled = True
            self.state_changed.emit(True)

            if use_evpn:
                self.status_updated.emit("Работает • Upstream: easy-vpn • Comms DNS")
            else:
                self.status_updated.emit("Работает • Зарубежный трафик: Opera Proxy (резерв Tor) • Comms DNS")

            # Start background watchdog & zDPI strategy optimizer
            self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
            self._watchdog_thread.start()

            self._optimizer_thread = threading.Thread(target=self._zdpi_optimizer_loop, daemon=True)
            self._optimizer_thread.start()

        except Exception as e:
            log(f"[EasyMode] Start failed: {e}")
            self.connecting = False
            self.active = False
            self.state_changed.emit(False)
            self.status_updated.emit(f"Ошибка запуска: {e}")

    def _watchdog_loop(self):
        """Monitors OP health -> falls back to Tor if OP is down, and switches back when OP recovers."""
        m = self.m
        while not self._stop_event.is_set() and self.active:
            for _ in range(150):
                if self._stop_event.is_set() or not self.active:
                    return
                time.sleep(0.1)

            if m.mode_mgr.easy_use_evpn_upstream:
                continue

            op_ok = check_socks5_connectivity(1785, timeout=3.5)
            desired = "opera" if op_ok else "tor"
            if desired != m.mode_mgr.easy_foreign_tag:
                m.mode_mgr.easy_foreign_tag = desired
                log(f"[EasyMode] Switching foreign outbound to: {desired}")
                try:
                    m.mode_mgr.stop_tun()
                    m.mode_mgr.stop_inetcpl_proxy()
                    m.mode_mgr.start_tun()
                    m.mode_mgr.start_inetcpl_proxy()
                except Exception as e:
                    log(f"[EasyMode] Error switching outbound: {e}")

                if desired == "opera":
                    self.status_updated.emit("Работает • Зарубежный трафик: Opera Proxy (резерв Tor) • Comms DNS")
                else:
                    self.status_updated.emit("Работает • Фалбек на Tor (OP недоступен) • Comms DNS")

    def _zdpi_optimizer_loop(self):
        """Background zDPI strategy selector: tests strategies on temp port and applies strictly better ones."""
        m = self.m
        zdpi_exe = os.path.join(CURRENT_DIR, "byedpi", "zdpi.exe")
        if not os.path.exists(zdpi_exe):
            zdpi_exe = os.path.join(CURRENT_DIR, "byedpi", "ciadpi.exe")
        if not os.path.exists(zdpi_exe):
            return

        # Load test sites
        sites = ["youtube.com", "discord.com", "googlevideo.com", "instagram.com", "rutracker.org"]
        sites_file = os.path.join(CURRENT_DIR, "byedpi", "byedpi_tester_priority_sites.txt")
        if os.path.exists(sites_file):
            try:
                with open(sites_file, "r", encoding="utf-8") as f:
                    loaded = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
                if loaded:
                    sites = loaded[:6]
            except Exception:
                pass

        # Load strategies
        strategies = []
        strat_file = os.path.join(CURRENT_DIR, "byedpi", "byedpi_tester_strategies.txt")
        if os.path.exists(strat_file):
            try:
                with open(strat_file, "r", encoding="utf-8") as f:
                    strategies = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
            except Exception:
                pass
        if not strategies:
            try:
                from byedpi.byedpi_tester import DEFAULT_STRATEGIES
                strategies = list(DEFAULT_STRATEGIES)
            except Exception:
                return

        # Score current strategy first
        current_params = " ".join(m.byedpi_manager.get_params())
        # Strip -p 1780 for testing on ZDPI_TEST_PORT
        tokens = current_params.split()
        cleaned = []
        skip_next = False
        for t in tokens:
            if skip_next:
                skip_next = False
                continue
            if t in ("-p", "--port"):
                skip_next = True
                continue
            if t.startswith("-p") and len(t) > 2 and t[2].isdigit():
                continue
            cleaned.append(t)
        current_clean = " ".join(cleaned)

        self.zdpi_status_updated.emit("zDPI: оценка текущей стратегии...")
        best_score = _test_zdpi_strategy(zdpi_exe, current_clean, sites, ZDPI_TEST_PORT)
        best_strat = current_clean
        self.zdpi_status_updated.emit(f"zDPI: автоподбор в фоне (счёт {best_score}/{len(sites)})")

        for idx, strat in enumerate(strategies):
            if self._stop_event.is_set() or not self.active:
                return
            score = _test_zdpi_strategy(zdpi_exe, strat, sites, ZDPI_TEST_PORT)
            if score > best_score:
                best_score = score
                best_strat = strat
                log(f"[EasyMode] Found better zDPI strategy ({score}/{len(sites)}): {strat}")
                try:
                    m.config["byedpi_params"] = strat
                    m.config["use_custom_settings"] = True
                    config_manager.save_config(m.config)
                    m.byedpi_manager.update_config(m.config)
                    m.byedpi_manager.stop()
                    time.sleep(0.4)
                    m.byedpi_manager.start()
                except Exception as e:
                    log(f"[EasyMode] Failed to hot-swap zDPI strategy: {e}")
                self.zdpi_status_updated.emit(f"zDPI: применена лучшая стратегия ({best_score}/{len(sites)})")
                if best_score >= len(sites):
                    break

        if self.active:
            self.zdpi_status_updated.emit(f"zDPI: оптимальная стратегия активна ({best_score}/{len(sites)})")

    def stop_easy(self):
        self._stop_event.set()
        self.connecting = False
        self.active = False
        m = self.m
        m.proxy_enabled = False

        try:
            m.mode_mgr.stop_tun()
            m.mode_mgr.stop_inetcpl_proxy()
            m.byedpi_manager.stop()
            m.opera_mgr.stop()
            m.tor_manager.stop()
            m.evpn_mgr.stop()
        except Exception as e:
            log(f"[EasyMode] Stop error: {e}")

        if self._dns_applied:
            set_comms_dns_silent(False)
            self._dns_applied = False

        self.state_changed.emit(False)
        self.status_updated.emit("Отключено")
        self.zdpi_status_updated.emit("zDPI: ожидание запуска")

    def toggle_easy(self):
        if self.active or self.connecting:
            self.stop_easy()
        else:
            self.start_easy()
