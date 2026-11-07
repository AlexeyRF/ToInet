# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.pyw'],
    pathex=[],
    binaries=[],
    datas=[('ui', 'ui'), ('managers', 'managers'), ('small_actions', 'small_actions'), ('server', 'server'), ('evpn', 'evpn'), ('tgws', 'tgws'), ('byedpi', 'byedpi'), ('icon.ico', '.'), ('Toinet.ppx', '.')],
    hiddenimports=['requests', 'pythoncom', 'win32com', 'win32com.client', 'psutil', 'cryptography', 'pyperclip', 'socks', 'h2', 'certifi', 'httpx', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'managers.system_utils', 'managers.config_manager', 'managers.bdsher', 'managers.torchok', 'managers.opera_manager', 'managers.vless_manager', 'managers.mode_manager', 'managers.evpn_manager', 'managers.ext_manager', 'managers.ssh_manager', 'ui.app_log_window', 'ui.window_ui', 'ui.tray_menu', 'ui.rules_editor', 'ui.autostart_settings', 'ui.byedpi_tester_gui', 'ui.edit_bridges', 'ui.maestro', 'ui.opera_settings', 'ui.tgws_tester_gui', 'ui.ssh_settings', 'small_actions.noisy_manager', 'small_actions.tester_manager', 'small_actions.socks5_layer', 'tgws.manager', 'tgws.settings'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    icon=['icon.ico'],
)
