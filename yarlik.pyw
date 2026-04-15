import os
import sys
import ctypes
from pathlib import Path

def get_desktop_path():
    """Получает путь к рабочему столу текущего пользователя"""
    try:
        # Получаем путь к рабочему столу через Windows API
        CSIDL_DESKTOP = 0x0000
        SHGFP_TYPE_CURRENT = 0
        
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(
            None,
            CSIDL_DESKTOP,
            None,
            SHGFP_TYPE_CURRENT,
            buf
        )
        return buf.value
    except:
        # Fallback на домашнюю директорию
        return os.path.join(os.path.expanduser("~"), "Desktop")

def get_app_directory():
    """Возвращает директорию, где находится приложение"""
    if getattr(sys, 'frozen', False):
        # Если приложение скомпилировано в exe
        return os.path.dirname(sys.executable)
    else:
        # Если запущено как скрипт
        return os.path.dirname(os.path.abspath(__file__))

def create_shortcut():
    """Создает ярлык на рабочем столе"""
    try:
        # Импортируем win32com для создания ярлыков
        import pythoncom
        from win32com.client import Dispatch
        
        desktop_path = get_desktop_path()
        app_dir = get_app_directory()
        app_name = "ToInet-MAX"
        
        # Путь к launch.bat
        bat_path = os.path.join(app_dir, "launch.bat")
        
        # Проверяем, существует ли launch.bat
        if not os.path.exists(bat_path):
            print(f"[Yarlik] Ошибка: Файл launch.bat не найден по пути: {bat_path}")
            return False
        
        # Путь к иконке
        icon_path = os.path.join(app_dir, "icon.ico")
        
        # Путь к ярлыку
        shortcut_path = os.path.join(desktop_path, f"{app_name}.lnk")
        
        # Инициализируем COM
        pythoncom.CoInitialize()
        
        try:
            # Создаем COM объект для ярлыка
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            
            shortcut.Targetpath = bat_path
            shortcut.WorkingDirectory = app_dir
            
            # Устанавливаем иконку, если файл существует
            if os.path.exists(icon_path):
                shortcut.IconLocation = icon_path
            else:
                # Если icon.ico не найден, используем стандартную иконку bat файла
                shortcut.IconLocation = bat_path
            
            shortcut.save()
            
            print(f"[Yarlik] Ярлык создан: {shortcut_path}")
            
        finally:
            pythoncom.CoUninitialize()
        
        return True
        
    except ImportError:
        print("[Yarlik] Ошибка: Не установлен модуль pywin32")
        print("Установите его командой: pip install pywin32")
        return False
    except Exception as e:
        print(f"[Yarlik] Ошибка создания ярлыка: {e}")
        return False

def check_shortcut_exists():
    """Проверяет, существует ли ярлык на рабочем столе"""
    desktop_path = get_desktop_path()
    app_name = "ToInet-MAX"
    shortcut_path = os.path.join(desktop_path, f"{app_name}.lnk")
    return os.path.exists(shortcut_path)

if __name__ == "__main__":
    # Тестовый запуск
    print("=== Yarlik - Создание ярлыка ===")
    print(f"Рабочий стол: {get_desktop_path()}")
    print(f"Директория приложения: {get_app_directory()}")
    print(f"Ярлык существует: {check_shortcut_exists()}")
    

    create_shortcut()