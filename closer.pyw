import os
import psutil

script_dir = os.path.dirname(os.path.abspath(__file__))
tor_path = os.path.join(script_dir, "tor", "tor.exe")

tor_path = os.path.normcase(os.path.normpath(tor_path))

for proc in psutil.process_iter(['pid', 'exe', 'name']):
    try:
        exe_path = proc.info['exe']
        if exe_path and os.path.normcase(os.path.normpath(exe_path)) == tor_path:
            proc.terminate()
            proc.wait(timeout=5)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue
