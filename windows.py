from __future__ import annotations

import lang
import ctypes
import json
import logging
import os
import psutil
import sys
import threading
import time
import webbrowser
import pystray
import pyperclip
import asyncio as _asyncio

from pathlib import Path
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont

from tgws import tg_ws_proxy, config as tgws_config


APP_NAME = "TgWsProxy"
APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "proxy.log"
FIRST_RUN_MARKER = APP_DIR / ".first_run_done"


DEFAULT_CONFIG = {
    "port": 1480,
    "host": "127.0.0.1",
    "dc_ip": ["2:149.154.167.220", "4:149.154.167.220"],
    "verbose": False,
}


_proxy_thread: Optional[threading.Thread] = None
_async_stop: Optional[object] = None
_tray_icon: Optional[object] = None
_config: dict = {}
_exiting: bool = False

log = logging.getLogger("tg-ws-tray")


def _acquire_lock() -> bool:
    _ensure_dirs()
    lock_files = list(APP_DIR.glob("*.lock"))
        
    for f in lock_files:
        try:
            pid = int(f.stem)
            if psutil.pid_exists(pid):
                try:
                    psutil.Process(pid).status()
                    return False
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

        f.unlink(missing_ok=True)

    lock_file = APP_DIR / f"{os.getpid()}.lock"
    lock_file.touch()
    return True


def _ensure_dirs():
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    _ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except Exception as exc:
            log.warning("Failed to load config: %s", exc)
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    _ensure_dirs()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def setup_logging(verbose: bool = False):
    _ensure_dirs()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-5s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))
    root.addHandler(fh)

    if not getattr(sys, "frozen", False):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG if verbose else logging.INFO)
        ch.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-5s  %(message)s",
            datefmt="%H:%M:%S"))
        root.addHandler(ch)


def _make_icon_image(size: int = 64):
    if Image is None:
        raise RuntimeError("Pillow is required for tray icon")
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    margin = 2
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill=(0, 136, 204, 255))
                 
    try:
        font = ImageFont.truetype("arial.ttf", size=int(size * 0.55))
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "T", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), "T", fill=(255, 255, 255, 255), font=font)

    return img


def _load_icon():
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists() and Image:
        try:
            return Image.open(str(icon_path))
        except Exception:
            pass
    return _make_icon_image()



def _run_proxy_thread(port: int, dc_opt: Dict[int, str], verbose: bool,
                      host: str = '127.0.0.1'):
    global _async_stop
    loop = _asyncio.new_event_loop()
    _asyncio.set_event_loop(loop)
    stop_ev = _asyncio.Event()
    _async_stop = (loop, stop_ev)
    
    try:
        tgws_config.proxy_config.port = port
        tgws_config.proxy_config.host = host
        tgws_config.proxy_config.dc_redirects = dc_opt
        loop.run_until_complete(
            tg_ws_proxy._run(stop_event=stop_ev))
    except Exception as exc:
        log.error("Proxy thread crashed: %s", exc)
        if "10048" in str(exc) or "Address already in use" in str(exc):
            _show_error("Не удалось запустить прокси:\nПорт уже используется другим приложением.\n\nЗакройте приложение, использующее этот порт, или измените порт в настройках прокси и перезапустите.")
    finally:
        loop.close()
        _async_stop = None


def start_proxy():
    global _proxy_thread, _config
    if _proxy_thread and _proxy_thread.is_alive():
        log.info("Proxy already running")
        return

    cfg = _config
    port = cfg.get("port", DEFAULT_CONFIG["port"])
    host = cfg.get("host", DEFAULT_CONFIG["host"])
    dc_ip_list = cfg.get("dc_ip", DEFAULT_CONFIG["dc_ip"])
    verbose = cfg.get("verbose", False)

    try:
        dc_opt = tgws_config.parse_dc_ip_list(dc_ip_list)
    except ValueError as e:
        log.error("Bad config dc_ip: %s", e)
        _show_error(f"Ошибка конфигурации:\n{e}")
        return

    log.info("Starting proxy on %s:%d ...", host, port)
    _proxy_thread = threading.Thread(
        target=_run_proxy_thread,
        args=(port, dc_opt, verbose, host),
        daemon=True, name="proxy")
    _proxy_thread.start()


def stop_proxy():
    global _proxy_thread, _async_stop
    if _async_stop:
        loop, stop_ev = _async_stop
        loop.call_soon_threadsafe(stop_ev.set)
        if _proxy_thread:
            _proxy_thread.join(timeout=2)
    _proxy_thread = None
    log.info("Proxy stopped")


def restart_proxy():
    log.info("Restarting proxy...")
    stop_proxy()
    time.sleep(0.3)
    start_proxy()


def _show_error(text: str, title: str = "TG WS Proxy — Ошибка"):
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)


def _show_info(text: str, title: str = "TG WS Proxy"):
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)


def _on_open_in_telegram(icon=None, item=None):
    host = _config.get("host", DEFAULT_CONFIG["host"])
    port = _config.get("port", DEFAULT_CONFIG["port"])
    url = f"tg://socks?server={host}&port={port}"
    log.info("Opening %s", url)
    try:
        result = webbrowser.open(url)
        if not result:
            raise RuntimeError("webbrowser.open returned False")
    except Exception:
        log.info("Browser open failed, copying to clipboard")
        try:
            pyperclip.copy(url)
            _show_info(
                f"Не удалось открыть Telegram автоматически.\n\n"
                f"Ссылка скопирована в буфер обмена, отправьте её в телеграмм и нажмите по ней ЛКМ:\n{url}",
                "TG WS Proxy")
        except Exception as exc:
            log.error("Clipboard copy failed: %s", exc)
            _show_error(f"Не удалось скопировать ссылку:\n{exc}")


def _on_restart(icon=None, item=None):
    threading.Thread(target=restart_proxy, daemon=True).start()


def _on_edit_config(icon=None, item=None):
    threading.Thread(target=_edit_config_dialog, daemon=True).start()


def _edit_config_dialog():
    try:
        from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QCheckBox, QPushButton, QMessageBox
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QColor, QPalette
    except ImportError:
        _show_error("PyQt5 не установлен.")
        return

    cfg = dict(_config)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowTitle("TG WS Proxy — Настройки")
    dialog.setFixedSize(420, 480)
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)

    TG_BLUE = "#3390ec"
    TG_BLUE_HOVER = "#2b7cd4"
    BG = "#ffffff"
    FIELD_BG = "#f0f2f5"
    FIELD_BORDER = "#d6d9dc"
    TEXT_PRIMARY = "#000000"
    TEXT_SECONDARY = "#707579"
    FONT_FAMILY = "Segoe UI"

    palette = dialog.palette()
    palette.setColor(QPalette.Window, QColor(BG))
    dialog.setPalette(palette)
    dialog.setAutoFillBackground(True)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(12)

    font_normal = QFont(FONT_FAMILY, 10)
    font_small = QFont(FONT_FAMILY, 9)
    font_bold = QFont(FONT_FAMILY, 10, QFont.Bold)

    def create_label(text, font, color=TEXT_PRIMARY):
        lbl = QLabel(text)
        lbl.setFont(font)
        lbl.setStyleSheet(f"color: {color};")
        return lbl

    layout.addWidget(create_label("IP-адрес прокси", font_normal))
    host_entry = QLineEdit(cfg.get("host", "127.0.0.1"))
    host_entry.setFont(font_normal)
    host_entry.setStyleSheet(f"background-color: {FIELD_BG}; border: 1px solid {FIELD_BORDER}; border-radius: 5px; padding: 5px; color: {TEXT_PRIMARY};")
    layout.addWidget(host_entry)

    layout.addWidget(create_label("Порт прокси", font_normal))
    port_entry = QLineEdit(str(cfg.get("port", 1480)))
    port_entry.setFont(font_normal)
    port_entry.setStyleSheet(f"background-color: {FIELD_BG}; border: 1px solid {FIELD_BORDER}; border-radius: 5px; padding: 5px; color: {TEXT_PRIMARY};")
    port_entry.setFixedWidth(120)
    layout.addWidget(port_entry)

    layout.addWidget(create_label("DC → IP маппинги (по одному на строку, формат DC:IP)", font_normal))
    dc_textbox = QTextEdit()
    dc_textbox.setFont(QFont("Consolas", 10))
    dc_textbox.setStyleSheet(f"background-color: {FIELD_BG}; border: 1px solid {FIELD_BORDER}; border-radius: 5px; padding: 5px; color: {TEXT_PRIMARY};")
    dc_textbox.setFixedHeight(120)
    dc_textbox.setPlainText("\n".join(cfg.get("dc_ip", DEFAULT_CONFIG["dc_ip"])))
    layout.addWidget(dc_textbox)

    verbose_var = QCheckBox("Подробное логирование (verbose)")
    verbose_var.setFont(font_normal)
    verbose_var.setStyleSheet(f"color: {TEXT_PRIMARY};")
    verbose_var.setChecked(cfg.get("verbose", False))
    layout.addWidget(verbose_var)

    layout.addWidget(create_label("Изменения вступят в силу после перезапуска прокси.", font_small, TEXT_SECONDARY))
    
    layout.addStretch()

    btn_layout = QHBoxLayout()
    
    btn_save = QPushButton(T("Сохранить", "Save") if 'T' in globals() else "Сохранить")
    btn_save.setFont(font_bold)
    btn_save.setFixedSize(140, 38)
    btn_save.setStyleSheet(f"QPushButton {{ background-color: {TG_BLUE}; color: white; border-radius: 5px; }} QPushButton:hover {{ background-color: {TG_BLUE_HOVER}; }}")
    
    btn_cancel = QPushButton(T("Отмена", "Cancel") if 'T' in globals() else "Отмена")
    btn_cancel.setFont(font_normal)
    btn_cancel.setFixedSize(140, 38)
    btn_cancel.setStyleSheet(f"QPushButton {{ background-color: {FIELD_BG}; color: {TEXT_PRIMARY}; border: 1px solid {FIELD_BORDER}; border-radius: 5px; }} QPushButton:hover {{ border: 1px solid #b0b0b0; }}")

    btn_layout.addWidget(btn_save)
    btn_layout.addWidget(btn_cancel)
    btn_layout.addStretch()
    
    layout.addLayout(btn_layout)

    def on_save():
        import socket as _sock
        host_val = host_entry.text().strip()
        try:
            _sock.inet_aton(host_val)
        except OSError:
            _show_error("Некорректный IP-адрес.")
            return

        try:
            port_val = int(port_entry.text().strip())
            if not (1 <= port_val <= 65535):
                raise ValueError
        except ValueError:
            _show_error("Порт должен быть числом 1-65535")
            return

        lines = [l.strip() for l in dc_textbox.toPlainText().strip().splitlines() if l.strip()]
        try:
            tgws_config.parse_dc_ip_list(lines)
        except ValueError as e:
            _show_error(str(e))
            return

        new_cfg = {
            "host": host_val,
            "port": port_val,
            "dc_ip": lines,
            "verbose": verbose_var.isChecked(),
        }
        save_config(new_cfg)
        _config.update(new_cfg)
        log.info("Config saved: %s", new_cfg)

        _tray_icon.menu = _build_menu()

        reply = QMessageBox.question(dialog, "Перезапустить?", 
                                     "Настройки сохранены.\n\nПерезапустить прокси сейчас?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            dialog.accept()
            restart_proxy()
        else:
            dialog.accept()

    btn_save.clicked.connect(on_save)
    btn_cancel.clicked.connect(dialog.reject)

    dialog.exec_()


def _on_open_logs(icon=None, item=None):
    log.info("Opening log file: %s", LOG_FILE)
    if LOG_FILE.exists():
        os.startfile(str(LOG_FILE))
    else:
        _show_info("Файл логов ещё не создан.", "TG WS Proxy")


def _on_exit(icon=None, item=None):
    global _exiting
    if _exiting:
        os._exit(0)
        return
    _exiting = True
    log.info("User requested exit")

    def _force_exit():
        time.sleep(3)
        os._exit(0)
    threading.Thread(target=_force_exit, daemon=True, name="force-exit").start()

    if icon:
        icon.stop()



def _show_first_run():
    _ensure_dirs()
    if FIRST_RUN_MARKER.exists():
        return

    host = _config.get("host", DEFAULT_CONFIG["host"])
    port = _config.get("port", DEFAULT_CONFIG["port"])
    tg_url = f"tg://socks?server={host}&port={port}"

    try:
        from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QFrame
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QColor, QPalette
    except ImportError:
        FIRST_RUN_MARKER.touch()
        return

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowTitle("TG WS Proxy")
    dialog.setFixedSize(520, 440)
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)

    TG_BLUE = "#3390ec"
    TG_BLUE_HOVER = "#2b7cd4"
    BG = "#ffffff"
    FIELD_BG = "#f0f2f5"
    FIELD_BORDER = "#d6d9dc"
    TEXT_PRIMARY = "#000000"
    TEXT_SECONDARY = "#707579"
    FONT_FAMILY = "Segoe UI"

    palette = dialog.palette()
    palette.setColor(QPalette.Window, QColor(BG))
    dialog.setPalette(palette)
    dialog.setAutoFillBackground(True)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.setSpacing(1)

    title_layout = QHBoxLayout()
    title_layout.setContentsMargins(0, 0, 0, 16)
    
    accent_bar = QFrame()
    accent_bar.setFixedSize(4, 32)
    accent_bar.setStyleSheet(f"background-color: {TG_BLUE}; border-radius: 2px;")
    title_layout.addWidget(accent_bar)
    
    title_lbl = QLabel("Прокси запущен и работает в системном трее")
    title_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
    title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; margin-left: 12px;")
    title_layout.addWidget(title_lbl)
    title_layout.addStretch()
    
    layout.addLayout(title_layout)

    sections = [
        ("Как подключить Telegram Desktop:", True),
        ("  Автоматически:", True),
        (f"  ПКМ по иконке в трее → «Открыть в Telegram»", False),
        (f"  Или ссылка: {tg_url}", False),
        ("\n  Вручную:", True),
        ("  Настройки → Продвинутые → Тип подключения → Прокси", False),
        (f"  SOCKS5 → {host} : {port} (без логина/пароля)", False),
    ]

    for text, bold in sections:
        lbl = QLabel(text)
        font = QFont(FONT_FAMILY, 10)
        if bold:
            font.setBold(True)
        lbl.setFont(font)
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(lbl)

    layout.addSpacing(16)

    separator = QFrame()
    separator.setFixedHeight(1)
    separator.setStyleSheet(f"background-color: {FIELD_BORDER};")
    layout.addWidget(separator)
    
    layout.addSpacing(12)

    auto_var = QCheckBox("Открыть прокси в Telegram сейчас")
    auto_var.setFont(QFont(FONT_FAMILY, 10))
    auto_var.setStyleSheet(f"color: {TEXT_PRIMARY};")
    auto_var.setChecked(True)
    layout.addWidget(auto_var)
    
    layout.addSpacing(16)
    
    def on_ok():
        FIRST_RUN_MARKER.touch()
        open_tg = auto_var.isChecked()
        dialog.accept()
        if open_tg:
            _on_open_in_telegram()

    btn_layout = QHBoxLayout()
    btn_ok = QPushButton("Начать")
    btn_ok.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
    btn_ok.setFixedSize(180, 42)
    btn_ok.setStyleSheet(f"QPushButton {{ background-color: {TG_BLUE}; color: white; border-radius: 5px; }} QPushButton:hover {{ background-color: {TG_BLUE_HOVER}; }}")
    btn_ok.clicked.connect(on_ok)
    
    btn_layout.addStretch()
    btn_layout.addWidget(btn_ok)
    btn_layout.addStretch()
    
    layout.addLayout(btn_layout)

    dialog.finished.connect(lambda: FIRST_RUN_MARKER.touch())
    dialog.exec_()


def _build_menu():
    if pystray is None:
        return None
    host = _config.get("host", DEFAULT_CONFIG["host"])
    port = _config.get("port", DEFAULT_CONFIG["port"])
    return pystray.Menu(
        pystray.MenuItem(
            f"Открыть в Telegram ({host}:{port})",
            _on_open_in_telegram,
            default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Перезапустить прокси", _on_restart),
        pystray.MenuItem("Настройки...", _on_edit_config),
        pystray.MenuItem("Открыть логи", _on_open_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(T("Выход", "Exit"), _on_exit),
    )


def run_tray():
    global _tray_icon, _config

    _config = load_config()
    save_config(_config)

    if LOG_FILE.exists():
        try:
            LOG_FILE.unlink()
        except Exception:
            pass

    setup_logging(_config.get("verbose", False))
    log.info("TG WS Proxy tray app starting")
    log.info("Config: %s", _config)
    log.info("Log file: %s", LOG_FILE)

    if pystray is None or Image is None:
        log.error("pystray or Pillow not installed; "
                  "running in console mode")
        start_proxy()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_proxy()
        return

    start_proxy()

    _show_first_run()

    icon_image = _load_icon()
    _tray_icon = pystray.Icon(
        APP_NAME,
        icon_image,
        "TG WS Proxy",
        menu=_build_menu())

    log.info("Tray icon running")
    _tray_icon.run()

    stop_proxy()
    log.info("Tray app exited")


def main():
    if not _acquire_lock():
        _show_info("Приложение уже запущено.", os.path.basename(sys.argv[0]))
        return

    run_tray()


if __name__ == "__main__":
    main()
