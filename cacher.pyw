import os
import shutil
from pathlib import Path

def clean_data_directory(data_path="data"):
    if not os.path.exists(data_path):
        print(f"Директория {data_path} не существует!")
        return False
    if not os.path.isdir(data_path):
        print(f"{data_path} не является директорией!")
        return False
    keep_files = {'geoip', 'geoip6'}
    for item in os.listdir(data_path):
        item_path = os.path.join(data_path, item)
        if item in keep_files:continue
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path): os.remove(item_path)
            elif os.path.isdir(item_path):shutil.rmtree(item_path)
        except Exception as e: pass

def main():
    data_path = "data"
    clean_data_directory(data_path)

if __name__ == "__main__":
    main()