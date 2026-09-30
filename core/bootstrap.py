import system_utils as lang
import sys
import os
def _ensure_dependencies():
    import sys, os
    if getattr(sys, 'frozen', False):
        return
    required = {
        'PyQt5': 'pyqt5',
        'psutil': 'psutil',
        'requests': 'requests',
        'cryptography': 'cryptography==46.0.5',
        'win32com': 'pywin32',
        'pyperclip': 'pyperclip==1.9.0',
        'socks': 'pysocks'
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing dependencies found: {', '.join(missing)}")
        print("Starting auto-installation...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("Successfully installed dependencies! Restarting application...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"Failed to install dependencies: {e}")
            sys.exit(1)
_ensure_dependencies()

if getattr(sys, 'frozen', False):
    import runpy
    original_exists = os.path.exists
    original_isfile = os.path.isfile
    exe_dir = os.path.dirname(sys.executable)
    
    def smart_check(path, original_func):
        if original_func(path):
            return True
        if isinstance(path, str) and path.endswith(('.py', '.pyw')):
            if path.startswith(exe_dir):
                rel = os.path.relpath(path, exe_dir)
                meipass_path = os.path.join(sys._MEIPASS, rel)
                if original_func(meipass_path):
                    return True
            meipass_path = os.path.join(sys._MEIPASS, os.path.basename(path))
            if original_func(meipass_path):
                return True
        return False

    os.path.exists = lambda p: smart_check(p, original_exists)
    os.path.isfile = lambda p: smart_check(p, original_isfile)
    # ----------------------------------------------------

    if len(sys.argv) >= 2 and sys.argv[1].endswith(('.py', '.pyw')):
        script_path = sys.argv[1]
        
        # Если передан абсолютный путь, который начинается с папки программы,
        # преобразуем его в относительный, чтобы найти внутри _MEIPASS
        if os.path.isabs(script_path) and script_path.startswith(exe_dir):
            rel_path = os.path.relpath(script_path, exe_dir)
            full_path = os.path.join(getattr(sys, '_MEIPASS', exe_dir), rel_path)
        else:
            # Иначе просто склеиваем (сработает для относительных путей)
            # или берем только имя файла как запасной вариант
            base_path = getattr(sys, '_MEIPASS', exe_dir)
            full_path = os.path.join(base_path, script_path)
            if not original_exists(full_path) and os.path.isabs(script_path):
                full_path = os.path.join(base_path, os.path.basename(script_path))
                
        if not original_exists(full_path):
            full_path = script_path
            
        sys.argv = [full_path] + sys.argv[2:]
        runpy.run_path(full_path, run_name="__main__")
        sys.exit(0)
    elif len(sys.argv) >= 3 and sys.argv[1] == '-m':
        sys.exit(1)

