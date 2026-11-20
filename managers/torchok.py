"""
Tor Manager (Torchok)
Orchestrates Tor daemon lifecycle, configuration generation, bridge management,
LAN sharing (0.0.0.0 vs 127.0.0.1), and updates.
"""
from managers import system_utils as lang
from managers.system_utils import AdoptedProcess, get_base_dir
import sys
import os
import subprocess
import time
import psutil
import json
import shutil
import tarfile
import re
import platform
import threading
from pathlib import Path
from PySide6.QtWidgets import QMessageBox

try:
    import requests
except ImportError:
    requests = None

CURRENT_DIR = get_base_dir()
DATA_DIR = os.path.join(CURRENT_DIR, "data")
TORRC_FILE = os.path.join(DATA_DIR, "torrc")
BRIDGES_FILE = os.path.join(DATA_DIR, "bridges.txt")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
UPDATE_INFO_FILE = os.path.join(CURRENT_DIR, "update_info.json")
TOR_LATEST_DIR = os.path.join(CURRENT_DIR, "tor_latest")
BACKUP_DIR = os.path.join(CURRENT_DIR, "backup")

MAESTRO_SCRIPT = os.path.join(CURRENT_DIR, "ui", "maestro.pyw")
MAESTRO_EXE = os.path.join(CURRENT_DIR, "bin", "maestro.exe")

DEFAULT_PROXY_PORT = 9853
DEFAULT_HTTP_PORT = 9854
DEFAULT_CONTROL_PORT = 9851
UPDATE_PROXY_PORT = 9750

LOG_LEVELS = {
    'notice': '[notice]',
    'warn': '[warn]',
    'err': '[err]'
}

DEFAULT_BRIDGES = [
    "webtunnel [2001:db8:3ce4:c7c7:1316:3072:b8e9:b915]:443 07E8A7DFCA7B76DD0E2F1E8C6C74D9910AAF279E url=https://shenvalleygamers.com/7HxRIWqsmkPOemUcLFTGuPaW ver=0.0.3",
    "webtunnel [2001:db8:915d:6373:6498:cec4:859d:4409]:443 0141998B7435FDFCE175410D5309C8EF2379EA68 url=https://homu.io/1zRuET5Xz19MUA4IwqbgUrcP ver=0.0.2",
    "webtunnel [2001:db8:12b1:a936:2095:ea48:63c4:2ffb]:443 5E5A525225F61595EB860044FB3E630C1A77DAEE url=https://secretinsociety.com/FuL5N2y4Tan9Wv4Xbsl2T4Ld ver=0.0.4",
    "webtunnel [2001:db8:aaf2:3e7d:b135:6398:bee7:c8e5]:443 C85C16134DF18A4B7FA0A0053C6F877E0450FB7B url=https://bridge.limoneneis.de/jABABR3DTBOgO9gCvY1dZjgu ver=0.0.4",
    "webtunnel [2001:db8:cf6:ce7:c7fc:5a42:72d5:8c8b]:443 D0A1F802127A925F47A7C9713F17A9E1D1292E54 url=https://cdn-131.airstrip1.net/4c5d6e7f8g9h0i1j2k3l4m5n ver=0.0.2",
    "webtunnel [2001:db8:50c6:f177:293a:6612:f682:feb0]:443 6736F1245C77FBDCE4252F5711DE3137A7C10125 url=https://www.itssohotrightnow.com/0bc106e5688f206329e24a350b084c43 ver=0.0.4",
    "webtunnel [2001:db8:1ecc:edad:a642:10d8:adc1:c886]:443 C2176476CDD39DFAB550BBC94E1DF3980398E5FC url=https://mstdn.plus/Lohguu6eequaethu ver=0.0.2"
]


def get_system_info():
    """Detects platform system and machine architecture"""
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    if "windows" in os_name:
        os_name = "windows"
    elif "linux" in os_name:
        os_name = "linux"
    elif "darwin" in os_name:
        os_name = "macos"

    if arch in ["x86_64", "amd64"]:
        arch = "x86_64"
    elif arch in ["i386", "i686"]:
        arch = "i686"
    elif arch in ["aarch64", "arm64"]:
        arch = "aarch64"
    return os_name, arch


def parse_download_url(html_content, os_name, arch, channel="stable"):
    """Extracts Tor Expert Bundle download URL from HTML"""
    links = re.findall(r'href="(https://[^"]+tor-expert-bundle-[^"]+\.tar\.gz)"', html_content)
    target_pattern = f"tor-expert-bundle-{os_name}-{arch}"
    filtered_links = [l for l in links if target_pattern in l]
    if not filtered_links:
        return None
    if channel == "alpha":
        result = [l for l in filtered_links if "a" in l.split('/')[-2]]
    else:
        result = [l for l in filtered_links if "a" not in l.split('/')[-2]]
    return result[0] if result else filtered_links[0]


def download_file(url, session, output_path):
    """Downloads a file using the provided requests session"""
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return output_path


class TorManager:
    def __init__(self, config=None):
        self.config = config if config is not None else self._load_initial_config()
        self.tor_running = False
        self.tor_process = None
        self.recreate_torrc = self._read_recreate_torrc()
        self.show_window = bool(self.config.get("tor_show_window", False))
        self.share_lan = bool(self.config.get("tor_share_lan", False))
        self.socks_port = int(self.config.get("tor_socks_port", DEFAULT_PROXY_PORT))
        self.http_port = int(self.config.get("tor_http_port", DEFAULT_HTTP_PORT))
        self.control_port = int(self.config.get("tor_control_port", DEFAULT_CONTROL_PORT))
        self.countries = self.config.get("tor_countries", ["us", "de", "fr", "nl", "se"])
        self._last_scan_time = 0

    def _load_initial_config(self):
        try:
            from managers import config_manager
            return config_manager.load_config()
        except Exception:
            return {}

    def update_config(self, config):
        """Обновляет конфигурацию из основного config"""
        if not config:
            return
        self.config = config
        self.show_window = bool(config.get("tor_show_window", False))
        new_share_lan = bool(config.get("tor_share_lan", False))
        if new_share_lan != self.share_lan:
            self.share_lan = new_share_lan
        self.socks_port = int(config.get("tor_socks_port", DEFAULT_PROXY_PORT))
        self.http_port = int(config.get("tor_http_port", DEFAULT_HTTP_PORT))
        self.control_port = int(config.get("tor_control_port", DEFAULT_CONTROL_PORT))
        self.countries = config.get("tor_countries", ["us", "de", "fr", "nl", "se"])

    def set_share_lan(self, enabled: bool):
        """Включает или выключает раздачу в локальную сеть (0.0.0.0 vs 127.0.0.1)"""
        self.share_lan = bool(enabled)
        try:
            from managers import config_manager
            cfg = config_manager.load_config()
            cfg["tor_share_lan"] = self.share_lan
            config_manager.save_config(cfg)
        except Exception as e:
            log(f"Ошибка сохранения tor_share_lan: {e}")
            
        self.config["tor_share_lan"] = self.share_lan
        if os.path.exists(TORRC_FILE):
            self._update_bridges_in_torrc()
        else:
            self._generate_torrc_from_bridges()
            
        if self.is_running():
            log(f"Перезапуск TOR для применения раздачи в LAN (tor_share_lan={self.share_lan})...")
            self.restart()

    def is_share_lan(self) -> bool:
        return self.share_lan

    def get_share_lan(self) -> bool:
        return self.share_lan

    def get_paths(self):
        """Определяет пути к tor.exe, lyrebird, geoip, data_dir, torrc"""
        ext = ".exe" if sys.platform == "win32" else ""
        base_dir = CURRENT_DIR

        if os.path.exists(UPDATE_INFO_FILE):
            try:
                with open(UPDATE_INFO_FILE, 'r', encoding='utf-8') as f:
                    uinfo = json.load(f)
                    folder_name = uinfo.get('use_folder')
                    if folder_name and os.path.exists(os.path.join(CURRENT_DIR, folder_name)):
                        base_dir = os.path.join(CURRENT_DIR, folder_name)
            except Exception:
                pass

        possible_tor_exes = [
            os.path.join(base_dir, "tor", f"tor{ext}"),
            os.path.join(CURRENT_DIR, "tor_latest", "tor", f"tor{ext}"),
            os.path.join(CURRENT_DIR, "tor", f"tor{ext}"),
            os.path.join(CURRENT_DIR, "backup", "tor", f"tor{ext}"),
            os.path.join(CURRENT_DIR, "bin", f"tor{ext}"),
            os.path.join(CURRENT_DIR, f"tor{ext}")
        ]

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            possible_tor_exes.insert(0, os.path.join(sys._MEIPASS, "tor", f"tor{ext}"))

        tor_exe = None
        for p in possible_tor_exes:
            if os.path.exists(p):
                tor_exe = os.path.abspath(p)
                break
        if not tor_exe:
            tor_exe = os.path.abspath(possible_tor_exes[0])

        tor_dir = os.path.dirname(tor_exe)

        possible_lyrebirds = [
            os.path.join(tor_dir, "pluggable_transports", f"lyrebird{ext}"),
            os.path.join(CURRENT_DIR, "tor", "pluggable_transports", f"lyrebird{ext}"),
            os.path.join(CURRENT_DIR, "tor_latest", "tor", "pluggable_transports", f"lyrebird{ext}"),
            os.path.join(CURRENT_DIR, "bin", f"lyrebird{ext}")
        ]
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            possible_lyrebirds.insert(0, os.path.join(sys._MEIPASS, "tor", "pluggable_transports", f"lyrebird{ext}"))

        lyrebird_exe = None
        for lp in possible_lyrebirds:
            if os.path.exists(lp):
                lyrebird_exe = os.path.abspath(lp)
                break
        if not lyrebird_exe:
            lyrebird_exe = os.path.abspath(possible_lyrebirds[0])

        data_dir = DATA_DIR
        os.makedirs(data_dir, exist_ok=True)
        geoip_path = os.path.join(data_dir, "geoip")
        geoip6_path = os.path.join(data_dir, "geoip6")

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            if not os.path.exists(geoip_path):
                cand = os.path.join(sys._MEIPASS, "data", "geoip")
                if os.path.exists(cand):
                    geoip_path = cand
            if not os.path.exists(geoip6_path):
                cand = os.path.join(sys._MEIPASS, "data", "geoip6")
                if os.path.exists(cand):
                    geoip6_path = cand

        return {
            'tor_exe': tor_exe,
            'lyrebird_exe': lyrebird_exe,
            'data_dir': data_dir,
            'geoip': geoip_path,
            'geoip6': geoip6_path,
            'torrc': TORRC_FILE
        }

    def _read_recreate_torrc(self):
        try:
            from managers import config_manager
            cfg = config_manager.load_config()
            val = cfg.get("recreate_torrc", "none")
            if isinstance(val, bool): return "full" if val else "none"
            if val == "true": return "full"
            if val == "false": return "bridges"
            return str(val).lower()
        except Exception:
            return "none"

    def _write_recreate_torrc(self, value):
        try:
            from managers import config_manager
            cfg = config_manager.load_config()
            cfg["recreate_torrc"] = str(value).lower()
            config_manager.save_config(cfg)
        except Exception:
            pass

    def _generate_torrc_from_bridges(self):
        """Генерирует torrc из bridges.txt с поддержкой раздачи в LAN и кастомных настроек"""
        paths = self.get_paths()
        bridges_path = BRIDGES_FILE
        if not os.path.exists(bridges_path) and getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            cand = os.path.join(sys._MEIPASS, "data", "bridges.txt")
            if os.path.exists(cand):
                bridges_path = cand

        bridges = []
        if os.path.exists(bridges_path):
            try:
                with open(bridges_path, "r", encoding="utf-8") as f:
                    bridges = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            except Exception:
                bridges = []

        if not bridges:
            bridges = list(DEFAULT_BRIDGES)
            try:
                os.makedirs(os.path.dirname(BRIDGES_FILE), exist_ok=True)
                with open(BRIDGES_FILE, "w", encoding="utf-8") as f:
                    f.write("# ToInet Tor Bridges\n" + "\n".join(DEFAULT_BRIDGES) + "\n")
            except Exception:
                pass

        data_dir_str = str(paths['data_dir']).replace('\\', '/')
        geoip_str = str(paths['geoip']).replace('\\', '/')
        geoip6_str = str(paths['geoip6']).replace('\\', '/')
        lyrebird_str = str(paths['lyrebird_exe']).replace('\\', '/')

        bind_addr = "0.0.0.0" if self.share_lan else "127.0.0.1"

        exit_nodes_str = ""
        if self.countries:
            if isinstance(self.countries, str):
                c_list = [c.strip() for c in self.countries.split(',') if c.strip()]
            else:
                c_list = [str(c).strip() for c in self.countries if str(c).strip()]
            if c_list:
                exit_nodes_str = f"ExitNodes " + ",".join([f"{{{c}}}" for c in c_list])

        torrc_lines = [
            f'DataDirectory "{data_dir_str}"',
            f'GeoIPFile "{geoip_str}"',
            f'GeoIPv6File "{geoip6_str}"',
            f'SocksPort {bind_addr}:{self.socks_port}',
            f'HTTPTunnelPort {bind_addr}:{self.http_port}',
            f'ControlPort 127.0.0.1:{self.control_port}',
            'HashedControlPassword 16:FDD492298759EE7D608D25F04A895488921206AD3109F87E7CC80F09D1'
        ]
        if exit_nodes_str:
            torrc_lines.append(exit_nodes_str)

        torrc_lines.append("UseBridges 1")
        torrc_lines.extend([f"Bridge {bridge}" for bridge in bridges])
        torrc_lines.extend([
            f'ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec "{lyrebird_str}"',
            "AvoidDiskWrites 1",
            "HardwareAccel 1",
            "ClientOnly 1",
            "AutomapHostsOnResolve 1",
            "SafeLogging 1"
        ])

        try:
            os.makedirs(os.path.dirname(TORRC_FILE), exist_ok=True)
            with open(TORRC_FILE, "w", encoding="utf-8") as f:
                f.write('\n'.join(torrc_lines) + '\n')
            log(f"Сгенерирован torrc (bind={bind_addr}, socks={self.socks_port}, http={self.http_port}, lan_share={self.share_lan})")
            return True
        except Exception as e:
            log(f"Ошибка записи torrc: {e}")
            return False

    def _update_bridges_in_torrc(self):
        """Обновляет мосты и параметры портов/раздачи в существующем torrc"""
        if not os.path.exists(TORRC_FILE):
            return self._generate_torrc_from_bridges()

        bridges_path = BRIDGES_FILE
        if not os.path.exists(bridges_path) and getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            cand = os.path.join(sys._MEIPASS, "data", "bridges.txt")
            if os.path.exists(cand):
                bridges_path = cand

        bridges = []
        if os.path.exists(bridges_path):
            try:
                with open(bridges_path, "r", encoding="utf-8") as f:
                    bridges = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            except Exception:
                pass
        if not bridges:
            bridges = list(DEFAULT_BRIDGES)

        try:
            with open(TORRC_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return self._generate_torrc_from_bridges()

        bind_addr = "0.0.0.0" if self.share_lan else "127.0.0.1"
        new_lines = []
        for line in lines:
            sline = line.strip()
            if sline.startswith("Bridge ") or sline == "UseBridges 1":
                continue
            if sline.startswith("SocksPort "):
                new_lines.append(f"SocksPort {bind_addr}:{self.socks_port}")
                continue
            if sline.startswith("HTTPTunnelPort "):
                new_lines.append(f"HTTPTunnelPort {bind_addr}:{self.http_port}")
                continue
            if sline.startswith("ControlPort "):
                new_lines.append(f"ControlPort 127.0.0.1:{self.control_port}")
                continue
            new_lines.append(line.rstrip())

        if bridges:
            new_lines.append("UseBridges 1")
            for b in bridges:
                new_lines.append(f"Bridge {b}")

        try:
            with open(TORRC_FILE, "w", encoding="utf-8") as f:
                f.write('\n'.join(new_lines) + '\n')
            log(f"Обновлен torrc (bind={bind_addr}, socks={self.socks_port}, http={self.http_port}, lan_share={self.share_lan})")
            return True
        except Exception as e:
            log(f"Ошибка обновления torrc: {e}")
            return False

    def _delete_torrc_files(self):
        """Удаляет существующий файл torrc"""
        if os.path.exists(TORRC_FILE):
            try:
                os.remove(TORRC_FILE)
            except Exception:
                pass

    def find_existing_process(self):
        """Ищет уже работающий процесс TOR по имени/пути или порту"""
        paths = self.get_paths()
        tor_path = os.path.normcase(os.path.normpath(paths['tor_exe']))
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = (proc.info.get('name') or "").lower()
                    if 'tor' in name:
                        try:
                            exe_path = proc.exe()
                            if exe_path and os.path.normcase(os.path.normpath(exe_path)) == tor_path:
                                return proc.info['pid']
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            pass
                        cmdline = proc.cmdline() or []
                        if any('torrc' in arg.lower() for arg in cmdline) or any('-f' == arg for arg in cmdline):
                            return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            log(f"Ошибка при поиске существующего процесса TOR: {e}")

        # Проверка порта SocksPort
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.05)
            res = sock.connect_ex(('127.0.0.1', self.socks_port))
            sock.close()
            if res == 0:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if 'tor' in (proc.info.get('name') or "").lower():
                            return proc.info['pid']
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def _launch_tor_direct(self):
        """Запускает tor.exe с файлом torrc напрямую"""
        paths = self.get_paths()
        tor_exe = paths['tor_exe']
        if not os.path.exists(tor_exe):
            log(f"tor.exe not found at {tor_exe}!")
            return False
        if not os.path.exists(TORRC_FILE):
            self._generate_torrc_from_bridges()
            if not os.path.exists(TORRC_FILE):
                log(f"torrc not found at {TORRC_FILE}!")
                return False

        creation_flags = subprocess.CREATE_NEW_CONSOLE if self.show_window else subprocess.CREATE_NO_WINDOW
        stdout = None if self.show_window else subprocess.DEVNULL
        stderr = None if self.show_window else subprocess.DEVNULL

        env = os.environ.copy()
        if sys.platform != "win32":
            lib_path = str(Path(tor_exe).parent)
            env['LD_LIBRARY_PATH'] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
            try: os.chmod(tor_exe, 0o755)
            except Exception: pass
            if os.path.exists(paths['lyrebird_exe']):
                try: os.chmod(paths['lyrebird_exe'], 0o755)
                except Exception: pass

        try:
            self.tor_process = subprocess.Popen(
                [tor_exe, '-f', TORRC_FILE],
                stdout=stdout,
                stderr=stderr,
                creationflags=creation_flags,
                cwd=CURRENT_DIR,
                env=env
            )
            time.sleep(1.0)
            if self.tor_process.poll() is not None:
                log(f"Ошибка: tor.exe аварийно завершился (код {self.tor_process.poll()})")
                self.tor_running = False
                self.tor_process = None
                return False
            self.tor_running = True
            log(f"tor.exe успешно запущен напрямую (PID {self.tor_process.pid})")
            return True
        except Exception as e:
            log(f"Failed to start tor.exe: {e}")
            self.tor_running = False
            self.tor_process = None
            return False

    def _stop_tor_direct(self):
        """Останавливает запущенный процесс TOR"""
        if self.tor_process:
            try:
                self.tor_process.terminate()
                try:
                    self.tor_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    pass
                if self.tor_process.poll() is None:
                    self.tor_process.kill()
                self.tor_process = None
                log("TOR процесс остановлен")
                return True
            except Exception as e:
                log(f"Ошибка остановки TOR процесса: {e}")

        paths = self.get_paths()
        tor_path = os.path.normcase(os.path.normpath(paths['tor_exe']))
        killed = False
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'tor' in proc.info['name'].lower():
                        exe_path = proc.exe()
                        if exe_path and os.path.normcase(os.path.normpath(exe_path)) == tor_path:
                            proc.kill()
                            killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            if killed:
                log("TOR процесс остановлен через сканирование процессов")
            return killed
        except Exception as e:
            log(f"Ошибка при поиске и остановке TOR: {e}")
            return False

    def start(self):
        """Запуск TOR"""
        if self.is_running():
            return True

        existing_pid = self.find_existing_process()
        if existing_pid:
            log(f"Найден уже запущенный процесс TOR (PID {existing_pid}), используем его.")
            self.tor_process = AdoptedProcess(existing_pid)
            self.tor_running = True
            return True

        if self.recreate_torrc == "full":
            self._delete_torrc_files()
            self._generate_torrc_from_bridges()
        elif self.recreate_torrc == "bridges":
            self._update_bridges_in_torrc()

        if not os.path.exists(TORRC_FILE):
            self._generate_torrc_from_bridges()

        if self._launch_tor_direct():
            self.tor_running = True
            return True

        return False

    def stop(self):
        """Останавливает TOR"""
        if not self.tor_running:
            return
        self._stop_tor_direct()
        self.tor_running = False

    def restart(self, parent=None):
        """Перезапускает TOR"""
        if self.tor_running:
            self.stop()
            time.sleep(1.5)

        if self.start():
            if parent:
                QMessageBox.information(parent, "Перезапуск TOR", "TOR успешно перезапущен!")
            return True
        else:
            if parent:
                QMessageBox.critical(parent, lang.T("Ошибка", "Error"), "Не удалось перезапустить TOR")
            return False

    def new_circuit(self, parent=None):
        """Запрашивает новую цепочку (NEWNYM) у TOR через ControlPort"""
        if not self.is_running():
            if parent:
                QMessageBox.warning(parent, lang.T("Ошибка", "Error"), "TOR не запущен.")
            return False

        try:
            import socket
            control_port = self.control_port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.5)
            s.connect(('127.0.0.1', control_port))
            s.sendall(b'AUTHENTICATE "toinet"\r\n')
            resp = s.recv(1024).decode('utf-8')
            if not resp.startswith('250'):
                log(f"ControlPort auth error ({control_port}): {resp}")
                s.close()
                if parent:
                    QMessageBox.warning(parent, lang.T("Ошибка", "Error"), f"Ошибка авторизации ControlPort: {resp}")
                return False

            s.sendall(b'SIGNAL NEWNYM\r\n')
            resp = s.recv(1024).decode('utf-8')
            s.close()
            if resp.startswith('250'):
                log("Успешно запрошена новая цепочка TOR")
                if parent:
                    QMessageBox.information(parent, "TOR", "Новая цепочка успешно запрошена!")
                return True
            else:
                log(f"NEWNYM error: {resp}")
                if parent:
                    QMessageBox.warning(parent, lang.T("Ошибка", "Error"), f"Ошибка при запросе новой цепочки:\n{resp}")
                return False
        except Exception as e:
            log(f"Внутренняя ошибка ControlPort: {e}")
            if parent:
                QMessageBox.warning(parent, lang.T("Ошибка", "Error"), f"Внутренняя ошибка:\n{e}")
            return False

    def is_running(self):
        """Возвращает статус работы TOR"""
        if self.tor_running and self.tor_process:
            if self.tor_process.poll() is not None:
                self.tor_running = False
                self.tor_process = None
        elif not self.tor_running:
            now = time.time()
            if now - getattr(self, '_last_scan_time', 0) > 15.0:
                self._last_scan_time = now
                existing_pid = self.find_existing_process()
                if existing_pid:
                    self.tor_process = AdoptedProcess(existing_pid)
                    self.tor_running = True
        return self.tor_running

    def toggle_recreate(self):
        """Цикличное переключение режима пересоздания torrc"""
        if self.recreate_torrc == "full": self.recreate_torrc = "bridges"
        elif self.recreate_torrc == "bridges": self.recreate_torrc = "none"
        else: self.recreate_torrc = "full"
        self._write_recreate_torrc(self.recreate_torrc)

    def get_recreate_mode(self):
        return self.recreate_torrc

    def delete_config(self):
        self._delete_torrc_files()

    def open_settings(self):
        """Открывает настройки TOR (bin/maestro.exe или ui/maestro.pyw)"""
        if os.path.exists(MAESTRO_EXE):
            try:
                subprocess.Popen([MAESTRO_EXE], cwd=CURRENT_DIR)
                log(f"Запущен {MAESTRO_EXE}")
                return True
            except Exception as e:
                log(f"Ошибка запуска {MAESTRO_EXE}: {e}")

        maestro_exists = os.path.exists(MAESTRO_SCRIPT) or (getattr(sys, 'frozen', False) and getattr(sys, '_MEIPASS', None) and os.path.exists(os.path.join(sys._MEIPASS, "ui", "maestro.pyw")))
        if maestro_exists:
            try:
                subprocess.Popen([sys.executable, MAESTRO_SCRIPT], cwd=CURRENT_DIR)
                log(f"Запущен {MAESTRO_SCRIPT}")
                return True
            except Exception as e:
                log(f"Ошибка запуска {MAESTRO_SCRIPT}: {e}")

        QMessageBox.critical(None, lang.T("Ошибка", "Error"),
                           f"Не найден файл настроек TOR:\n{MAESTRO_SCRIPT}")
        return False

    def update_tor(self, channel="stable"):
        """Обновление бинарников Tor Expert Bundle через временный Tor прокси"""
        if not requests:
            log("Библиотека 'requests' не установлена. Обновление пропущено.")
            return False

        os_name, arch = get_system_info()
        log(f"Система: {os_name} ({arch})")

        paths = self.get_paths()
        if not os.path.exists(paths['tor_exe']):
            log("Исполняемый файл Tor не найден. Обновление через прокси невозможно.")
            return False

        log("Запуск временного экземпляра Tor для загрузки обновления...")
        temp_torrc_path = os.path.join(DATA_DIR, "torrc_update_tmp")
        data_dir_str = str(paths['data_dir']).replace('\\', '/')
        geoip_str = str(paths['geoip']).replace('\\', '/')
        geoip6_str = str(paths['geoip6']).replace('\\', '/')
        lyrebird_str = str(paths['lyrebird_exe']).replace('\\', '/')

        temp_lines = [
            f'DataDirectory "{data_dir_str}"',
            f'GeoIPFile "{geoip_str}"',
            f'GeoIPv6File "{geoip6_str}"',
            f'SocksPort 127.0.0.1:{UPDATE_PROXY_PORT}',
            "UseBridges 1"
        ]
        temp_lines.extend([f"Bridge {b}" for b in DEFAULT_BRIDGES])
        temp_lines.extend([
            f'ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec "{lyrebird_str}"',
            "AvoidDiskWrites 1",
            "HardwareAccel 1",
            "ClientOnly 1",
            "AutomapHostsOnResolve 1",
            "SafeLogging 1"
        ])

        try:
            with open(temp_torrc_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(temp_lines))

            tor_proc = subprocess.Popen(
                [paths['tor_exe'], "-f", temp_torrc_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            log("Ожидание начальной инициализации Tor...")
            bootstrapped = False
            start_time = time.time()
            while True:
                line = tor_proc.stdout.readline()
                if not line:
                    break
                if "Bootstrapped 100%" in line:
                    bootstrapped = True
                    break
                if time.time() - start_time > 180:
                    log("Таймаут подключения к сети Tor для обновления.")
                    break

            if not bootstrapped:
                tor_proc.terminate()
                if os.path.exists(temp_torrc_path):
                    os.remove(temp_torrc_path)
                return False

            log("Tor готов. Загрузка страницы дистрибутивов...")
            proxies = {
                'http': f'socks5h://127.0.0.1:{UPDATE_PROXY_PORT}',
                'https': f'socks5h://127.0.0.1:{UPDATE_PROXY_PORT}'
            }
            session = requests.Session()
            session.proxies = proxies

            update_url = "https://www.torproject.org/download/tor/"
            resp = session.get(update_url, timeout=30)
            resp.raise_for_status()

            download_url = parse_download_url(resp.text, os_name, arch, channel)
            if not download_url:
                log("Не удалось найти ссылку для скачивания Tor.")
                tor_proc.terminate()
                if os.path.exists(temp_torrc_path):
                    os.remove(temp_torrc_path)
                return False

            archive_filename = download_url.split('/')[-1]
            archive_path = os.path.join(CURRENT_DIR, archive_filename)
            log(f"Скачивание {download_url}...")
            download_file(download_url, session, archive_path)
            log(f"Архив сохранен в {archive_path}")

            tor_proc.terminate()
            tor_proc.wait()
            if os.path.exists(temp_torrc_path):
                os.remove(temp_torrc_path)

        except Exception as e:
            log(f"Ошибка процесса обновления: {e}")
            if os.path.exists(temp_torrc_path):
                try: os.remove(temp_torrc_path)
                except Exception: pass
            return False

        try:
            log("Обновление каталогов Tor...")
            if os.path.exists(BACKUP_DIR):
                shutil.rmtree(BACKUP_DIR, ignore_errors=True)

            if os.path.exists(TOR_LATEST_DIR):
                shutil.move(TOR_LATEST_DIR, BACKUP_DIR)
            else:
                os.makedirs(BACKUP_DIR, exist_ok=True)
                for d in ['tor', 'data']:
                    src = os.path.join(CURRENT_DIR, d)
                    if os.path.exists(src):
                        shutil.copytree(src, os.path.join(BACKUP_DIR, d), dirs_exist_ok=True)

            os.makedirs(TOR_LATEST_DIR, exist_ok=True)
            log(f"Распаковка {archive_path} в {TOR_LATEST_DIR}...")
            with tarfile.open(archive_path, "r:gz") as tar:
                if hasattr(tarfile, 'data_filter'):
                    tar.extractall(path=TOR_LATEST_DIR, filter='data')
                else:
                    tar.extractall(path=TOR_LATEST_DIR)

            if os.path.exists(archive_path):
                os.remove(archive_path)

            with open(UPDATE_INFO_FILE, 'w', encoding='utf-8') as f:
                json.dump({'use_folder': 'tor_latest', 'last_update': time.time()}, f, indent=2)

            log("Обновление Tor успешно завершено!")
            return True
        except Exception as e:
            log(f"Ошибка при распаковке обновления Tor: {e}")
            return False


def log(msg):
    print(f"[TOR Manager] {msg}")


def get_manager(config=None):
    """Возвращает экземпляр менеджера TOR"""
    return TorManager(config)
