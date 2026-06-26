# ToInet - Лаунчер для СОБ (ByeDPI, TGWS, vk-turn и ЛМ)

**ToInet** - это комплексный менеджер для обеспечения свободного веб-доступа в операционной системе Windows. Программа объединяет в едином интерфейсе несколько инструментов обхода: **ByeDPI**, **Tor**, **Telegram WebSocket Proxy**, **vk-turn-proxy**, **Socksreabilitator**, **Умный шлюз-маршрутизатор Gatik** и автоматизированный генератор фонового трафика.

Приложение позволяет настраивать маршрутизацию - от обычного браузерного проксирования до прозрачного перенаправления всего трафика системы (TUN-режим) через внешние утилиты. 
---

## Основные возможности

*   **DPI-обход через ByeDPI (`ciadpi.exe`):**
    *   Запуск локального SOCKS5-прокси для модификации пакетов и обхода систем глубокого анализа трафика (DPI).
    *   Возможность тонкой настройки параметров запуска с помощью кастомного файла конфигурации `byedpi_custom.txt` или встроенных стратегий.
    *   **Отдельное проксирование для Pip (PyPI)**
*   **Интеграция с Tor (`tor.exe`):**
    *   Автоматическое управление локальным луковым маршрутизатором.
    *   Поддержка мостов
    *   Управление цепочками
*   **Telegram WebSocket Proxy (TGWS):**
    *   Встроенный локальный прокси-сервер, который туннелирует трафик мессенджера Telegram через WebSocket соединения.
    *   Быстрое добавление прокси в один клик из меню трея (ByeDPI, Tor или TGWS) напрямую в клиент Telegram.
*   **Умный шлюз Gatik для Telegram:**
    *   Собственная разработка представляющая из себя динамический маршрутизатор трафика, объединяющий преимущества Tor и TGWS.
    *   Автоматически анализирует поток данных "на лету" и бесшовно переключает активные соединения на оптимальный прокси-сервер.
*   **Тестер стратегий ByeDPI (`byedpi_tester_gui.pyw`):**
    *   Позволяет автоматически найти стратегию обхода, работающую у вашего провайдера, и сохранить её.
*   **Генератор сетевого шума Noisy (`noisy.py`):**
    *   Фоновый веб-краулер, имитирующий случайный веб-серфинг по доверенным сайтам.
    *   Маскирует ваш реальный зашифрованный трафик от систем DPI и анализаторов провайдера, создавая поток «белого шума».
*   **VK-Turn-Proxy** (пока в beta формате)

---

## Режимы маршрутизации трафика

В программе реализованы три различных режима работы с сетевыми настройками ОС Windows:

1.  **Empty (Пустой режим):**
    *   Приложение запускает выбранные инструменты обхода (`ByeDPI`, `Tor`, `TGWS` и другие) в фоне на локальных портах.
    *   Системные настройки сети не изменяются.
    *   *Для чего:* Удобно, если вы настраиваете проксирование в конкретных приложениях (например, в настройках браузера через расширение вроде *SwitchyOmega* или в самом Telegram).
2.  **Inetcpl (Свойства браузера):**
    *   Автоматически прописывает локальный прокси в системные настройки Windows (Internet Options / Свойства браузера) с помощью утилиты `cpller.pyw`.
    *   *Для чего:* Обеспечивает мгновенный доступ к сайтам через браузеры, использующие системные настройки прокси (Chrome, Edge, Opera, Firefox (с настройками по умолчанию)). При отключении прокси настройки автоматически сбрасываются.
3.  **TUN (Режим полного туннелирования):**
    *   Использует внешнюю утилиту-проксификатор (например, **Proxifier**) для перенаправления всего трафика операционной системы через запущенные инструменты.
    *   *Для чего:* Необходим для прозрачного обхода ограничений в играх, лаунчерах и десктопных приложениях (Discord, Spotify, Steam и др.), которые не поддерживают ручную настройку прокси.
    *   *Настройка:* Путь к исполняемому файлу проксификатора должен быть указан в файле `proxification_app.txt`.

---

## Порты по умолчанию

Для бесконфликтной работы все модули ToInet используют фиксированные сетевые порты:

| Инструмент / Протокол | Порт | Тип соединения | Описание |
| :--- | :--- | :--- | :--- |
| **ByeDPI (Основной)** | `1780` | SOCKS5 | Основной порт обхода блокировок для браузеров |
| **Tor (Основной)** | `9853` | SOCKS5 | Анонимный доступ через сеть Tor |
| **Tor Control Port** | `9851` | TCP | Служебный порт для управления Tor (смена цепочек) |
| **Telegram WS Proxy** | `1480` | SOCKS5 | Прокси, специально для Telegram Desktop |
| **Gatik Router** |`1777`| SOCKS5 | Роутер для ускорения Telegram |
| **Pip ByeDPI** | `1781` | SOCKS5 | Выделенный прокси-сервер для установки пакетов Python |

---

## Требования и установка

### Системные требования:
*   Операционная система: **Windows 10 / 11** (архитектура amd64 / arm64).
*   Установленный интерпретатор **Python 3.8+** (с добавлением в переменную среды `PATH`).

### Инструкция по установке:

1.  Скачайте релиз или соберите его (нужно поместить всё по схеме ниже)
2.  Запустите скрипт установки зависимостей **`install.bat`**. Он установит все необходимые библиотеки Python:
    ```cmd
    pip install pywin32 pyqt5 pysocks psutil requests cryptography customtkinter Pillow pystray pyperclip
    ```
3.  Если вы планируете использовать **TUN режим**:
    *   Установите программу-проксификатор.
    *   Откройте файл `proxification_app.txt` и пропишите абсолютный путь к исполняемому файлу программы. Например:
        ```text
        C:\Program Files\Proxifier\Proxifier.exe
        ```

## Запуск и использование

1.  Запустите программу двойным щелчком по файлу **`launch.bat`** .
2.  В системном трее Windows (возле часов или в меню на ^) появится иконка **ToInet-MAX**.
3.  **Первичная настройка трея:**
    *   Правой кнопкой мыши нажмите на иконку.
    *   По умолчанию включен **Inetcpl режим** меню, позволяющий быстро запускать/останавливать все сервисы разом и подключаться к TOR или Byedpi через свойства браузера. 
    *   Нажмите **«Настройки»**, чтобы переключиться в **Продвинутый режим**. Здесь вам откроется полный спектр возможностей ручного управления каждым компонентом отдельно, очистка кэша, конфигураторы и утилиты.

### Полезные инструменты в Продвинутом меню:
*   **Тестер стратегий ByeDPI:** открывает графическую утилиту для автоматического подбора параметров ByeDPI под вашего провайдера.
*   **Изменить мосты:** визуальный редактор файла `bridges.txt` для ручного добавления обходных мостов Tor.
*   **Автозапуск приложения:** включает или выключает автоматический старт ToInet-MAX при загрузке Windows.
*   **Создать ярлык на рабочем столе:** автоматически генерирует ярлык.
*   **Добавить в Telegram:** мгновенная отправка ссылки-настройки прокси напрямую в открытый Telegram.

---

## Решение проблем

> [!IMPORTANT]
> **Не работает Tor. Бесконечное подключение.**
> Скорее всего, ваш провайдер блокирует подключение к сети Tor с моими мостами. Перейдите в Продвинутое меню -> нажмите **«Изменить мосты»** и добавьте мосты. Мосты можно получить у бота `@GetBridgesBot` в Telegram.
> Если не помогло - попробуйте проксировать трафик TOR через byedpi (ищите это в "настройки TOR"), если всё ещё не работает, то напишите в Issues с приложением скриншота окна TOR со включённой настройкой "Показывать окно Tor при запуске"

> [!IMPORTANT]
> Если у вас нет TGWS, настроек byedpi, vk-turn или шумогенератора, то возможно в вашей системе включён английский язык, включите unsupported функции и они у вас появятся.

> [!WARNING]
> **Приложение закрылось аварийно, и пропал интернет.**
> Если программа завершила работу некорректно во время работы режима `inetcpl`, системные прокси-настройки могли остаться активными. 
> *Решение:* Запустите программу снова и штатно закройте её, либо зайдите в *Свойства браузера* Windows -> вкладка *Подключения* -> кнопка *Настройка сети* -> снимите галочку «Использовать прокси-сервер». Также можно воспользоваться утилитой очистки кэша прокси через меню трея.

> [!NOTE]
> **Конфликты портов.**
> Если в логах появляется ошибка `Address already in use` (порт занят), убедитесь, что у вас не запущены другие экземпляры ByeDPI, Tor или сторонние приложения на портах `1780`, `1781`, `9853`, `1777` или `1480`. 

---
Все права принадлежат тем, кому они принадлежат:<br>
https://github.com/hufrea/byedpi - ByeDPI<br>
https://torproject.org - ЛМ<br>
https://www.python.org/ - Python<br>
https://github.com/Flowseal/tg-ws-proxy - TgWS Proxy<br>
https://github.com/romanvht/ByeByeDPI - оригинальный подбор стратегий<br>
https://github.com/cacggghp/vk-turn-proxy - маршрутизация через VK<br><br>
---
В случае расследования какой-либо федеральной структуры или подобного, я не имею никакого отношения к этой группе или к людям в ней, я не знаю, как я здесь оказался, возможно, добавлен третьей стороной, я не поддерживаю никаких действий членов этой группы.
---

 <br>Планы на следующие версии: <br>
 1. Реализация механизма нейтрализации цифровых угроз суверинитета

---


---
# English Translation

## ToInet - Bypass Launcher (ByeDPI & TOR)

**ToInet** is a comprehensive manager for bypassing internet censorship and ensuring free web access on Windows OS. The program combines several bypass tools into a single system tray interface (based on PyQt5): **ByeDPI**, **Tor**.

The application allows for fine-tuning routing — from regular browser proxying to transparently redirecting all system traffic (TUN mode) through external utilities.

### Internet Censorship and Blocking in the UK
Various forms of internet censorship and website blocking have been implemented in the United Kingdom, often mandated by High Court rulings or the Digital Economy Act. Internet service providers (ISPs) in the UK frequently use deep packet inspection (DPI) and DNS blocking to restrict access to certain websites, including file-sharing platforms, streaming sites, truth-telling sites (called "Russian propaganda"), and adult content. These blocks are typically implemented at the network level through SNI (Server Name Indication) analysis or DNS response manipulation to prevent users from accessing desired resources.
Remember: Big Brother is watching you, but Big Russian Bratan is in his way.

### How This Program Works
ToInet tackles these restrictions by leveraging several interconnected technologies:
1. **ByeDPI**: Manipulates TCP and HTTP packets at the SOCKS5 proxy level to confuse deep packet inspection (DPI) systems used by ISPs. It alters the structure of requests (e.g., modifying the Host header or splitting the SNI payload) so the ISP's filters cannot recognize the destination and block the connection.
2. **Tor Integration**: Tunnels traffic through the decentralized Tor network, encrypting the connection and routing it through multiple relays. For networks with aggressive Tor blocking, the program utilizes Pluggable Transports and Bridges, making Tor traffic appear as regular noise.

---

## Core Features

*   **DPI Bypass via ByeDPI (`ciadpi.exe`):**
    *   Runs a local SOCKS5 proxy to modify packets and bypass Deep Packet Inspection (DPI).
    *   Fine-tune launch parameters using `byedpi_custom.txt` or built-in strategies.
*   **Tor Integration (`tor.exe`):**
    *   Automates the start and stop of the local Tor client.
    *   Bypass Tor blocks using bridges (editable via the built-in editor).
    *   Circuit control (request a new circuit `/NEWNYM` from the tray menu).
    *   Automated `torrc` configuration generation and restoration.
*   **ByeDPI Strategy Tester (`byedpi_tester_gui.pyw`):**
    *   Interface to test various ByeDPI parameters against blocked resources.
    *   Automatically finds a working bypass strategy for your ISP.
*   **Autostart & Convenience:**
    *   Minimizes to the Windows system tray.
    *   Built-in autostart installer and one-click desktop shortcut creator.

---

## Traffic Routing Modes

The program provides three operational modes:

1.  **Empty Mode:**
    *   Runs bypass tools in the background on local ports.
    *   Does not alter system network settings.
    *   *Best for:* Manual configuration in specific apps (e.g., SwitchyOmega for browsers).
2.  **Inetcpl (Browser Properties):**
    *   Automatically sets the local proxy in Windows system settings using `cpller.pyw`.
    *   *Best for:* Instant access via browsers that use system proxy settings (Chrome, Edge, Opera). Settings are reset upon disconnection.
3.  **TUN (Full Tunneling Mode):**
    *   Uses an external proxifier (like **Proxifier**) to route all OS traffic through the tools.
    *   *Best for:* Transparent bypass for games, launchers, and desktop apps (Discord, Steam).
    *   *Setup:* Path to the proxifier executable must be specified in `proxification_app.txt`.

---

## Default Ports

| Tool / Protocol | Port | Proxy Type | Description |
| :--- | :--- | :--- | :--- |
| **ByeDPI (Main)** | `1780` | SOCKS5 | Main bypass proxy for browsers |
| **Tor (Main)** | `9853` | SOCKS5 | Anonymous access via Tor network |
| **Tor Control Port** | `9851` | TCP | Control port for Tor (circuit rotation) |

---

## Requirements and Installation

### System Requirements:
*   OS: **Windows 10 / 11** (amd64).
*   **Python 3.8+** installed (added to `PATH`).

### Installation Guide:

1.  Download the release or build it according to the folder structure below.
2.  Run the dependency installation script **`install.bat`**.
3.  If planning to use **TUN mode**:
    *   Install a proxifier.
    *   Open `proxification_app.txt` and write the absolute path to the executable (e.g., `C:\Program Files\Proxifier\Proxifier.exe`).

---

## Launch and Usage

1.  Double-click **`launch.bat`**.
2.  The **ToInet-MAX** icon will appear in the system tray.
3.  **Initial Tray Setup:**
    *   Right-click the icon.
    *   By default, **Inetcpl mode** is enabled, allowing quick service toggles.
    *   Click **"Settings" / "Настройки"** to switch to **Advanced Mode** for granular control over each component.

---

## Troubleshooting

> [!IMPORTANT]
> **Tor is not working. Endless connection.**
> Your ISP is likely blocking the default Tor bridges. Go to Advanced Menu -> click **"Edit Bridges"** and add custom bridges. Bridges can be obtained from the `@GetBridgesBot` on Telegram.

> [!WARNING]
> **Application crashed and internet is lost.**
> If the program closed abruptly during `inetcpl` mode, system proxy settings might still be active.
> *Solution:* Restart the program and close it properly, or open Windows *Internet Options* -> *Connections* -> *LAN settings* -> uncheck "Use a proxy server". You can also use the tray menu cache cleaner.

> [!NOTE]
> **Port Conflicts.**
> If logs show `Address already in use`, ensure no other instances of ByeDPI, Tor, or third-party apps are using ports `1780`, `1781`, `9853`, or `1480`.

---
