import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
import os
import psutil

script_dir = CURRENT_DIR
tor_path = os.path.join(script_dir, "tor", "tor.exe")

tor_path = os.path.normcase(os.path.normpath(tor_path))

for proc in psutil.process_iter(['pid', 'name']):
    try:
        if proc.info['name'] and 'tor' in proc.info['name'].lower():
            exe_path = proc.exe()
            if exe_path and os.path.normcase(os.path.normpath(exe_path)) == tor_path:
                proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue



