import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from managers import system_utils as lang
import os
import sys
import json
import argparse
import signal as sys_signal
import threading

_parent_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
from managers.system_utils import get_base_dir
CURRENT_DIR = get_base_dir()

class UpdateInfoFile:
    def __init__(self, mode):
        self.mode = mode
        self.buffer = ""
    def __enter__(self):
        self.buffer = ""
        return self
    def __exit__(self, *args):
        if 'w' in self.mode or 'a' in self.mode:
            if self.buffer.strip():
                try:
                    from managers import config_manager
                    info = json.loads(self.buffer)
                    cfg = config_manager.load_config()
                    for k, v in info.items():
                        cfg['update_info_' + k] = v
                    config_manager.save_config(cfg)
                except Exception as e:
                    print(f"Failed to save update_info: {e}")
    def read(self):
        from managers import config_manager
        cfg = config_manager.load_config()
        info = {k.replace('update_info_', ''): v for k, v in cfg.items() if k.startswith('update_info_')}
        return json.dumps(info)
    def write(self, data):
        self.buffer += data

def _mock_open(path, mode='r', *args, **kwargs):
    if 'update_info.json' in str(path):
        return UpdateInfoFile(mode)
    p_str = str(path)
    if os.path.basename(p_str) == "config.json" and "data" not in os.path.dirname(os.path.abspath(p_str)):
        target = os.path.join(CURRENT_DIR, "data", "config.json")
        return open(target, mode, *args, **kwargs)
    return open(path, mode, *args, **kwargs)

def _mock_exists(path):
    if 'update_info.json' in str(path):
        return True
    p_str = str(path)
    if os.path.basename(p_str) == "config.json" and "data" not in os.path.dirname(os.path.abspath(p_str)):
        target = os.path.join(CURRENT_DIR, "data", "config.json")
        return os.path.exists(target)
    return os.path.exists(path)

class MockPath:
    def __init__(self, path):
        import pathlib
        self.path = pathlib.Path(path)
    def exists(self):
        if 'update_info.json' in str(self.path): return True
        return self.path.exists()
    def __str__(self): return str(self.path)
    def __truediv__(self, other):
        if 'update_info.json' in str(other): return MockPath(self.path / other)
        return self.path / other

from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QListWidget, QListWidgetItem, QFileDialog, 
                             QMessageBox, QGroupBox, QGridLayout, QComboBox,
                             QRadioButton, QButtonGroup, QCheckBox, QProgressDialog, QSpinBox, QScrollArea)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon
import requests
from io import BytesIO
import platform
import shutil
import tarfile
import re
import time
import subprocess

PROJECT_FOLDER = Path(CURRENT_DIR)
CONFIG_FILE = PROJECT_FOLDER / "data" / "tor_config.json"
UPDATE_INFO_FILE = PROJECT_FOLDER / "update_info.json"
TOR_LATEST_DIR = PROJECT_FOLDER / "tor_latest"
BACKUP_DIR = PROJECT_FOLDER / "backup"
DEFAULT_PROXY_PORT = 9050
UPDATE_PROXY_PORT = 9750

LOG_LEVELS = {
    'notice': '[notice]',
    'warn': '[warn]',
    'err': '[err]'
}

def get_default_bridges():
    return [
        "webtunnel [2001:db8:3ce4:c7c7:1316:3072:b8e9:b915]:443 07E8A7DFCA7B76DD0E2F1E8C6C74D9910AAF279E url=https://shenvalleygamers.com/7HxRIWqsmkPOemUcLFTGuPaW ver=0.0.3",
        "webtunnel [2001:db8:915d:6373:6498:cec4:859d:4409]:443 0141998B7435FDFCE175410D5309C8EF2379EA68 url=https://homu.io/1zRuET5Xz19MUA4IwqbgUrcP ver=0.0.2",
        "webtunnel [2001:db8:12b1:a936:2095:ea48:63c4:2ffb]:443 5E5A525225F61595EB860044FB3E630C1A77DAEE url=https://secretinsociety.com/FuL5N2y4Tan9Wv4Xbsl2T4Ld ver=0.0.4",
        "webtunnel [2001:db8:aaf2:3e7d:b135:6398:bee7:c8e5]:443 C85C16134DF18A4B7FA0A0053C6F877E0450FB7B url=https://bridge.limoneneis.de/jABABR3DTBOgO9gCvY1dZjgu ver=0.0.4",
        "webtunnel [2001:db8:cf6:ce7:c7fc:5a42:72d5:8c8b]:443 D0A1F802127A925F47A7C9713F17A9E1D1292E54 url=https://cdn-131.airstrip1.net/4c5d6e7f8g9h0i1j2k3l4m5n ver=0.0.2",
        "webtunnel [2001:db8:50c6:f177:293a:6612:f682:feb0]:443 6736F1245C77FBDCE4252F5711DE3137A7C10125 url=https://www.itssohotrightnow.com/0bc106e5688f206329e24a350b084c43 ver=0.0.4",
        "webtunnel [2001:db8:1ecc:edad:a642:10d8:adc1:c886]:443 C2176476CDD39DFAB550BBC94E1DF3980398E5FC url=https://mstdn.plus/Lohguu6eequaethu ver=0.0.2"
    ]

def get_system_info():
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

def get_paths(base_dir=None):
    if base_dir is None:
        base_dir = CURRENT_DIR
    base_path = Path(base_dir)
    ext = ".exe" if sys.platform == "win32" else ""
    
    possible_tor_exes = [
        base_path / "tor" / f"tor{ext}",
        base_path / "backup" / "tor" / f"tor{ext}",
        base_path / f"tor{ext}",
        Path(CURRENT_DIR) / "tor" / f"tor{ext}"
    ]
    
    tor_exe = None
    for p in possible_tor_exes:
        if p.exists():
            tor_exe = p
            break
    
    if not tor_exe:
        tor_exe = base_path / "tor" / f"tor{ext}"

    tor_dir = tor_exe.parent
    lyrebird_exe = tor_dir / "pluggable_transports" / f"lyrebird{ext}"
    if not lyrebird_exe.exists() and (Path(CURRENT_DIR) / "tor" / "pluggable_transports" / f"lyrebird{ext}").exists():
        lyrebird_exe = Path(CURRENT_DIR) / "tor" / "pluggable_transports" / f"lyrebird{ext}"

    data_dir = base_path / "data"
    if not data_dir.exists() and (Path(CURRENT_DIR) / "data").exists():
        data_dir = Path(CURRENT_DIR) / "data"
    
    return {
        'tor_exe': tor_exe,
        'lyrebird_exe': lyrebird_exe,
        'data_dir': data_dir,
        'geoip': data_dir / "geoip",
        'geoip6': data_dir / "geoip6",
        'torrc': data_dir / "torrc"
    }

def load_config(config_name=None):
    candidates = [
        Path(CURRENT_DIR) / "data" / "tor_config.json",
        Path(CURRENT_DIR) / "tor_config.json"
    ]
    cfg_file = None
    for c in candidates:
        if c.exists():
            cfg_file = c
            break
    if not cfg_file:
        return {}
    
    try:
        with open(cfg_file, 'r', encoding='utf-8') as f:
            configs = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}
    
    if config_name:
        return configs.get(config_name, {})
    
    if 'default' in configs:
        return configs['default']
    return configs

load_tor_config = load_config

def save_config(config_name, config_data):
    cfg_file = Path(CURRENT_DIR) / "data" / "tor_config.json"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    configs = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, 'r', encoding='utf-8') as f:
                configs = json.load(f)
        except Exception:
            pass
    elif (Path(CURRENT_DIR) / "tor_config.json").exists():
        try:
            with open(Path(CURRENT_DIR) / "tor_config.json", 'r', encoding='utf-8') as f:
                configs = json.load(f)
        except Exception:
            pass
    
    configs[config_name] = config_data
    with open(cfg_file, 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)

save_tor_config = save_config

def parse_download_url(html_content, os_name, arch, channel):
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

def download_file(url, session):
    local_filename = Path(CURRENT_DIR) / url.split('/')[-1]
    print(f"Downloading {url}...")
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def generate_torrc_config(config, paths=None):
    if paths is None:
        paths = get_paths()
        
    exit_nodes = ""
    if config.get('countries'):
        exit_nodes = ",".join([f"{{{country}}}" for country in config['countries']])
    
    data_dir = paths['data_dir']
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)

    port = config.get('port', DEFAULT_PROXY_PORT)
    torrc_content = f"""DataDirectory {data_dir}
GeoIPFile {paths['geoip']}
GeoIPv6File {paths['geoip6']}
SocksPort 0.0.0.0:{port}
ControlPort 9851
HashedControlPassword 16:FDD492298759EE7D608D25F04A895488921206AD3109F87E7CC80F09D1
"""
    if exit_nodes:
        torrc_content += f"ExitNodes {exit_nodes}\n"
    
    torrc_content += f"""UseBridges 1
ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec {paths['lyrebird_exe']}
AvoidDiskWrites 1
HardwareAccel 1
ClientOnly 1
AutomapHostsOnResolve 1
SafeLogging 1
"""
    bridges = config.get('bridges') or get_default_bridges()
    for bridge in bridges:
        torrc_content += f"Bridge {bridge}\n"
    
    torrc_path = paths['torrc']
    torrc_path.parent.mkdir(parents=True, exist_ok=True)
    torrc_path.write_text(torrc_content.strip(), encoding='utf-8')
    return torrc_path

generate_torrc = generate_torrc_config

def run_tor(torrc_path, tor_exe_path, log_filter=None):
    tor_exe_path = Path(tor_exe_path)
    if not tor_exe_path.exists():
        raise FileNotFoundError(f"Tor not found: {tor_exe_path}")
    
    env = os.environ.copy()
    if sys.platform != "win32":
        lib_path = str(tor_exe_path.parent)
        env['LD_LIBRARY_PATH'] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
        os.chmod(tor_exe_path, 0o755)
        lyrebird_path = tor_exe_path.parent / "pluggable_transports" / ("lyrebird" if sys.platform != "win32" else "lyrebird.exe")
        if lyrebird_path.exists():
            os.chmod(lyrebird_path, 0o755)

    process = subprocess.Popen(
        [str(tor_exe_path), "-f", str(torrc_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env
    )
    
    def filter_log(stream):
        for line in iter(stream.readline, ''):
            if not log_filter:
                print(line, end="")
            else:
                for level in log_filter:
                    if level in LOG_LEVELS and LOG_LEVELS[level] in line:
                        print(line, end="")
                        break
    
    threading.Thread(target=filter_log, args=(process.stdout,), daemon=True).start()
    threading.Thread(target=filter_log, args=(process.stderr,), daemon=True).start()
    
    return process

def update_tor(channel="stable"):
    if not requests:
        print("Error: 'requests' library is not installed. Update skipped.")
        return False

    os_name, arch = get_system_info()
    print(f"System detected: {os_name} ({arch})")
    
    base_dir = Path(CURRENT_DIR)
    update_info_file = Path(CURRENT_DIR) / "update_info.json"
    if update_info_file.exists():
        try:
            with _mock_open(update_info_file, 'r') as f:
                info = json.load(f)
                folder_name = info.get('use_folder')
                if folder_name and (Path(CURRENT_DIR) / folder_name).exists():
                    base_dir = Path(CURRENT_DIR) / folder_name
        except Exception:
            pass

    paths = get_paths(base_dir)
    if not paths['tor_exe'].exists():
        paths = get_paths(Path(CURRENT_DIR))
        if not paths['tor_exe'].exists():
            print("Error: Tor executable not found. Cannot perform update through proxy.")
            return False

    print("Starting temporary Tor for update...")
    update_config = {
        'port': UPDATE_PROXY_PORT,
        'bridges': get_default_bridges(),
        'countries': None
    }
    
    torrc_path = generate_torrc_config(update_config, paths)
    
    env = os.environ.copy()
    if sys.platform != "win32":
        lib_path = str(paths['tor_exe'].parent)
        env['LD_LIBRARY_PATH'] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
        os.chmod(paths['tor_exe'], 0o755)
        if paths['lyrebird_exe'].exists():
            os.chmod(paths['lyrebird_exe'], 0o755)

    tor_process = None
    try:
        tor_process = subprocess.Popen(
            [str(paths['tor_exe']), "-f", str(torrc_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env
        )
        
        print("Waiting for Tor to bootstrap...")
        bootstrapped = False
        start_time = time.time()
        timeout = 300
        
        while True:
            line = tor_process.stdout.readline()
            if not line: break
            if "Bootstrapped 100%" in line:
                bootstrapped = True
                break
            if time.time() - start_time > timeout:
                print("Timeout waiting for Tor to bootstrap.")
                break
                
        if not bootstrapped:
            print("Tor failed to bootstrap for update.")
            tor_process.terminate()
            return False
        
        print("Tor is ready. Fetching download page...")
        proxies = {
            'http': f'socks5h://127.0.0.1:{UPDATE_PROXY_PORT}',
            'https': f'socks5h://127.0.0.1:{UPDATE_PROXY_PORT}'
        }
        
        session = requests.Session()
        session.proxies = proxies
        
        update_url = "https://www.torproject.org/download/tor/"
        response = session.get(update_url)
        response.raise_for_status()
        
        download_url = parse_download_url(response.text, os_name, arch, channel)
        if not download_url:
            print("Could not find download URL.")
            tor_process.terminate()
            return False
            
        archive_path = download_file(download_url, session)
        print(f"Downloaded to {archive_path}")
        
        print("Stopping temporary Tor...")
        tor_process.terminate()
        tor_process.wait()
        tor_process = None
        
    except Exception as e:
        if tor_process:
            try: tor_process.terminate()
            except: pass
        print(f"Update failed: {e}")
        return False

    print("Updating folders...")
    backup_dir = Path(CURRENT_DIR) / "backup"
    tor_latest_dir = Path(CURRENT_DIR) / "tor_latest"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    
    if tor_latest_dir.exists():
        shutil.move(str(tor_latest_dir), str(backup_dir))
    else:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for d in ['tor', 'data', 'docs']:
            src = Path(CURRENT_DIR) / d
            if src.exists():
                shutil.move(str(src), str(backup_dir / d))

    tor_latest_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Unpacking {archive_path} to {tor_latest_dir}...")
    with tarfile.open(archive_path, "r:gz") as tar:
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(path=tor_latest_dir, filter='data')
        else:
            tar.extractall(path=tor_latest_dir)
    
    try: os.remove(archive_path)
    except: pass

    for d in ['data', 'docs']:
        wrong_path = tor_latest_dir / "tor" / d
        right_path = tor_latest_dir / d
        if wrong_path.exists():
            if right_path.exists():
                shutil.rmtree(str(right_path))
            shutil.move(str(wrong_path), str(right_path))

    tor_inner = tor_latest_dir / "tor" / "tor"
    tor_exe_inner = tor_latest_dir / "tor" / "tor" / "tor.exe"
    tor_exe_right = tor_latest_dir / "tor" / "tor.exe"
    if tor_exe_inner.exists() and not tor_exe_right.exists():
        temp_tor = tor_latest_dir / "tor_temp_swap"
        shutil.move(str(tor_inner), str(temp_tor))
        shutil.rmtree(str(tor_latest_dir / "tor"))
        shutil.move(str(temp_tor), str(tor_latest_dir / "tor"))
    
    with _mock_open(update_info_file, 'w') as f:
        json.dump({'use_folder': 'tor_latest', 'last_update': time.time(), 'branch': channel}, f)
    
    print("Update complete.")
    return True

update_tor_cli = update_tor

def get_user_config():
    config = {}
    config['port'] = input("Enter port (default 9050): ") or "9050"
    
    countries_input = input("Enter exit countries (us,de,fr etc. or empty): ").strip()
    if countries_input:
        config['countries'] = [c.strip() for c in countries_input.split(',')]
    else:
        config['countries'] = []
    
    print("Enter bridges (empty line to finish, default is webtunnel):")
    bridges = []
    while True:
        bridge = input("Bridge: ").strip()
        if not bridge:
            if not bridges:
                bridges = get_default_bridges()
            break
        bridges.append(bridge)
    config['bridges'] = bridges
    
    print("Select log levels: notice, warn, err")
    log_input = input("Levels (default all): ").strip()
    if log_input:
        config['log_levels'] = [l.strip() for l in log_input.split(',') if l.strip() in LOG_LEVELS]
    else:
        config['log_levels'] = list(LOG_LEVELS.keys())
    
    config['check_updates'] = input("Check updates on startup? (y/n): ").lower() == 'y'
    
    save = input("Save configuration? (y/n): ").lower()
    if save == 'y':
        config_name = input("Config name (e.g. 'default'): ").strip() or "default"
        save_config(config_name, config)
        print(f"Config '{config_name}' saved.")
    
    return config

def cli_main(argv=None):
    parser = argparse.ArgumentParser(description="Tor Manager (Launcher + Updater & Configurator)")
    parser.add_argument('--gui', action='store_true', help="Launch GUI configurator")
    parser.add_argument('--config', help="Config name to load from tor_config.json")
    parser.add_argument('--update', action='store_true', help="Force update Tor")
    parser.add_argument('--port', type=int, help="Proxy port (default 9050 or from config)")
    parser.add_argument('--countries', help="Comma-separated exit countries (e.g. us,de,fr)")
    parser.add_argument('--bridges', help="Path to bridges file or comma-separated bridges")
    parser.add_argument('--channel', choices=['stable', 'alpha'], default='stable', help="Update channel")
    parser.add_argument('--cli', action='store_true', help="Force CLI mode")
    args = parser.parse_args(argv)
    
    if args.gui:
        launch_gui()
        return
        
    config = load_config(args.config) if args.config else {}
    if not config and args.config:
        print(f"Config '{args.config}' not found.")
        return
    elif not config and not (args.port or args.countries or args.bridges or args.update):
        if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            config = get_user_config()
        else:
            config = {'port': DEFAULT_PROXY_PORT, 'bridges': get_default_bridges()}

    if args.port:
        config['port'] = args.port
    if args.countries:
        config['countries'] = [c.strip() for c in args.countries.split(',')]
    if args.bridges:
        if os.path.exists(args.bridges):
            with open(args.bridges, 'r', encoding='utf-8') as f:
                config['bridges'] = [l.strip() for l in f if l.strip()]
        else:
            config['bridges'] = [b.strip() for b in args.bridges.split(',')]

    if args.update or config.get('check_updates'):
        print("Checking for updates...")
        update_tor(channel=args.channel)

    base_dir = Path(CURRENT_DIR)
    update_info_file = Path(CURRENT_DIR) / "update_info.json"
    if update_info_file.exists():
        try:
            with _mock_open(update_info_file, 'r') as f:
                info = json.load(f)
                folder_name = info.get('use_folder')
                if folder_name and (Path(CURRENT_DIR) / folder_name).exists():
                    base_dir = Path(CURRENT_DIR) / folder_name
                    print(f"Using Tor from: {folder_name}")
        except Exception:
            pass

    paths = get_paths(base_dir)
    
    print("Generating torrc...")
    torrc_path = generate_torrc_config(config, paths)
    
    print(f"Starting Tor from {paths['tor_exe']}...")
    try:
        tor_process = run_tor(torrc_path, paths['tor_exe'], config.get('log_levels'))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Maybe you need to run with --update first?")
        return

    def signal_handler(sig, frame):
        print("\nStopping Tor...")
        tor_process.terminate()
        try:
            tor_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            tor_process.kill()
        sys.exit(0)
    
    sys_signal.signal(sys_signal.SIGINT, signal_handler)
    if hasattr(sys_signal, 'SIGTERM'):
        sys_signal.signal(sys_signal.SIGTERM, signal_handler)
    
    print("Tor started. Press Ctrl+C to stop.")
    try:
        tor_process.wait()
    except KeyboardInterrupt:
        signal_handler(sys_signal.SIGINT, None)

# Dictionary with countries and their code
countries = {
    "Австралия": ("au", ""),
    "Австрия": ("at", ""),
    "Болгария": ("bg", ""),
    "Бразилия": ("br", ""),
    "Великобритания": ("gb", ""),
    "Венгрия": ("hu", ""),
    "Германия": ("de", ""),
    "Дания": ("dk", ""),
    "Исландия": ("is", ""),
    "Испания": ("es", ""),
    "Канада": ("ca", ""),
    "Нидерланды": ("nl", ""),
    "Польша": ("pl", ""),
    "Россия": ("ru", ""),
    "Румыния": ("ro", ""),
    "Сингапур": ("sg", ""),
    "Словакия": ("sk", ""),
    "США": ("us", ""),
    "Финляндия": ("fi", ""),
    "Франция": ("fr", ""),
    "Чехия": ("cz", ""),
    "Швейцария": ("ch", ""),
    "Швеция": ("se", ""),
    "Япония": ("jp", "")
}

class CountryListWidget(QListWidget):
    """Custom list widget for displaying countries"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.MultiSelection)
        self.setMinimumHeight(200)
        self.setFont(QFont("Segoe UI", 10))
        
    def add_country(self, name, code):
        """Add a country item"""
        item = QListWidgetItem(f"{name}")
        item.setData(Qt.UserRole, code)
        item.setData(Qt.UserRole + 1, name)
        self.addItem(item)
        
    def get_selected_countries(self):
        """Get list of selected country codes"""
        codes = []
        for item in self.selectedItems():
            codes.append(item.data(Qt.UserRole))
        return codes

class TorUpdaterThread(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, channel="stable", archive_path=None):
        super().__init__()
        self.channel = channel
        self.archive_path = archive_path
        self.project_folder = Path(CURRENT_DIR)
        self.tor_latest_dir = self.project_folder / "tor"
        self.backup_dir = self.project_folder / "backup"

    def get_system_info(self):
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

    def get_bridges(self):
        return get_default_bridges()

    def parse_download_url(self, html_content, os_name, arch, channel):
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

    def run(self):
        tor_process = None
        try:
            try:
                import subprocess, platform, time
                self.progress.emit(T("Остановка всех процессов Tor...", "Stopping all Tor processes..."))
                if platform.system().lower() == "windows":
                    subprocess.run(["taskkill", "/F", "/IM", "tor.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(["killall", "tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
            except:
                pass

            update_info_path = self.project_folder / "update_info.json"
            
            if self.archive_path:
                local_filename = Path(self.archive_path)
                self.progress.emit(T(f"Использование локального архива: {local_filename.name}...", f"Using local archive: {local_filename.name}..."))
                self._extract_and_apply(local_filename)
                return
            else:
                self.progress.emit("Определение системы...")
                os_name, arch = self.get_system_info()
                
                base_dir = self.project_folder
            if True:
                try:
                    with _mock_open(update_info_path, 'r') as f:
                        info = json.load(f)
                        folder_name = info.get('use_folder')
                        if folder_name and (self.project_folder / folder_name).exists():
                            base_dir = self.project_folder / folder_name
                except:
                    pass

            tor_exe = base_dir / "tor" / ("tor.exe" if os_name == "windows" else "tor")
            lyrebird_exe = base_dir / "tor" / "pluggable_transports" / ("lyrebird.exe" if os_name == "windows" else "lyrebird")
            
            if not tor_exe.exists():
                found = False
                for fallback in [self.project_folder, self.backup_dir, self.project_folder / "tor"]:
                    t_exe = fallback / "tor" / ("tor.exe" if os_name == "windows" else "tor")
                    l_exe = fallback / "tor" / "pluggable_transports" / ("lyrebird.exe" if os_name == "windows" else "lyrebird")
                    if t_exe.exists():
                        tor_exe, lyrebird_exe = t_exe, l_exe
                        found = True
                        break
                if not found:
                    self.finished.emit(False, T("Tor executable не найден. Восстановите файлы или скачайте Tor вручную.", "Tor executable not found. Restore files or download Tor manually."))
                    return

            self.progress.emit(T("Генерация временного torrc...", "Generating temporary torrc..."))
            torrc_path = self.project_folder / "temp_torrc"
            data_dir = self.project_folder / "temp_data"
            data_dir.mkdir(exist_ok=True)
            
            bridges_str = "\n".join([f"Bridge {b}" for b in self.get_bridges()])
            torrc_content = f"""
DataDirectory {data_dir}
SocksPort 127.0.0.1:9750
UseBridges 1
ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec {lyrebird_exe}
AvoidDiskWrites 1
ClientOnly 1
{bridges_str}
"""
            torrc_path.write_text(torrc_content.strip())
            
            self.progress.emit(T("Запуск Tor для загрузки обновления...", "Starting Tor to download the update..."))
            env = os.environ.copy()
            if os_name != "windows":
                lib_path = str(tor_exe.parent)
                env['LD_LIBRARY_PATH'] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
                os.chmod(tor_exe, 0o755)
                if lyrebird_exe.exists():
                    os.chmod(lyrebird_exe, 0o755)

            creation_flags = 0
            if os_name == "windows":
                creation_flags = subprocess.CREATE_NO_WINDOW
                
            tor_process = subprocess.Popen(
                [str(tor_exe), "-f", str(torrc_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                creationflags=creation_flags
            )
            
            self.progress.emit(T("Ожидание подключения Tor (Bootstrap)...", "Waiting for Tor connection (Bootstrap)..."))
            bootstrapped = False
            start_time = time.time()
            timeout = 360
            
            while True:
                if tor_process.poll() is not None:
                    break
                line = tor_process.stdout.readline()
                if not line:
                    break
                if "Bootstrapped 100%" in line:
                    bootstrapped = True
                    break
                if time.time() - start_time > timeout:
                    break
                    
            if not bootstrapped:
                tor_process.terminate()
                self.finished.emit(False, T("Не удалось подключиться к сети Tor (таймаут).", "Failed to connect to the Tor network (timeout)."))
                return
            
            self.progress.emit(T("Tor подключен. Поиск обновлений...", "Tor connected. Searching for updates..."))
            proxies = {
                'http': 'socks5h://127.0.0.1:9750',
                'https': 'socks5h://127.0.0.1:9750'
            }
            
            session = requests.Session()
            session.proxies = proxies
            
            response = session.get("https://www.torproject.org/download/tor/")
            response.raise_for_status()
            
            download_url = self.parse_download_url(response.text, os_name, arch, self.channel)
            if not download_url:
                tor_process.terminate()
                self.finished.emit(False, T("Не удалось найти ссылку на скачивание.", "Failed to find the download link."))
                return
                
            self.progress.emit(T(f"Скачивание обновления: {download_url.split('/')[-1]}...", f"Downloading update: {download_url.split('/')[-1]}..."))
            local_filename = self.project_folder / download_url.split('/')[-1]
            with session.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            if not self.archive_path:
                self.progress.emit(T("Остановка временного Tor...", "Stopping temporary Tor..."))
                tor_process.terminate()
                tor_process.wait()
                tor_process = None
            
            self._extract_and_apply(local_filename)
            
        except Exception as e:
            if tor_process:
                try:
                    tor_process.terminate()
                except:
                    pass
            self.finished.emit(False, T(f"Ошибка при обновлении: {str(e)}", f"Error during update: {str(e)}"))

    def _extract_and_apply(self, local_filename):
        self.progress.emit(T("Распаковка обновления...", "Extracting update..."))
        try:
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            for d in ['tor', 'data', 'docs']:
                src = self.project_folder / d
                if src.exists():
                    shutil.move(str(src), str(self.backup_dir / d))
        except PermissionError as pe:
            self.finished.emit(False, T(f"Файлы заняты другим процессом. Закройте ToInet/Tor и попробуйте снова.\nПодробности: {pe}", f"Files are locked by another process. Close ToInet/Tor and try again.\nDetails: {pe}"))
            return

        if str(local_filename).endswith('.zip'):
            import zipfile
            with zipfile.ZipFile(local_filename, 'r') as zip_ref:
                zip_ref.extractall(self.project_folder)
        else:
            import tarfile
            with tarfile.open(local_filename, "r:gz") as tar:
                if hasattr(tarfile, 'data_filter'):
                    tar.extractall(path=self.project_folder, filter='data')
                else:
                    tar.extractall(path=self.project_folder)
        
        if not self.archive_path:
            import os
            try: os.remove(local_filename)
            except: pass
            
        # FIX: Move tor, data, docs out of tor/ if Tor archive has them nested
        import shutil
        for d in ['data', 'docs']:
            wrong_path = self.project_folder / "tor" / d
            right_path = self.project_folder / d
            if wrong_path.exists():
                if right_path.exists():
                    shutil.rmtree(str(right_path))
                shutil.move(str(wrong_path), str(right_path))
        
        tor_inner = self.project_folder / "tor" / "tor"
        tor_exe_inner = self.project_folder / "tor" / "tor" / "tor.exe"
        tor_exe_right = self.project_folder / "tor" / "tor.exe"
        if tor_exe_inner.exists() and not tor_exe_right.exists():
            # Meaning it unpacked to tor/tor/tor.exe
            # We should move contents of tor/tor to tor/
            temp_tor = self.project_folder / "tor_temp_swap"
            shutil.move(str(tor_inner), str(temp_tor))
            shutil.rmtree(str(self.project_folder / "tor"))
            shutil.move(str(temp_tor), str(self.project_folder / "tor"))
        
        self.progress.emit("Обновление конфигурации...")
        update_info_path = self.project_folder / "update_info.json"
        info = {}
        if True:
            import json
            with _mock_open(update_info_path, 'r') as f:
                info = json.load(f)
        if 'use_folder' in info:
            del info['use_folder']
        info['branch'] = self.channel
        import json
        with _mock_open(update_info_path, 'w') as f:
            json.dump(info, f)
            
        self.finished.emit(True, T("Обновление успешно завершено! Изменения вступят в силу после перезапуска.", "Update successfully completed! Changes will take effect after restart."))

class TorrcConfigurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Конфигуратор" if not lang._is_en else "Tor Configurator")
        self.resize(800, 700)
        
        # Dark Title Bar for Windows
        try:
            import ctypes
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            hwnd = int(self.winId())
            rendering_policy = ctypes.c_int(1)
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy))
        except:
            pass
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 12px;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #005FB8;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 11px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #3c3c3c;
                color: #e0e0e0;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #005FB8;
            }
            QPushButton {
                background-color: #005FB8;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0078D4;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#browseBtn {
                background-color: #555;
                padding: 5px 15px;
            }
            QPushButton#browseBtn:hover {
                background-color: #666;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
                color: #e0e0e0;
                font-size: 11px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #005FB8;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #555;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #2b2b2b;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666;
            }
            QRadioButton {
                color: #e0e0e0;
                font-size: 11px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 13px;
                height: 13px;
            }
            QRadioButton::indicator:unchecked {
                border: 1px solid #555;
                border-radius: 7px;
                background-color: #3c3c3c;
            }
            QRadioButton::indicator:checked {
                border: 1px solid #005FB8;
                border-radius: 7px;
                background-color: #005FB8;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #3c3c3c;
                color: #e0e0e0;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-right: 5px;
            }
            QComboBox:hover {
                border-color: #005FB8;
            }
        """)
        
        # Set default paths
        self.current_dir = CURRENT_DIR
        
        # Determine base tor dir from update_info.json
        self.base_tor_dir = self.current_dir
        update_info_path = os.path.join(self.current_dir, "update_info.json")
        try:
            with _mock_open(update_info_path, 'r') as f:
                info = json.load(f)
                folder_name = info.get('use_folder')
                if folder_name and os.path.exists(os.path.join(self.current_dir, folder_name)):
                    self.base_tor_dir = os.path.join(self.current_dir, folder_name)
        except:
            pass

        self.data_dir = os.path.join(self.current_dir, "data")
        tor_resource_base = self.base_tor_dir
        if not os.path.exists(os.path.join(tor_resource_base, "data", "geoip")) and getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            tor_resource_base = sys._MEIPASS

        self.geoip_path = os.path.join(tor_resource_base, "data", "geoip")
        self.geoipv6_path = os.path.join(tor_resource_base, "data", "geoip6")
        self.bridges_path = os.path.join(self.current_dir, "data", "bridges.txt")
        self.pt_config_path = os.path.join(tor_resource_base, "tor", "pluggable_transports", "pt_config.json")
        self.base_tor_dir = tor_resource_base
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #2b2b2b; }")
        central_widget = QWidget()
        central_widget.setObjectName("scrollContent")
        central_widget.setStyleSheet("QWidget#scrollContent { background-color: #2b2b2b; }")
        scroll.setWidget(central_widget)
        self.setCentralWidget(scroll)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        

        
        # Countries selection group
        countries_group = QGroupBox(T("Выбрать страны конечного ip", "Select exit IP countries"))
        countries_layout = QVBoxLayout()
        countries_layout.setSpacing(10)
        
        # Country list
        self.country_list = CountryListWidget()
        for name, (code, _) in sorted(countries.items()):
            self.country_list.add_country(name, code)
        countries_layout.addWidget(self.country_list)
        
        # Selected countries display
        self.selected_label = QLabel(T("Выбрано: Ничего", "Selected: None"))
        self.selected_label.setStyleSheet("color: #005FB8; font-weight: bold;")
        self.selected_label.setAlignment(Qt.AlignCenter)
        self.country_list.itemSelectionChanged.connect(self.update_selected_label)
        countries_layout.addWidget(self.selected_label)
        
        countries_group.setLayout(countries_layout)
        main_layout.addWidget(countries_group)
        
        # Bridges mode selection group
        bridges_mode_group = QGroupBox(T("Режим мостов", "Bridges Mode"))
        bridges_mode_layout = QVBoxLayout()
        
        # Radio buttons for bridge modes
        self.bridge_mode_group = QButtonGroup()
        
        self.normal_mode_rb = QRadioButton(T("Обычный режим (использовать bridges.txt)", "Normal mode (use bridges.txt)"))
        self.normal_mode_rb.setChecked(True)
        self.webtunnel_mode_rb = QRadioButton(T("Предустановленные webtunnel мосты", "Pre-installed webtunnel bridges"))
        self.obfs4_mode_rb = QRadioButton(T("Предустановленные obfs4 мосты", "Pre-installed obfs4 bridges"))
        self.snowflake_mode_rb = QRadioButton(T("Предустановленные snowflake мосты", "Pre-installed snowflake bridges"))
        self.conjure_mode_rb = QRadioButton(T("Предустановленные conjure мосты", "Pre-installed conjure bridges"))
        self.meek_mode_rb = QRadioButton(T("Предустановленные meek мосты", "Pre-installed meek bridges"))
        
        self.bridge_mode_group.addButton(self.normal_mode_rb, 0)
        self.bridge_mode_group.addButton(self.webtunnel_mode_rb, 1)
        self.bridge_mode_group.addButton(self.obfs4_mode_rb, 2)
        self.bridge_mode_group.addButton(self.snowflake_mode_rb, 3)
        self.bridge_mode_group.addButton(self.conjure_mode_rb, 4)
        self.bridge_mode_group.addButton(self.meek_mode_rb, 5)
        
        bridges_mode_layout.addWidget(self.normal_mode_rb)
        bridges_mode_layout.addWidget(self.webtunnel_mode_rb)
        bridges_mode_layout.addWidget(self.obfs4_mode_rb)
        bridges_mode_layout.addWidget(self.snowflake_mode_rb)
        bridges_mode_layout.addWidget(self.conjure_mode_rb)
        bridges_mode_layout.addWidget(self.meek_mode_rb)
        
        # Connect radio buttons to update UI
        self.normal_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.webtunnel_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.obfs4_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.snowflake_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.conjure_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.meek_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        
        bridges_mode_group.setLayout(bridges_mode_layout)
        main_layout.addWidget(bridges_mode_group)
        
        # Bridges file group (for normal mode)
        bridges_file_group = QGroupBox(T("Мосты (для обычного режима)", "Bridges (for normal mode)"))
        bridges_file_layout = QGridLayout()
        
        bridges_label = QLabel(T("Файл мостов (bridges.txt):", "Bridges file (bridges.txt):"))
        bridges_label.setStyleSheet("font-weight: normal;")
        bridges_file_layout.addWidget(bridges_label, 0, 0)
        
        self.bridges_edit = QLineEdit()
        self.bridges_edit.setText(self.bridges_path)
        self.bridges_edit.setReadOnly(True)
        bridges_file_layout.addWidget(self.bridges_edit, 0, 1)
        
        bridges_browse_btn = QPushButton(T("Выбрать", "Browse"))
        bridges_browse_btn.setObjectName("browseBtn")
        bridges_browse_btn.clicked.connect(self.browse_bridges)
        bridges_file_layout.addWidget(bridges_browse_btn, 0, 2)
        
        bridges_file_group.setLayout(bridges_file_layout)
        main_layout.addWidget(bridges_file_group)
        self.bridges_file_group = bridges_file_group
        
        # Tor directories group
        tor_group = QGroupBox(T("Файлы TOR", "TOR Files"))
        tor_layout = QGridLayout()
        
        # Data directory
        data_label = QLabel(T("Папка Data:", "Data Folder:"))
        data_label.setStyleSheet("font-weight: normal;")
        tor_layout.addWidget(data_label, 0, 0)
        
        self.data_edit = QLineEdit()
        self.data_edit.setText(self.data_dir)
        tor_layout.addWidget(self.data_edit, 0, 1)
        
        data_browse_btn = QPushButton(T("Выбрать", "Browse"))
        data_browse_btn.setObjectName("browseBtn")
        data_browse_btn.clicked.connect(self.browse_data_dir)
        tor_layout.addWidget(data_browse_btn, 0, 2)
        
        # GeoIP file
        geoip_label = QLabel(T("GeoIP Файл:", "GeoIP File:"))
        geoip_label.setStyleSheet("font-weight: normal;")
        tor_layout.addWidget(geoip_label, 1, 0)
        
        self.geoip_edit = QLineEdit()
        self.geoip_edit.setText(self.geoip_path)
        tor_layout.addWidget(self.geoip_edit, 1, 1)
        
        geoip_browse_btn = QPushButton(T("Выбрать", "Browse"))
        geoip_browse_btn.setObjectName("browseBtn")
        geoip_browse_btn.clicked.connect(lambda: self.browse_file(self.geoip_edit))
        tor_layout.addWidget(geoip_browse_btn, 1, 2)
        
        # GeoIPv6 file
        geoipv6_label = QLabel(T("GeoIPv6 Файл:", "GeoIPv6 File:"))
        geoipv6_label.setStyleSheet("font-weight: normal;")
        tor_layout.addWidget(geoipv6_label, 2, 0)
        
        self.geoipv6_edit = QLineEdit()
        self.geoipv6_edit.setText(self.geoipv6_path)
        tor_layout.addWidget(self.geoipv6_edit, 2, 1)
        
        geoipv6_browse_btn = QPushButton(T("Выбрать", "Browse"))
        geoipv6_browse_btn.setObjectName("browseBtn")
        geoipv6_browse_btn.clicked.connect(lambda: self.browse_file(self.geoipv6_edit))
        tor_layout.addWidget(geoipv6_browse_btn, 2, 2)
        
        tor_group.setLayout(tor_layout)
        main_layout.addWidget(tor_group)

        # Upstream Proxy group
        proxy_group = QGroupBox(T("Прокси для TOR (Upstream Proxy)", "Proxy for TOR (Upstream Proxy)"))
        proxy_layout = QGridLayout()

        proxy_type_label = QLabel(T("Тип прокси:", "Proxy Type:"))
        proxy_layout.addWidget(proxy_type_label, 0, 0)
        
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems([T("Нет", "None"), "SOCKS4", "SOCKS5", "HTTP/HTTPS"])
        proxy_layout.addWidget(self.proxy_type_combo, 0, 1)

        proxy_host_label = QLabel(T("Адрес:", "Address:"))
        proxy_layout.addWidget(proxy_host_label, 1, 0)
        self.proxy_host_edit = QLineEdit()
        self.proxy_host_edit.setPlaceholderText("127.0.0.1")
        proxy_layout.addWidget(self.proxy_host_edit, 1, 1)

        proxy_port_label = QLabel(T("Порт:", "Port:"))
        proxy_layout.addWidget(proxy_port_label, 1, 2)
        self.proxy_port_edit = QLineEdit()
        self.proxy_port_edit.setPlaceholderText("1080")
        self.proxy_port_edit.setFixedWidth(60)
        proxy_layout.addWidget(self.proxy_port_edit, 1, 3)

        proxy_user_label = QLabel(T("Логин:", "Username:"))
        proxy_layout.addWidget(proxy_user_label, 2, 0)
        self.proxy_user_edit = QLineEdit()
        proxy_layout.addWidget(self.proxy_user_edit, 2, 1)

        proxy_pass_label = QLabel(T("Пароль:", "Password:"))
        proxy_layout.addWidget(proxy_pass_label, 2, 2)
        self.proxy_pass_edit = QLineEdit()
        self.proxy_pass_edit.setEchoMode(QLineEdit.Password)
        proxy_layout.addWidget(self.proxy_pass_edit, 2, 3)

        proxy_group.setLayout(proxy_layout)
        main_layout.addWidget(proxy_group)
        
        # Tor Update Settings
        update_group = QGroupBox(T("Настройки обновления TOR", "TOR Update Settings"))
        update_layout = QGridLayout()

        branch_label = QLabel(T("Ветка обновления:", "Update Branch:"))
        branch_label.setStyleSheet("font-weight: normal;")
        update_layout.addWidget(branch_label, 0, 0)

        self.branch_combo = QComboBox()
        self.branch_combo.addItems(["stable", "alpha"])
        update_layout.addWidget(self.branch_combo, 0, 1)

        self.autoupdate_cb = QCheckBox(T("Автообновление TOR при запуске ToInet", "Auto-update TOR when ToInet starts"))
        self.autoupdate_cb.setStyleSheet("color: #e0e0e0; font-size: 11px;")
        self.autoupdate_cb.toggled.connect(self.on_autoupdate_changed)
        update_layout.addWidget(self.autoupdate_cb, 1, 0, 1, 2)

        update_btn = QPushButton(T("Проверить и обновить", "Check and update"))
        update_btn.clicked.connect(self.run_update)
        update_layout.addWidget(update_btn, 2, 0)

        rollback_btn = QPushButton(T("Откат к бекапу", "Rollback to backup"))
        rollback_btn.clicked.connect(self.rollback_update)
        update_layout.addWidget(rollback_btn, 2, 1)

        archive_btn = QPushButton(T("Установить из архива", "Install from archive"))
        archive_btn.clicked.connect(self.install_from_archive)
        update_layout.addWidget(archive_btn, 3, 0, 1, 2)

        update_group.setLayout(update_layout)
        main_layout.addWidget(update_group)
        
        self.load_update_settings()

        # Proxy Pool
        pool_group = QGroupBox(T("Пул прокси (Load Balancing)", "Proxy Pool (Load Balancing)"))
        pool_group.setFont(QFont("Segoe UI", 10))
        pool_layout = QHBoxLayout(pool_group)
        self.pool_checkbox = QCheckBox(T("Включить пул (запуск нескольких экземпляров)", "Enable Pool (Run multiple instances)"))
        self.pool_spinbox = QSpinBox()
        self.pool_spinbox.setRange(2, 10)
        self.pool_spinbox.setValue(3)
        self.pool_spinbox.setEnabled(False)
        self.pool_checkbox.toggled.connect(self.pool_spinbox.setEnabled)
        pool_layout.addWidget(self.pool_checkbox)
        pool_layout.addWidget(QLabel(T("Количество:", "Count:")))
        pool_layout.addWidget(self.pool_spinbox)
        main_layout.addWidget(pool_group)

        self.load_pool_settings()
        
        # Initialize bridge UI state
        self.on_bridge_mode_changed()

        # Extra tools layout
        tools_layout = QHBoxLayout()
        
        edit_bridges_btn = QPushButton(T("Смена мостов", "Edit Bridges"))
        edit_bridges_btn.clicked.connect(lambda: self.run_edit_bridges())
        edit_bridges_btn.setStyleSheet("background-color: #555; font-size: 11px;")
        tools_layout.addWidget(edit_bridges_btn)
        
        delete_config_btn = QPushButton(T("Удаление конфигурации TOR", "Delete TOR Config"))
        delete_config_btn.clicked.connect(lambda: self.delete_tor_config())
        delete_config_btn.setStyleSheet("background-color: #d32f2f; font-size: 11px;")
        tools_layout.addWidget(delete_config_btn)
        
        main_layout.addLayout(tools_layout)

        # Generate button
        generate_btn = QPushButton(T("Создать конфигурацию", "Generate Configuration"))
        generate_btn.setMinimumHeight(40)
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #005FB8;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0078D4;
            }
        """)
        generate_btn.clicked.connect(self.generate_torrc)
        main_layout.addWidget(generate_btn)
        
    def load_update_settings(self):
        update_info_path = os.path.join(self.current_dir, "update_info.json")
        if True:
            try:
                with _mock_open(update_info_path, 'r') as f:
                    info = json.load(f)
                    if info.get('auto_update', False):
                        self.autoupdate_cb.setChecked(True)
                    
                    branch = info.get('branch', 'stable')
                    index = self.branch_combo.findText(branch)
                    if index >= 0:
                        self.branch_combo.setCurrentIndex(index)
            except:
                pass

    def run_edit_bridges(self):
        import subprocess
        exe_path = os.path.join(self.current_dir, "bin", "edit_bridges.exe")
        if os.path.exists(exe_path):
            subprocess.Popen([exe_path], cwd=self.current_dir, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    def delete_tor_config(self):
        reply = QMessageBox.question(self, T("Подтверждение", "Confirm"), 
            T("Вы уверены, что хотите удалить конфигурацию TOR?", "Are you sure you want to delete TOR config?"), 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            import shutil
            for f in ["data/torrc"]:
                p = os.path.join(self.current_dir, f)
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass
            QMessageBox.information(self, T("Готово", "Done"), T("Конфигурация TOR удалена", "TOR Config deleted"))

    def load_pool_settings(self):
        try:
            from managers import config_manager
            config = config_manager.load_config()
            pool_enabled = config.get("tor_pool_enabled", False)
            pool_size = config.get("tor_pool_size", 3)
            self.pool_checkbox.setChecked(pool_enabled)
            self.pool_spinbox.setValue(pool_size)
        except Exception as e:
            print("Failed to load pool settings:", e)


    def on_autoupdate_changed(self, state):
        update_info_path = os.path.join(self.current_dir, "update_info.json")
        info = {}
        if True:
            try:
                with _mock_open(update_info_path, 'r') as f:
                    info = json.load(f)
            except:
                pass
        
        info['auto_update'] = self.autoupdate_cb.isChecked()
        try:
            with _mock_open(update_info_path, 'w') as f:
                json.dump(info, f)
        except:
            pass

    def install_from_archive(self):
        file_path, _ = QFileDialog.getOpenFileName(self, T("Выберите архив Tor", "Select Tor archive"), "", "Archives (*.zip *.tar.gz)")
        if file_path:
            self.run_update(archive_path=file_path)

    def run_update(self, archive_path=None):
        branch = self.branch_combo.currentText()
        
        # Save branch preference
        self.on_autoupdate_changed(None)
        update_info_path = os.path.join(self.current_dir, "update_info.json")
        try:
            with _mock_open(update_info_path, 'r') as f:
                info = json.load(f)
            info['branch'] = branch
            with _mock_open(update_info_path, 'w') as f:
                json.dump(info, f)
        except:
            pass

        # Check IP only if downloading
        if not archive_path:
            country_code = None
            try:
                res = requests.get('http://ip-api.com/json', proxies={'http': 'socks5h://127.0.0.1:9853', 'https': 'socks5h://127.0.0.1:9853'}, timeout=3).json()
                country_code = res.get('countryCode')
            except:
                try:
                    res = requests.get('http://ip-api.com/json', timeout=3).json()
                    country_code = res.get('countryCode')
                except:
                    pass

            if country_code == 'RU':
                QMessageBox.warning(self, T("Внимание", "Warning"), T("Отключите все экземпляры TOR, скачивание из РФ невозможно.", "Disable all TOR instances, downloading from RF is impossible."))
                return
            elif country_code == 'GB':
                reply = QMessageBox.question(self, T("Предупреждение", "Warning"), T("Внимание: скачивание Tor в Великобритании может привлечь внимание госорганов. Продолжить?", "Warning: downloading Tor in the UK may attract the attention of government authorities. Continue?"), QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return

        self.progress_dialog = QProgressDialog(T("Подготовка к обновлению...", "Preparing to update..."), T("Отмена", "Cancel"), 0, 0, self)
        self.progress_dialog.setWindowTitle(T("Обновление Tor", "Tor Update"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #3c3c3c;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #005FB8;
            }
        """)
        self.progress_dialog.show()
        
        self.updater_thread = TorUpdaterThread(channel=branch, archive_path=archive_path)
        self.updater_thread.progress.connect(self.update_progress)
        self.updater_thread.finished.connect(self.update_finished)
        self.updater_thread.start()

    def update_progress(self, msg):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(msg)

    def update_finished(self, success, msg):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        if success:
            QMessageBox.information(self, T("Успех", "Success"), msg)
            new_dir = os.path.join(self.current_dir, "tor")
            if os.path.exists(new_dir):
                self.base_tor_dir = new_dir
                self.data_edit.setText(os.path.join(new_dir, "data"))
                self.geoip_edit.setText(os.path.join(new_dir, "data", "geoip"))
                self.geoipv6_edit.setText(os.path.join(new_dir, "data", "geoip6"))
        else:
            QMessageBox.critical(self, T("Ошибка", "Error"), msg)

    def rollback_update(self):
        update_info_path = os.path.join(self.current_dir, "update_info.json")
        backup_dir = os.path.join(self.current_dir, "backup")
        
        if not os.path.exists(backup_dir):
            QMessageBox.warning(self, T("Ошибка", "Error"), T("Папка backup не найдена. Откат невозможен.", "Backup folder not found. Rollback is impossible."))
            return
            
        try:
            import subprocess, platform, time
            if platform.system().lower() == "windows":
                subprocess.run(["taskkill", "/F", "/IM", "tor.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["killall", "tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
        except:
            pass

        try:
            import shutil
            # Move from backup to root
            for d in ['tor', 'data', 'docs']:
                src = os.path.join(backup_dir, d)
                dst = os.path.join(self.current_dir, d)
                if os.path.exists(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.move(src, dst)
            
            # Delete tor_latest if it exists
            tor_latest_dir = os.path.join(self.current_dir, "tor_latest")
            if os.path.exists(tor_latest_dir):
                shutil.rmtree(tor_latest_dir)
                
            info = {}
            if True:
                with _mock_open(update_info_path, 'r') as f:
                    info = json.load(f)
            
            info['use_folder'] = ''
            with _mock_open(update_info_path, 'w') as f:
                json.dump(info, f)
                
            QMessageBox.information(self, T("Успешно", "Success"), T("Откат выполнен успешно. Файлы восстановлены из бекапа.", "Rollback successful. Files restored from backup."))
            self.base_tor_dir = self.current_dir
            self.data_edit.setText(os.path.join(self.current_dir, "data"))
            self.geoip_edit.setText(os.path.join(self.current_dir, "data", "geoip"))
            self.geoipv6_edit.setText(os.path.join(self.current_dir, "data", "geoip6"))
        except PermissionError:
            QMessageBox.critical(self, T("Ошибка", "Error"), T("Файлы заняты другим процессом. Пожалуйста, закройте ToInet/Tor перед откатом.", "Files are locked by another process. Please close ToInet/Tor before rolling back."))
        except Exception as e:
            QMessageBox.critical(self, T("Ошибка", "Error"), T(f"Не удалось выполнить откат: {e}", f"Failed to rollback: {e}"))

    def on_bridge_mode_changed(self):
        """Handle bridge mode change"""
        if self.normal_mode_rb.isChecked():
            self.bridges_file_group.setVisible(True)
        else:
            self.bridges_file_group.setVisible(False)
                
    def update_selected_label(self):
        """Update the selected countries label"""
        selected = self.country_list.selectedItems()
        if selected:
            countries_text = []
            for item in selected:
                name = item.data(Qt.UserRole + 1)
                countries_text.append(name)
            self.selected_label.setText(f"Выбрано: {', '.join(countries_text)}")
        else:
            self.selected_label.setText("Выбрано: Ничего")
            
    def browse_bridges(self):
        """Browse for bridges.txt file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл моста", "", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.bridges_edit.setText(path)
            
    def browse_data_dir(self):
        """Browse for data directory"""
        path = QFileDialog.getExistingDirectory(self, "Выбрать Data папку")
        if path:
            self.data_edit.setText(path)
            
    def browse_file(self, line_edit):
        """Browse for any file"""
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать Файл")
        if path:
            line_edit.setText(path)
    
    def load_pt_config(self):
        """Load pluggable transports configuration from JSON file"""
        try:
            if os.path.exists(self.pt_config_path):
                with open(self.pt_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Return default config if file not found
                return {
                    "pluggableTransports": {
                        "lyrebird": "ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec ${pt_path}lyrebird.exe",
                        "snowflake": "ClientTransportPlugin snowflake exec ${pt_path}lyrebird.exe",
                        "conjure": "ClientTransportPlugin conjure exec ${pt_path}conjure-client.exe -registerURL https://registration.refraction.network/api"
                    },
                    "bridges": {
                        "meek": [
                            "meek_lite 192.0.2.20:80 url=https://1603026938.rsc.cdn77.org front=www.phpmyadmin.net utls=HelloRandomizedALPN"
                        ],
                        "obfs4": [
                            "obfs4 37.218.245.14:38224 D9A82D2F9C2F65A18407B1D2B764F130847F8B5D cert=bjRaMrr1BRiAW8IE9U5z27fQaYgOhX1UCmOpg2pFpoMvo6ZgQMzLsaTzzQNTlm7hNcb+Sg iat-mode=0",
                            "obfs4 209.148.46.65:443 74FAD13168806246602538555B5521A0383A1875 cert=ssH+9rP8dG2NLDN2XuFw63hIO/9MNNinLmxQDpVa+7kTOa9/m+tGWT1SmSYpQ9uTBGa6Hw iat-mode=0",
                            "obfs4 146.57.248.225:22 10A6CD36A537FCE513A322361547444B393989F0 cert=K1gDtDAIcUfeLqbstggjIw2rtgIKqdIhUlHp82XRqNSq/mtAjp1BIC9vHKJ2FAEpGssTPw iat-mode=0",
                            "obfs4 45.145.95.6:27015 C5B7CD6946FF10C5B3E89691A7D3F2C122D2117C cert=TD7PbUO0/0k6xYHMPW3vJxICfkMZNdkRrb63Zhl5j9dW3iRGiCx0A7mPhe5T2EDzQ35+Zw iat-mode=0",
                            "obfs4 51.222.13.177:80 5EDAC3B810E12B01F6FD8050D2FD3E277B289A08 cert=2uplIpLQ0q9+0qMFrK5pkaYRDOe460LL9WHBvatgkuRr/SL31wBOEupaMMJ6koRE6Ld0ew iat-mode=0",
                            "obfs4 212.83.43.95:443 BFE712113A72899AD685764B211FACD30FF52C31 cert=ayq0XzCwhpdysn5o0EyDUbmSOx3X/oTEbzDMvczHOdBJKlvIdHHLJGkZARtT4dcBFArPPg iat-mode=1",
                            "obfs4 212.83.43.74:443 39562501228A4D5E27FCA4C0C81A01EE23AE3EE4 cert=PBwr+S8JTVZo6MPdHnkTwXJPILWADLqfMGoVvhZClMq/Urndyd42BwX9YFJHZnBB3H0XCw iat-mode=1"
                        ],
                        "snowflake": [
                            "snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://1098762253.rsc.cdn77.org/ fronts=app.datapacket.com,www.datapacket.com ice=stun:stun.epygi.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.mixvoip.com:3478,stun:stun.nextcloud.com:3478,stun:stun.bethesda.net:3478,stun:stun.nextcloud.com:443 utls-imitate=hellorandomizedalpn",
                            "snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA fingerprint=8838024498816A039FCBBAB14E6F40A0843051FA url=https://1098762253.rsc.cdn77.org/ fronts=app.datapacket.com,www.datapacket.com ice=stun:stun.epygi.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.mixvoip.com:3478,stun:stun.nextcloud.com:3478,stun:stun.bethesda.net:3478,stun:stun.nextcloud.com:443 utls-imitate=hellorandomizedalpn"
                        ]
                    }
                }
        except Exception as e:
            QMessageBox.warning(self, T("Предупреждение", "Warning"), f"Не удалось загрузить pt_config.json: {e}")
            return None
    
    def get_bridges_and_transport(self):
        """Get bridges and transport plugin based on selected mode"""
        pt_config = self.load_pt_config()
        if not pt_config:
            return [], None
        
        bridges = []
        transport_plugin = None
        pt_path = os.path.join(self.base_tor_dir, "tor", "pluggable_transports", "")
        
        if self.normal_mode_rb.isChecked():
            # Normal mode: read from bridges.txt
            bridges_path = self.bridges_edit.text()
            if os.path.exists(bridges_path):
                try:
                    with open(bridges_path, 'r', encoding='utf-8') as f:
                        bridges = [line.strip() for line in f if line.strip()]
                except Exception as e:
                    QMessageBox.critical(self, T("Ошибка", "Error"), f"Не удалось прочитать файл мостов: {e}")
                    return [], None
            
            # For normal mode, use lyrebird for all transports
            if "pluggableTransports" in pt_config and "lyrebird" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["lyrebird"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.webtunnel_mode_rb.isChecked():
            # WebTunnel preset bridges
            bridges = get_default_bridges()
            if "pluggableTransports" in pt_config and "lyrebird" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["lyrebird"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.obfs4_mode_rb.isChecked():
            # Obfs4 preset bridges
            if "bridges" in pt_config and "obfs4" in pt_config["bridges"]:
                bridges = pt_config["bridges"]["obfs4"]
            if "pluggableTransports" in pt_config and "lyrebird" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["lyrebird"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.snowflake_mode_rb.isChecked():
            # Snowflake preset bridges
            if "bridges" in pt_config and "snowflake" in pt_config["bridges"]:
                bridges = pt_config["bridges"]["snowflake"]
            if "pluggableTransports" in pt_config and "snowflake" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["snowflake"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.conjure_mode_rb.isChecked():
            # Conjure preset bridges
            conjure_bridge = "conjure 143.110.214.222:80 url=https://registration.refraction.network.global.prod.fastly.net/api front=cdn.sstatic.net"
            bridges = [conjure_bridge]
            if "pluggableTransports" in pt_config and "conjure" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["conjure"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.meek_mode_rb.isChecked():
            # Meek preset bridges
            if "bridges" in pt_config and "meek" in pt_config["bridges"]:
                bridges = pt_config["bridges"]["meek"]
            if "pluggableTransports" in pt_config and "lyrebird" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["lyrebird"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        return [], None
            
    def generate_torrc(self):
        """Generate the torrc configuration file"""
        # Get selected countries
        selected_countries = self.country_list.get_selected_countries()
        
        if not selected_countries:
            reply = QMessageBox.question(
                self, "Нет выбранных стран",
                "Вы не выбрали ни одной страны. Продолжить?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Get bridges and transport plugin based on mode
        bridges, transport_plugin = self.get_bridges_and_transport()
        
        # Check if we have bridges when needed
        if not self.normal_mode_rb.isChecked() and not bridges:
            reply = QMessageBox.question(
                self, "Нет мостов",
                "Не удалось загрузить предустановленные мосты. Продолжить без мостов?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Generate torrc content
        torrc_lines = [
            f"DataDirectory {self.data_edit.text()}",
            f"GeoIPFile {self.geoip_edit.text()}",
            f"GeoIPv6File {self.geoipv6_edit.text()}",
            "SocksPort 9853",
            "ControlPort 9851",
            "HashedControlPassword 16:FDD492298759EE7D608D25F04A895488921206AD3109F87E7CC80F09D1",
        ]
        
        # Add ExitNodes if countries are selected
        if selected_countries:
            exit_nodes = ','.join(f'{{{code}}}' for code in selected_countries)
            torrc_lines.append(f"ExitNodes {exit_nodes}")

        # Add Upstream Proxy configuration
        proxy_type = self.proxy_type_combo.currentText()
        proxy_host = self.proxy_host_edit.text().strip()
        proxy_port = self.proxy_port_edit.text().strip()
        proxy_user = self.proxy_user_edit.text().strip()
        proxy_pass = self.proxy_pass_edit.text().strip()

        if proxy_type != "Нет" and proxy_host and proxy_port:
            if proxy_type == "SOCKS4":
                torrc_lines.append(f"Socks4Proxy {proxy_host}:{proxy_port}")
            elif proxy_type == "SOCKS5":
                torrc_lines.append(f"Socks5Proxy {proxy_host}:{proxy_port}")
                if proxy_user:
                    torrc_lines.append(f"Socks5ProxyUsername {proxy_user}")
                if proxy_pass:
                    torrc_lines.append(f"Socks5ProxyPassword {proxy_pass}")
            elif proxy_type == "HTTP/HTTPS":
                torrc_lines.append(f"HTTPSProxy {proxy_host}:{proxy_port}")
                if proxy_user and proxy_pass:
                    torrc_lines.append(f"HTTPSProxyAuthenticator {proxy_user}:{proxy_pass}")
        
        # Add bridges configuration
        if bridges:
            torrc_lines.append("UseBridges 1")
            torrc_lines.extend(f"Bridge {bridge}" for bridge in bridges)
            if transport_plugin:
                torrc_lines.append(transport_plugin)
        elif self.normal_mode_rb.isChecked():
            # Check if we're in normal mode but no bridges found
            bridges_path = self.bridges_edit.text()
            if os.path.exists(bridges_path):
                QMessageBox.warning(self, T("Предупреждение", "Warning"), "Файл мостов пуст или содержит некорректные данные")
        
        # Add additional settings
        torrc_lines.extend([
            "AvoidDiskWrites 1",
            "HardwareAccel 1",
            "ClientOnly 1",
            "AutomapHostsOnResolve 1",
            "SafeLogging 1"
        ])
        
        # Write to file
        output_path = os.path.join(self.current_dir, "data", "torrc")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(torrc_lines))
            
            # Save pool settings to data/config.json
            try:
                from managers import config_manager
                config = config_manager.load_config()
                config["tor_pool_enabled"] = self.pool_checkbox.isChecked()
                config["tor_pool_size"] = self.pool_spinbox.value()
                config_manager.save_config(config)
            except Exception as e:
                print(f"Failed to save pool settings: {e}")
            
            # Show success message with mode info

            mode_text = ""
            if self.webtunnel_mode_rb.isChecked():
                mode_text = " (webtunnel)"
            elif self.obfs4_mode_rb.isChecked():
                mode_text = " (obfs4)"
            elif self.snowflake_mode_rb.isChecked():
                mode_text = " (snowflake)"
            elif self.conjure_mode_rb.isChecked():
                mode_text = " (conjure)"
            elif self.meek_mode_rb.isChecked():
                mode_text = " (meek)"
            
            QMessageBox.information(
                self, "Успешно",
                f"Конфигурация успешно сохранена в {output_path}{mode_text}"
            )
            self.statusBar().showMessage(f"Configuration saved to {output_path}", 5000)
            
        except Exception as e:
            QMessageBox.critical(self, T("Ошибка", "Error"), f"Не удалось записать конфигурацию, ошибка: {e}")

def launch_gui():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    icon_path = os.path.join(CURRENT_DIR, 'icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = TorrcConfigurator()
    window.show()
    sys.exit(app.exec())

def main():
    cli_flags = {'--update', '--config', '--port', '--countries', '--bridges', '--channel', '--cli', '--run', '-h', '--help'}
    if any(arg in cli_flags or arg.startswith('--config=') or arg.startswith('--port=') or arg.startswith('--channel=') for arg in sys.argv[1:]):
        cli_main()
    else:
        launch_gui()

if __name__ == '__main__':
    main()


