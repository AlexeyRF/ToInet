import sys
import os
import subprocess

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exe_path = os.path.join(CURRENT_DIR, "bin", "tgws_settings.exe")

def main():
    if os.path.exists(exe_path):
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.Popen([exe_path], creationflags=creationflags)
    else:
        print(f"Error: {exe_path} not found.")

if __name__ == "__main__":
    main()
