import sys
import os

def apply_runtime_patches():
    if not getattr(sys, 'frozen', False):
        return

    import runpy
    import builtins
    import subprocess
    import shutil

    original_exists = os.path.exists
    original_isfile = os.path.isfile
    original_isdir = os.path.isdir
    _orig_open = builtins.open
    _orig_popen = subprocess.Popen
    exe_dir = os.path.dirname(sys.executable)
    meipass = getattr(sys, '_MEIPASS', exe_dir)
    
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
        norm_exe = os.path.normpath(exe_dir)
        candidates = []
        if norm_p.lower().startswith(norm_exe.lower()):
            rel = os.path.relpath(norm_p, norm_exe)
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
            if 'r' in mode_str and not any(m in mode_str for m in ('w', 'a', 'x', '+')):
                resolved = resolve_resource_path(file)
                if original_exists(resolved):
                    file = resolved
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

    # Ensure required working directories exist for One-File mode
    for d in ("data", "logs", "evpn"):
        os.makedirs(os.path.join(exe_dir, d), exist_ok=True)

    # Copy default user data files if not already present beside exe
    default_files = [
        (os.path.join(meipass, "data", "bridges.txt"), os.path.join(exe_dir, "data", "bridges.txt")),
        (os.path.join(meipass, "data", "google_cidrs.json"), os.path.join(exe_dir, "data", "google_cidrs.json")),
        (os.path.join(meipass, "evpn", "subs.txt"), os.path.join(exe_dir, "evpn", "subs.txt")),
        (os.path.join(meipass, "Toinet.ppx"), os.path.join(exe_dir, "Toinet.ppx")),
    ]
    for src, dst in default_files:
        if not original_exists(dst) and original_exists(src):
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            except Exception:
                pass
