#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import ctypes
import re

def set_proxy(port):
    """Включение прокси на указанном порту"""
    proxy_server = f"socks=127.0.0.1:{port}"
    
    # Включение прокси и установка адреса
    os.system(f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f')
    os.system(f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyServer /t REG_SZ /d "{proxy_server}" /f')
    
    print(f"✅ Прокси включен: {proxy_server}")
    
    # Уведомление системы об изменениях
    refresh_internet_settings()

def disable_proxy():
    """Отключение прокси и удаление настроек"""
    # Отключение прокси
    os.system('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f')
    
    # Удаление строки сервера (игнорируем ошибку, если ключа нет)
    os.system('reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyServer /f 2>nul')
    
    print("✅ Прокси отключен, настройки удалены")
    
    # Уведомление системы об изменениях
    refresh_internet_settings()

def refresh_internet_settings():
    """Обновление настроек интернета в системе"""
    INTERNET_OPTION_SETTINGS_CHANGED = 39
    INTERNET_OPTION_REFRESH = 37
    
    internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
    internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
    internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)

def show_usage():
    """Показать справку по использованию"""
    print("Использование: python cpller.pyw port flag")
    print("  port - номер порта (например 9853)")
    print("  flag - 1 для включения прокси, 0 для отключения")
    print("\nПримеры:")
    print("  python cpller.pyw 9853 1  # Включить прокси на порту 9853")
    print("  python cpller.pyw 9853 0  # Отключить прокси")

def validate_port(port):
    """Проверка корректности порта"""
    try:
        port_num = int(port)
        if 1 <= port_num <= 65535:
            return True
        else:
            print("❌ Ошибка: порт должен быть от 1 до 65535")
            return False
    except ValueError:
        print("❌ Ошибка: порт должен быть числом")
        return False

def validate_flag(flag):
    """Проверка корректности флага"""
    if flag in ['0', '1']:
        return True
    else:
        print("❌ Ошибка: флаг должен быть 0 или 1")
        return False

def main():
    # Проверка аргументов командной строки
    if len(sys.argv) != 3:
        print("❌ Ошибка: неверное количество аргументов")
        show_usage()
        sys.exit(1)
    
    port = sys.argv[1]
    flag = sys.argv[2]
    
    # Валидация аргументов
    if not validate_port(port):
        sys.exit(1)
    
    if not validate_flag(flag):
        sys.exit(1)
    
    # Выполнение соответствующего действия
    if flag == '1':
        set_proxy(port)
    else:  # flag == '0'
        disable_proxy()
    
    print("\n✨ Настройки прокси успешно применены!")

if __name__ == "__main__":
    # Проверка, что скрипт запущен с правами администратора (рекомендуется, но не обязательно)
    try:
        main()
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
        sys.exit(1)