"""
Скрипт ОБЫЧНОЙ сборки релизов ToInet-MAX (без обновления внешних бинарников).
Быстро упаковывает проект на основе текущих локальных файлов и модулей.
"""

import sys
from pathlib import Path

# Добавляем папку build в sys.path для импорта основного модуля
BUILD_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_DIR))

from build_all import build_all

if __name__ == "__main__":
    build_all(update_binaries=False)
