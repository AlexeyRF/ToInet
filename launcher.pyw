import subprocess
import sys
from pathlib import Path
project_dir = Path(__file__).parent.absolute()
tor_exe_path = project_dir / 'tor' / 'tor.exe'
torrc_path = project_dir / 'torrc'
if not tor_exe_path.exists(): sys.exit("Tor exe not found")
if not torrc_path.exists(): sys.exit("torrc not found")
try:process = subprocess.Popen([str(tor_exe_path), '-f', str(torrc_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
except Exception as e: sys.exit(f"Failed to start Tor: {e}")
try: process.wait()
except KeyboardInterrupt: process.terminate()
