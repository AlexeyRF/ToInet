import os
import subprocess
import signal
import sys
import time
import argparse
import json
import platform
import shutil
import tarfile
import re
import threading
from pathlib import Path

# Try to import requests for the updater
try:
    import requests
except ImportError:
    requests = None

PROJECT_FOLDER = Path(__file__).parent.absolute()
CONFIG_FILE = PROJECT_FOLDER / "tor_config.json"
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

def get_paths(base_dir=PROJECT_FOLDER):
    base_path = Path(base_dir)
    ext = ".exe" if sys.platform == "win32" else ""
    
    # We look for tor in several possible locations
    # 1. base_dir/tor/tor.exe (Expert Bundle)
    # 2. base_dir/backup/tor/tor.exe (Legacy updater structure)
    # 3. base_dir/tor.exe (Flat)
    
    possible_tor_exes = [
        base_path / "tor" / f"tor{ext}",
        base_path / "backup" / "tor" / f"tor{ext}",
        base_path / f"tor{ext}"
    ]
    
    tor_exe = None
    for p in possible_tor_exes:
        if p.exists():
            tor_exe = p
            break
    
    if not tor_exe:
        tor_exe = base_path / "tor" / f"tor{ext}" # Default assumption

    tor_dir = tor_exe.parent
    # Pluggable transports are usually in tor/pluggable_transports/
    lyrebird_exe = tor_dir / "pluggable_transports" / f"lyrebird{ext}"
    
    # Data dir is usually sibling to tor dir in expert bundle
    data_dir = tor_dir.parent / "data"
    
    return {
        'tor_exe': tor_exe,
        'lyrebird_exe': lyrebird_exe,
        'data_dir': data_dir,
        'geoip': data_dir / "geoip",
        'geoip6': data_dir / "geoip6",
        'torrc': PROJECT_FOLDER / "torrc"
    }

def load_config(config_name=None):
    if not CONFIG_FILE.exists():
        return {}
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            configs = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}
    
    if config_name:
        return configs.get(config_name, {})
    
    # If no config_name, look for 'default' or return the whole dict if it's not nested
    if 'default' in configs:
        return configs['default']
    return configs

def save_config(config_name, config_data):
    configs = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                configs = json.load(f)
        except Exception:
            pass
    
    configs[config_name] = config_data
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)

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
    local_filename = PROJECT_FOLDER / url.split('/')[-1]
    print(f"Downloading {url}...")
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

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

def update_tor(channel="stable"):
    if not requests:
        print("Error: 'requests' library is not installed. Update skipped.")
        return False

    os_name, arch = get_system_info()
    print(f"System detected: {os_name} ({arch})")
    
    # Try to find existing Tor to use as proxy for download
    base_dir = PROJECT_FOLDER
    if UPDATE_INFO_FILE.exists():
        try:
            with open(UPDATE_INFO_FILE, 'r') as f:
                info = json.load(f)
                folder_name = info.get('use_folder')
                if folder_name and (PROJECT_FOLDER / folder_name).exists():
                    base_dir = PROJECT_FOLDER / folder_name
        except Exception:
            pass

    paths = get_paths(base_dir)
    if not paths['tor_exe'].exists():
        paths = get_paths(PROJECT_FOLDER)
        if not paths['tor_exe'].exists():
            print(f"Error: Tor executable not found. Cannot perform update through proxy.")
            return False

    print("Starting temporary Tor for update...")
    update_config = {
        'port': UPDATE_PROXY_PORT,
        'bridges': get_default_bridges(),
        'countries': None
    }
    
    torrc_path = generate_torrc(update_config, paths)
    
    env = os.environ.copy()
    if sys.platform != "win32":
        lib_path = str(paths['tor_exe'].parent)
        env['LD_LIBRARY_PATH'] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
        os.chmod(paths['tor_exe'], 0o755)
        if paths['lyrebird_exe'].exists():
            os.chmod(paths['lyrebird_exe'], 0o755)

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
        
    except Exception as e:
        print(f"Update failed: {e}")
        return False

    print("Updating folders...")
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    
    # Move current to backup
    if TOR_LATEST_DIR.exists():
        shutil.move(str(TOR_LATEST_DIR), str(BACKUP_DIR))
    else:
        # If we don't have tor_latest, try to backup existing core folders from project root
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        for d in ['tor', 'data', 'docs']:
            src = PROJECT_FOLDER / d
            if src.exists():
                shutil.move(str(src), str(BACKUP_DIR / d))

    TOR_LATEST_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Unpacking {archive_path} to {TOR_LATEST_DIR}...")
    with tarfile.open(archive_path, "r:gz") as tar:
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(path=TOR_LATEST_DIR, filter='data')
        else:
            tar.extractall(path=TOR_LATEST_DIR)
    
    os.remove(archive_path)
    
    with open(UPDATE_INFO_FILE, 'w') as f:
        json.dump({'use_folder': 'tor_latest', 'last_update': time.time()}, f)
    
    print("Update complete.")
    return True

def generate_torrc(config, paths):
    exit_nodes = ""
    if config.get('countries'):
        exit_nodes = ",".join([f"{{{country}}}" for country in config['countries']])
    
    data_dir = paths['data_dir']
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)

    torrc_content = f"""
DataDirectory {data_dir}
GeoIPFile {paths['geoip']}
GeoIPv6File {paths['geoip6']}
SocksPort 0.0.0.0:{config.get('port', DEFAULT_PROXY_PORT)}
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
    torrc_path.write_text(torrc_content.strip())
    return torrc_path

def run_tor(torrc_path, tor_exe_path, log_filter=None):
    if not tor_exe_path.exists():
        raise FileNotFoundError(f"Tor not found: {tor_exe_path}")
    
    env = os.environ.copy()
    if sys.platform != "win32":
        lib_path = str(tor_exe_path.parent)
        env['LD_LIBRARY_PATH'] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
        os.chmod(tor_exe_path, 0o755)
        # Also try to chmod lyrebird
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

def main():
    parser = argparse.ArgumentParser(description="Tor Manager (Launcher + Updater)")
    parser.add_argument('--config', help="Config name to load")
    parser.add_argument('--update', action='store_true', help="Force update Tor")
    args = parser.parse_args()
    
    config = load_config(args.config)
    if not config and args.config:
        print(f"Config '{args.config}' not found.")
        return
    elif not config:
        config = get_user_config()

    if args.update or config.get('check_updates'):
        print("Checking for updates...")
        update_tor()

    base_dir = PROJECT_FOLDER
    if UPDATE_INFO_FILE.exists():
        try:
            with open(UPDATE_INFO_FILE, 'r') as f:
                info = json.load(f)
                folder_name = info.get('use_folder')
                if folder_name and (PROJECT_FOLDER / folder_name).exists():
                    base_dir = PROJECT_FOLDER / folder_name
                    print(f"Using Tor from: {folder_name}")
        except Exception:
            pass

    paths = get_paths(base_dir)
    
    print("Generating torrc...")
    torrc_path = generate_torrc(config, paths)
    
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
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Tor started. Press Ctrl+C to stop.")
    try:
        tor_process.wait()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
