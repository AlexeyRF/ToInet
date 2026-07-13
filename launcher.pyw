import subprocess
import sys
import json
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    project_dir = Path(sys.executable).parent.absolute()
    script_dir = Path(__file__).parent.absolute()
else:
    project_dir = Path(__file__).parent.absolute()
    script_dir = project_dir

tor_exe_path = project_dir / 'tor' / 'tor.exe'
torrc_path = project_dir / 'torrc'
if not tor_exe_path.exists(): sys.exit("Tor exe not found")
if not torrc_path.exists(): sys.exit("torrc not found")

pool_enabled = False
pool_size = 3
config_path = project_dir / 'config.json'
if config_path.exists():
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            show_window = config.get("tor_show_window", False)
            pool_enabled = config.get("tor_pool_enabled", False)
            pool_size = int(config.get("tor_pool_size", 3))
    except:
        pass

creation_flags = subprocess.CREATE_NEW_CONSOLE if show_window else subprocess.CREATE_NO_WINDOW
stdout = None if show_window else subprocess.DEVNULL
stderr = None if show_window else subprocess.DEVNULL

if not pool_enabled or pool_size <= 1:
    try:
        process = subprocess.Popen([str(tor_exe_path), '-f', str(torrc_path)], stdout=stdout, stderr=stderr, creationflags=creation_flags)
    except Exception as e: sys.exit(f"Failed to start Tor: {e}")
    try: process.wait()
    except KeyboardInterrupt: process.terminate()
else:
    # Pool mode
    socks_port = 9853
    try:
        with open(torrc_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("SocksPort "):
                    socks_port = int(line.split()[1])
    except:
        pass
        
    processes = []
    upstream_ports = []
    control_ports = []
    data_dir_base = project_dir / "data"
    
    pool_dirs = []
    for i in range(pool_size):
        socks = socks_port + 1000 + i
        control = socks_port + 2000 + i
        upstream_ports.append(socks)
        control_ports.append(control)
        data_dir = data_dir_base / f"tor_pool_{i}"
        data_dir.mkdir(parents=True, exist_ok=True)
        pool_dirs.append(data_dir)
        
        args = [
            str(tor_exe_path), '-f', str(torrc_path),
            '--SocksPort', str(socks),
            '--ControlPort', str(control),
            '--DataDirectory', str(data_dir)
        ]
        try:
            p = subprocess.Popen(args, stdout=stdout, stderr=stderr, creationflags=creation_flags)
            processes.append(p)
        except Exception as e:
            print(f"Failed to start Tor instance {i}: {e}")
            
    pool_script = script_dir / "proxy_pool.py"
    if pool_script.exists():
        try:
            pool_proc = subprocess.Popen([
                sys.executable,
                str(pool_script),
                '--listen-port', str(socks_port),
                '--upstream-ports', ','.join(map(str, upstream_ports)),
                '--control-ports', ','.join(map(str, control_ports))
            ], stdout=stdout, stderr=stderr, creationflags=creation_flags)
            processes.append(pool_proc)
        except Exception as e:
            print(f"Failed to start proxy pool: {e}")
            
    try:
        import time
        while True:
            # Check if any process terminated
            any_dead = False
            for p in processes:
                if p.poll() is not None:
                    any_dead = True
                    break
            
            if any_dead:
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        pass
        
    for p in processes:
        try:
            p.terminate()
        except:
            pass
            
    # Wait a bit for processes to release locks on data directories
    import time
    time.sleep(1)
    
    # Keep pool directories so Tor can cache descriptors and bootstrap quickly next time.
    pass


