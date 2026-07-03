import os
import zipfile
import glob

# Название проекта
PROJECT_NAME = "ToInet-MAX"

# Список расширений и конкретных файлов для включения (основные файлы)
EXTENSIONS = ['*.py', '*.pyw', '*.ico', '*.bat']
SPECIFIC_FILES = ['bridges.txt', "byedpi_tester_priority_sites.txt", "byedpi_tester_sites.txt", "byedpi_tester_strategies.txt"]

# Дополнительные файлы и папки для полной сборки
FULL_RELEASE_FILES = [
    'data/geoip',
    'data/geoip6',
    'byedpi/ciadpi.exe',
    'tor/tor.exe',
    'tor/tor-gencert.exe',
    'tor/pluggable_transports/conjure-client.exe',
    'tor/pluggable_transports/lyrebird.exe',
    'tor/pluggable_transports/pt_config.json'
]

def build_full_release_for_arch(arch_name, exe_name, opera_exe):
    output_zip = f"{PROJECT_NAME}_full_release_{arch_name}.zip"
    print(f"Сборка ПОЛНОГО релиза {PROJECT_NAME} ({arch_name})...")
    
    # Собираем список всех файлов для включения
    files_to_include = []
    
    # 1. Основные файлы по расширениям в корне
    for ext in EXTENSIONS:
        files_to_include.extend(glob.glob(ext))
    
    # 2. Конкретные текстовые файлы в корне
    for filename in SPECIFIC_FILES:
        if os.path.exists(filename):
            files_to_include.append(filename)

    if os.path.exists(exe_name):
        files_to_include.append(exe_name)
    else:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {exe_name} не найден!")
        
    if os.path.exists(opera_exe):
        files_to_include.append(opera_exe)
    else:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {opera_exe} не найден!")
    
    # Исключаем скрипты сборки
    current_script = os.path.basename(__file__)
    files_to_include = [f for f in files_to_include if f != current_script and not f.startswith("build_")]
    
    # Убираем дубликаты
    files_to_include = list(set(files_to_include))
    
    print(f"Найдено базовых файлов: {len(files_to_include)}")
    
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Сначала добавляем базовые файлы
            for file in files_to_include:
                arcname = os.path.join(PROJECT_NAME, file)
                zipf.write(file, arcname)
            
            # Добавляем бинарники и данные с сохранением структуры
            for file_path in FULL_RELEASE_FILES:
                if os.path.exists(file_path):
                    arcname = os.path.join(PROJECT_NAME, file_path)
                    zipf.write(file_path, arcname)
                else:
                    print(f"ПРЕДУПРЕЖДЕНИЕ: Файл не найден: {file_path}")
                
        print(f"Полный релиз успешно создан: {output_zip}\n")
    except Exception as e:
        print(f"Ошибка при создании архива: {e}")

if __name__ == "__main__":
    build_full_release_for_arch("x64", "bin/client-windows-amd64.exe", "bin/opera-proxy.windows-amd64.exe")
    build_full_release_for_arch("arm64", "bin/client-windows-arm64.exe", "bin/opera-proxy.windows-arm64.exe")
