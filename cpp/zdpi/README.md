# zDPI — Продвинутый ByeDPI с движком Zapret2 для Windows

**zDPI** — это гибридный высокопроизводительный локальный SOCKS4/5 прокси-сервер для Windows, объединяющий лучшие возможности проектов [ByeDPI (ciadpi)](https://github.com/hufrea/byedpi) и [Zapret2 (zapret)](https://github.com/bol-van/zapret2).

---

## 🌟 Ключевые преимущества

1. **Чистый User-Space (Без драйверов и прав Администратора)**:
   - В отличие от оригинального Zapret на Windows, которому требуется драйвер ядра `WinDivert.sys`, тестовый режим подписи драйверов или права администратора, zDPI работает полностью в пространстве пользователя через сокеты Winsock2.
2. **Продвинутый L7-диссектор из Zapret2**:
   - Полный разбор протоколов TLS ClientHello, HTTP/1.x, QUIC Initial, Discord, WireGuard.
   - Поддержка динамических маркеров Zapret: `midsld` (середина SLD домена), `sld`, `endsld`, `sniext`, `sni`, `endsni`, `extlen`, `method`.
3. **Встроенные современные Fake-шаблоны Zapret2**:
   - В бинарник встроены актуальные бинарные шаблоны фальшивых пакетов: `fake_tls_google`, `fake_tls_kyber`, `fake_tls_rutracker`, `fake_http_iana`, `fake_quic_google`, `fake_discord_ip_discovery`.
4. **QUIC Drop (`--quic-drop`)**:
   - Мгновенный сброс QUIC Initial пакетов при UDP Associate, заставляющий браузеры (Chrome, Edge, Firefox) немедленно переключаться на TCP HTTP/2 с TLS обходом (критично для стабильного воспроизведения YouTube 4K/8K без задержек буферизации).
5. **Готовые пресеты в один клик**:
   - `--preset general` — универсальный режим (YouTube, Discord, заблокированные сайты).
   - `--preset youtube` — максимальная оптимизация под YouTube (Google Video CDN, `midsld` split, Kyber fake).
   - `--preset discord` — оптимизация для голосовых каналов, медиа и шлюзов Discord.

---

## 🚀 Быстрый старт

Просто запустите один из готовых командных файлов:
- **`start_zdpi.bat`** — запуск универсального режима (порт 1080).
- **`start_youtube.bat`** — запуск режима YouTube (порт 1080).
- **`start_discord.bat`** — запуск режима Discord (порт 1080).

Или выполните в командной строке:
```cmd
zdpi.exe
```
*(По умолчанию без параметров запускается универсальный пресет на `127.0.0.1:1080`)*.

---

## ⚙️ Настройка приложений и браузера

После запуска zDPI слушает локальный SOCKS5 порт: `127.0.0.1:1080`.

### Google Chrome / Brave / Edge / Яндекс.Браузер
Используйте расширение (например, **SwitchyOmega**, **ZeroOmega** или **FoxyProxy**):
- Протокол: **SOCKS5**
- Сервер: `127.0.0.1`
- Порт: `1080`

Либо запустите браузер с параметром командной строки:
```cmd
chrome.exe --proxy-server="socks5://127.0.0.1:1080"
```

### Mozilla Firefox
1. Настройки -> Основные -> Параметры сети -> Настроить...
2. Выберите **Ручная настройка прокси**.
3. Узел SOCKS: `127.0.0.1`, Порт: `1080`, версия: **SOCKS v5**.
4. Включите галочку: **«Отправлять DNS-запросы через прокси при использовании SOCKS v5»**.

### Discord
В клиентах с поддержкой прокси укажите SOCKS5 `127.0.0.1:1080`, либо используйте системные утилиты вроде Proxifier для направления трафика `Discord.exe` через zDPI.

---

## 📖 Параметры командной строки

zDPI поддерживает как синтаксис ByeDPI, так и синтаксис Zapret:

```text
ПРЕСЕТЫ:
    --preset <name>           Готовая стратегия: youtube, discord, general
                              (По умолчанию: general)

ОПЦИИ ZAPRET2:
    --dpi-desync <modes>      Режимы десинхронизации (через запятую):
                              fake, split, disorder, fakedsplit, fakeddisorder,
                              multisplit, tlsrec, oob
    --dpi-desync-split-pos <p>Позиции/маркеры разреза:
                              midsld, sld, endsld, sniext, sni, endsni, extlen, method
                              (или числовое смещение)
    --dpi-desync-ttl <num>    TTL для fake-пакетов (по умолчанию: 3)
    --dpi-desync-fake-tls <t> Шаблон TLS fake: google, kyber, rutracker, путь к файлу или hex
    --dpi-desync-fake-quic <t>Шаблон QUIC fake: google, путь к файлу или hex
    --dpi-desync-fake-sni <s> Подмена SNI в fake-пакетах
    --quic-drop, --drop-quic  Сброс QUIC Initial для форсирования TCP HTTP/2
    --wsize <size_kb>         Ограничение размера окна TCP

ОПЦИИ BYEDPI:
    -i, --ip <ip>             IP адрес для прослушивания (по умолчанию: 127.0.0.1)
    -p, --port <num>          Порт для прослушивания (по умолчанию: 1080)
    -c, --max-conn <count>    Максимальное количество соединений (по умолчанию: 512)
    -b, --buf-size <size>     Размер буфера (по умолчанию: 16384)
    -x, --debug <level>       Уровень отладочных сообщений: 0, 1 или 2
    -g, --def-ttl <num>       TTL для исходящих соединений
    -s, --split <pos_t>       Разрезать на позиции
    -d, --disorder <pos_t>    Разрезать и отправить в обратном порядке
    -f, --fake <pos_t>        Разрезать и отправить fake-пакет
    -r, --tlsrec <pos_t>      Создать TLS-запись на позиции
    -t, --ttl <num>           TTL fake-пакетов
    -n, --fake-sni <str>      Поддельный SNI
    -M, --mod-http <mods>     Модификации HTTP: h (hostcase), d (domcase), r (reverse),
                              m (methodeol), u (unixeol), t (tab)
    -A, --auto <t,r,s,n,c>    Авто-определение блокировок: torst, redirect, ssl_err
    -H, --hosts <file|:str>   Белый список хостов
    -j, --ipset <file|:str>   Белый список IP
    -U, --no-udp              Отключить поддержку UDP Associate
    -N, --no-domain           Отключить резолв доменов
```

---

## 🛠️ Сборка из исходников

Для пересборки проекта на Windows необходим MinGW-w64:

```bash
mingw32-make clean
mingw32-make -j4
```

Сборка компилирует бинарный файл `zdpi.exe`, зависящий только от стандартных системных библиотек Windows (`ws2_32.dll`, `mswsock.dll`, `advapi32.dll`).
