import os
import sys
import subprocess

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, "bin", "autostart_settings.exe")
    if os.path.exists(exe_path):
        subprocess.Popen([exe_path], cwd=base_dir)
    else:
        print(f"Error: binary not found: {exe_path}")

class AutostartSettingsWindow:
    def __init__(self, *args, **kwargs):
        pass
    def show(self):
        main()

if __name__ == "__main__":
    main()
