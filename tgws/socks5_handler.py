import asyncio
import logging
import struct
import socket as _socket
import time

from .raw_websocket import RawWebSocket, WsHandshakeError
from .stats import stats
from .config import proxy_config

log = logging.getLogger('tg-ws-proxy-socks')

_TG_RANGES = [
    (struct.unpack('!I', _socket.inet_aton('185.76.151.0'))[0],
     struct.unpack('!I', _socket.inet_aton('185.76.151.255'))[0]),
    (struct.unpack('!I', _socket.inet_aton('149.154.160.0'))[0],
     struct.unpack('!I', _socket.inet_aton('149.154.175.255'))[0]),
    (struct.unpack('!I', _socket.inet_aton('91.105.192.0'))[0],
     struct.unpack('!I', _socket.inet_aton('91.105.193.255'))[0]),
    (struct.unpack('!I', _socket.inet_aton('91.108.0.0'))[0],
     struct.unpack('!I', _socket.inet_aton('91.108.255.255'))[0]),
]

_IP_TO_DC = {
    '149.154.175.50': 1, '149.154.175.51': 1, '149.154.175.54': 1,
    '149.154.167.41': 2, '149.154.167.50': 2, '149.154.167.51': 2, '149.154.167.220': 2,
    '149.154.175.100': 3, '149.154.175.101': 3,
    '149.154.167.91': 4, '149.154.167.92': 4,
    '91.108.56.100': 5, '91.108.56.126': 5, '91.108.56.101': 5, '91.108.56.116': 5, 
    '91.105.192.100': 203,
}

_ws_blacklist = set()
_dc_fail_until = {}
_DC_FAIL_COOLDOWN = 60.0

def _human_bytes(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(n) < 1024: return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def _is_telegram_ip(ip):
    try:
        n = struct.unpack('!I', _socket.inet_aton(ip))[0]
        return any(lo <= n <= hi for lo, hi in _TG_RANGES)
    except OSError:
        return False

def _is_http_transport(data):
    return (data[:5] == b'POST ' or data[:4] == b'GET ' or
            data[:5] == b'HEAD ' or data[:8] == b'OPTIONS ')

def _dc_from_init(data):
    try:
        from ._aes import Cipher, algorithms, modes
        key = bytes(data[8:40])
        iv = bytes(data[40:56])
        cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        encryptor = cipher.encryptor()
        keystream = encryptor.update(b'\x00' * 64) + encryptor.finalize()
        plain = bytes(a ^ b for a, b in zip(data[56:64], keystream[56:64]))
        proto = struct.unpack('<I', plain[0:4])[0]
        dc_raw = struct.unpack('<h', plain[4:6])[0]
        if proto in (0xEFEFEFEF, 0xEEEEEEEE, 0xDDDDDDDD):
            dc = abs(dc_raw)
            if 1 <= dc <= 1000:
                return dc, (dc_raw < 0)
    except Exception:
        pass
    return None, False

def _ws_domains(dc, is_media):
    base = 'telegram.org' if dc > 5 else 'web.telegram.org'
    if is_media is None or is_media:
        return [f'kws{dc}-1.{base}', f'kws{dc}.{base}']
    return [f'kws{dc}.{base}', f'kws{dc}-1.{base}']

async def _bridge_ws(reader, writer, ws, label, dc=None, dst=None, port=None, is_media=False):
    dc_tag = f"DC{dc}{'m' if is_media else ''}" if dc else "DC?"
    dst_tag = f"{dst}:{port}" if dst else "?"
    up_bytes = 0
    down_bytes = 0
    up_packets = 0
    down_packets = 0
    start_time = asyncio.get_event_loop().time()
    
    async def tcp_to_ws():
        nonlocal up_bytes, up_packets
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk: break
                stats.bytes_up += len(chunk)
                up_bytes += len(chunk)
                up_packets += 1
                await ws.send(chunk)
        except Exception: pass

    async def ws_to_tcp():
        nonlocal down_bytes, down_packets
        try:
            while True:
                data = await ws.recv()
                if data is None: break
                stats.bytes_down += len(data)
                down_bytes += len(data)
                down_packets += 1
                writer.write(data)
                await writer.drain()
        except Exception: pass

    tasks = [asyncio.create_task(tcp_to_ws()), asyncio.create_task(ws_to_tcp())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks: t.cancel()
        elapsed = asyncio.get_event_loop().time() - start_time
        log.info("[%s] %s (%s) WS SOCKS session closed: ^%s (%d pkts) v%s (%d pkts) in %.1fs",
                 label, dc_tag, dst_tag, _human_bytes(up_bytes), up_packets, _human_bytes(down_bytes), down_packets, elapsed)
        try: await ws.close()
        except: pass

async def _bridge_tcp(reader, writer, remote_reader, remote_writer, label, dc=None, dst=None, port=None, is_media=False):
    async def forward(src, dst_w, tag):
        try:
            while True:
                data = await src.read(65536)
                if not data: break
                if 'up' in tag: stats.bytes_up += len(data)
                else: stats.bytes_down += len(data)
                dst_w.write(data)
                await dst_w.drain()
        except Exception: pass
    tasks = [asyncio.create_task(forward(reader, remote_writer, 'up')), asyncio.create_task(forward(remote_reader, writer, 'down'))]
    try: await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks: t.cancel()
        for w in (writer, remote_writer):
            try: w.close()
            except: pass

async def _pipe(r, w):
    try:
        while True:
            data = await r.read(65536)
            if not data: break
            w.write(data)
            await w.drain()
    except Exception: pass
    finally:
        try: w.close()
        except: pass

def _socks5_reply(status):
    return bytes([0x05, status, 0x00, 0x01]) + b'\x00' * 6

async def _tcp_fallback(reader, writer, dst, port, init, label, dc=None, is_media=False):
    try:
        rr, rw = await asyncio.wait_for(asyncio.open_connection(dst, port), timeout=10)
    except Exception as exc:
        return False
    rw.write(init)
    await rw.drain()
    await _bridge_tcp(reader, writer, rr, rw, label, dc=dc, dst=dst, port=port, is_media=is_media)
    return True

async def handle_socks5(first_byte, reader, writer, secret):
    peer = writer.get_extra_info('peername')
    label = f"{peer[0]}:{peer[1]}" if peer else "?"
    try:
        hdr_rest = await asyncio.wait_for(reader.readexactly(1), timeout=10)
        nmethods = hdr_rest[0]
        await reader.readexactly(nmethods)
        writer.write(b'\x05\x00')
        await writer.drain()

        req = await asyncio.wait_for(reader.readexactly(4), timeout=10)
        _ver, cmd, _rsv, atyp = req
        if cmd != 1:
            writer.write(_socks5_reply(0x07))
            await writer.drain()
            return
        if atyp == 1:
            raw = await reader.readexactly(4)
            dst = _socket.inet_ntoa(raw)
        elif atyp == 3:
            dlen = (await reader.readexactly(1))[0]
            dst = (await reader.readexactly(dlen)).decode()
        elif atyp == 4:
            raw = await reader.readexactly(16)
            dst = _socket.inet_ntop(_socket.AF_INET6, raw)
        else:
            writer.write(_socks5_reply(0x08))
            await writer.drain()
            return
        port = struct.unpack('!H', await reader.readexactly(2))[0]

        if not _is_telegram_ip(dst):
            try:
                rr, rw = await asyncio.wait_for(asyncio.open_connection(dst, port), timeout=10)
            except Exception:
                writer.write(_socks5_reply(0x05))
                await writer.drain()
                return
            writer.write(_socks5_reply(0x00))
            await writer.drain()
            await asyncio.wait([asyncio.create_task(_pipe(reader, rw)), asyncio.create_task(_pipe(rr, writer))], return_when=asyncio.FIRST_COMPLETED)
            return

        writer.write(_socks5_reply(0x00))
        await writer.drain()

        try: init = await asyncio.wait_for(reader.readexactly(64), timeout=15)
        except asyncio.IncompleteReadError: return

        if _is_http_transport(init):
            return

        dc, is_media = _dc_from_init(init)
        if dc is None and dst in _IP_TO_DC: dc = _IP_TO_DC.get(dst)
        
        if dc is None or dc not in proxy_config.dc_redirects:
            await _tcp_fallback(reader, writer, dst, port, init, label)
            return

        dc_key = (dc, is_media if is_media is not None else True)
        now = time.monotonic()
        media_tag = (" media" if is_media else (" media?" if is_media is None else ""))

        if dc_key in _ws_blacklist or now < _dc_fail_until.get(dc_key, 0):
            await _tcp_fallback(reader, writer, dst, port, init, label, dc=dc, is_media=is_media)
            return

        domains = _ws_domains(dc, is_media)
        target = proxy_config.dc_redirects[dc]
        ws = None
        ws_failed_redirect = False
        all_redirects = True

        for domain in domains:
            try:
                ws = await RawWebSocket.connect(target, domain, timeout=10)
                all_redirects = False
                break
            except WsHandshakeError as exc:
                if exc.is_redirect:
                    ws_failed_redirect = True
                    continue
                else:
                    all_redirects = False
            except Exception:
                all_redirects = False
        
        if ws is None:
            if ws_failed_redirect and all_redirects: _ws_blacklist.add(dc_key)
            else: _dc_fail_until[dc_key] = now + _DC_FAIL_COOLDOWN
            await _tcp_fallback(reader, writer, dst, port, init, label, dc=dc, is_media=is_media)
            return

        _dc_fail_until.pop(dc_key, None)
        await ws.send(init)
        await _bridge_ws(reader, writer, ws, label, dc=dc, dst=dst, port=port, is_media=is_media)
    except Exception as exc:
        log.error("[%s] SOCKS5 error: %s", label, exc)
