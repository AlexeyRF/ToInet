import os
import zipfile
import glob
import shutil

# Название проекта
PROJECT_NAME = "ToInet-MAX"

# Список расширений и конкретных файлов для включения
EXTENSIONS = ['*.py', '*.pyw', '*.ico', '*.bat']
SPECIFIC_FILES = ['bridges.txt']

def build_release_for_arch(arch_name, exe_name, opera_exe):
    output_zip = f"{PROJECT_NAME}_release_{arch_name}.zip"
    print(f"Сборка релиза {PROJECT_NAME} ({arch_name})...")
    
    # Собираем список всех файлов для включения
    files_to_include = []
    
    # Файлы по расширениям
    for ext in EXTENSIONS:
        files_to_include.extend(glob.glob(ext))
    
    # Конкретные файлы
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
    
    if not files_to_include:
        print("Ошибка: не найдено файлов для включения в релиз!")
        return

    print(f"Найдено файлов для {arch_name}: {len(files_to_include)}")
    
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files_to_include:
                # Помещаем файлы внутрь папки с названием проекта
                arcname = os.path.join(PROJECT_NAME, file)
                zipf.write(file, arcname)
                
        print(f"Релиз успешно создан: {output_zip}\n")
    except Exception as e:
        print(f"Ошибка при создании архива: {e}")

if __name__ == "__main__":
    build_release_for_arch("x64", "bin/client-windows-amd64.exe", "bin/opera-proxy.windows-amd64.exe")
    build_release_for_arch("arm64", "bin/client-windows-arm64.exe", "bin/opera-proxy.windows-arm64.exe")
