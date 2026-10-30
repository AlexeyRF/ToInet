"""
Скрипт сборки релизов ToInet-MAX С ОБНОВЛЕНИЕМ бинарников.
Перед сборкой проверяет и загружает свежие версии:
  - sing-box (SagerNet/sing-box)
  - opera-proxy (Alexey71/opera-proxy)
  - ByeDPI ciadpi.exe (hufrea/byedpi)
  - Tor Expert Bundle & GeoIP (torproject.org)
Затем компилирует ToInet.exe и собирает оба релизных архива.
"""

import sys
from pathlib import Path

# Добавляем папку build в sys.path для импорта основного модуля
BUILD_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_DIR))

from build_all import build_all

if __name__ == "__main__":
    build_all(update_binaries=True)
