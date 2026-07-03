import os
import subprocess
import sys
import shutil

def build():
    print("Начинаем сборку ToInet в EXE...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "ToInet",
        "--onefile", # Упаковать все в 1 EXE файл (без папки _internal)
        "--windowed", # Без консольного окна
        "--icon", "icon.ico",
        "--noconfirm", # Перезаписывать старые сборки
    ]
    
    # Так как мы используем --onefile и переопределили CURRENT_DIR на папку с EXE,
    # бинарники (tor, byedpi, bin) и конфиги НЕ нужно упаковывать внутрь EXE.
    # Их нужно будет просто положить рядом с ToInet.exe при дистрибуции.
    # Но нам нужно упаковать скрытые python-скрипты, которые вызываются через runpy.
    datas = [
        ("*.py", "."),
        ("*.pyw", "."),
        ("tgws/*.py", "tgws"),
        ("tgws/*.pyw", "tgws"),
        ("icon.ico", ".") # Иконка нужна для GUI (её можно будет загружать из _MEIPASS)
    ]
    
    sep = ";" if os.name == "nt" else ":"
    for src, dst in datas:
        cmd.extend(["--add-data", f"{src}{sep}{dst}"])
        
    cmd.append("main.pyw")
    
    try:
        subprocess.check_call(cmd)
        print("\nСборка успешно завершена! Исполняемый файл находится в папке dist/ToInet")
    except subprocess.CalledProcessError as e:
        print(f"\nОшибка при сборке: {e}")

if __name__ == "__main__":
    # Проверяем наличие pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("Устанавливаем PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    build()
