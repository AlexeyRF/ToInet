# ToInet-MAX — Лаунчер для СОБ (ByeDPI, TGWS, Tor, Opera, VLESS, EVPN, SSH)

<p align="center">
  <img src="icon.ico" width="128" height="128" alt="ToInet Logo">
</p>

**ToInet-MAX** — это менеджер для обеспечения свободного и быстрого доступа в интернет в операционной системе Windows (доступна также [версия для Android](https://github.com/AlexeyRF/ToInet-Mobile)). Программа объединяет в едином интерфейсе передовые инструменты обхода блокировок: **ByeDPI**, **Tor**, **Telegram WebSocket Proxy (TGWS)**, **Умный шлюз-маршрутизатор Gatik**, **Opera Proxy**, **VLESS / EVPN (sing-box)**, **Защищенный SSH SOCKS5 Туннель**, **SOCKS-реабилитатор** и фоновый генератор сетевого шума.

---

## Основная цель проекта

> [!IMPORTANT]
> **Главная миссия ToInet-MAX** — предоставление свободного, стабильного и безопасного доступа к интернету широким массам пользователей без необходимости обладать глубокими техническими знаниями, а также **максимальная экономия трафика, отправляемого на собственный VPS**.
> 
> Большинство коммерческих VPN и приватных серверов имеют строгие лимиты пропускной способности или тарифицируются за каждый переданный гигабайт. ToInet-MAX решает эту проблему за счет интеллектуальной гибридной маршрутизации:
> 1. **Локальный DPI-обход (ByeDPI):** тяжелый контент (видеохостинги, стриминг, веб-серфинг) разблокируется прямо на вашем компьютере с помощью фрагментации и модификации TCP/HTTP/TLS пакетов без передачи внешнего трафика на ваш сервер.
> 2. **Бесплатные внешние шлюзы (Tor, Opera Proxy, TGWS, Gatik):** сервисы обхода, не расходующие лимиты вашего VPS.
> 3. **Точечный туннелинг (SSH / VLESS):** защищенное подключение к собственному VPS используется только при необходимости, обеспечивая колоссальную экономию сетевого трафика и расходов на серверную инфраструктуру.

---

## Основные возможности

*   **DPI-обход через ByeDPI (`ciadpi.exe`):**
    *   Локальный SOCKS5-прокси, модифицирующий сетевые пакеты для обхода систем глубокого анализа трафика (DPI/ТСПУ).
    *   Гибкая настройка параметров запуска через кастомные профили или встроенные стратегии.
    *   **Отдельное проксирование для Pip (PyPI):** ускорение и разблокировка установки пакетов Python.
*   **Интеграция с Tor (`tor.exe`):**
    *   Автоматизированное управление локальным луковым маршрутизатором.
    *   Поддержка подключаемых транспортов (obfs4, webtunnel, snowflake) и встроенный редактор мостов (`bridges.txt`).
    *   Управление цепочками (запрос нового маршрута `/NEWNYM` в один клик или сочетанием клавиш).
*   **Защищенный SSH SOCKS5 Туннель (`ssh_tunnel.exe` на C++):**
    *   Высокопроизводительный нативный C++ туннель через системный OpenSSH Windows (`ssh.exe -D`).
    *   **Полная конфигурируемость без хардкода:** хост, SSH-порт, логин, пароль и локальный SOCKS-порт настраиваются через удобное графическое окно или файл конфигурации.
    *   **Безопасный AskPass:** пароли безопасно передаются напрямую в процесс SSH без интерактивных консольных окон.
    *   Автопереподключение при обрыве связи и привязка к Windows Job Object (чистое фоновое завершение всех процессов).
*   **Telegram WebSocket Proxy (TGWS) & MTProto:**
    *   Локальный прокси-сервер для туннелирования трафика Telegram через WebSocket и HTTPS.
    *   **Умное мультиплексирование:** одновременная работа в режимах **SOCKS5** и **MTProto** на едином порту (`1480`).
    *   Поддержка секретов MTProto и маскировки под Fake TLS домены.
    *   Мгновенное добавление прокси в Telegram Desktop в один клик.
*   **Умный шлюз-маршрутизатор Gatik (`gatik.exe` на C++):**
    *   Нативная C++ разработка для динамической маршрутизации и ускорения трафика Telegram.
    *   Анализирует соединения "на лету" и балансирует поток данных между различными шлюзами.
*   **Opera Proxy (`opera-proxy.windows-amd64.exe`):**
    *   Локальный SOCKS5/HTTP прокси, использующий защищенную инфраструктуру Opera.
    *   Поддержка пула соединений (Load Balancing) и выбора региона (Европа, Америка, Азия).
*   **VLESS и EVPN (ядро `sing-box`):**
    *   Поддержка современных протоколов VLESS Reality, Trojan, ShadowTLS.
    *   Менеджер подписок EVPN с поддержкой динамической ротации серверов, проверки задержки и защищенного DNS.
*   **Тестер стратегий ByeDPI (`byedpi_tester_gui.pyw`):**
    *   Автоматический перебор и тестирование стратегий обхода под особенности вашего интернет-провайдера.
*   **Генератор сетевого шума Noisy (`noisy.py`):**
    *   Создает правдоподобный фоновый трафик для маскировки паттернов активности пользователя от провайдерских систем анализа.
*   **Системные утилиты C++:**
    *   `cpller.exe` — мгновенное переключение системных параметров прокси Windows (WinINet / Internet Settings).
    *   Управление системным DNS (Comms DNS, Xbox DNS, сброс) и фикс сервисов Google Antigravity (Agy Fix).

---

## Интерфейс приложения

ToInet-MAX поддерживает два режима графического интерфейса:
1. **Современное окно приложения (Modern Window):** стильный минималистичный интерфейс на PyQt5 с центральной кнопкой включения, выбором режимов, мониторингом статуса и быстрым доступом ко всем модулям.
2. **Продвинутое меню трея (System Tray):** компактный доступ ко всем функциям через значок в системном трее Windows:
   * **Простой режим:** запуск и остановка всех инструментов в один клик, быстрое подключение системного прокси к выбранному источнику (TOR, ByeDPI, Opera, SSH).
   * **Продвинутый режим:** индивидуальное управление каждым сервисом (запуск, остановка, перезапуск), открытие настроек, быстрая отправка прокси в Telegram.

---

## Режимы маршрутизации трафика

В программе реализованы четыре ключевых режима работы с сетью:

1. **Empty (Пустой режим):**
   * Все выбранные инструменты работают на локальных портах в фоне.
   * Системные сетевые параметры Windows не изменяются.
   * *Применение:* индивидуальная настройка конкретных приложений (браузерные расширения FoxyProxy/SwitchyOmega, Telegram, торрент-клиенты).
2. **Inetcpl (Свойства браузера Windows):**
   * Автоматически прописывает локальный прокси в системные параметры Windows через нативную утилиту `cpller.exe`.
   * *Применение:* браузеры (Chrome, Edge, Yandex, Opera, Firefox) сразу начинают работать через выбранный шлюз без дополнительных плагинов. При выходе настройки корректно сбрасываются.
3. **TUN (Режим полного туннелирования):**
   * Направляет весь сетевой стек операционной системы через ядро `sing-box` или внешний проксификатор (**Proxifier**).
   * *Применение:* игры, лаунчеры, голосовые чаты (Discord, Steam, Spotify), не имеющие встроенных настроек прокси.
4. **EVPN (Режим подписок):**
   * Глобальная маршрутизация трафика через пулы проверенных VLESS-узлов с автоматическим переключением при сбоях.

---

## Сетевые порты по умолчанию

| Модуль / Протокол | Порт | Тип прокси | Назначение |
| :--- | :--- | :--- | :--- |
| **ByeDPI (Главный)** | `1780` | SOCKS5 | Основной локальный DPI-обходчик |
| **ByeDPI (HTTP)** | `1782` | HTTP | HTTP-мост для ByeDPI |
| **ByeDPI (Pip PyPI)**| `1781` | SOCKS5 | Выделенный порт для пакетного менеджера pip |
| **Tor (Главный)** | `9853` | SOCKS5 | Луковый маршрутизатор Tor |
| **Tor (HTTP)** | `9854` | HTTP | HTTP-мост для сети Tor |
| **Tor Control Port** | `9851` | TCP | Управление цепочками и смена IP Tor |
| **SSH Tunnel** | `1770` | SOCKS5 | Защищенный SSH-туннель к вашему серверу (C++ / OpenSSH) |
| **Opera Proxy** | `1785` | HTTP / SOCKS5 | Скоростной прокси через инфраструктуру Opera |
| **Telegram WS (TGWS)**| `1480`| SOCKS5 & MTProto | Мультиплексированный прокси для Telegram Desktop |
| **Gatik Router** | `1777` | SOCKS5 | C++ балансировщик и акселератор для Telegram |
| **VLESS / EVPN** | `1790` | SOCKS5 | Прокси через внешние VLESS-серверы sing-box |
| **SOCKS-реабилитатор**| `1788` | SOCKS5 | Сервис восстановления нестабильных socks-соединений |

---

## Установка и запуск

### Системные требования:
* Операционная система: **Windows 10 / Windows 11** (x64 / ARM64).
* OpenSSH Client (встроен в Windows по умолчанию в «Дополнительных компонентах»).
* Для Python-версии: **Python 3.8+** (с отметкой «Add Python to PATH»).

### Быстрый старт:
1. Скачайте архив релиза (или клонируйте репозиторий).
2. Для запуска из исходников запустите `install.bat` (установит зависимости `PyQt5`, `psutil`, `requests`, `cryptography` и др.), затем `launch.bat`.
3. Для Portable-версии просто запустите `ToInet.exe`.

### Сборка C++ утилит:
Скомпилировать нативные высокоскоростные утилиты (`cpller.exe`, `gatik.exe`, `ssh_tunnel.exe`) можно одним кликом через:
```cmd
cpp\build.bat
```
Скрипт автоматически найдет установленный Visual Studio MSVC (`cl.exe`) или `g++` и соберет оптимизированные бинарники в папку `bin/`.

---

## Настройка SSH Туннеля

Для подключения к вашему VPS:
1. Откройте **«Настройки SSH Туннеля»** из меню трея или через окно настроек приложения.
2. Введите параметры вашего сервера:
   * **Хост / IP:** адрес вашего VPS.
   * **SSH Порт:** порт службы SSH (по умолчанию `22`).
   * **Логин:** ваш пользователь (например, `root`).
   * **Пароль:** пароль учетной записи.
   * **Локальный порт:** порт локального SOCKS5-прокси (по умолчанию `1770`).
3. Нажмите **«Сохранить»** и **«Запустить туннель»**.
4. Доступны быстрые кнопки:
   * **«Добавить в Telegram»** — моментально открывает Telegram Desktop с преднастроенным SOCKS5.
   * **«Направить систему (inetcpl)»** — переключает глобальный системный браузерный интернет на ваш SSH SOCKS5.
   * **«Скопировать SOCKS5»** — помещает адрес `socks5://127.0.0.1:1770` в буфер обмена.

---

## Решение проблем

> [!TIP]
> **При аварийном закрытии пропал интернет:**
> Если приложение было завершено аварийно в режиме `inetcpl`, снимите галочку системного прокси: *Параметры Windows -> Сеть и Интернет -> Прокси-сервер -> Использовать прокси-сервер (Откл)*, либо запустите ToInet снова и выполните пункт *Очистка кеша*.

> [!TIP]
> **Бесконечное подключение Tor:**
> Провайдер может блокировать стандартные публичные узлы. Откройте пункт *«Изменить мосты»* в расширенном меню и добавьте свежие мосты (их можно получить у бота `@GetBridgesBot` в Telegram).

---

## Правовая оговорка и благодарности

Проект создан исключительно в целях обеспечения надежного доступа к информации и оптимизации расхода серверных мощностей:
* https://github.com/hufrea/byedpi — ByeDPI
* https://torproject.org — The Tor Project
* https://github.com/Flowseal/tg-ws-proxy — TG WS Proxy
* https://github.com/SagerNet/sing-box — Sing-box core
* https://github.com/Alexey71/opera-proxy — Opera proxy

---
---

# English Translation

## ToInet-MAX — Censorship Bypass Launcher & Traffic Saver

<p align="center">
  <img src="icon.ico" width="128" height="128" alt="ToInet Logo">
</p>

**ToInet-MAX** is a comprehensive network manager and multi-tool designed to restore open, unrestricted, and privacy-respecting Internet access on Windows OS (also available: [Android version](https://github.com/AlexeyRF/ToInet-Mobile)). The application unites the most effective anti-censorship and tunneling tools into a single coherent interface: **ByeDPI**, **Tor**, **Telegram WebSocket Proxy (TGWS)**, **Gatik Smart Gateway Router**, **Opera Proxy**, **VLESS / EVPN (sing-box core)**, **Secure SSH SOCKS5 Tunnel**, **SOCKS Rehabilitator**, and background traffic obfuscation.

---

## 🎯 Primary Project Mission: Mass Access & VPS Bandwidth Savings

> [!IMPORTANT]
> **The primary goal of ToInet-MAX** is to bring seamless, free Internet access to the general public while **drastically saving bandwidth on your personal VPS**.
>
> Most private VPS providers and commercial VPN services impose strict monthly data quotas or charge per gigabyte. ToInet-MAX eliminates excessive server costs via smart hybrid routing:
> 1. **Local DPI Evasion (ByeDPI):** Heavy bandwidth consumers (streaming platforms, video hostings, web media) are unblocked locally on your machine via TCP/HTTP/TLS packet manipulation, avoiding any VPS traffic consumption.
> 2. **Free External Pathways (Tor, Opera Proxy, TGWS, Gatik):** Public and resilient routing backends that require zero VPS resources.
> 3. **Targeted Tunneling (SSH / VLESS):** Your private VPS is utilized only when encrypted off-shore tunneling is strictly necessary, conserving your VPS bandwidth and minimizing hosting costs.

---

## 🌟 Core Features

*   **DPI Bypass via ByeDPI (`ciadpi.exe`):**
    *   Runs a local SOCKS5 proxy modifying TCP/TLS frames to bypass Deep Packet Inspection systems without external proxy servers.
    *   Custom strategies and automated tuning via `byedpi_tester_gui.pyw`.
    *   **Dedicated Pip (PyPI) proxy:** Fast and reliable Python package management.
*   **Tor Integration (`tor.exe`):**
    *   Full lifecycle management for the Tor onion routing daemon.
    *   Pluggable Transports (obfs4, webtunnel, snowflake) and built-in bridge configuration editor.
    *   Circuit renewal (`/NEWNYM`) on demand with shortcut support.
*   **Secure SSH SOCKS5 Tunnel (`ssh_tunnel.exe` in C++):**
    *   Native C++ OpenSSH supervisor utilizing Windows `ssh.exe -D`.
    *   **Zero hardcoded credentials:** Server host, port, username, password, and local SOCKS port are entirely configurable via GUI and config file.
    *   **Silent AskPass integration:** Passwords are delivered directly and securely without intrusive terminal dialogs.
    *   Auto-reconnect resilience and Windows Job Object assignment for clean shutdown.
*   **Telegram WebSocket Proxy (TGWS) & MTProto:**
    *   Multiplexes SOCKS5 and MTProto connections on a single port (`1480`).
    *   Fake TLS domain and MTProto secret configuration.
    *   One-click instant import into Telegram Desktop.
*   **Gatik Smart Router (`gatik.exe` in C++):**
    *   High-performance dynamic load balancer designed to optimize Telegram connections between multiple proxies.
*   **Opera Proxy (`opera-proxy`):**
    *   Fast SOCKS5/HTTP tunnel utilizing Opera's global infrastructure with region selection and connection pooling.
*   **VLESS & EVPN Routing (`sing-box`):**
    *   VLESS Reality, Trojan, and subscription management with auto-latency verification.
*   **Native C++ Utilities:**
    *   `cpller.exe` — Instant Windows Internet Settings (WinINet) proxy management.
    *   DNS management (Comms DNS, Xbox DNS, reset) and Google Antigravity unblocking (Agy Fix).

---

## 🔌 Default Network Ports

| Tool / Protocol | Port | Proxy Type | Description |
| :--- | :--- | :--- | :--- |
| **ByeDPI (Main)** | `1780` | SOCKS5 | Local DPI evasion proxy |
| **ByeDPI (HTTP)** | `1782` | HTTP | HTTP bridge for ByeDPI |
| **ByeDPI (Pip PyPI)**| `1781` | SOCKS5 | Dedicated proxy for Python pip |
| **Tor (Main)** | `9853` | SOCKS5 | Onion router SOCKS proxy |
| **Tor (HTTP)** | `9854` | HTTP | HTTP bridge for Tor |
| **Tor Control Port** | `9851` | TCP | Circuit control & identity renewal |
| **SSH Tunnel** | `1770` | SOCKS5 | Secure OpenSSH dynamic proxy (C++) |
| **Opera Proxy** | `1785` | HTTP / SOCKS5 | Fast tunnel via Opera VPN infrastructure |
| **Telegram WS (TGWS)**| `1480`| SOCKS5 & MTProto | Telegram multiplexed proxy |
| **Gatik Router** | `1777` | SOCKS5 | C++ dynamic Telegram balancer |
| **VLESS / EVPN** | `1790` | SOCKS5 | SOCKS5 proxy via remote sing-box nodes |
| **SOCKS Rehabilitator**| `1788` | SOCKS5 | Connection recovery port |

---

## 🔨 Building and Running

1. **Python version:** Run `install.bat`, then `launch.bat`.
2. **Portable version:** Run `ToInet.exe`.
3. **Compiling C++ Utilities:**
   ```cmd
   cpp\build.bat
   ```
   Compiles `cpller.exe`, `gatik.exe`, `ssh_tunnel.exe`, and `programs_settings.exe` directly into `bin/` using MSVC or GCC.


---

## 🇫🇷 Traduction en français (Documentation)

# ToInet-MAX — Gestionnaire universel de contournement et de routage (ByeDPI, TGWS, Tor, Opera, VLESS, EVPN, SSH)

<p align="center">
  <img src="icon.ico" width="128" height="128" alt="Logo ToInet">
</p>

**ToInet-MAX** est une suite complète conçue pour garantir un accès libre, rapide et sécurisé à Internet sous Windows (une [version Android](https://github.com/AlexeyRF/ToInet-Mobile) est également disponible). Elle réunit dans une interface unifiée les technologies les plus efficaces : **ByeDPI**, **Tor**, **Telegram WebSocket Proxy (TGWS)**, **Routeur intelligent Gatik**, **Opera Proxy**, **VLESS / EVPN (sing-box)**, **Tunnel sécurisé SSH SOCKS5**, **Réhabilitateur SOCKS** et un générateur de bruit réseau.

---

### Objectif principal du projet

> [!IMPORTANT]
> **La mission fondamentale de ToInet-MAX** est d'offrir un accès à Internet libre, stable et sécurisé au plus grand nombre d'utilisateurs sans nécessiter de compétences techniques avancées, tout en assurant une **économie maximale de la bande passante envoyée vers votre propre VPS**.
> 
> La majorité des fournisseurs de VPS et VPN privés appliquent des limites strictes de données ou facturent chaque gigaoctet transféré. ToInet-MAX résout ce problème grâce à un routage hybride et intelligent :
> 1. **Contournement DPI local (ByeDPI) :** les contenus volumineux (vidéos, streaming, navigation web courante) sont débloqués directement sur votre machine locale par fragmentation et modification des paquets TCP/TLS, sans consommer le trafic de votre serveur distant.
> 2. **Passerelles publiques gratuites (Tor, Opera Proxy, TGWS, Gatik) :** services de déblocage autonomes qui ne décomptent aucun quota sur votre VPS.
> 3. **Tunneling ciblé (SSH / VLESS) :** la connexion chiffrée vers votre serveur privé n'est sollicitée que pour les flux nécessaires, réduisant drastiquement les coûts d'infrastructure.

---

### Fonctionnalités principales

*   **Contournement DPI local avec ByeDPI (`ciadpi.exe`) :**
    *   Proxy SOCKS5 local modifiant les trames TCP/TLS pour déjouer les filtres d'inspection profonde (DPI).
    *   Profils et stratégies ajustables avec outil de test graphique intégré (`byedpi_tester_gui.pyw`).
    *   **Proxy dédié pour Pip (PyPI) :** accélération et déblocage de l'installation des paquets Python.
*   **Intégration complète de Tor (`tor.exe`) :**
    *   Gestion automatisée du démon de routage en oignon.
    *   Support des transports enfichables (obfs4, webtunnel, snowflake) et éditeur graphique de ponts (`bridges.txt`).
    *   Renouvellement instantané des circuits (`/NEWNYM`) par raccourci clavier ou clic droit.
*   **Tunnel SSH SOCKS5 sécurisé (`ssh_tunnel.exe` en C++) :**
    *   Superviseur natif C++ pilotant l'OpenSSH natif de Windows (`ssh.exe -D`).
    *   **Aucun identifiant codé en dur :** serveur, port SSH, nom d'utilisateur, mot de passe et port SOCKS local sont entièrement configurables via l'interface graphique et le fichier `config.json`.
    *   **Sécurité AskPass & Clé éphémère :** chiffrement du mot de passe en mémoire avec suppression instantanée de la clé de déchiffrement dès l'ouverture du tunnel (aucun mot de passe visible dans le gestionnaire des tâches).
    *   Reconnexion automatique et gestion de processus Windows Job Object (nettoyage garanti à l'arrêt).
*   **Gestionnaire unifié des chemins de programmes (`programs_settings.exe` en C++) :**
    *   Application graphique native C++ (Win32 & DWM Dark Mode) regroupant la configuration du Proxificateur (TUN) et des programmes additionnels.
    *   Accessible directement via le bouton **"Пути программ"** (**"Program Paths"** / **"Chemins des programmes"**).
*   **Telegram WebSocket Proxy (TGWS) & MTProto :**
    *   Multiplexage intelligent : prise en charge simultanée de **SOCKS5** et **MTProto** sur le même port (`1480`).
    *   Support du Fake TLS et secrets MTProto.
    *   Importation directe dans Telegram Desktop en un seul clic.
*   **Routeur dynamique Gatik (`gatik.exe` en C++) :**
    *   Équilibreur de charge haute performance pour optimiser les connexions Telegram.
*   **Opera Proxy (`opera-proxy`) :**
    *   Tunnel rapide SOCKS5/HTTP s'appuyant sur l'infrastructure mondiale d'Opera avec sélection de région.
*   **Routage VLESS & EVPN (`sing-box`) :**
    *   Gestion des protocoles VLESS Reality, Trojan, ShadowTLS et vérification automatique de latence.
*   **Utilitaires natifs C++ :**
    *   `cpller.exe` — Application instantanée des paramètres proxy système Windows (WinINet).
    *   Gestion DNS (Comms DNS, Xbox DNS, réinitialisation) et déblocage de Google Antigravity.
*   **Interface multilingue unifiée :**
    *   Prise en charge intégrale du **Français**, de l'**Anglais** et du **Russe** avec détection automatique du système ou sélection manuelle dans les paramètres.

---

### 🔌 Tableau des ports réseau par défaut

| Outil / Protocole | Port | Type de Proxy | Description |
| :--- | :--- | :--- | :--- |
| **ByeDPI (Principal)** | `1780` | SOCKS5 | Contournement DPI local |
| **ByeDPI (HTTP)** | `1782` | HTTP | Pont HTTP pour ByeDPI |
| **ByeDPI (Pip PyPI)** | `1781` | SOCKS5 | Proxy dédié aux paquets Python |
| **Tor (Principal)** | `9853` | SOCKS5 | Proxy SOCKS du réseau Tor |
| **Tor (HTTP)** | `9854` | HTTP | Pont HTTP pour le réseau Tor |
| **Tor Control Port** | `9851` | TCP | Port de contrôle & renouvellement des circuits |
| **SSH Tunnel** | `1770` | SOCKS5 | Proxy dynamique OpenSSH sécurisé (C++) |
| **Opera Proxy** | `1785` | HTTP / SOCKS5 | Tunnel via l'infrastructure Opera VPN |
| **Telegram WS (TGWS)** | `1480` | SOCKS5 & MTProto | Proxy multiplexé pour Telegram |
| **Routeur Gatik** | `1777` | SOCKS5 | Équilibreur dynamique C++ pour Telegram |
| **VLESS / EVPN** | `1790` | SOCKS5 | Proxy SOCKS5 vers nœuds sing-box distants |
| **Réhabilitateur SOCKS** | `1788` | SOCKS5 | Port de rétablissement de connexion |

---

### 🔨 Compilation et exécution

1. **Version Python :** Exécutez `install.bat`, puis `launch.bat`.
2. **Version portable :** Lancez `ToInet.exe`.
3. **Compilation des outils C++ :**
   ```cmd
   cpp\build.bat
   ```
   Compile `cpller.exe`, `gatik.exe`, `ssh_tunnel.exe` et `programs_settings.exe` directement dans le dossier `bin/` avec MSVC ou GCC.
