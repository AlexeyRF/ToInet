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
        # [Converter] Disabled by user request
        return False

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
