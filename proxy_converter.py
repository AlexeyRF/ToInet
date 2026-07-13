import asyncio
import argparse
import struct
import urllib.parse
import socket

async def pipe(reader, writer):
    try:
        while True:
            data = await reader.read(8192)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()

async def handle_socks2http(reader, writer, upstream_host, upstream_port):
    try:
        ver_nmethods = await reader.readexactly(2)
        if ver_nmethods[0] != 5:
            writer.close()
            return
        methods = await reader.readexactly(ver_nmethods[1])
        writer.write(b'\x05\x00')
        await writer.drain()

        req = await reader.readexactly(4)
        if req[1] != 1:  # Only CONNECT supported
            writer.write(b'\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00')
            await writer.drain()
            writer.close()
            return

        atyp = req[3]
        if atyp == 1:
            addr = socket.inet_ntoa(await reader.readexactly(4))
        elif atyp == 3:
            domain_len = (await reader.readexactly(1))[0]
            addr = (await reader.readexactly(domain_len)).decode()
        elif atyp == 4:
            addr = socket.inet_ntop(socket.AF_INET6, await reader.readexactly(16))
        else:
            writer.close()
            return

        port_bytes = await reader.readexactly(2)
        port = struct.unpack('!H', port_bytes)[0]

        up_reader, up_writer = await asyncio.open_connection(upstream_host, upstream_port)
        
        connect_req = f"CONNECT {addr}:{port} HTTP/1.1\r\nHost: {addr}:{port}\r\n\r\n"
        up_writer.write(connect_req.encode())
        await up_writer.drain()

        resp = await up_reader.readuntil(b'\r\n\r\n')
        if not resp.startswith(b'HTTP/1.1 200') and not resp.startswith(b'HTTP/1.0 200'):
            writer.write(b'\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00')
            await writer.drain()
            writer.close()
            up_writer.close()
            return

        writer.write(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
        await writer.drain()

        asyncio.create_task(pipe(reader, up_writer))
        asyncio.create_task(pipe(up_reader, writer))

    except Exception:
        writer.close()

async def handle_http2socks(reader, writer, upstream_host, upstream_port):
    try:
        line = await reader.readuntil(b'\r\n')
        parts = line.decode().strip().split()
        if len(parts) < 3:
            writer.close()
            return

        method, url, version = parts
        
        headers = b''
        while True:
            hline = await reader.readuntil(b'\r\n')
            headers += hline
            if hline == b'\r\n':
                break

        if method.upper() == 'CONNECT':
            host, port = url.split(':')
            port = int(port)
            
            up_reader, up_writer = await asyncio.open_connection(upstream_host, upstream_port)
            
            up_writer.write(b'\x05\x01\x00')
            await up_writer.drain()
            resp = await up_reader.readexactly(2)
            if resp != b'\x05\x00':
                writer.close()
                up_writer.close()
                return

            host_bytes = host.encode()
            req = b'\x05\x01\x00\x03' + bytes([len(host_bytes)]) + host_bytes + struct.pack('!H', port)
            up_writer.write(req)
            await up_writer.drain()

            resp = await up_reader.readexactly(10)
            if resp[1] != 0:
                writer.close()
                up_writer.close()
                return

            writer.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            await writer.drain()

            asyncio.create_task(pipe(reader, up_writer))
            asyncio.create_task(pipe(up_reader, writer))
            
        else:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname or url.split('/')[0]
            port = parsed.port or 80
            
            up_reader, up_writer = await asyncio.open_connection(upstream_host, upstream_port)
            
            up_writer.write(b'\x05\x01\x00')
            await up_writer.drain()
            resp = await up_reader.readexactly(2)
            if resp != b'\x05\x00':
                writer.close()
                up_writer.close()
                return

            host_bytes = host.encode()
            req = b'\x05\x01\x00\x03' + bytes([len(host_bytes)]) + host_bytes + struct.pack('!H', port)
            up_writer.write(req)
            await up_writer.drain()

            resp = await up_reader.readexactly(10)
            if resp[1] != 0:
                writer.close()
                up_writer.close()
                return

            path = parsed.path if hasattr(parsed, 'path') else '/'
            if getattr(parsed, 'query', ''): path += '?' + parsed.query
            if not path: path = '/'
            new_req = f"{method} {path} {version}\r\n".encode() + headers
            up_writer.write(new_req)
            await up_writer.drain()

            asyncio.create_task(pipe(reader, up_writer))
            asyncio.create_task(pipe(up_reader, writer))

    except Exception:
        writer.close()

async def main():
    parser = argparse.ArgumentParser(description="Proxy Converter")
    parser.add_argument("--socks2http", action="append", metavar="LISTEN_PORT:UPSTREAM_PORT", help="SOCKS5 listener forwarding to HTTP upstream")
    parser.add_argument("--http2socks", action="append", metavar="LISTEN_PORT:UPSTREAM_PORT", help="HTTP listener forwarding to SOCKS5 upstream")
    
    args = parser.parse_args()
    servers = []
    
    if args.socks2http:
        for mapping in args.socks2http:
            listen_p, upstream_p = map(int, mapping.split(':'))
            handler = lambda r, w, uh="127.0.0.1", up=upstream_p: handle_socks2http(r, w, uh, up)
            server = await asyncio.start_server(handler, '127.0.0.1', listen_p)
            servers.append(server)
            print(f"SOCKS2HTTP: Listening on {listen_p} -> 127.0.0.1:{upstream_p}")
            
    if args.http2socks:
        for mapping in args.http2socks:
            listen_p, upstream_p = map(int, mapping.split(':'))
            handler = lambda r, w, uh="127.0.0.1", up=upstream_p: handle_http2socks(r, w, uh, up)
            server = await asyncio.start_server(handler, '127.0.0.1', listen_p)
            servers.append(server)
            print(f"HTTP2SOCKS: Listening on {listen_p} -> 127.0.0.1:{upstream_p}")
            
    if not servers:
        print("No proxy mappings specified.")
        return
        
    async with asyncio.TaskGroup() as tg:
        for s in servers:
            tg.create_task(s.serve_forever())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
