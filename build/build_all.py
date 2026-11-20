"""
Скрипт сборки релизов ToInet-MAX.

Поддерживает режимы:
  1. Обычная сборка (из имеющихся в репозитории файлов и бинарников).
  2. Сборка с обновлением (предварительная загрузка свежих версий sing-box, opera-proxy, byedpi, Tor).

Типы релизов (сохраняются в директорию build/releases/):
  - ToInet-MAX-python_amd64.zip     (Python-версия)
  - ToInet-MAX-portable_amd64.zip   (Portable-версия в папке)
  - ToInet-MAX-one_file_amd64.exe   (One-File версия: единый exe-файл)
"""

import os
import sys
import glob
import json
import shutil
import tarfile
import zipfile
import subprocess
import urllib.request
import re
import argparse
from pathlib import Path

PROJECT_NAME = "ToInet-MAX"
BASE_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = Path(__file__).resolve().parent

RELEASES_DIR = BUILD_DIR / "releases"
WORK_DIR = BUILD_DIR / "work"
WORK_ONEFILE_DIR = BUILD_DIR / "work_onefile"
DIST_DIR = BUILD_DIR / "dist"
DIST_ONEFILE_DIR = BUILD_DIR / "dist_onefile"
TEMP_DIR = BUILD_DIR / "temp"

os.chdir(str(BASE_DIR))

# Файлы и папки, исключаемые из архивов
EXCLUDE_DIRS = {"__pycache__", ".git", ".dev", ".vscode", ".idea",
                "build", "dist", "releases",
                "pyinstaller_build", "pyinstaller_build_onefile",
                "pyinstaller_dist_onefile"}
EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".log", ".tmp"}
EXCLUDE_DATA_FILES = {"cached-certs", "cached-descriptors", "cached-descriptors.new",
                      "cached-microdesc-consensus", "cached-microdescs", "cached-microdescs.new",
                      "lock", "state", "torrc", "keys", "pt_state"}
EXCLUDE_EVPN_FILES = {"subs_cache.json", "working_nodes.json", "evpn_config.json",
                      "vless_state.json", "blacklist.json", "evpn.log"}

# Модули, исключаемые из сборщика PyInstaller
# Исключение тяжелых ML / Data Science пакетов (torch, scipy, sklearn, transformers и т.д.)
# предотвращает раздувание EXE на 2.5-3 ГБ.
# Модуль zDPI ML использует встроенный чистый Python-движок (KNN + генетический синтез).
EXCLUDE_MODULES = [
    # Неиспользуемые GUI библиотеки
    "PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
    "PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
    "PySide2", "tkinter", "Tkinter",
    # Тяжелые ML / Deep Learning / Scientific пакеты
    "torch", "torchvision", "torchaudio", "triton",
    "scipy", "sklearn", "scikit_learn",
    "matplotlib", "pandas", "numpy", "polars",
    "transformers", "datasets", "huggingface_hub", "safetensors",
    "cv2", "PIL", "Pillow",
    "onnx", "onnxruntime", "openvino", "tensorboard",
    "IPython", "ipykernel", "jupyter", "notebook", "traitlets",
    "sympy", "llvmlite", "numba", "cupy", "jax", "dask",
    "accelerate", "bitsandbytes",
    "pytest", "unittest", "unittest.mock"
]


def download_file(url, output_path, timeout=60):
    """Скачивает файл с заголовком User-Agent"""
    print(f"  -> Скачивание: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=timeout) as response, open(output_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print(f"  -> Сохранено: {output_path}")


def update_singbox():
    """Обновление sing-box из официального репозитория SagerNet/sing-box"""
    print("\n[1/4] Проверка обновления sing-box...")
    try:
        req = urllib.request.Request("https://api.github.com/repos/SagerNet/sing-box/releases/latest",
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        target_asset = None
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if 'windows-amd64.zip' in name and 'legacy' not in name:
                target_asset = asset
                break
                
        if not target_asset:
            print("  [!] Не найден подходящий ассет sing-box windows-amd64.")
            return

        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_zip = TEMP_DIR / "singbox_temp.zip"
        download_file(target_asset['browser_download_url'], str(temp_zip))
        
        target_dir = Path("bin/sing-box")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(temp_zip, 'r') as zipf:
            for member in zipf.infolist():
                filename = os.path.basename(member.filename)
                if filename in ("sing-box.exe", "libcronet.dll"):
                    source = zipf.open(member)
                    target = open(target_dir / filename, "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
                    print(f"  -> Извлечен: {filename}")
                    
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        print("  -> sing-box успешно обновлен.")
    except Exception as e:
        print(f"  [ПРЕДУПРЕЖДЕНИЕ] Не удалось обновить sing-box: {e}. Используется существующая версия.")


def update_opera_proxy():
    """Обновление opera-proxy из репозитория Alexey71/opera-proxy"""
    print("\n[2/4] Проверка обновления opera-proxy...")
    try:
        req = urllib.request.Request("https://api.github.com/repos/Alexey71/opera-proxy/releases/latest",
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        target_url = None
        for asset in data.get('assets', []):
            if asset.get('name') == 'opera-proxy.windows-amd64.exe':
                target_url = asset['browser_download_url']
                break
                
        if not target_url:
            print("  [!] Не найден opera-proxy.windows-amd64.exe в релизах.")
            return

        target_path = Path("bin/opera-proxy.windows-amd64.exe")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        download_file(target_url, str(target_path))
        print("  -> opera-proxy успешно обновлен.")
    except Exception as e:
        print(f"  [ПРЕДУПРЕЖДЕНИЕ] Не удалось обновить opera-proxy: {e}. Используется существующая версия.")


def update_byedpi():
    """Обновление ciadpi (ByeDPI) из репозитория hufrea/byedpi"""
    print("\n[3/4] Проверка обновления ByeDPI (ciadpi.exe)...")
    try:
        req = urllib.request.Request("https://api.github.com/repos/hufrea/byedpi/releases/latest",
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        target_url = None
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if 'x86_64-w64.zip' in name:
                target_url = asset['browser_download_url']
                break
                
        if not target_url:
            print("  [!] Не найден ByeDPI x86_64-w64.zip в релизах.")
            return

        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_zip = TEMP_DIR / "byedpi_temp.zip"
        download_file(target_url, str(temp_zip))
        
        target_dir = Path("byedpi")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(temp_zip, 'r') as zipf:
            for member in zipf.infolist():
                filename = os.path.basename(member.filename)
                if filename.lower() == "ciadpi.exe":
                    source = zipf.open(member)
                    target = open(target_dir / "ciadpi.exe", "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
                    print("  -> Извлечен ciadpi.exe")
                    
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        print("  -> ByeDPI успешно обновлен.")
    except Exception as e:
        print(f"  [ПРЕДУПРЕЖДЕНИЕ] Не удалось обновить ByeDPI: {e}. Используется существующая версия.")


def update_tor():
    """Обновление Tor Expert Bundle с torproject.org"""
    print("\n[4/4] Проверка обновления Tor Expert Bundle...")
    try:
        req = urllib.request.Request("https://www.torproject.org/download/tor/",
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            
        links = re.findall(r'href="(https://[^"]+tor-expert-bundle-windows-x86_64[^"]+\.tar\.gz)"', html)
        if not links:
            print("  [!] Не найдена ссылка на скачивание Tor Expert Bundle.")
            return
            
        stable_links = [l for l in links if "a" not in l.split('/')[-2]]
        download_url = stable_links[0] if stable_links else links[0]
        
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_tar = TEMP_DIR / "tor_temp.tar.gz"
        download_file(download_url, str(temp_tar))
        
        temp_ext = TEMP_DIR / "tor_temp_ext"
        if temp_ext.exists():
            shutil.rmtree(temp_ext)
        temp_ext.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(temp_tar, "r:gz") as tar:
            tar.extractall(temp_ext)
            
        # Копируем бинарники tor
        src_tor = temp_ext / "tor"
        dst_tor = Path("tor")
        dst_tor.mkdir(parents=True, exist_ok=True)
        if src_tor.exists():
            for item in src_tor.iterdir():
                dest = dst_tor / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            print("  -> Скопированы файлы tor/")
            
        # Копируем geoip/geoip6 в data/
        src_data = temp_ext / "data"
        dst_data = Path("data")
        dst_data.mkdir(parents=True, exist_ok=True)
        if src_data.exists():
            for gfile in ("geoip", "geoip6"):
                if (src_data / gfile).exists():
                    shutil.copy2(src_data / gfile, dst_data / gfile)
                    print(f"  -> Обновлена база {gfile}")
                    
        # Очистка
        if os.path.exists(temp_tar):
            os.remove(temp_tar)
        if temp_ext.exists():
            shutil.rmtree(temp_ext)
            
        print("  -> Tor успешно обновлен.")
    except Exception as e:
        print(f"  [ПРЕДУПРЕЖДЕНИЕ] Не удалось обновить Tor: {e}. Используется существующая версия.")


# Шаблоны и домены, исключаемые из списка блокировки (не являются экстремизмом):
# Торренты, легитимные медиа, библиотеки, музыка, почта, юмор, игровые порталы
NON_EXTREMIST_EXCLUSIONS = [
    # Торренты и файлообмен
    'rutracker.org', 'waptorrent',
    # Почта и связь
    'protonmail.com', 'gmail.ru', 'fasebook.com', 'uk-ua.fasebook',
    # Музыкальные сервисы и поиск MP3
    'last.fm', 'last.by', 'last.bu', 'pleer.com', 'pleer.net', 'kivvi.kz', 'lalamus.com',
    'ipleer.fm', 'myzuka', 'muzofon', 'zvonko.me', 'zvuk.me', 'realmusic.ru', 'tune.cc',
    'fmusic', 'gdeepmusic', 'hqmp3', 'kibergrad', 'kinopesenki', 'domino-music',
    'mp3', 'muz', 'pesni', 'pesnja', 'pesenok', 'audios.xyz', 'laudios.ru', 'ozaudio.ru',
    'unasmuz', 'vmuzic', 'vmuzike', 'vozmimp3', 'vozmitxt', 'xmusic', 'yesmp3',
    'musezone', 'musicalka', 'musvid', 'my-hit.me', 'mypesnik', 'myzlo', 'naitimp3',
    'nemp.ru', 'nemp3.ru', 'onesong.ru', 'online-song.net', 'plus-music', 'songhouse',
    'songspro', 'textpesni', 'webkind.ru', 'wedkind.ru', 'wikibit.net', 'alllyrix', 'altwall.net',
    'eeefm.eom',
    # Электронные библиотеки, аккорды, документы
    'coollib.net', 'lib.rus.ec', 'lib.aldebaran.ru', 'lib.mn', 'libes.ru', 'libforum.ru',
    'libros.am', 'cultlib.alfaspace.net', 'docplayer.ru', 'mychords.net', 'ru.scribd.com',
    'pdf.knigi-x.ru', 'pandia.ru', 'uchebana5.ru', 'refdb.ru', 'mybiblioteka.su', 'vb.userdocs.ru',
    'litbash.sitecity.ru',
    # Игры и развлечения
    'gametracker.com', 'clashroyaledeckbuilder.com', 'poigraem.net', 'digftnplay.ru',
    # Мемы, аниме, юмор
    'joyreactor.cc', 'joyreactor.ee', 'anime.old.reactor.cc', 'animevid.ru', 'absurdopedia.net',
    'demotivators.to', 'dezinfo.net', 'troll-face.ru', 'hlamer.ru', 'hm6.ru', 'nibler.ru',
    'ucrazy.ru', 'crazynet.ru', 'copypaste.me',
    # Новостные издания и порталы
    'snob.ru', 'mk.ru', 'inosmi.ru', 'regnum.ru', 'zaks.ru', 'zavtra.ru', 'newsland.com',
    'newslab.ru', 'news29.ru', 'bnkomi.ru', 'sovinform.ru', 'sovsekretno.ru', 'credo.ru',
    'portal.credo.ru', 'bolshoyvopros.ru', 'anews.com', 'argumentua.com', 'gazeta.ua',
    'fakty.ictv.ua', 'uapress.info', 'uagolos.com', 'mediaport.ua', 'replyua.net',
    'vesti.kg', 'dal.by',
    # Тематические форумы и дача
    'talks.guns.ru', 'wcb.ru', 'driveural.ru', 'color.ru', 'fanat1k.ru', 'fank.ru',
    'fans-edge.info', 'vip-samodelki.ru', 'tvoybaby.org', 'style.emoolive.ru', 'bod-mod.ru',
    'otvetmail.ru', 'radonvideo.ru', 'rbtube.ru', 'smotrovik.me', 'smoz.ru', 'tubethe.com',
    'videoscop.cc', 'videosme.ru', 'vidooly.com', 'vidoz.net', 'vidoz.pp.ua', 'vids.bastizone.com',
    'truba.com', 'tube.com', 'go2films.ru', 'cxz.to', 'grandhdcns.net',
    # Блоговые платформы и городские порталы
    'maxpark.com', 'mirtesen.ru', 'zakon.mirtesen', 'zakon.mirtesen.ru', 'livejornal.com',
    'livejoumai.com', 'liveiournal.com', 'livegournal.com', 'livrjournal.com', 'livainternet.ru',
    'gorod.cn.ua', 'gorodsalavat.ru', 'gorno-altaisk.info', 'kuban.ru', 'portalpermi.ru',
    'kazak-chita.ru', 'shurarb.ru',
    # Опечатки и служебные
    'google.ry', 'youtube.come', 'yotube.com', 'video.yandex.ra', 'ok.ni', 'km.ru', 'mobi.ru',
    'el.ru', 'k.com', 'kre.ru',
    # Хостинги картинок и файлов
    'i.piccy.info', 'i037.radikal.ru', 'keep4u.ru', 's2.postimg.org', 'simplest-image-hosting.net',
    'file-up.net', 'filka.info', 'rapidzona.com', 'rabidshare.info', 'mc01.userfiles.me',
    'mc01.usersfiles.me', 'msxc.userfiles.me',
    # Прочие неэкстремистские сайты
    'bilokurakvne.pp.ua', 'carshsmpoo.ru', 'chuhotezvous.ru', 'dmitrilove.my1.ru',
    'elniki-fans.ru', 'forum.kukmara-rayon.ru', 'ilia13.dubki.ru', 'intelbi.ru',
    'iodzone.de', 'iomedia.ru', 'korsar-bomb.do.am', 'loys.life', 'master-of-life.ru',
    'masteroff.org', 'minjust.net', 'mixpromo.net', 'mmoru.com', 'molvica.com', 'mozzic.ru',
    'nationalism.org', 'nofollow.ru', 'novostink.ru', 'nrnews.ru', 'offtop.ru', 'opppa.ru',
    'palbit.ru', 'palbu.ru', 'phao.info', 'punk.nnov.ru', 'rest24.mypage.ru', 'rfvrfzcenter.com',
    'ri-online.ru', 'rodonews.ru', 'rr-rus.ru', 'sakh-88.nm.ru', 'schooler.org.ua',
    'setkazak.mybb.ru', 'shareclip.net', 'shob.ru', 'simplest-image-hosting.net',
    'slavyanskaya-kultura.ru', 'specnaz.ru', 'stroidom.com.ua', 'tatar-gazeta.ru',
    'tatarlar.ru', 'tekstili.blogspot.ru', 'tekstovoi.ru', 'tovbin.hoter.ru',
    'uboyno.ru', 'ufagub.com', 'uzhgorod.in', 'vchaspik.ua', 'vdesyatku.biz',
    'victorbeliy.mypage.ru', 'vladrons.com', 'vnmazurenko.biogspot.ru', 'vsesuki.com',
    'western-138.ru', 'xartman.ru', 'za-info.ru', 'zdravomyslie.ru'
]


def is_non_extremist_domain(d: str) -> bool:
    clean = d.lower().strip('.* ')
    for pat in NON_EXTREMIST_EXCLUSIONS:
        if clean == pat or clean.endswith('.' + pat) or pat in clean:
            return True
    return False


def sync_blocked_domains():
    """Автоматическая загрузка, фильтрация и слияние списка экстремистских доменов при сборке"""
    print("\n[СИНХРОНИЗАЦИЯ] Обновление списка экстремистских доменов (AlexeyRF/extremism_domains)...")
    new_domains = []
    try:
        url = "https://raw.githubusercontent.com/AlexeyRF/extremism_domains/main/banned_domains.txt"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
            new_domains = [l.strip() for l in text.splitlines() if l.strip()]
        print(f"  -> Загружено {len(new_domains)} доменов из репозитория.")
    except Exception as e:
        print(f"  [ПРЕДУПРЕЖДЕНИЕ] Не удалось загрузить extremism_domains: {e}. Используются локальные данные.")

    ppx_file = BASE_DIR / "Toinet.ppx"
    if ppx_file.exists():
        content = ppx_file.read_text(encoding="utf-8")
        pattern = r'(<Rule enabled="true">\s*<Action type="Block"\s*/>\s*<Targets>)(.*?)(</Targets>\s*<Name>Block</Name>)'
        m = re.search(pattern, content, re.DOTALL)
        if m:
            old_raw = m.group(2)
            old_items = [x.strip() for x in re.split(r'[\s;\n\r]+', old_raw) if x.strip()]
            all_items = old_items + new_domains
            seen = set()
            unique_items = []
            for it in all_items:
                clean = it.strip('; \r\n\t').lower()
                if not clean or is_non_extremist_domain(clean):
                    continue
                if clean not in seen:
                    seen.add(clean)
                    unique_items.append(it.strip('; \r\n\t'))

            lines = []
            chunk = []
            for item in unique_items:
                chunk.append(item)
                if len(chunk) >= 5:
                    lines.append('; '.join(chunk) + ';')
                    chunk = []
            if chunk:
                lines.append('; '.join(chunk) + ';')

            formatted_targets = '\n' + '\n'.join(lines) + '\n'
            new_rule = m.group(1) + formatted_targets + m.group(3)
            new_content = content[:m.start()] + new_rule + content[m.end():]
            ppx_file.write_text(new_content, encoding="utf-8")

            data_banned = BASE_DIR / "data" / "banned_domains.txt"
            data_banned.parent.mkdir(parents=True, exist_ok=True)
            data_banned.write_text("\n".join(unique_items) + "\n", encoding="utf-8")
            print(f"  -> Профиль Toinet.ppx и data/banned_domains.txt обновлены ({len(unique_items)} проверенных доменов).")


def update_all_binaries():
    """Последовательно обновляет все внешние зависимости"""
    print("\n==================================================")
    print("      ЗАГРУЗКА И ОБНОВЛЕНИЕ БИНАРНИКОВ")
    print("==================================================")
    update_singbox()
    update_opera_proxy()
    update_byedpi()
    update_tor()


def add_to_zip(zipf, rel_path, arc_prefix=PROJECT_NAME):
    """Рекурсивно добавляет файл или каталог в ZIP-архив с фильтрацией мусора"""
    p = Path(rel_path)
    if not p.is_absolute():
        p = BASE_DIR / p
    if not p.exists():
        return
        
    if p.is_file():
        rel_file = p.resolve().relative_to(BASE_DIR)
        arcname = os.path.join(arc_prefix, str(rel_file).replace("\\", "/"))
        zipf.write(p, arcname)
        return

    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            file_path = Path(root) / f
            if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
                continue
            if file_path.parent.name == "data" and file_path.name in EXCLUDE_DATA_FILES:
                continue
            if file_path.parent.name == "evpn" and file_path.name in EXCLUDE_EVPN_FILES:
                continue
            rel_file = file_path.resolve().relative_to(BASE_DIR)
            arcname = os.path.join(arc_prefix, str(rel_file).replace("\\", "/"))
            zipf.write(file_path, arcname)


def build_python_zip():
    """Сборка Python-версии архива"""
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    output_zip = RELEASES_DIR / f"{PROJECT_NAME}-python_amd64.zip"
    print(f"\n[СБОРКА] Формирование Python-релиза -> {output_zip}...")
    
    with zipfile.ZipFile(str(output_zip), 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Корневые файлы
        root_files = ["main.pyw", "icon.ico", "launch.bat", "README.md", "Toinet.ppx"]
        for rf in root_files:
            add_to_zip(zipf, rf)
            
        # Каталоги с исходным кодом и скриптами
        code_dirs = ["ui", "managers", "evpn", "byedpi"]
        for cdir in code_dirs:
            add_to_zip(zipf, cdir)
            
        # Внешние бинарники и ресурсы
        bin_resources = [
            "bin/cpller.exe",
            "bin/gatik.exe",
            "bin/ssh_tunnel.exe",
            "bin/programs_settings.exe",
            "bin/tgws.exe",
            "bin/tgws_settings.exe",
            "bin/edit_bridges.exe",
            "bin/ssh_settings.exe",
            "bin/opera_settings.exe",
            "bin/rules_editor.exe",
            "bin/autostart_settings.exe",
            "bin/zdpi_ml_optimizer.exe",
            "bin/opera-proxy.windows-amd64.exe",
            "bin/sing-box",
            "bin/tgws_accel.dll",
            "data/geoip",
            "data/geoip6",
            "data/bridges.txt",
            "data/google_cidrs.json",
            "data/banned_domains.txt",
            "data/telegram.jpg",
            "data/telegram.png",
            "tor/tor.exe",
            "tor/tor-gencert.exe",
            "tor/pluggable_transports",
        ]
        for res in bin_resources:
            add_to_zip(zipf, res)
            
    size_mb = os.path.getsize(output_zip) / (1024 * 1024)
    print(f"[УСПЕХ] Python-релиз собран: {output_zip} ({size_mb:.1f} МБ)")
    return str(output_zip)


def compile_exe():
    """Компиляция ToInet.exe через PyInstaller со всеми вшитыми модулями"""
    print("\n[СБОРКА] Компиляция ToInet.exe через PyInstaller...")
    workpath = WORK_DIR
    distpath = DIST_DIR
    
    if workpath.exists():
        try:
            shutil.rmtree(workpath)
        except Exception:
            pass
    if distpath.exists():
        try:
            shutil.rmtree(distpath)
        except Exception:
            pass

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "ToInet",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--icon", str((BASE_DIR / "icon.ico").resolve()),
        "--workpath", str(workpath),
        "--distpath", str(distpath),
        "--specpath", str(BUILD_DIR),
        "--paths", str(BASE_DIR),
        "--noconfirm",
        "--clean",
    ]
    
    # Скрытые импорты
    hidden_imports = [
        "requests", "pythoncom", "win32com", "win32com.client",
        "psutil", "cryptography", "pyperclip", "socks", "h2", "certifi", "httpx",
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "managers.system_utils", "managers.config_manager", "managers.bdsher",
        "managers.torchok", "managers.opera_manager", "managers.vless_manager",
        "managers.mode_manager", "managers.evpn_manager", "managers.ext_manager",
        "managers.ssh_manager", "managers.dependencies", "managers.runtime_patch", "managers.service_controller",
        "ui.app_log_window", "ui.window_ui", "ui.tray_menu",
        "ui.byedpi_tester_gui", "ui.maestro",
        "managers.tgws_manager"
    ]
    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])
        
    for em in EXCLUDE_MODULES:
        cmd.extend(["--exclude-module", em])
        
    # Вшиваем модули в sys._MEIPASS
    sep = ";" if os.name == "nt" else ":"
    dirs_to_add = ["ui", "managers", "evpn", "byedpi"]
    for d in dirs_to_add:
        src_path = (BASE_DIR / d).resolve()
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}{d}"])
            
    for rf in ("icon.ico", "Toinet.ppx"):
        src_path = (BASE_DIR / rf).resolve()
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}."])
            
    cmd.append(str((BASE_DIR / "main.pyw").resolve()))
    
    subprocess.check_call(cmd)
    
    exe_path = distpath / "ToInet.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"EXE файл не был создан по пути {exe_path}!")
        
    exe_size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"  -> Исполняемый файл создан: {exe_path} ({exe_size_mb:.1f} МБ)")
    return str(exe_path)


def build_portable_zip(compiled_exe_path):
    """Сборка Portable-версии архива"""
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    output_zip = RELEASES_DIR / f"{PROJECT_NAME}-portable_amd64.zip"
    print(f"\n[СБОРКА] Формирование Portable-релиза -> {output_zip}...")
    
    with zipfile.ZipFile(str(output_zip), 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Сам скомпилированный бинарник
        zipf.write(str(compiled_exe_path), os.path.join(PROJECT_NAME, "ToInet.exe"))
        
        # Корневые файлы для Portable
        for rf in ["icon.ico", "README.md", "Toinet.ppx"]:
            add_to_zip(zipf, rf)
            
        # Батник для быстрого запуска ToInet.exe
        portable_bat_content = "@echo off\r\ncd /d \"%~dp0\"\r\nstart \"\" ToInet.exe\r\n"
        zipf.writestr(f"{PROJECT_NAME}/launch.bat", portable_bat_content)
        
        # Стратегии и списки сайтов zDPI
        for bf in glob.glob("byedpi/*.txt"):
            add_to_zip(zipf, bf)
        add_to_zip(zipf, "byedpi/ciadpi.exe")
        add_to_zip(zipf, "byedpi/zdpi.exe")
        
        # Ресурсы sing-box, Tor, Opera, базы
        portable_resources = [
            "bin/cpller.exe",
            "bin/gatik.exe",
            "bin/ssh_tunnel.exe",
            "bin/programs_settings.exe",
            "bin/tgws.exe",
            "bin/tgws_settings.exe",
            "bin/edit_bridges.exe",
            "bin/ssh_settings.exe",
            "bin/opera_settings.exe",
            "bin/rules_editor.exe",
            "bin/autostart_settings.exe",
            "bin/zdpi_ml_optimizer.exe",
            "bin/opera-proxy.windows-amd64.exe",
            "bin/sing-box",
            "bin/tgws_accel.dll",
            "data/geoip",
            "data/geoip6",
            "data/bridges.txt",
            "data/google_cidrs.json",
            "data/banned_domains.txt",
            "data/telegram.jpg",
            "data/telegram.png",
            "evpn/subs.txt",
            "tor/tor.exe",
            "tor/tor-gencert.exe",
            "tor/pluggable_transports",
        ]
        for res in portable_resources:
            add_to_zip(zipf, res)
            
    size_mb = os.path.getsize(output_zip) / (1024 * 1024)
    print(f"[УСПЕХ] Portable-релиз собран: {output_zip} ({size_mb:.1f} МБ)")
    return str(output_zip)


def build_onefile_release():
    """Сборка One-File версии: единый полностью самодостаточный EXE файл со всеми бинарниками и ресурсами"""
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    exe_name = f"{PROJECT_NAME}-one_file_amd64.exe"
    output_exe = RELEASES_DIR / exe_name
    print(f"\n[СБОРКА] Компиляция One-File релиза -> {output_exe}...")
    
    workpath = WORK_ONEFILE_DIR
    distpath = DIST_ONEFILE_DIR
    
    for p in (workpath, distpath):
        if p.exists():
            try:
                shutil.rmtree(p)
            except Exception:
                pass

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", f"{PROJECT_NAME}-one_file_amd64",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--icon", str((BASE_DIR / "icon.ico").resolve()),
        "--workpath", str(workpath),
        "--distpath", str(distpath),
        "--specpath", str(BUILD_DIR),
        "--paths", str(BASE_DIR),
        "--noconfirm",
        "--clean",
    ]
    
    # Скрытые импорты
    hidden_imports = [
        "requests", "pythoncom", "win32com", "win32com.client",
        "psutil", "cryptography", "pyperclip", "socks", "h2", "certifi", "httpx",
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "managers.system_utils", "managers.config_manager", "managers.bdsher",
        "managers.torchok", "managers.opera_manager", "managers.vless_manager",
        "managers.mode_manager", "managers.evpn_manager", "managers.ext_manager",
        "managers.ssh_manager", "managers.dependencies", "managers.runtime_patch", "managers.service_controller",
        "ui.app_log_window", "ui.window_ui", "ui.tray_menu",
        "ui.byedpi_tester_gui", "ui.maestro",
        "managers.tgws_manager"
    ]
    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])
        
    for em in EXCLUDE_MODULES:
        cmd.extend(["--exclude-module", em])
        
    sep = ";" if os.name == "nt" else ":"
    
    # Модули и код
    dirs_to_add = ["ui", "managers", "evpn", "byedpi"]
    for d in dirs_to_add:
        src_path = (BASE_DIR / d).resolve()
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}{d}"])
            
    # Внешние бинарники (bin, tor)
    for bdir in ("bin", "tor"):
        src_path = (BASE_DIR / bdir).resolve()
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}{bdir}"])
        
    # Данные и базы
    data_files = [
        "data/geoip",
        "data/geoip6",
        "data/bridges.txt",
        "data/google_cidrs.json",
        "data/banned_domains.txt",
        "data/telegram.jpg",
        "data/telegram.png",
    ]
    for df in data_files:
        src_path = (BASE_DIR / df).resolve()
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}data"])
            
    # Подписки evpn
    subs_path = (BASE_DIR / "evpn/subs.txt").resolve()
    if subs_path.exists():
        cmd.extend(["--add-data", f"{subs_path}{sep}evpn"])
        
    # Корневые ресурсы и маркер One-File режима
    marker_file = BUILD_DIR / "onefile_mode.marker"
    marker_file.write_text("onefile", encoding="utf-8")
    cmd.extend(["--add-data", f"{marker_file}{sep}."])

    for rf in ("icon.ico", "Toinet.ppx", "README.md"):
        src_path = (BASE_DIR / rf).resolve()
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}."])
            
    cmd.append(str((BASE_DIR / "main.pyw").resolve()))
    
    subprocess.check_call(cmd)
    
    built_exe = distpath / f"{PROJECT_NAME}-one_file_amd64.exe"
    if not built_exe.exists():
        raise FileNotFoundError(f"EXE файл One-File не был создан по пути {built_exe}!")
        
    shutil.copy2(built_exe, output_exe)
    
    try:
        shutil.rmtree(distpath)
    except Exception:
        pass
        
    size_mb = os.path.getsize(output_exe) / (1024 * 1024)
    print(f"[УСПЕХ] One-File релиз собран: {output_exe} ({size_mb:.1f} МБ)")
    return str(output_exe)


def clean_temp_files():
    """Удаление временных патчей и мусора"""
    for pf in glob.glob("patch*.py"):
        try:
            os.remove(pf)
            print(f"Удален временный файл: {pf}")
        except Exception:
            pass
    # Очистка устаревших папок сборки в корне, если они остались
    for legacy_dir in ("pyinstaller_build", "pyinstaller_build_onefile", "pyinstaller_dist_onefile", "dist", "releases"):
        p = BASE_DIR / legacy_dir
        if p.exists():
            try:
                shutil.rmtree(p)
            except Exception:
                pass
    for spec_file in ("ToInet-MAX-one_file_amd64.spec", "ToInet.spec"):
        p = BASE_DIR / spec_file
        if p.exists():
            try:
                os.remove(p)
            except Exception:
                pass
    # Очистка временных папок сборки внутри build
    for build_sub in ("work", "work_onefile", "dist_onefile", "temp"):
        p = BUILD_DIR / build_sub
        if p.exists():
            try:
                shutil.rmtree(p)
            except Exception:
                pass
    evpn_junk = [
        "evpn/subs_cache.json",
        "evpn/working_nodes.json",
        "evpn/evpn_config.json",
        "evpn/evpn.log",
        "evpn/vless_state.json",
        "evpn/blacklist.json",
    ]
    for jf in evpn_junk:
        if os.path.exists(jf):
            try:
                os.remove(jf)
                print(f"Удален временный файл EVPN: {jf}")
            except Exception:
                pass


def build_all(update_binaries=False, target="all"):
    """Основной процесс сборки"""
    print("==================================================")
    mode_text = "С ОБНОВЛЕНИЕМ БИНАРНИКОВ" if update_binaries else "ОБЫЧНАЯ СБОРКА"
    print(f"      СБОРКА РЕЛИЗОВ {PROJECT_NAME} ({mode_text})")
    print(f"      Целевой релиз: {target.upper()}")
    print("==================================================")
    
    clean_temp_files()
    
    # Автоматическая синхронизация и очистка заблокированных доменов
    sync_blocked_domains()
    
    if update_binaries:
        update_all_binaries()
        
    python_zip = None
    portable_zip = None
    onefile_exe = None
    
    if target in ("all", "python"):
        # 1. Сборка Python версии
        python_zip = build_python_zip()
        
    if target in ("all", "portable"):
        # 2. Компиляция ToInet.exe для Portable
        exe_path = compile_exe()
        # 3. Сборка Portable версии
        portable_zip = build_portable_zip(exe_path)
        
    if target in ("all", "one_file"):
        # 4. Сборка One-File версии
        onefile_exe = build_onefile_release()
    
    print("\n==================================================")
    print("               ИТОГИ СБОРКИ:")
    print("==================================================")
    if python_zip:
        print(f"1. Python-архив:   {python_zip}")
    if portable_zip:
        print(f"2. Portable-архив: {portable_zip}")
    if onefile_exe:
        print(f"3. One-File файл:  {onefile_exe}")
    print("==================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сборщик релизов ToInet-MAX")
    parser.add_argument("--update", action="store_true", help="Обновить бинарники (sing-box, opera-proxy, byedpi, Tor) перед сборкой")
    parser.add_argument("--type", choices=["all", "python", "portable", "one_file"], default="all",
                        help="Тип релиза для сборки: all (все), python, portable, one_file")
    args = parser.parse_args()
    build_all(update_binaries=args.update, target=args.type)
