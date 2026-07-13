import os
import sys
import subprocess
import psutil

try:
    # Оставляем импорт для PyInstaller, чтобы он собрал зависимости конвертера (asyncio, argparse и т.д.)
    import proxy_converter
except ImportError:
    pass

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CONVERTER_SCRIPT = os.path.join(CURRENT_DIR, "proxy_converter.py")

class ConverterManager:
    def __init__(self):
        self.process = None

    def start(self):
        if self.process and self.process.poll() is None:
            return True

        if not os.path.exists(CONVERTER_SCRIPT):
            return False

        # Configuration:
        # Opera: SOCKS2HTTP (Listen 1786 -> Upstream 1785)
        # Tor: HTTP2SOCKS (Listen 9854 -> Upstream 9853)
        # ByeDPI: HTTP2SOCKS (Listen 1782 -> Upstream 1780)
        
        args = [
            sys.executable, CONVERTER_SCRIPT,
            "--socks2http", "1786:1785",
            "--http2socks", "9854:9853",
            "--http2socks", "1782:1780"
        ]

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
        print("[Converter] Слой конвертации прокси запущен (SOCKS/HTTP мосты)")
        return True

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None
            print("[Converter] Слой конвертации прокси остановлен")

_manager = ConverterManager()

def get_manager():
    return _manager
