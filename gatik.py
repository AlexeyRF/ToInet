import asyncio
import struct
import logging
import time

# Настройка логирования для вывода информации в консоль
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# === НАСТРОЙКИ СЕТИ ===
# Адрес и порт нашего умного шлюза (эти данные нужно вбить в Telegram)
LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 1777

# Прокси для СКАЧИВАНИЯ (быстрый Download - TOR)
DOWNLOAD_PROXY_HOST = '127.0.0.1'
DOWNLOAD_PROXY_PORT = 9853

# Прокси для ЗАГРУЗКИ (быстрый Upload - TGWS)
UPLOAD_PROXY_HOST = '127.0.0.1'
UPLOAD_PROXY_PORT = 1480

# Порог размера первого пакета (в байтах).
# Вы можете подкорректировать это значение, если маршрутизация будет ошибаться.
UPLOAD_THRESHOLD = 1024 

# Глобальный флаг: до какого времени форсировать все новые соединения через TGWS
global_upload_mode_until = 0
# ======================

async def forward(r, w, is_upload=None, direction=None, initial_bytes=0):
    """Функция двусторонней пересылки трафика между клиентом и апстрим-прокси"""
    global global_upload_mode_until
    bytes_transferred = initial_bytes
    try:
        while True:
            data = await r.read(16384)
            if not data:
                break
            w.write(data)
            await w.drain()
            
            bytes_transferred += len(data)
            
            if direction == "up":
                # Если соединение идет через TOR (Скачивание), но клиент отправил больше 64 KB
                # Значит это Upload, и мы должны оборвать соединение, чтобы клиент переподключился.
                if not is_upload and bytes_transferred > 65536:
                    logging.warning(f"Обнаружена тяжелая отправка ({bytes_transferred} байт) на линии TOR! Обрываем для переподключения на TGWS...")
                    global_upload_mode_until = time.time() + 15
                    w.close()
                    break
                
                # Если мы уже на TGWS и успешно отправляем, продлеваем окно режима Upload
                if is_upload and bytes_transferred > 65536:
                    global_upload_mode_until = max(global_upload_mode_until, time.time() + 15)

    except Exception:
        pass
    finally:
        w.close()

async def handle_client(reader, writer):
    up_writer = None
    try:
        # 1. Читаем начальный SOCKS5 Handshake от Telegram
        version, nmethods = await reader.readexactly(2)
        methods = await reader.readexactly(nmethods)
        
        # Отвечаем, что авторизация не требуется
        writer.write(b'\x05\x00')
        await writer.drain()

        # 2. Читаем запрос CONNECT
        version, cmd, rsv, atyp = await reader.readexactly(4)
        if cmd != 1:  # Поддерживаем только CONNECT
            return
        
        # Разбираем адрес назначения
        if atyp == 1: # IPv4
            dst_addr = await reader.readexactly(4)
            dst_ip = '.'.join(str(b) for b in dst_addr)
        elif atyp == 3: # Доменное имя
            domain_len = (await reader.readexactly(1))[0]
            dst_addr = await reader.readexactly(domain_len)
            dst_ip = dst_addr.decode()
        elif atyp == 4: # IPv6
            dst_addr = await reader.readexactly(16)
            import socket
            dst_ip = socket.inet_ntop(socket.AF_INET6, dst_addr)
        else:
            return

        dst_port_bytes = await reader.readexactly(2)
        dst_port = struct.unpack('!H', dst_port_bytes)[0]

        # 3. ОТВЕЧАЕМ УСПЕХОМ ДО ТОГО КАК ПОДКЛЮЧИМСЯ К АПСТРИМУ
        # Это заставит Telegram отправить первый пакет данных, который мы проанализируем
        reply = b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00'
        writer.write(reply)
        await writer.drain()

        # 4. Перехватываем первый пакет с реальными данными от Telegram
        first_chunk = await reader.read(16384)
        if not first_chunk:
            return

        # Ждем немного (до 0.1 сек), чтобы дождаться основного payload'а,
        # если клиент отправляет MTProto-заголовок и данные раздельно.
        try:
            while len(first_chunk) < UPLOAD_THRESHOLD:
                chunk = await asyncio.wait_for(reader.read(16384), timeout=0.1)
                if not chunk:
                    break
                first_chunk += chunk
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass

        # 5. МАГИЯ МАРШРУТИЗАЦИИ: 
        is_upload = len(first_chunk) > UPLOAD_THRESHOLD
        
        global global_upload_mode_until
        if time.time() < global_upload_mode_until:
            is_upload = True
            
        upstream_host = UPLOAD_PROXY_HOST if is_upload else DOWNLOAD_PROXY_HOST
        upstream_port = UPLOAD_PROXY_PORT if is_upload else DOWNLOAD_PROXY_PORT

        direction_label = "ЗАГРУЗКА (TGWS)" if is_upload else "СКАЧИВАНИЕ (TOR)"
        logging.info(f"Соединение к {dst_ip}:{dst_port} | 1-й пакет: {len(first_chunk)} байт -> Идем через {direction_label}")

        # 6. Подключаемся к выбранному прокси (TOR или TGWS)
        up_reader, up_writer = await asyncio.open_connection(upstream_host, upstream_port)
        
        # Handshake с выбранным прокси
        up_writer.write(b'\x05\x01\x00')
        await up_writer.drain()
        up_resp = await up_reader.readexactly(2)
        if up_resp != b'\x05\x00':
            logging.error("Апстрим прокси не принял запрос без авторизации")
            return
            
        # Отправляем CONNECT запрос в апстрим
        req = b'\x05\x01\x00' + bytes([atyp])
        if atyp == 1:
            req += dst_addr
        elif atyp == 3:
            req += bytes([len(dst_addr)]) + dst_addr
        elif atyp == 4:
            req += dst_addr
        req += dst_port_bytes
        
        up_writer.write(req)
        await up_writer.drain()
        
        # Читаем ответ от апстрима (пропускаем заголовок)
        up_conn_resp = await up_reader.readexactly(4)
        if up_conn_resp[1] != 0:
            return
            
        bnd_atyp = up_conn_resp[3]
        if bnd_atyp == 1:
            await up_reader.readexactly(4 + 2)
        elif bnd_atyp == 3:
            dlen = (await up_reader.readexactly(1))[0]
            await up_reader.readexactly(dlen + 2)
        elif bnd_atyp == 4:
            await up_reader.readexactly(16 + 2)

        # 7. Отправляем перехваченный нами первый пакет на нужный прокси
        up_writer.write(first_chunk)
        await up_writer.drain()

        # 8. Запускаем туннель (ожидаем завершения хотя бы одного направления)
        t1 = asyncio.create_task(forward(reader, up_writer, is_upload, "up", len(first_chunk)))
        t2 = asyncio.create_task(forward(up_reader, writer, is_upload, "down", 0))
        
        done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()

    except asyncio.IncompleteReadError:
        pass
    except Exception as e:
        pass
    finally:
        writer.close()
        if up_writer:
            up_writer.close()

async def main():
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    logging.info(f"=== Telegram SOCKS5 Router запущен на {LISTEN_HOST}:{LISTEN_PORT} ===")
    logging.info(f"TOR (Скачивание): {DOWNLOAD_PROXY_HOST}:{DOWNLOAD_PROXY_PORT}")
    logging.info(f"TGWS (Загрузка):  {UPLOAD_PROXY_HOST}:{UPLOAD_PROXY_PORT}")
    logging.info("Зайдите в Telegram и укажите SOCKS5 прокси: 127.0.0.1 порт 1777 (без пароля)")
    
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Программа остановлена.")
