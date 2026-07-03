#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Socks5-слой для ByeDPI (режим клиент-upstream)
===================================================
Этот скрипт запускает ByeDPI с фиксированным путем (./byedpi/ciadpi.exe) и
фиксированным портом 1788. Затем он запускает локальный SOCKS5 прокси (по умолчанию 1080),
который перенаправляет все подключения клиентов через ByeDPI на удаленный SOCKS5 сервер,
указанный в аргументах командной строки.

Настраиваются только адрес/порт удаленного SOCKS5 и индекс стратегии.

Основные возможности
--------------------
* Выбор стратегии из того же файла, что и GUI‑тестер (`byedpi_tester_strategies.txt`).
* Автозапуск `ciadpi.exe` (или другого бинарника ByeDPI) с выбранной стратегией.
* Двойное SOCKS5‑соединение: наш сервер принимает клиентские запросы, а затем
  через ByeDPI открывает соединение с удалённым SOCKS5‑сервером и передаёт
  туда исходный запрос клиента.
* Стандартный SOCKS5‑handshake без аутентификации.
* Корректное завершение работы (Ctrl+C / SIGTERM).
* Логи с метками времени, без внешних зависимостей (только std‑lib).

Usage example
-------------
```bash
python socks5_layer.py \
    --byedpi-path ./byedpi/ciadpi.exe \
    --strategy-index 0 \
    --listen-port 1080 \
    --byedpi-port 1081 \
    --upstream-proxy 1.2.3.4:1080
```
The script will start ``ciadpi.exe`` with the selected strategy, listening on
``127.0.0.1:1081``.  It then launches a SOCKS5 server on ``127.0.0.1:1080`` that
relays data to the ByeDPI daemon.

Dependencies
------------
* Python 3.8+
* No external packages – only the standard library.

"""

import argparse
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import select
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Простой логгер с временными метками для stdout."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

# ---------------------------------------------------------------------------
# Менеджер процесса ByeDPI
# ---------------------------------------------------------------------------

class ByeDPI:
    """Управление одним процессом ByeDPI (ciadpi.exe).

    Процесс запускается с указанной стратегией и принудительно слушает на
    ``ip:port``. Класс предлагает методы ``start`` и ``stop`` и хранит
    дескриптор подпроцесса.
    """

    def __init__(self, exe_path: Path, strategy: str, ip: str = "127.0.0.1", port: int = 1081):
        self.exe_path = exe_path
        self.strategy = strategy
        self.ip = ip
        self.port = port
        self.process: subprocess.Popen | None = None

    def _build_cmd(self) -> List[str]:
        # Стратегия может содержать заполнители, такие как {sni}; оставляем как есть.
        args = [str(self.exe_path), "--ip", self.ip, "--port", str(self.port)]
        # Разделение стратегии с сохранением кавычек – та же логика, что в byedpi_tester.
        # Очень маленькая реализация с использованием shlex.
        import shlex
        strategy_args = shlex.split(self.strategy)
        args.extend(strategy_args)
        return args

    def start(self) -> None:
        if self.process is not None:
            raise RuntimeError("ByeDPI already running")
        cmd = self._build_cmd()
        log(f"Starting ByeDPI: {' '.join(cmd)}")
        # ``creationflags`` для скрытия консольного окна на Windows.
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
        )
        # Дать демону немного времени на привязку порта.
        time.sleep(0.5)
        if self.process.poll() is not None:
            out, err = self.process.communicate()
            raise RuntimeError(f"ByeDPI failed to start: {err.decode(errors='ignore')}")
        log(f"ByeDPI started (PID {self.process.pid}) on {self.ip}:{self.port}")

    def stop(self) -> None:
        if self.process is None:
            return
        log("Stopping ByeDPI…")
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.process = None
        log("ByeDPI stopped.")

# ---------------------------------------------------------------------------
# Минималистичный SOCKS5 сервер – следует RFC 1928
# ---------------------------------------------------------------------------

class Socks5Connection(threading.Thread):
    """Обработка одного клиентского подключения.

    Поток выполнения:
    1. Выполнение SOCKS5 рукопожатия с клиентом.
    2. Открытие подключения к локальному демону ByeDPI.
    3. Через это подключение установка SOCKS5 рукопожатия с удаленным
       upstream прокси.
    4. Двунаправленная пересылка данных между клиентом и удаленным прокси.
    """

    def __init__(self, client_sock: socket.socket, byedpi_addr: Tuple[str, int], upstream_addr: Tuple[str, int], username: str = None, password: str = None):
        super().__init__(daemon=True)
        self.client_sock = client_sock
        self.byedpi_addr = byedpi_addr
        self.upstream_addr = upstream_addr
        self.username = username
        self.password = password
        self.buffer_size = 4096

    def run(self) -> None:
        try:
            self._handle()
        finally:
            self.client_sock.close()

    def _handle(self) -> None:
        # 1. Приветствие
        header = self.client_sock.recv(2)
        if len(header) < 2:
            return
        ver, nmethods = struct.unpack("!BB", header)
        if ver != 5:
            return
        methods = self.client_sock.recv(nmethods)
        # Мы поддерживаем только "без аутентификации" (0x00)
        self.client_sock.sendall(struct.pack("!BB", 5, 0))

        # 2. Запрос от клиента
        req = self.client_sock.recv(4)
        if len(req) < 4:
            return
        ver, cmd, _, atyp = struct.unpack("!BBBB", req)
        if ver != 5 or cmd != 1:  # поддерживается только CONNECT
            self._send_reply(0x07)  # Command not supported
            return
        # Разбор целевого адреса из запроса клиента
        if atyp == 1:  # IPv4
            addr = socket.inet_ntoa(self.client_sock.recv(4))
        elif atyp == 3:  # Domain name
            domain_len = self.client_sock.recv(1)[0]
            addr = self.client_sock.recv(domain_len).decode()
        elif atyp == 4:  # IPv6
            addr = socket.inet_ntop(socket.AF_INET6, self.client_sock.recv(16))
        else:
            self._send_reply(0x08)  # Address type not supported
            return
        port = struct.unpack('!H', self.client_sock.recv(2))[0]
        log(f"Client request: CONNECT {addr}:{port}")

        # 3. Подключение к локальному демону ByeDPI (выступает прозрачным пересыльщиком)
        try:
            byedpi_sock = socket.create_connection(self.byedpi_addr, timeout=5)
        except Exception as e:
            log(f"Failed to connect to ByeDPI daemon: {e}")
            self._send_reply(0x05)  # Connection refused
            return

        # 4. Через ByeDPI установка SOCKS5 подключения к удаленному прокси
        try:
            # a) Выполнение SOCKS5 рукопожатия с удаленным прокси через ByeDPI
            if self.username and self.password:
                byedpi_sock.sendall(b"\x05\x02\x00\x02")  # VER, NMETHODS=2, NO_AUTH, USER/PASS
                resp = byedpi_sock.recv(2)
                if len(resp) != 2 or resp[0] != 5:
                    raise RuntimeError("Upstream SOCKS5 handshake failed")
                if resp[1] == 2:
                    # Аутентификация логин/пароль
                    u_bytes = self.username.encode('utf-8')
                    p_bytes = self.password.encode('utf-8')
                    auth_req = b"\x01" + bytes([len(u_bytes)]) + u_bytes + bytes([len(p_bytes)]) + p_bytes
                    byedpi_sock.sendall(auth_req)
                    auth_resp = byedpi_sock.recv(2)
                    if len(auth_resp) != 2 or auth_resp[0] != 1 or auth_resp[1] != 0:
                        raise RuntimeError("Upstream SOCKS5 authentication failed")
                elif resp[1] != 0:
                    raise RuntimeError("Upstream SOCKS5 requires unsupported auth method")
            else:
                byedpi_sock.sendall(b"\x05\x01\x00")  # VER, NMETHODS=1, METHOD=0 (no auth)
                resp = byedpi_sock.recv(2)
                if len(resp) != 2 or resp[0] != 5 or resp[1] != 0:
                    raise RuntimeError("Upstream SOCKS5 handshake failed (no auth response)")

            # b) Отправка запроса CONNECT удаленному прокси (цель - оригинальный запрошенный адрес)
            # Сборка запроса, который мы получили от клиента
            conn_req = struct.pack('!BBBB', 5, 1, 0, atyp)
            conn_req += self._read_address(atyp)
            conn_req += struct.pack('!H', port)
            byedpi_sock.sendall(conn_req)
            upstream_reply = byedpi_sock.recv(10)  # minimal reply length
            if len(upstream_reply) < 2 or upstream_reply[1] != 0:
                raise RuntimeError(f"Upstream proxy rejected connection, reply: {upstream_reply}")
        except Exception as e:
            log(f"Failed to establish upstream SOCKS5 via ByeDPI: {e}")
            self._send_reply(0x05)
            byedpi_sock.close()
            return

        # 5. Ответ клиенту об успехе (используется адрес привязки, сообщенный удаленным прокси)
        bind_ip = socket.inet_aton(upstream_reply[4:8]) if len(upstream_reply) >= 8 else socket.inet_aton('0.0.0.0')
        bind_port = struct.unpack('!H', upstream_reply[8:10])[0] if len(upstream_reply) >= 10 else 0
        reply = struct.pack('!BBBB', 5, 0, 0, 1) + bind_ip + struct.pack('!H', bind_port)
        self.client_sock.sendall(reply)

        # 6. Пересылка данных между клиентом и установленным подключением к удаленному прокси
        self._pipe(self.client_sock, byedpi_sock)

    def _read_address(self, atyp: int) -> bytes:
        """Чтение части с адресом (без порта) из запроса клиента.
        Возвращает сырые байты, необходимые для сборки SOCKS5 запроса CONNECT.
        """
        if atyp == 1:  # IPv4
            return self.client_sock.recv(4)
        elif atyp == 3:  # Domain name
            dlen = self.client_sock.recv(1)[0]
            return bytes([dlen]) + self.client_sock.recv(dlen)
        elif atyp == 4:  # IPv6
            return self.client_sock.recv(16)
        return b''

    def _send_reply(self, rep: int) -> None:
        """Отправка SOCKS5 ответа с указанным кодом результата клиенту.
        ``rep`` следует кодам RFC 1928 (0 = успех, 5 = в соединении отказано и т.д.).
        """
        # Минимальный ответ: VER, REP, RSV, ATYP=1 (IPv4), BND.ADDR=0.0.0.0, BND.PORT=0
        reply = struct.pack('!BBBBIH', 5, rep, 0, 1, 0, 0)
        self.client_sock.sendall(reply)

    def _pipe(self, sock1: socket.socket, sock2: socket.socket) -> None:
        # Простая двунаправленная пересылка с использованием select.
        sockets = [sock1, sock2]
        while True:
            r, _, _ = select.select(sockets, [], [], 1.0)
            if not r:
                continue
            for s in r:
                try:
                    data = s.recv(self.buffer_size)
                    if not data:
                        return
                    if s is sock1:
                        sock2.sendall(data)
                    else:
                        sock1.sendall(data)
                except Exception:
                    return

class Socks5Server(threading.Thread):
    """Поток прослушивания, порождающий объекты ``Socks5Connection``.
    Перенаправляет клиентский трафик через ByeDPI на удаленный SOCKS5 прокси.
    """

    def __init__(self, listen_addr: Tuple[str, int], byedpi_addr: Tuple[str, int], upstream_addr: Tuple[str, int], username: str = None, password: str = None):
        super().__init__(daemon=True)
        self.listen_addr = listen_addr
        self.byedpi_addr = byedpi_addr      # локальный адрес демона ByeDPI
        self.upstream_addr = upstream_addr  # адрес удаленного SOCKS5 прокси
        self.username = username
        self.password = password
        self._stop_event = threading.Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.listen_addr)
        self.sock.listen(128)
        log(f"SOCKS5 server listening on {self.listen_addr[0]}:{self.listen_addr[1]}")

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                client, addr = self.sock.accept()
                log(f"Incoming connection from {addr[0]}:{addr[1]}")
                conn = Socks5Connection(client, self.byedpi_addr, self.upstream_addr, self.username, self.password)
                conn.start()
            except OSError:
                break
        self.sock.close()
        log("SOCKS5 server stopped.")

    def stop(self) -> None:
        self._stop_event.set()
        # Инициирование фиктивного подключения для разблокировки accept()
        try:
            dummy = socket.create_connection(self.listen_addr, timeout=1)
            dummy.close()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Главная точка входа – разбор аргументов, загрузка стратегий, плавное завершение
# ---------------------------------------------------------------------------

def load_strategies(strategies_path: Path) -> List[str]:
    if not strategies_path.is_file():
        raise FileNotFoundError(f"Strategies file not found: {strategies_path}")
    with strategies_path.open(encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    return lines

def main() -> None:
    parser = argparse.ArgumentParser(description="Local SOCKS5 proxy that routes through ByeDPI to an upstream SOCKS5 server")
    parser.add_argument("--strategies-file", default="byedpi_tester_strategies.txt",
                        help="File with ByeDPI strategies (default: byedpi_tester_strategies.txt)")
    parser.add_argument("--strategy-index", type=int, default=0,
                        help="Zero‑based index of the strategy to use")
    parser.add_argument("--listen-port", type=int, default=1080,
                        help="Local SOCKS5 listening port (default 1080)")
    parser.add_argument("--byedpi-port", type=int, default=1788,
                        help="Port for the internal ByeDPI daemon (default 1788)")
    parser.add_argument("--upstream-host", required=True, help="Hostname or IP of the remote SOCKS5 proxy")
    parser.add_argument("--upstream-port", type=int, required=True, help="Port of the remote SOCKS5 proxy")
    parser.add_argument("--username", type=str, default=None, help="Username for remote SOCKS5 proxy")
    parser.add_argument("--password", type=str, default=None, help="Password for remote SOCKS5 proxy")
    args = parser.parse_args()

    # Разрешение путей относительно расположения скрипта.
    base_dir = Path(__file__).parent
    # Фиксированный путь к бинарнику ByeDPI относительно корня проекта
    byedpi_exe = (base_dir / "byedpi/ciadpi.exe").resolve()
    strategies_path = (base_dir / args.strategies_file).resolve()

    strategies = load_strategies(strategies_path)
    if args.strategy_index < 0 or args.strategy_index >= len(strategies):
        log(f"Invalid strategy index {args.strategy_index}; available: 0‑{len(strategies)-1}")
        sys.exit(1)
    strategy = strategies[args.strategy_index]
    # Убеждаемся, что стратегия заставляет ByeDPI слушать на порту byedpi_port
    if "-p" not in strategy:
        strategy += f" -p {args.byedpi_port}"
    else:
        # заменяем любое существующее значение -p
        import re
        strategy = re.sub(r"-p\s+\d+", f"-p {args.byedpi_port}", strategy)
    log(f"Selected strategy [{args.strategy_index}]: {strategy}")

    # Инициализация демона ByeDPI
    byedpi = ByeDPI(byedpi_exe, strategy, ip="127.0.0.1", port=args.byedpi_port)
    byedpi.start()

    # Запуск локального SOCKS5 сервера, который будет перенаправлять
    # клиентские подключения через ByeDPI на удаленный SOCKS5 прокси.
    upstream_addr = (args.upstream_host, args.upstream_port)
    socks_server = Socks5Server(
        ("127.0.0.1", args.listen_port),
        ("127.0.0.1", args.byedpi_port),
        upstream_addr,
        args.username,
        args.password
    )
    socks_server.start()

    # Обработка плавного завершения работы.
    def shutdown(signum, frame):  # pragma: no cover – executed on SIGINT/SIGTERM
        log("Received termination signal – shutting down…")
        socks_server.stop()
        byedpi.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Поддержание жизни главного потока, пока работают фоновые потоки.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
