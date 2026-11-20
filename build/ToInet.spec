# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\Documents\\ToInet-MAX\\main.pyw'],
    pathex=['D:\\Documents\\ToInet-MAX'],
    binaries=[],
    datas=[('D:\\Documents\\ToInet-MAX\\ui', 'ui'), ('D:\\Documents\\ToInet-MAX\\managers', 'managers'), ('D:\\Documents\\ToInet-MAX\\server', 'server'), ('D:\\Documents\\ToInet-MAX\\evpn', 'evpn'), ('D:\\Documents\\ToInet-MAX\\byedpi', 'byedpi'), ('D:\\Documents\\ToInet-MAX\\icon.ico', '.'), ('D:\\Documents\\ToInet-MAX\\Toinet.ppx', '.')],
    hiddenimports=['requests', 'pythoncom', 'win32com', 'win32com.client', 'psutil', 'cryptography', 'pyperclip', 'socks', 'h2', 'certifi', 'httpx', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'managers.system_utils', 'managers.config_manager', 'managers.bdsher', 'managers.torchok', 'managers.opera_manager', 'managers.vless_manager', 'managers.mode_manager', 'managers.evpn_manager', 'managers.ext_manager', 'managers.ssh_manager', 'managers.dependencies', 'managers.runtime_patch', 'managers.service_controller', 'ui.app_log_window', 'ui.window_ui', 'ui.tray_menu', 'ui.rules_editor', 'ui.autostart_settings', 'ui.byedpi_tester_gui', 'ui.edit_bridges', 'ui.maestro', 'ui.opera_settings', 'ui.ssh_settings', 'managers.tgws_manager', 'ui.tgws_settings', 'ui.zdpi_ml_optimizer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PySide2', 'tkinter', 'Tkinter', 'torch', 'torchvision', 'torchaudio', 'triton', 'scipy', 'sklearn', 'scikit_learn', 'matplotlib', 'pandas', 'numpy', 'polars', 'transformers', 'datasets', 'huggingface_hub', 'safetensors', 'cv2', 'PIL', 'Pillow', 'onnx', 'onnxruntime', 'openvino', 'tensorboard', 'IPython', 'ipykernel', 'jupyter', 'notebook', 'traitlets', 'sympy', 'llvmlite', 'numba', 'cupy', 'jax', 'dask', 'accelerate', 'bitsandbytes', 'pytest', 'unittest', 'unittest.mock'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ToInet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['D:\\Documents\\ToInet-MAX\\icon.ico'],
)
