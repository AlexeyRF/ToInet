# ToInet-MAX

<p align="center">
  <img src="icon.ico" width="96" height="96" alt="ToInet Logo">
</p>

<p align="center">
  <a href="#русский">Русский</a> •
  <a href="#english">English</a> •
  <a href="#français">Français</a>
</p>

---

## Русский

**ToInet-MAX** — универсальный лаунчер и менеджер инструментов обхода сетевых ограничений для Windows.  
Доступна также [версия для Android](https://github.com/AlexeyRF/ToInet-Mobile).

Проект создан для свободного доступа в сеть и **максимальной экономии трафика вашего VPS**: ресурсоемкий контент (видео, стриминг, веб-серфинг) обходится локально или через бесплатные публичные шлюзы, защищенный туннель к личному серверу задействуется только при необходимости.

### Основные возможности

* **ByeDPI:** локальный обход DPI (модификация и фрагментация TCP/HTTP/TLS пакетов) прямо на компьютере без внешних серверов.
* **Tor:** анонимная маршрутизация трафика с поддержкой мостов и подключаемых транспортов (obfs4, snowflake и др.).
* **TGWS & Gatik:** высокоскоростное проксирование и динамическая балансировка трафика для Telegram (SOCKS5 и MTProto).
* **Opera Proxy:** быстрый прокси-туннель через инфраструктуру Opera.
* **EVPN:** поддержка современных протоколов (VLESS Reality, Trojan) на базе sing-box с поддержкой подписок.
* **SSH SOCKS5 Туннель:** защищенное подключение к собственному VPS на базе C++ и нативного Windows OpenSSH.
* **Интеграция с системой:** мгновенное переключение системного прокси Windows (Inetcpl) и поддержка режима полного туннелирования (TUN / Proxifier).

### Как запускать

* **Portable-версия:** запустите `ToInet.exe`.
* **Из исходников (Python 3.8+):** просто запустите `launch.bat` или `main.pyw` — все недостающие зависимости установятся автоматически при первом старте.

### Авторы используемых средств обхода

* **ByeDPI** — [hufrea](https://github.com/hufrea/byedpi)
* **Tor** — [The Tor Project](https://www.torproject.org/)
* **TG WS Proxy** — [Flowseal](https://github.com/Flowseal/tg-ws-proxy)
* **sing-box** — [SagerNet](https://github.com/SagerNet/sing-box)
* **Opera Proxy** — [Alexey71](https://github.com/Alexey71/opera-proxy)
* **Подписки VLESS** — [zieng2](https://github.com/zieng2/wl)

> Остальные методы обхода и компоненты (Gatik, SSH Tunnel, системные утилиты и лаунчер) разработаны автором репозитория.

---

## English

**ToInet-MAX** is an all-in-one anti-censorship launcher and network routing manager for Windows.  
An [Android version](https://github.com/AlexeyRF/ToInet-Mobile) is also available.

Engineered for open Internet access while **maximizing bandwidth savings on your personal VPS**: data-heavy traffic (video streaming, media, web) is unblocked locally or via public gateways, reserving your private VPS tunnel only for essential needs.

### Key Features

* **ByeDPI:** Local DPI evasion (TCP/HTTP/TLS packet manipulation and fragmentation) without external servers.
* **Tor:** Onion routing daemon with built-in bridge configuration and pluggable transports (obfs4, snowflake, etc.).
* **TGWS & Gatik:** High-performance proxying and dynamic traffic balancing for Telegram (SOCKS5 & MTProto).
* **Opera Proxy:** Fast proxy tunnel utilizing Opera's network infrastructure.
* **EVPN:** Modern anti-censorship protocols (VLESS Reality, Trojan) powered by sing-box with subscription support.
* **SSH SOCKS5 Tunnel:** Secure dynamic proxy tunnel to your own VPS using native Windows OpenSSH.
* **System Integration:** Instant Windows system proxy toggle (Inetcpl) and full TUN / Proxifier routing support.

### How to Run

* **Portable version:** Run `ToInet.exe`.
* **From source (Python 3.8+):** Simply run `launch.bat` or `main.pyw` — all required dependencies are installed automatically on first launch.

### Authors of Bypass Tools

* **ByeDPI** — [hufrea](https://github.com/hufrea/byedpi)
* **Tor** — [The Tor Project](https://www.torproject.org/)
* **TG WS Proxy** — [Flowseal](https://github.com/Flowseal/tg-ws-proxy)
* **sing-box** — [SagerNet](https://github.com/SagerNet/sing-box)
* **Opera Proxy** — [Alexey71](https://github.com/Alexey71/opera-proxy)
* **VLESS Subscriptions** — [zieng2](https://github.com/zieng2/wl)

> The remaining bypass methods and components (Gatik, SSH Tunnel, system utilities, and launcher) were developed by the repository author.

---

## Français

**ToInet-MAX** est un gestionnaire universel d'outils de contournement de la censure et de routage réseau pour Windows.  
Une [version Android](https://github.com/AlexeyRF/ToInet-Mobile) est également disponible.

Conçu pour restaurer un accès libre à Internet tout en **préservant au maximum le quota de bande passante de votre propre VPS** : les contenus volumineux (vidéos, streaming, web) sont débloqués localement ou via des passerelles publiques, tandis que le tunnel vers votre serveur privé n'est sollicité qu'en cas de nécessité.

### Fonctionnalités principales

* **ByeDPI :** Contournement DPI local (fragmentation et modification des paquets TCP/HTTP/TLS) sans serveur tiers.
* **Tor :** Routage en oignon avec prise en charge des ponts et des transports enfichables (obfs4, snowflake, etc.).
* **TGWS & Gatik :** Proxy rapide et équilibrage dynamique pour Telegram (SOCKS5 et MTProto).
* **Opera Proxy :** Tunnel proxy rapide s'appuyant sur l'infrastructure d'Opera.
* **EVPN :** Prise en charge des protocoles récents (VLESS Reality, Trojan) via sing-box avec gestion des abonnements.
* **Tunnel SSH SOCKS5 :** Connexion dynamique sécurisée vers votre propre VPS via OpenSSH natif.
* **Intégration système :** Basculement instantané du proxy système Windows (Inetcpl) et mode de routage TUN / Proxifier global.

### Comment lancer

* **Version portable :** Lancez `ToInet.exe`.
* **Depuis les sources (Python 3.8+) :** Lancez simplement `launch.bat` ou `main.pyw` — toutes les dépendances requises s'installent automatiquement au premier démarrage.

### Auteurs des outils de contournement utilisés

* **ByeDPI** — [hufrea](https://github.com/hufrea/byedpi)
* **Tor** — [The Tor Project](https://www.torproject.org/)
* **TG WS Proxy** — [Flowseal](https://github.com/Flowseal/tg-ws-proxy)
* **sing-box** — [SagerNet](https://github.com/SagerNet/sing-box)
* **Opera Proxy** — [Alexey71](https://github.com/Alexey71/opera-proxy)
* **Abonnements VLESS** — [zieng2](https://github.com/zieng2/wl)

> Les autres méthodes de contournement et composants (Gatik, SSH Tunnel, utilitaires système et le lanceur) ont été développés par l'auteur du projet.
