import sys
import os

def ensure_dependencies():
    if getattr(sys, 'frozen', False):
        return

    required = [
        ('PySide6.QtWidgets', 'PySide6'),
        ('psutil', 'psutil'),
        ('requests', 'requests'),
        ('cryptography', 'cryptography'),
        ('win32com.client', 'pywin32'),
        ('pythoncom', 'pywin32'),
        ('pyperclip', 'pyperclip'),
        ('socks', 'pysocks'),
        ('h2', 'h2'),
        ('certifi', 'certifi'),
        ('httpx', 'httpx'),
    ]

    missing = []
    for mod, pkg in required:
        try:
            __import__(mod)
        except ImportError:
            if pkg not in missing:
                missing.append(pkg)

    if not missing:
        return

    print(f"Missing dependencies found: {', '.join(missing)}")
    print("Starting auto-installation...")

    # Ensure pip is available
    try:
        import pip
    except ImportError:
        try:
            import ensurepip
            ensurepip.bootstrap()
        except Exception:
            pass

    import subprocess
    is_pythonw = sys.executable.lower().endswith("pythonw.exe")
    python_exe = sys.executable[:-5] + ".exe" if is_pythonw else sys.executable
    creationflags = subprocess.CREATE_NEW_CONSOLE if is_pythonw and os.name == 'nt' else 0

    installed = False
    # 1. Attempt standard installation
    try:
        cmd = [python_exe, "-m", "pip", "install"] + missing
        subprocess.check_call(cmd, creationflags=creationflags)
        installed = True
    except Exception as e:
        print(f"Standard install failed ({e}), trying with --user...")
        # 2. Attempt installation with --user
        try:
            cmd = [python_exe, "-m", "pip", "install", "--user"] + missing
            subprocess.check_call(cmd, creationflags=creationflags)
            installed = True
        except Exception as e2:
            print(f"Failed to install dependencies: {e2}")
            err_msg = (
                f"Не удалось автоматически установить модули: {', '.join(missing)}.\n"
                f"Ошибка: {e2}\n\n"
                f"Пожалуйста, выполните в терминале:\n"
                f"pip install {' '.join(missing)}"
            )
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, err_msg, "ToInet-MAX — Ошибка установки зависимостей", 0x10)
            except Exception:
                pass
            sys.exit(1)

    if installed:
        print("Successfully installed dependencies! Restarting application...")
        script = os.path.abspath(sys.argv[0])
        args = [sys.executable, script] + sys.argv[1:]
        try:
            subprocess.Popen(args)
            sys.exit(0)
        except Exception:
            os.execv(sys.executable, args)
