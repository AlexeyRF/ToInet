#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import json
import shutil
import subprocess
import time
import ctypes
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

# Версия программы
APP_VERSION = "2.2.1"
APP_TITLE = "Antigravity Unlocker"

# Константы для NRPT
AG_NRPT_TAG = "AG_UNLOCKER_NRPT"
AG_NRPT_NAMESPACES = [
    ".googleapis.com",
    ".googleusercontent.com",
    "accounts.google.com",
    ".google",
    ".goog",
]
AG_NRPT_NAMESERVERS = "'111.88.96.50','111.88.96.51','2a00:ab00:1233:26::50','2a00:ab00:1233:26::51'"


# ---------------------------- Вспомогательные функции ---------------------------

def clear_screen() -> None:
    """Очистка экрана консоли."""
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")


def is_admin() -> bool:
    """Проверка, запущена ли программа с правами администратора (Windows)."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False


def mask_path(path: str) -> str:
    """Заменяет системные пути на переменные окружения для безопасного вывода."""
    result = path
    for var in ["LOCALAPPDATA", "APPDATA", "USERPROFILE"]:
        val = os.environ.get(var, "")
        if val:
            result = result.replace(val, f"%{var}%")
    return result


def run_powershell(cmd: str, check: bool = False) -> Tuple[int, str, str]:
    """Выполняет команду PowerShell и возвращает (код_возврата, stdout, stderr)."""
    process = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return process.returncode, process.stdout.strip(), process.stderr.strip()


# ---------------------------- Работа с DNS (NRPT) -------------------------------

def is_nrpt_applied() -> bool:
    """Проверяет, установлены ли наши NRPT-правила."""
    cmd = f"(Get-DnsClientNrptRule -ErrorAction SilentlyContinue | Where-Object {{$_.Comment -eq '{AG_NRPT_TAG}'}} | Measure-Object).Count"
    rc, out, _ = run_powershell(cmd)
    if rc == 0 and out.isdigit():
        return int(out) >= len(AG_NRPT_NAMESPACES)
    return False


def remove_dns_nrpt() -> None:
    """Удаляет все NRPT-правила с нашим тегом."""
    # Восстанавливаем префикс-политику IPv6 (по умолчанию)
    subprocess.run(
        ["netsh", "interface", "ipv6", "set", "prefixpolicy", "::ffff:0:0/96", "35", "4"],
        capture_output=True
    )
    cmd = (
        f"Get-DnsClientNrptRule -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.Comment -eq '{AG_NRPT_TAG}' }} | "
        f"Remove-DnsClientNrptRule -Force -ErrorAction SilentlyContinue; "
        f"Clear-DnsClientCache -ErrorAction SilentlyContinue"
    )
    run_powershell(cmd)


def setup_dns_nrpt() -> bool:
    """Устанавливает NRPT-правила для Google-доменов. Возвращает True при успехе."""
    # Удаляем старые правила
    remove_dns_nrpt()

    # Предпочитаем IPv4 над IPv6 для стабильности
    subprocess.run(
        ["netsh", "interface", "ipv6", "set", "prefixpolicy", "::ffff:0:0/96", "46", "4"],
        capture_output=True
    )

    for ns in AG_NRPT_NAMESPACES:
        cmd = (
            f"Add-DnsClientNrptRule -Namespace '{ns}' -NameServers @({AG_NRPT_NAMESERVERS}) "
            f"-Comment '{AG_NRPT_TAG}' -DisplayName 'AG Unlocker' -ErrorAction Stop"
        )
        rc, _, err = run_powershell(cmd)
        if rc != 0:
            # Если ошибка доступа, выводим предупреждение
            if "Access is denied" in err or "requires elevation" in err:
                print(f"  [ERR] Не удалось применить NRPT для {ns}: требуются права администратора.")
            else:
                print(f"  [ERR] Не удалось применить NRPT для {ns}: {err}")
            return False
    # Сброс кэша DNS
    run_powershell("Clear-DnsClientCache -ErrorAction SilentlyContinue")
    return True


def handle_restore_dns() -> None:
    """Обработчик пункта меню: восстановление DNS."""
    print("Удаление NRPT-правил DNS... ", end="", flush=True)
    remove_dns_nrpt()
    print("готово.")
    print("\nГотово!")
    time.sleep(2)


# ---------------------------- Поиск установок Antigravity -----------------------

def find_all_installs() -> List[Path]:
    """Ищет все установки Antigravity / Antigravity IDE / CLI."""
    installs = []
    local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
    prog_files = Path(os.environ.get("PROGRAMFILES", ""))
    prog_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", ""))

    candidates = [
        local_appdata / "Programs" / "Antigravity",
        prog_files / "Antigravity",
        prog_files_x86 / "Antigravity",
        local_appdata / "Antigravity",
        local_appdata / "Programs" / "Antigravity IDE",
        prog_files / "Antigravity IDE",
        prog_files_x86 / "Antigravity IDE",
        local_appdata / "Antigravity IDE",
        Path("D:/Programs/Antigravity IDE"),
        Path("C:/Programs/Antigravity IDE"),
        local_appdata / "agy" / "bin",
    ]

    for p in candidates:
        if p.exists() and p.is_dir():
            # Проверяем наличие признаков установки
            if (p / "resources").exists() or (p / "agy.exe").exists():
                if p not in installs:
                    installs.append(p)
    return installs


# ---------------------------- Патч бинарных файлов (замена строк) --------------

def patch_binary(bin_path: Path) -> Tuple[bool, str]:
    """
    Заменяет в бинарнике 'ineligible' на 'inexigible'.
    Возвращает (успешно, сообщение).
    """
    try:
        with open(bin_path, "rb") as f:
            data = bytearray(f.read())
    except Exception as e:
        return False, f"Ошибка чтения: {e}"

    old_bytes = b"ineligible"
    new_bytes = b"inexigible"

    found = False
    # Ищем все вхождения
    for i in range(len(data) - len(old_bytes) + 1):
        if data[i:i+len(old_bytes)] == old_bytes:
            data[i:i+len(new_bytes)] = new_bytes
            found = True

    if not found:
        # Проверяем, не пропатчен ли уже
        already = False
        for i in range(len(data) - len(new_bytes) + 1):
            if data[i:i+len(new_bytes)] == new_bytes:
                already = True
                break
        if already:
            return True, "Уже пропатчено"
        else:
            return False, "Сигнатура не найдена"

    # Завершаем процессы, использующие этот файл
    proc_name = bin_path.name
    subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True)
    time.sleep(0.5)

    try:
        with open(bin_path, "wb") as f:
            f.write(data)
    except Exception as e:
        return False, f"Ошибка записи: {e}"

    return True, "OK"


def patch_all_binaries(inst_path: Path) -> None:
    """Патчит все бинарные файлы в установке (agy.exe, language_server.exe)."""
    # CLI
    cli = inst_path / "agy.exe"
    if cli.exists():
        ok, msg = patch_binary(cli)
        print(f"  [OK] CLI binary patched" if ok else f"  [ERR] CLI patch failed: {msg}")

    # Language Server
    ls_candidates = [
        inst_path / "resources" / "bin" / "language_server.exe",
        inst_path / "resources" / "app" / "extensions" / "antigravity" / "bin" / "language_server_windows_x64.exe",
        inst_path / "resources" / "app" / "extensions" / "antigravity" / "bin" / "language_server.exe",
    ]
    for ls in ls_candidates:
        if ls.exists():
            ok, msg = patch_binary(ls)
            print(f"  [OK] LS binary patched" if ok else f"  [ERR] LS patch failed: {msg}")


# ---------------------------- Распаковка ASAR -----------------------------------

def extract_asar(app_asar: Path, app_dir: Path) -> bool:
    """
    Распаковывает app.asar в app_dir. Возвращает True при успехе.
    Реализация основана на разборе заголовка ASAR.
    """
    if not app_asar.exists():
        return False
    if app_dir.exists():
        # удаляем старую распакованную директорию, чтобы избежать конфликтов
        shutil.rmtree(app_dir, ignore_errors=True)
    app_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(app_asar, "rb") as f:
            # Читаем заголовок: 4 байта размер данных, 4 байта размер заголовка и т.д.
            header_size_bytes = f.read(16)
            if len(header_size_bytes) < 16:
                return False
            # data_size = int.from_bytes(header_size_bytes[0:4], 'little')
            header_size = int.from_bytes(header_size_bytes[4:8], 'little')
            # header_object_size = int.from_bytes(header_size_bytes[8:12], 'little')
            header_string_size = int.from_bytes(header_size_bytes[12:16], 'little')

            # Читаем JSON-заголовок
            header_bytes = f.read(header_string_size)
            if len(header_bytes) < header_string_size:
                return False
            header_json = header_bytes.decode('utf-8')
            tree = json.loads(header_json)

            base_offset = header_size + 8  # 8 байт размера заголовка (header_size + 8)

            def extract_entry(entry: Dict[str, Any], current_path: Path):
                """Рекурсивно извлекает файлы/папки из записи asar."""
                if "files" in entry:
                    for name, child in entry["files"].items():
                        next_path = current_path / name
                        extract_entry(child, next_path)
                else:
                    size = entry.get("size", 0)
                    offset_str = entry.get("offset", "0")
                    offset = int(offset_str)
                    unpacked = entry.get("unpacked", False)

                    # Создаем родительские папки
                    current_path.parent.mkdir(parents=True, exist_ok=True)

                    if not unpacked:
                        # Читаем данные из asar
                        f.seek(base_offset + offset)
                        remaining = size
                        with open(current_path, "wb") as out:
                            while remaining > 0:
                                to_read = min(remaining, 65536)
                                buf = f.read(to_read)
                                if not buf:
                                    break
                                out.write(buf)
                                remaining -= len(buf)
                    else:
                        # unpacked файлы лежат в .asar.unpacked, но мы их копируем отдельно
                        pass

            # Извлекаем все файлы из дерева
            extract_entry(tree, app_dir)

            # Копируем содержимое .asar.unpacked, если есть
            unpacked_dir = app_asar.with_suffix(".asar.unpacked")
            if unpacked_dir.exists() and unpacked_dir.is_dir():
                def copy_dir(src: Path, dst: Path):
                    for item in src.iterdir():
                        if item.is_dir():
                            copy_dir(item, dst / item.name)
                        else:
                            shutil.copy2(item, dst / item.name)
                copy_dir(unpacked_dir, app_dir)

            # Переименовываем asar в .bak
            bak = app_asar.with_suffix(".asar.bak")
            if bak.exists():
                bak.unlink()
            app_asar.rename(bak)
            return True

    except Exception:
        return False


# ---------------------------- Патч IDE (main.js) ------------------------------

def patch_ide(main_js: Path) -> Tuple[bool, str]:
    """
    Патчит main.js для Antigravity IDE.
    Возвращает (успешно, сообщение).
    """
    try:
        with open(main_js, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Ошибка чтения: {e}"

    # Проверка, не пропатчено ли уже (ищем маркер)
    if content.rstrip().endswith("// UNLOCKED"):
        # Если есть маркер, считаем, что уже пропатчено (но проверяем, не старый ли патч)
        if "/*[AG_PATCHED]*/" in content or "[AG_PROXY_HOOK]" in content:
            return False, "Обнаружена старая версия патча. Выполните чистую переустановку IDE."
        return True, "Уже пропатчено"

    # Сигнатура функции
    pattern = re.compile(
        r'async\s+([A-Za-z_$0-9]+)\(([A-Za-z_$0-9]+)\)\s*\{\s*if\(this\.([A-Za-z_$0-9]+)\.send\(\{type:[A-Za-z_$0-9]+\.isGcpTos\?"GCP_SIGN_IN":"SIGN_IN"\}\),this\.([A-Za-z_$0-9]+)\.resetIsTierGCPTos\(\),this\.[A-Za-z_$0-9]+\.isGoogleInternal\)\{try\{await this\.([A-Za-z_$0-9]+)\.loadCodeAssist\([A-Za-z_$0-9]+\);const\{settings:([A-Za-z_$0-9]+),userTier:([A-Za-z_$0-9]+)\}=await this\.refreshUserStatus\([A-Za-z_$0-9]+\),([A-Za-z_$0-9]+)=([A-Za-z_$0-9]+)\([A-Za-z_$0-9]+\);this\.([A-Za-z_$0-9]+)\.pushUpdate\([A-Za-z_$0-9]+\),this\.[A-Za-z_$0-9]+\.send\(\{type:"AUTH_SUCCESS",tokenInfo:[A-Za-z_$0-9]+\}\),this\.([A-Za-z_$0-9]+)\.fire\(\{settings:[A-Za-z_$0-9]+,userTier:[A-Za-z_$0-9]+\}\)\}catch\(([A-Za-z_$0-9]+)\)\{.*?(?:return\}|return;\s*\})',
        re.DOTALL
    )

    match = pattern.search(content)
    if not match:
        return False, "Сигнатура не найдена (возможно, другая версия)"

    fname = match.group(1)
    var_t = match.group(2)
    var_t_send = match.group(3)
    var_y = match.group(4)
    var_func = match.group(9)
    var_f = match.group(10)
    var_h = match.group(11)
    var_i = match.group(8)

    # Новый код функции (упрощенный, с обходом проверок)
    payload = f"""async {fname}({var_t}){{
    this.{var_t_send}.send({{type:{var_t}.isGcpTos?"GCP_SIGN_IN":"SIGN_IN"}});
    this.{var_y}.resetIsTierGCPTos();
    try {{
        try {{ await this.{var_y}.loadCodeAssist({var_t}); }} catch(_) {{}}
        try {{ await this.{var_y}.onboardUser("standard-tier", {var_t}); }} catch(_) {{
            try {{ await this.{var_y}.onboardUser("free-tier", {var_t}); }} catch(__) {{}}
        }}
        let __res = {{ settings: {{}}, userTier: {{ id: "pro", description: "Pro" }} }};
        try {{ __res = await this.refreshUserStatus({var_t}); }} catch(_) {{}}
        const {var_i} = {var_func}({var_t});
        try {{ this.{var_f}.pushUpdate({var_i}); }} catch(_) {{}}
        this.{var_t_send}.send({{type:"AUTH_SUCCESS",tokenInfo:{var_t}}});
        this.{var_h}.fire({{settings:__res.settings, userTier:__res.userTier}});
    }} catch(e) {{}}
    return;
"""

    start = match.start()
    end = match.end()
    new_content = content[:start] + payload + content[end:]
    new_content += "\n// UNLOCKED"

    try:
        with open(main_js, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        return False, f"Ошибка записи: {e}"

    return True, "OK"


# ---------------------------- Патч Desktop (main.js) --------------------------

def strip_desktop_hook(content: str) -> str:
    """Удаляет существующий хук, если он есть."""
    # Ищем блок // [AG_PROXY_HOOK] ... // [/AG_PROXY_HOOK]
    start = content.find("// [AG_PROXY_HOOK]")
    if start != -1:
        end = content.find("// [/AG_PROXY_HOOK]", start)
        if end != -1:
            end += len("// [/AG_PROXY_HOOK]")
            # Удаляем также завершающий // UNLOCKED
            rest = content[end:].lstrip()
            if rest.startswith("// UNLOCKED"):
                rest = rest[len("// UNLOCKED"):]
            return content[:start] + rest
    # Удаляем голый // UNLOCKED
    if content.rstrip().endswith("// UNLOCKED"):
        pos = content.rfind("// UNLOCKED")
        return content[:pos]
    return content


def apply_desktop_inline_patches(content: str) -> str:
    """Применяет инлайн-патчи к main.js Desktop."""
    output = content

    # Замена ineligible -> inexigible
    output = output.replace("ineligible", "inexigible")

    # Патч getUserStatus
    pattern_getus = re.compile(r'let ([A-Za-z_$]+)=.*\.getUserStatus\(\{\}\)\)\)\.userStatus;if([A-Za-z_$]+)\{')
    output = pattern_getus.sub(
        lambda m: f'let {m.group(1)}=...getUserStatus({{}}))).userStatus;{m.group(2)}={{"planStatus":{{"planInfo":{{"planName":"pro"}}}},"disableTelemetry":false,"userDataCollectionForceDisabled":false}};if({m.group(2)}){{',
        output
    )

    # Патч _handleAuthErrorResponse
    pattern_auth = re.compile(r'_handleAuthErrorResponse\(([A-Za-z_$]+)\)\{var ([A-Za-z_$]+)=([A-Za-z_$]+)\?\.failureDetails;')
    output = pattern_auth.sub(
        lambda m: f'_handleAuthErrorResponse({m.group(1)}){{var {m.group(2)}={m.group(3)}?.failureDetails; if({m.group(2)}?.case==="inexigible"){{ this._authActor.send({{type:"AUTH_SUCCESS",tokenInfo:{{accessToken:""}},scopes:[],isGcpTos:false}}); return; }}',
        output
    )

    # Патч SET_INELIGIBLE
    pattern_inel = re.compile(r'\?\.failureDetails\?\.case==="ineligible"\?this\._authActor\.send\(\{type:"SET_INELIGIBLE"')
    output = pattern_inel.sub(
        '?.failureDetails?.case==="NEVER_MATCH"?this._authActor.send({type:"SET_INELIGIBLE"',
        output
    )

    # Патч isEligible: false -> true
    pattern_elig = re.compile(r'(isEligible:\s*)false')
    output = pattern_elig.sub(r'\1true', output)

    return output


def patch_desktop(main_js: Path) -> Tuple[bool, str]:
    """
    Патчит main.js для Antigravity Desktop.
    Вставляет прокси-сервер и инлайн-патчи.
    """
    try:
        with open(main_js, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Ошибка чтения: {e}"

    # Удаляем старый хук, если есть
    cleaned = strip_desktop_hook(content)

    # Применяем инлайн-патчи
    inline_patched = apply_desktop_inline_patches(cleaned)

    # Хук для прокси
    hook = r"""// [AG_PROXY_HOOK]
const _elec = require('electron');
const http = require('http');
const https = require('https');
const zlib = require('zlib');

let agProxyPort = 0;
let realLsPort = 0;
let agApiPort = 0;

const proxyServer = http.createServer((req, res) => {
    if (!realLsPort) {
        if (!res.headersSent) res.writeHead(500);
        return res.end('No LS port');
    }
    const options = {
        hostname: '127.0.0.1',
        port: realLsPort,
        path: req.url,
        method: req.method,
        headers: req.headers,
        rejectUnauthorized: false
    };

    const proxyReq = https.request(options, (proxyRes) => {
        if (req.url.includes('main.js')) {
            const chunks = [];
            proxyRes.on('data', c => chunks.push(c));
            proxyRes.on('end', () => {
                let buffer = Buffer.concat(chunks);
                const encoding = (proxyRes.headers['content-encoding'] || '').toLowerCase();
                let wasCompressed = false;
                if (encoding.includes('gzip')) {
                    try { buffer = zlib.gunzipSync(buffer); wasCompressed = true; } catch(e){}
                } else if (encoding.includes('br')) {
                    try { buffer = zlib.brotliDecompressSync(buffer); wasCompressed = true; } catch(e){}
                }

                let body = buffer.toString('utf-8');

                body = body.replace(/_handleAuthErrorResponse\(([a-zA-Z_$]+)\)\{var ([a-zA-Z_$]+)=\1\?\.failureDetails;/g, '_handleAuthErrorResponse($1){var $2=$1?.failureDetails; if($2?.case==="ineligible"){ this._authActor.send({type:"AUTH_SUCCESS",tokenInfo:{accessToken:""},scopes:[],isGcpTos:false}); return; }');
                body = body.replace(/\?\.failureDetails\?\.case==="ineligible"\?this\._authActor\.send\(\{type:"SET_INELIGIBLE"/g, '?.failureDetails?.case==="NEVER_MATCH"?this._authActor.send({type:"SET_INELIGIBLE"');

                const pattern2 = /let ([A-Za-z_$]+)=.*\.getUserStatus\(\{\}\)\)\)\.userStatus;if\(\1\)\{/g;
                body = body.replace(pattern2, (match, p1) => {
                    return match.replace(`if(${p1}){`, `${p1}={planStatus:{planInfo:{planName:"pro"}}, disableTelemetry:false, userDataCollectionForceDisabled:false};if(${p1}){`);
                });

                let outBuffer = Buffer.from(body, 'utf-8');
                if (wasCompressed) {
                    if (encoding.includes('gzip')) outBuffer = zlib.gzipSync(outBuffer);
                    else if (encoding.includes('br')) outBuffer = zlib.brotliCompressSync(outBuffer);
                }

                const headers = { ...proxyRes.headers };
                headers['content-length'] = outBuffer.length;
                if (!res.headersSent) res.writeHead(proxyRes.statusCode, headers);
                res.end(outBuffer);
            });
        } else {
            if (!res.headersSent) res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res, { end: true });
        }
    });

    proxyReq.on('error', (e) => {
        if (!res.headersSent) res.writeHead(500);
        res.end();
    });
    req.pipe(proxyReq, { end: true });
});

proxyServer.listen(0, '127.0.0.1', () => { agProxyPort = proxyServer.address().port; });

const apiProxyServer = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    const body = [];
    req.on('data', c => body.push(c));
    req.on('end', () => {
        const reqBody = Buffer.concat(body).toString('utf-8');
        if (req.url.includes('UserStatus') || req.url.includes('getUserStatus') || req.url.includes('refreshUserStatus') || req.url.includes('userStatus')) {
            return res.end(JSON.stringify({
                userStatus: {
                    userTier: { id: "pro", description: "Pro" },
                    currentTier: { id: "STANDARD", hasOnboardedPreviously: true },
                    planStatus: { planInfo: { planName: "pro", isEligible: true } },
                    eligible: true,
                    ineligibleReason: null,
                    disableTelemetry: false,
                    userDataCollectionForceDisabled: false,
                    allowedTiers: [{ id: "STANDARD", name: "Standard", isDefault: true }]
                }
            }));
        }
        if (req.url.includes('loadCodeAssist')) {
            return res.end(JSON.stringify({
                currentTier: { id: "STANDARD", hasOnboardedPreviously: true },
                cloudaicompanionProject: "",
                allowedTiers: [{ id: "STANDARD", name: "Standard", isDefault: true }],
                paidTier: void 0
            }));
        }
        if (req.url.includes('onboardUser')) {
            return res.end(JSON.stringify({
                done: true,
                response: {
                    cloudaicompanionProject: { id: "" }
                }
            }));
        }
        if (req.url.includes('listExperiments')) {
            return res.end(JSON.stringify({ flags: [], experimentIds: [] }));
        }
        if (req.url.includes('fetchAdminControls')) {
            return res.end(JSON.stringify({}));
        }
        if (req.url.includes('getCodeAssistGlobalUserSetting')) {
            return res.end(JSON.stringify({}));
        }
        if (req.url.includes('refreshUserQuota') || req.url.includes('retrieveUserQuota')) {
            return res.end(JSON.stringify({}));
        }
        if (req.url.includes('listAvailableTiers') || req.url.includes('isEligible')) {
            return res.end(JSON.stringify({ tiers: [], isEligible: true, ineligibleReason: null }));
        }
        // Catch-all: return eligible response for any unrecognized endpoint
        // so the Desktop never sees an empty response (which it might interpret as ineligible).
        return res.end(JSON.stringify({
            eligible: true,
            ineligibleReason: null,
            allowedTiers: [{ id: "STANDARD", name: "Standard", isDefault: true }],
            currentTier: { id: "STANDARD", hasOnboardedPreviously: true },
            planStatus: { planInfo: { planName: "pro", isEligible: true } },
            userTier: { id: "pro", description: "Pro" }
        }));
    });
});

apiProxyServer.listen(0, '127.0.0.1', () => { agApiPort = apiProxyServer.address().port; });

const _origWhenReady = _elec.app.whenReady;
_elec.app.whenReady = function() {
    return _origWhenReady.call(this).then(() => {
        _elec.session.defaultSession.webRequest.onBeforeRequest({ urls: ['*://*.googleapis.com/*', '*://127.0.0.1:*/*', '*://localhost:*/*'] }, (details, callback) => {
            const urlObj = new URL(details.url);
            if (urlObj.hostname.includes('googleapis.com')) {
                return callback({ redirectURL: `http://127.0.0.1:${agApiPort}${urlObj.pathname}` });
            }
            if (urlObj.port != agProxyPort && !details.url.includes('ag_bypass')) {
                realLsPort = urlObj.port;
                if (details.url.includes('.js') || details.url.includes('.css') || details.url.includes('.png') || details.url.includes('.woff') || details.url.includes('main.js') || details.url.includes('index.html') || details.url.includes('/')) {
                    urlObj.protocol = 'http:'; urlObj.port = agProxyPort; urlObj.searchParams.set('ag_bypass', '1');
                    return callback({ redirectURL: urlObj.toString() });
                }
            }
            callback({});
        });
    });
};
// [/AG_PROXY_HOOK]
"""

    new_content = hook + "\n" + inline_patched + "\n// UNLOCKED"

    try:
        with open(main_js, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        return False, f"Ошибка записи: {e}"

    return True, "OK"


# ---------------------------- Патч extension.js --------------------------------

def patch_extension_js(ext_path: Path) -> Tuple[bool, str]:
    """
    Патчит extension.js (для IDE). Возвращает (успешно, сообщение).
    """
    if not ext_path.exists():
        return False, "Файл не найден"

    try:
        with open(ext_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Ошибка чтения: {e}"

    if "/*[AG_EXT_PATCHED]*/" in content:
        return True, "Уже пропатчено"

    # Сигнатура для extension.js
    pattern = re.compile(
        r'const t=await ([A-Za-z_$][A-Za-z_$0-9.]*)\.UserStatus\.getUserStatus\(\);if\(!t\)return\[\];const n=\(0,([A-Za-z_$][A-Za-z_$0-9.]*)\)\(t,([A-Za-z_$][A-Za-z_$0-9.]*)\),\{email:([A-Za-z_$][A-Za-z_$0-9]*),name:([A-Za-z_$][A-Za-z_$0-9]*)\}=n;return""===([A-Za-z_$][A-Za-z_$0-9]*)\?\[\]:',
        re.DOTALL
    )

    new_content = pattern.sub(
        lambda m: f'const t=await {m.group(1)}.UserStatus.getUserStatus();let {m.group(4)}="",{m.group(5)}="";try{{if(t){{const n=(0,{m.group(2)})(t,{m.group(3)});{m.group(4)}=n.email||"";{m.group(5)}=n.name||"";}}}}catch(_){{}}if({m.group(4)}===""){{{m.group(4)}="antigravity-user";{m.group(5)}="User";}}return false?[]:',
        content
    )

    if new_content == content:
        return False, "Сигнатура не найдена"

    marked = "/*[AG_EXT_PATCHED]*/\n" + new_content
    try:
        with open(ext_path, "w", encoding="utf-8") as f:
            f.write(marked)
    except Exception as e:
        return False, f"Ошибка записи: {e}"

    return True, "OK"


# ---------------------------- Обработка установки Antigravity ------------------

def process_install(install_path: Path) -> Tuple[bool, str]:
    """
    Обрабатывает одну установку Antigravity: завершает процессы, патчит бинарники,
    распаковывает asar, патчит JS-файлы.
    Возвращает (успешно, сообщение).
    """
    # Завершаем процессы
    for proc in ["antigravity", "language_server", "agy"]:
        subprocess.run(["taskkill", "/F", "/IM", f"{proc}.exe"], capture_output=True)
    time.sleep(1)

    # Патчим бинарники
    patch_all_binaries(install_path)

    # Если это CLI (есть agy.exe), то на этом всё
    if (install_path / "agy.exe").exists():
        return True, "Antigravity CLI"

    resources = install_path / "resources"
    app_dir = resources / "app"
    app_asar = resources / "app.asar"

    if app_asar.exists():
        if not extract_asar(app_asar, app_dir):
            return False, "Ошибка распаковки app.asar"

    # Патчим IDE или Desktop
    ide_js = app_dir / "out" / "main.js"
    desktop_js = app_dir / "dist" / "main.js"

    if ide_js.exists():
        ok, msg = patch_ide(ide_js)
        if not ok:
            return False, f"IDE patch: {msg}"
        # extension.js
        ext_js = install_path / "resources" / "app" / "extensions" / "antigravity" / "dist" / "extension.js"
        if ext_js.exists():
            ok2, msg2 = patch_extension_js(ext_js)
            if not ok2 and "Уже" not in msg2:
                print(f"  [WARN] extension.js: {msg2}")
        return True, "Antigravity IDE"
    elif desktop_js.exists():
        ok, msg = patch_desktop(desktop_js)
        if not ok:
            return False, f"Desktop patch: {msg}"
        return True, "Antigravity Desktop"

    return False, "Компоненты приложения не найдены"


def handle_patch_antigravity() -> None:
    """Обработчик пункта меню 1."""
    installs = find_all_installs()
    if not installs:
        print("Установки Antigravity не найдены.")
        time.sleep(2)
        return

    successes = []
    failures = []

    for inst in installs:
        print("--------------------------------------------------")
        print(f"Обработка: {mask_path(str(inst))}")
        ok, msg = process_install(inst)
        if ok:
            print(f"[OK] Успешно пропатчено: {msg}")
            successes.append(msg)
        else:
            print(f"[ERR] Ошибка: {msg}")
            failures.append(f"{mask_path(str(inst))} - {msg}")

    # Применяем NRPT, если есть админские права
    if (successes or failures) and is_admin():
        if not is_nrpt_applied():
            print("\nПатч для Google серверов... ", end="", flush=True)
            if setup_dns_nrpt():
                print("OK")
            else:
                print("пропущено")

    print_results(successes, failures)


# ---------------------------- Gemini CLI патч ----------------------------------

def is_gemini_cli_installed() -> bool:
    """Проверяет, установлен ли Gemini CLI глобально."""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return False
    path = Path(appdata) / "npm" / "node_modules" / "@google" / "gemini-cli"
    return path.exists() and path.is_dir()


def get_system_gemini_api_key() -> Optional[str]:
    """Пытается получить GEMINI_API_KEY из окружения или переменной пользователя."""
    # Проверка env
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key.startswith("AIzaSy") and len(key) == 39:
        return key
    # Проверка через PowerShell
    rc, out, _ = run_powershell("[Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')")
    if rc == 0 and out.startswith("AIzaSy") and len(out) == 39:
        return out
    return None


def get_system_gcloud_project() -> Optional[str]:
    """Получает проект Google Cloud из env или настроек."""
    # Проверка env
    proj = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if proj:
        return proj
    # Проверка через PowerShell
    rc, out, _ = run_powershell("[Environment]::GetEnvironmentVariable('GOOGLE_CLOUD_PROJECT', 'User')")
    if rc == 0 and out:
        return out
    # Проверка settings.json
    settings_path = Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                proj = data.get("project", "")
                if proj:
                    return proj
        except:
            pass
    return None


def is_valid_project_id(proj: str) -> bool:
    """Проверяет валидность Project ID."""
    if not proj:
        return False
    if len(proj) < 4 or len(proj) > 30:
        return False
    return all(c.islower() or c.isdigit() or c == '-' for c in proj)


def update_settings_project_id(project_id: str) -> bool:
    """Обновляет поле project в ~/.gemini/settings.json."""
    settings_path = Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    data["project"] = project_id
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False


def run_gemini_patcher() -> Tuple[bool, str]:
    """
    Запускает встроенный скрипт patch_gemini.py (находится рядом с этим файлом).
    Возвращает (успешно, сообщение).
    """
    # Получаем путь к скрипту patch_gemini.py, предполагая, что он лежит в той же папке
    script_dir = Path(__file__).parent
    script_path = script_dir / "patch_gemini.py"
    if not script_path.exists():
        # Если нет, пробуем создать временный файл с содержимым из строки (но лучше встроить)
        # Здесь мы можем встроить код patch_gemini.py как строку и записать во временный файл.
        # Для простоты предполагаем, что он есть.
        return False, "Файл patch_gemini.py не найден"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, "Успешно"
        else:
            return False, f"Ошибка: {result.stderr.strip()}"
    except Exception as e:
        return False, str(e)


def handle_patch_gemini() -> None:
    """Обработчик пункта меню 2."""
    if not is_gemini_cli_installed():
        print("Gemini CLI не найден.")
        time.sleep(2)
        return

    successes = []
    failures = []

    # NRPT для Gemini
    if is_admin() and not is_nrpt_applied():
        print("\nПатч для Google серверов... ", end="", flush=True)
        if setup_dns_nrpt():
            print("OK")
        else:
            print("пропущено")

    existing_key = get_system_gemini_api_key()
    existing_project = get_system_gcloud_project()

    print("\n" + "=" * 60)
    print("Gemini CLI (разблокировка)")
    if existing_key:
        masked = f"{existing_key[:6]}***{existing_key[-4:]}"
        print(f"  - Нажмите Enter для использования сохранённого ключа ({masked})")
        print("  - Или введите 'skip' для сброса ключа и перехода к OAuth")
        print("  - Или вставьте новый AIzaSy-ключ")
    else:
        print("  - Вставьте AIzaSy-ключ")
        print("  - Или нажмите Enter для пропуска (авторизация через браузер/OAuth)")
    print("-" * 60)

    api_key = ""
    while True:
        inp = input("> ").strip()
        if not inp:
            if existing_key:
                api_key = existing_key
                print(f"Используется сохранённый API-ключ.")
            else:
                print("(пропущено - будет использоваться OAuth)")
            break
        if inp.lower() in ("skip", "oauth"):
            print("(сброшено - будет использоваться OAuth)")
            break
        if inp.startswith("AIzaSy") and len(inp) == 39:
            api_key = inp
            masked = f"{api_key[:6]}***{api_key[-4:]}"
            print(f"API-ключ получен: {masked}")
            break
        else:
            print("Неверный формат. Ожидается AIzaSy (39 символов).")

    print("\n" + "=" * 60)
    print("Google Cloud Project ID (идентификатор проекта)")
    print("Требуется для OAuth. Можно получить в консоли Google.")
    if existing_project:
        print(f"  - Нажмите Enter для использования сохранённого Project ID ({existing_project})")
        print("  - Или введите 'skip' для сброса")
        print("  - Или введите новый Project ID")
    else:
        print("  - Введите Project ID")
        print("  - Или нажмите Enter для пропуска (будет использован cloudshell-gca)")
    print("-" * 60)

    project_id = ""
    while True:
        inp = input("> ").strip()
        if not inp:
            if existing_project:
                project_id = existing_project
                print(f"Используется сохранённый Project ID: {project_id}")
            else:
                print("(пропущено - по умолчанию cloudshell-gca)")
            break
        if inp.lower() in ("skip", "default"):
            print("(сброшено)")
            break
        if is_valid_project_id(inp):
            project_id = inp
            print(f"Project ID получен: {project_id}")
            break
        else:
            print("Неверный формат. Допустимы: строчные латиница, цифры, дефис, длина 4-30.")

    # Устанавливаем переменные окружения
    if api_key:
        run_powershell(f"[Environment]::SetEnvironmentVariable('GEMINI_API_KEY', '{api_key}', 'User')")
    else:
        run_powershell("[Environment]::SetEnvironmentVariable('GEMINI_API_KEY', $null, 'User')")
    if project_id:
        run_powershell(f"[Environment]::SetEnvironmentVariable('GOOGLE_CLOUD_PROJECT', '{project_id}', 'User')")
        update_settings_project_id(project_id)
    else:
        run_powershell("[Environment]::SetEnvironmentVariable('GOOGLE_CLOUD_PROJECT', $null, 'User')")

    print("--------------------------------------------------")
    print("Разблокировка Gemini CLI...")
    ok, msg = run_gemini_patcher()
    if ok:
        print("[OK] Gemini CLI успешно разблокирован!")
        successes.append("Gemini CLI")
    else:
        print(f"[ERR] Ошибка разблокировки: {msg}")
        failures.append(f"Gemini CLI - {msg}")

    print_results(successes, failures)


# ---------------------------- Вывод результатов --------------------------------

def print_results(successes: List[str], failures: List[str]) -> None:
    """Выводит итоги операций."""
    print("\n" + "=" * 60)
    print("ИТОГИ:")
    if successes:
        print("Успешно разблокированы:")
        for s in successes:
            print(f"  [+] {s}")
    if failures:
        print("Ошибки:")
        for f in failures:
            print(f"  [-]{f}")
    print("=" * 60)
    print("Чтобы вернуться в главное меню, нажмите Enter")
    input()


# ---------------------------- Главное меню -------------------------------------

def show_admin_warning() -> None:
    """Показывает предупреждение, если программа запущена без прав администратора."""
    clear_screen()
    print(APP_TITLE)
    print()
    print("Внимание: программа запущена без прав администратора.")
    print()
    print("Без админ-прав будут сняты только клиентские региональные")
    print("ограничения. Серверный патч (NRPT) требует повышенных привилегий")
    print("и будет пропущен.")
    print()
    print("Если вы находитесь в санкционной территории и упираетесь")
    print("в 'User location is not supported' — закройте окно и")
    print("запустите программу от имени Администратора.")
    print()
    input("Нажмите Enter чтобы продолжить...")


def main() -> None:
    # Установка заголовка окна консоли (только Windows)
    if sys.platform == "win32":
        os.system(f"title Antigravity Unlocker v{APP_VERSION}")
        # Попытка включить режим виртуального терминала
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except:
            pass

    if not is_admin():
        show_admin_warning()

    while True:
        clear_screen()
        print(APP_TITLE)
        print()
        print("1. Разблокировать Antigravity / Antigravity IDE / Antigravity CLI")
        print("2. Разблокировать Gemini CLI")
        print("3. Отменить NRPT-патч (отключит исправление ошибок '400')")
        print("0. Выход")
        print()
        if not is_admin():
            print("Запущено без админ-прав: серверный патч будет пропущен.")
            print()
        choice = input("> ").strip()

        if choice == "1":
            handle_patch_antigravity()
        elif choice == "2":
            handle_patch_gemini()
        elif choice == "3":
            handle_restore_dns()
        elif choice == "0":
            break
        else:
            print("Неверный выбор.")
            time.sleep(1)


if __name__ == "__main__":
    main()