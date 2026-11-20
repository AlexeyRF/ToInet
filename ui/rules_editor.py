import sys
import os
import subprocess

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exe_path = os.path.join(CURRENT_DIR, "bin", "rules_editor.exe")

class RulesEditorDialog:
    def __init__(self, parent=None):
        pass

    def exec(self):
        if os.path.exists(exe_path):
            p = subprocess.Popen([exe_path])
            p.wait()
        else:
            print(f"Error: {exe_path} not found.")

def main():
    if os.path.exists(exe_path):
        p = subprocess.Popen([exe_path])
        p.wait()
    else:
        print(f"Error: {exe_path} not found.")

if __name__ == "__main__":
    main()
