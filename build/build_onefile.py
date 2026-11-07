"""
Скрипт сборки One-File релиза ToInet-MAX (единый автономный .exe файл).
Собирает всё (код, бинарники, библиотеки и базы) в один исполняемый файл.
"""

import sys
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_DIR))

from build_all import build_all

if __name__ == "__main__":
    build_all(update_binaries=False, target="one_file")
