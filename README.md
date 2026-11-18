# ToInet-MAX

<p align="center">
  <a href="#русский">Русский</a> •
  <a href="#english">English</a> •
  <a href="#français">Français</a>
</p>

---

## Русский

**ToInet-MAX** — универсальный лаунчер и менеджер инструментов обхода сетевых ограничений для Windows.  
Доступна также [версия для Android](https://github.com/AlexeyRF/ToInet-Mobile).

Проект создан для свободного доступа в сеть и **максимальной экономии трафика вашего VPS**: ресурсоемкий контент (видеохостинги, стриминг, веб-серфинг) обходится локально или через бесплатные публичные шлюзы, а защищенный туннель к личному серверу задействуется только при реальной необходимости.

### Основные возможности

* **zDPI:** локальный обход DPI (десинхронизация и фрагментация TCP/HTTP/TLS/QUIC) прямо на компьютере без внешних серверов.
* **Tor:** анонимная маршрутизация трафика с поддержкой мостов и подключаемых транспортов (obfs4, snowflake, conjure).
* **TGWS & Gatik:** MTProto-проксирование через веб-сокеты и динамический SOCKS5-шлюз для Telegram.
* **Opera Proxy:** быстрый прокси-туннель через распределенную инфраструктуру Opera.
* **EVPN (sing-box):** современные протоколы (VLESS Reality, Trojan) с поддержкой подписок.
* **SSH SOCKS5 Туннель:** защищенное подключение к собственному VPS на базе C++ и нативного Windows OpenSSH.

### Как запускать

* **One-File версия:** запустите `ToInet-MAX-one_file_amd64.exe` (всё включено в один исполняемый файл, установка не требуется).
* **Portable-версия:** запустите `ToInet.exe` внутри распакованной папки релиза.
* **Из исходников (Python 3.8 – 3.14+):** запустите `launch.bat` или `main.pyw` — все необходимые зависимости (PySide6, requests, cryptography и др.) установятся автоматически при первом старте.

### Авторы используемых средств обхода

* **ByeDPI** — [hufrea](https://github.com/hufrea/byedpi)
* **Zapret2** — [bol-van](https://github.com/bol-van/zapret2) *(L7-диссекторы и desync-техники в zDPI)*
* **Tor** — [The Tor Project](https://www.torproject.org/)
* **TG WS Proxy** — [Flowseal](https://github.com/Flowseal/tg-ws-proxy)
* **sing-box** — [SagerNet](https://github.com/SagerNet/sing-box)
* **Opera Proxy** — [Alexey71](https://github.com/Alexey71/opera-proxy)
* **Подписки VLESS** — [zieng2](https://github.com/zieng2/wl)

> Остальные компоненты и методы обхода (гибридный zDPI, Gatik, SSH Tunnel, cpller, ML-оптимизатор, системные утилиты и лаунчер) разработаны автором репозитория.

---

## English

**ToInet-MAX** is an all-in-one anti-censorship launcher and network routing manager for Windows.  
An [Android version](https://github.com/AlexeyRF/ToInet-Mobile) is also available.

Engineered for open Internet access while **maximizing bandwidth savings on your personal VPS**: data-heavy traffic (video streaming, media, web surfing) is unblocked locally or via public gateways, reserving your private VPS tunnel only for essential needs.

### Key Features

* **zDPI:** Local DPI evasion (TCP/HTTP/TLS/QUIC desynchronization and fragmentation) directly on your PC without external servers.
* **Tor:** Anonymous onion routing with bridge support and pluggable transports (obfs4, snowflake, conjure).
* **TGWS & Gatik:** WebSocket-based MTProto proxying and dynamic SOCKS5 gateway for Telegram.
* **Opera Proxy:** Fast proxy tunnel utilizing Opera's distributed infrastructure.
* **EVPN (sing-box):** Modern anti-censorship protocols (VLESS Reality, Trojan) with subscription support.
* **SSH SOCKS5 Tunnel:** Secure dynamic VPS connection powered by C++ and native Windows OpenSSH.

### How to Run

* **One-File version:** Run `ToInet-MAX-one_file_amd64.exe` (all-in-one standalone executable, no installation needed).
* **Portable version:** Run `ToInet.exe` inside the extracted release folder.
* **From source (Python 3.8 – 3.14+):** Run `launch.bat` or `main.pyw` — all required dependencies (PySide6, requests, cryptography, etc.) are installed automatically on first launch.

### Authors of Bypass Tools

* **ByeDPI** — [hufrea](https://github.com/hufrea/byedpi)
* **Zapret2** — [bol-van](https://github.com/bol-van/zapret2) *(L7 dissectors and desync techniques in zDPI)*
* **Tor** — [The Tor Project](https://www.torproject.org/)
* **TG WS Proxy** — [Flowseal](https://github.com/Flowseal/tg-ws-proxy)
* **sing-box** — [SagerNet](https://github.com/SagerNet/sing-box)
* **Opera Proxy** — [Alexey71](https://github.com/Alexey71/opera-proxy)
* **VLESS Subscriptions** — [zieng2](https://github.com/zieng2/wl)

> The remaining bypass methods and components (hybrid zDPI, Gatik, SSH Tunnel, cpller, ML Optimizer, system utilities, and launcher) were developed by the repository author.

---

## Français

**ToInet-MAX** est un gestionnaire universel d'outils de contournement de la censure et de routage réseau pour Windows.  
Une [version Android](https://github.com/AlexeyRF/ToInet-Mobile) est également disponible.

Conçu pour restaurer un accès libre à Internet tout en **préservant au maximum le quota de bande passante de votre propre VPS** : les contenus volumineux (vidéos, streaming, web) sont débloqués localement ou via des passerelles publiques, tandis que le tunnel vers votre serveur privé n'est sollicité qu'en cas de réelle nécessité.

### Fonctionnalités principales

* **zDPI :** Contournement DPI local (désynchronisation et fragmentation TCP/HTTP/TLS/QUIC) directement sur votre PC sans serveur tiers.
* **Tor :** Routage en oignon anonyme avec gestion des ponts et transports enfichables (obfs4, snowflake, conjure).
* **TGWS & Gatik :** Proxy MTProto sur WebSockets et passerelle SOCKS5 dynamique pour Telegram.
* **Opera Proxy :** Tunnel proxy rapide s'appuyant sur l'infrastructure distribuée d'Opera.
* **EVPN (sing-box) :** Protocoles récents (VLESS Reality, Trojan) avec prise en charge des abonnements.
* **Tunnel SSH SOCKS5 :** Connexion sécurisée vers votre propre VPS via un superviseur C++ et OpenSSH natif.

### Comment lancer

* **Version One-File :** Lancez `ToInet-MAX-one_file_amd64.exe` (exécutable unique autonome tout-en-un, aucune installation requise).
* **Version portable :** Lancez `ToInet.exe` dans le dossier extrait de la version publiée.
* **Depuis les sources (Python 3.8 – 3.14+) :** Lancez simplement `launch.bat` ou `main.pyw` — toutes les dépendances requises (PySide6, requests, cryptography, etc.) s'installent automatiquement au premier lancement.

### Auteurs des outils de contournement utilisés

* **ByeDPI** — [hufrea](https://github.com/hufrea/byedpi)
* **Zapret2** — [bol-van](https://github.com/bol-van/zapret2) *(dissecteurs L7 et techniques de désynchronisation dans zDPI)*
* **Tor** — [The Tor Project](https://www.torproject.org/)
* **TG WS Proxy** — [Flowseal](https://github.com/Flowseal/tg-ws-proxy)
* **sing-box** — [SagerNet](https://github.com/SagerNet/sing-box)
* **Opera Proxy** — [Alexey71](https://github.com/Alexey71/opera-proxy)
* **Abonnements VLESS** — [zieng2](https://github.com/zieng2/wl)

> Les autres composants et méthodes de contournement (zDPI hybride, Gatik, SSH Tunnel, cpller, optimiseur ML, utilitaires système et le lanceur) ont été développés par l'auteur du projet.
