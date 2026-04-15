#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для настройки автозапуска приложения при старте системы
"""

import os
import sys
import winreg
from pathlib import Path

def get_app_path():
    """Получает путь к исполняемому файлу"""
    if getattr(sys, 'frozen', False):
        # Если приложение скомпилировано в exe
        return sys.executable
    else:
        # Если запущено как скрипт - возвращаем путь к launch.bat
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(script_dir, "launch.bat")

def get_app_name():
    """Получает имя приложения"""
    return "ToInet-MAX"

def create_launch_bat():
    """Создает launch.bat файл если его нет"""
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    launch_bat_path = os.path.join(script_dir, "launch.bat")
    
    if not os.path.exists(launch_bat_path):
        try:
            main_pyw_path = os.path.join(script_dir, "main.pyw")
            with open(launch_bat_path, 'w', encoding='utf-8') as f:
                f.write(f'@echo off\n')
                f.write(f'cd /d "{script_dir}"\n')
                f.write(f'start /b pythonw "{main_pyw_path}"\n')
            print(f"[AutoLauncher] Создан файл {launch_bat_path}")
        except Exception as e:
            print(f"[AutoLauncher] Ошибка создания launch.bat: {e}")
    
    return launch_bat_path

def enable_auto_start():
    """Включает автозапуск приложения через launch.bat"""
    try:
        # Создаем launch.bat если его нет
        launch_bat_path = create_launch_bat()
        
        if not os.path.exists(launch_bat_path):
            print(f"[AutoLauncher] Файл {launch_bat_path} не существует")
            return False
        
        app_name = get_app_name()
        
        # Открываем ключ автозапуска
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Добавляем запись с путем к launch.bat
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, launch_bat_path)
        winreg.CloseKey(key)
        
        print(f"[AutoLauncher] Автозапуск включен для {app_name} -> {launch_bat_path}")
        return True
    except Exception as e:
        print(f"[AutoLauncher] Ошибка включения автозапуска: {e}")
        return False

def disable_auto_start():
    """Отключает автозапуск приложения"""
    try:
        app_name = get_app_name()
        
        # Открываем ключ автозапуска
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Удаляем запись
        try:
            winreg.DeleteValue(key, app_name)
        except FileNotFoundError:
            # Запись не найдена - ничего страшного
            pass
        
        winreg.CloseKey(key)
        
        print(f"[AutoLauncher] Автозапуск отключен для {app_name}")
        return True
    except Exception as e:
        print(f"[AutoLauncher] Ошибка отключения автозапуска: {e}")
        return False

def check_auto_start():
    """Проверяет, включен ли автозапуск"""
    try:
        app_name = get_app_name()
        
        # Открываем ключ автозапуска
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        
        # Проверяем наличие записи
        try:
            value, _ = winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            # Проверяем, что значение указывает на launch.bat
            return value.endswith("launch.bat") and os.path.exists(value)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        print(f"[AutoLauncher] Ошибка проверки автозапуска: {e}")
        return False

if __name__ == "__main__":
    # Тестовый запуск
    print("=== Auto Launcher Setuper ===")
    print(f"Приложение: {get_app_name()}")
    print(f"Путь к launch.bat: {get_app_path()}")
    print(f"Автозапуск включен: {check_auto_start()}")
    
    choice = input("\n1. Включить автозапуск\n2. Отключить автозапуск\nВыберите действие (1/2): ")
    if choice == "1":
        enable_auto_start()
    elif choice == "2":
        disable_auto_start()