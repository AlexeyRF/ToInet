# ToInet - Лаунчер для СОБ (ByeDPI, TGWS и ЛМ)
---
Все права принадлежат тем, кому они принадлежат:<br>
https://github.com/hufrea/byedpi - ByeDPI<br>
https://torproject.org - ЛМ<br>
https://www.python.org/ - Python<br>
https://github.com/Flowseal/tg-ws-proxy - TgWS Proxy<br>
https://github.com/1tayH/noisy - Noisy <br>
https://github.com/InterceptSuite/ProxyBridge - маршрутизатор прокси<br><br>
---
В случае расследования какой-либо федеральной структуры или подобного, я не имею никакого отношения к этой группе или к людям в ней, я не знаю, как я здесь оказался, возможно, добавлен третьей стороной, я не поддерживаю никаких действий членов этой группы.
---

Как собрать (текущая версия): <br>
1. Скачайте ЛМ и поместите его таким образом, что корень -> (data (внутри geoip и geoip6), tor (внутри (tor.exe, tor-gencert.exe, pluggable_transports (внутри conjure-client.exe, lyrebird.exe, pt_config.json)))
2. Скачайте ByeDPI и поместите корень -> byedpi (внутри должен быть ciadpi.exe, bat файлы не нужны)
3. Установите любую иконку icon.ico

Либо вы можете использовать готовую версию, для неё нужен только python и установка модулей install.bat <br>
 <br>Планы на следующие версии: <br>
 1. Proxifier \ Proxybridge mode 
 2. Генерация пакетов UDP и noisy
 3. I2P
 4. Режим обхода DNS GEOBLOCK через YogaDNS или подобные
 5. Перенос основного порта на 9853
 6. Добавление смены ip (new curcuit)
 7. Режим сервиса
 8. Режим ретрансляции snowflake
 9. Реализация механизма нейтрализации цифровых угроз
