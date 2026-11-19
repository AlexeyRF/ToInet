import sys
import os

def apply_runtime_patches():
    if not getattr(sys, 'frozen', False):
        return

    import runpy
    import builtins
    import subprocess
    import shutil

    # Патчим QTextCursor для совместимости с .End на экземпляре (например, text_edit.textCursor().End) в PySide6
    try:
        from PySide6.QtGui import QTextCursor
        _orig_tc_getattr = getattr(QTextCursor, '__getattr__', None)
        def _tc_getattr(self, name):
            if hasattr(type(self), name):
                return getattr(type(self), name)
            if _orig_tc_getattr:
                return _orig_tc_getattr(self, name)
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        QTextCursor.__getattr__ = _tc_getattr
        if not hasattr(QTextCursor, 'End'):
            setattr(QTextCursor, 'End', QTextCursor.MoveOperation.End)
    except Exception:
        pass

    original_exists = os.path.exists
    original_isfile = os.path.isfile
    original_isdir = os.path.isdir
    _orig_open = builtins.open
    _orig_popen = subprocess.Popen
    exe_dir = os.path.dirname(sys.executable)
    meipass = getattr(sys, '_MEIPASS', exe_dir)

    from managers.system_utils import is_onefile_mode, get_appdata_dir

    onefile = is_onefile_mode()
    if onefile:
        storage_dir = get_appdata_dir()
        os.environ["TOINET_ONEFILE"] = "1"
        os.environ["TOINET_BASE_DIR"] = storage_dir
        try:
            os.chdir(storage_dir)
        except Exception:
            pass
    else:
        storage_dir = exe_dir

    def resolve_resource_path(path):
        if not path or not isinstance(path, (str, bytes, os.PathLike)):
            return path
        try:
            path_str = os.fspath(path) if isinstance(path, os.PathLike) else str(path)
        except Exception:
            return path
        if original_exists(path_str):
            return path_str
        norm_p = os.path.normpath(path_str)
        candidates = []

        # 1. Если путь внутри storage_dir (APPDATA в One-File режиме)
        norm_storage = os.path.normpath(storage_dir)
        if norm_p.lower().startswith(norm_storage.lower()):
            rel = os.path.relpath(norm_p, norm_storage)
            candidates.append(os.path.join(meipass, rel))

        # 2. Если путь внутри exe_dir
        norm_exe = os.path.normpath(exe_dir)
        if norm_p.lower().startswith(norm_exe.lower()):
            rel = os.path.relpath(norm_p, norm_exe)
            if onefile and storage_dir != exe_dir:
                candidates.append(os.path.join(storage_dir, rel))
            candidates.append(os.path.join(meipass, rel))

        candidates.append(os.path.join(meipass, norm_p))
        candidates.append(os.path.join(meipass, os.path.basename(path_str)))
        for cand in candidates:
            if original_exists(cand):
                return cand
        return path_str

    def smart_check(path, original_func):
        if original_func(path):
            return True
        resolved = resolve_resource_path(path)
        return original_func(resolved)

    os.path.exists = lambda p: smart_check(p, original_exists)
    os.path.isfile = lambda p: smart_check(p, original_isfile)
    os.path.isdir = lambda p: smart_check(p, original_isdir)

    def smart_open(file, mode='r', *args, **kwargs):
        if isinstance(file, (str, bytes, os.PathLike)):
            mode_str = str(mode)
            try:
                file_str = os.fspath(file) if isinstance(file, os.PathLike) else str(file)
            except Exception:
                file_str = str(file)

            if 'r' in mode_str and not any(m in mode_str for m in ('w', 'a', 'x', '+')):
                resolved = resolve_resource_path(file)
                if original_exists(resolved):
                    file = resolved
            else:
                # Режим записи: в One-File режиме перенаправляем в storage_dir (APPDATA)
                if onefile and storage_dir != exe_dir:
                    norm_f = os.path.normpath(file_str)
                    norm_exe = os.path.normpath(exe_dir)
                    if norm_f.lower().startswith(norm_exe.lower()):
                        rel = os.path.relpath(norm_f, norm_exe)
                        file = os.path.join(storage_dir, rel)
                    elif not os.path.isabs(file_str):
                        file = os.path.join(storage_dir, file_str)
                # Автоматически создаем родительские папки при записи
                try:
                    pdir = os.path.dirname(os.fspath(file) if isinstance(file, os.PathLike) else str(file))
                    if pdir and not original_exists(pdir):
                        os.makedirs(pdir, exist_ok=True)
                except Exception:
                    pass
        return _orig_open(file, mode, *args, **kwargs)

    builtins.open = smart_open

    def smart_popen(cmd, *pargs, **kwargs):
        if isinstance(cmd, list) and cmd:
            new_cmd = list(cmd)
            if isinstance(new_cmd[0], (str, bytes, os.PathLike)):
                resolved = resolve_resource_path(new_cmd[0])
                if original_exists(resolved):
                    new_cmd[0] = resolved
            cmd = new_cmd
        elif isinstance(cmd, (str, bytes, os.PathLike)):
            resolved = resolve_resource_path(cmd)
            if original_exists(resolved):
                cmd = resolved
        if onefile:
            cwd = kwargs.get('cwd')
            if cwd is None or cwd == exe_dir or (isinstance(cwd, str) and os.path.normpath(cwd).lower() == os.path.normpath(exe_dir).lower()):
                kwargs['cwd'] = storage_dir
        return _orig_popen(cmd, *pargs, **kwargs)

    subprocess.Popen = smart_popen

    if len(sys.argv) >= 2 and sys.argv[1].endswith(('.py', '.pyw')):
        script_path = sys.argv[1]
        
        # If absolute path begins with exe folder, convert to relative to find in _MEIPASS
        norm_script = os.path.normcase(os.path.normpath(script_path))
        norm_exe = os.path.normcase(os.path.normpath(exe_dir))
        base_path = getattr(sys, '_MEIPASS', exe_dir)
        if os.path.isabs(script_path) and norm_script.startswith(norm_exe):
            rel_path = os.path.relpath(script_path, exe_dir)
            full_path = os.path.join(base_path, rel_path)
        else:
            full_path = os.path.join(base_path, os.path.normpath(script_path))
            if not original_exists(full_path):
                full_path = os.path.join(base_path, os.path.basename(script_path))
                
        if not original_exists(full_path):
            full_path = script_path
            
        sys.argv = [full_path] + sys.argv[2:]
        runpy.run_path(full_path, run_name="__main__")
        sys.exit(0)
    elif len(sys.argv) >= 3 and sys.argv[1] == '-m':
        sys.exit(1)

    # Ensure required working directories exist for storage_dir (AppData in onefile mode)
    for d in ("data", "logs", "evpn", "byedpi", "tor", "bin"):
        os.makedirs(os.path.join(storage_dir, d), exist_ok=True)

    # In One-File mode, extract all bundled directories (tor, bin, byedpi, data, evpn) from sys._MEIPASS into storage_dir (AppData)
    if onefile:
        user_config_names = {"config.json", "tor_config.json", "subs.txt", "Toinet.ppx"}
        for folder in ("tor", "bin", "byedpi", "data", "evpn"):
            src_folder = os.path.join(meipass, folder)
            dst_folder = os.path.join(storage_dir, folder)
            if original_exists(src_folder):
                for root, _, files in os.walk(src_folder):
                    rel = os.path.relpath(root, src_folder)
                    target_dir = os.path.join(dst_folder, rel) if rel != "." else dst_folder
                    os.makedirs(target_dir, exist_ok=True)
                    for f in files:
                        src_f = os.path.join(root, f)
                        dst_f = os.path.join(target_dir, f)
                        # Do not overwrite existing user configs
                        if f in user_config_names and original_exists(dst_f):
                            continue
                        if not original_exists(dst_f) or os.path.getsize(dst_f) != os.path.getsize(src_f):
                            try:
                                shutil.copy2(src_f, dst_f)
                            except Exception:
                                pass

    # Copy default user data files if not already present in storage_dir
    default_files = [
        (os.path.join(meipass, "data", "bridges.txt"), os.path.join(storage_dir, "data", "bridges.txt")),
        (os.path.join(meipass, "data", "google_cidrs.json"), os.path.join(storage_dir, "data", "google_cidrs.json")),
        (os.path.join(meipass, "data", "banned_domains.txt"), os.path.join(storage_dir, "data", "banned_domains.txt")),
        (os.path.join(meipass, "data", "telegram.jpg"), os.path.join(storage_dir, "data", "telegram.jpg")),
        (os.path.join(meipass, "data", "telegram.png"), os.path.join(storage_dir, "data", "telegram.png")),
        (os.path.join(meipass, "evpn", "subs.txt"), os.path.join(storage_dir, "evpn", "subs.txt")),
        (os.path.join(meipass, "Toinet.ppx"), os.path.join(storage_dir, "Toinet.ppx")),
        (os.path.join(meipass, "icon.ico"), os.path.join(storage_dir, "icon.ico")),
        (os.path.join(meipass, "README.md"), os.path.join(storage_dir, "README.md")),
    ]
    # Also copy byedpi tester priority sites and strategies if bundled
    for bf in ("byedpi_tester_priority_sites.txt", "byedpi_tester_sites.txt", "byedpi_tester_strategies.txt"):
        src = os.path.join(meipass, "byedpi", bf)
        if not original_exists(src):
            src = os.path.join(meipass, "ui", bf)
        if original_exists(src):
            default_files.append((src, os.path.join(storage_dir, "byedpi", bf)))
            default_files.append((src, os.path.join(storage_dir, bf)))

    for src, dst in default_files:
        if not original_exists(dst) and original_exists(src):
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            except Exception:
                pass

    # If running in onefile mode, and user previously had configs next to exe, migrate them to AppData
    if onefile and exe_dir != storage_dir:
        migration_files = [
            (os.path.join(exe_dir, "data", "config.json"), os.path.join(storage_dir, "data", "config.json")),
            (os.path.join(exe_dir, "data", "tor_config.json"), os.path.join(storage_dir, "data", "tor_config.json")),
            (os.path.join(exe_dir, "data", "bridges.txt"), os.path.join(storage_dir, "data", "bridges.txt")),
            (os.path.join(exe_dir, "data", "banned_domains.txt"), os.path.join(storage_dir, "data", "banned_domains.txt")),
            (os.path.join(exe_dir, "evpn", "subs.txt"), os.path.join(storage_dir, "evpn", "subs.txt")),
            (os.path.join(exe_dir, "Toinet.ppx"), os.path.join(storage_dir, "Toinet.ppx")),
        ]
        for src, dst in migration_files:
            if original_exists(src) and not original_exists(dst):
                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                except Exception:
                    pass
