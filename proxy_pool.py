import argparse
import socket
import threading
import select
import time
import sys

class TCPRelay(threading.Thread):
    def __init__(self, client_sock, upstream_addr):
        super().__init__(daemon=True)
        self.client_sock = client_sock
        self.upstream_addr = upstream_addr

    def run(self):
        try:
            upstream_sock = socket.create_connection(self.upstream_addr, timeout=5)
        except Exception as e:
            print(f"[ProxyPool] Failed to connect to upstream {self.upstream_addr}: {e}")
            self.client_sock.close()
            return

        self._pipe(self.client_sock, upstream_sock)

    def _pipe(self, sock1, sock2):
        sockets = [sock1, sock2]
        try:
            while True:
                r, _, _ = select.select(sockets, [], [], 1.0)
                if not r:
                    continue
                for s in r:
                    try:
                        data = s.recv(8192)
                        if not data:
                            return
                        if s is sock1:
                            sock2.sendall(data)
                        else:
                            sock1.sendall(data)
                    except Exception:
                        return
        finally:
            sock1.close()
            sock2.close()

class TorMonitor(threading.Thread):
    def __init__(self, socks_port, control_port, server_ref):
        super().__init__(daemon=True)
        self.socks_port = socks_port
        self.control_port = control_port
        self.server_ref = server_ref
        self.is_ready = False

    def check_status(self):
        try:
            with socket.create_connection(('127.0.0.1', self.control_port), timeout=2) as s:
                s.sendall(b'AUTHENTICATE "toinet"\r\n')
                resp = s.recv(1024)
                if b'250 OK' not in resp:
                    return False
                s.sendall(b'GETINFO status/bootstrap-phase\r\n')
                resp = s.recv(1024)
                if b'BOOTSTRAP PROGRESS=100' in resp:
                    return True
        except Exception:
            pass
        return False

    def run(self):
        while True:
            ready = self.check_status()
            if ready and not self.is_ready:
                print(f"[TorMonitor] Instance on SocksPort {self.socks_port} reached 100% bootstrap.")
                self.is_ready = True
                self.server_ref.add_active(self.socks_port)
            elif not ready and self.is_ready:
                print(f"[TorMonitor] Instance on SocksPort {self.socks_port} dropped below 100% bootstrap.")
                self.is_ready = False
                self.server_ref.remove_active(self.socks_port)
            time.sleep(2)

class ProxyPoolServer(threading.Thread):
    def __init__(self, listen_port):
        super().__init__(daemon=True)
        self.listen_addr = ('127.0.0.1', listen_port)
        self.active_upstreams = []
        self.lock = threading.Lock()
        self.current_idx = 0
        self._stop_event = threading.Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.listen_addr)
        self.sock.listen(128)
        print(f"[ProxyPool] Listening on {self.listen_addr[0]}:{self.listen_addr[1]}")

    def add_active(self, port):
        with self.lock:
            if port not in self.active_upstreams:
                self.active_upstreams.append(port)
                print(f"[ProxyPool] Active upstreams: {self.active_upstreams}")

    def remove_active(self, port):
        with self.lock:
            if port in self.active_upstreams:
                self.active_upstreams.remove(port)
                print(f"[ProxyPool] Active upstreams: {self.active_upstreams}")

    def get_next_upstream(self):
        with self.lock:
            if not self.active_upstreams:
                return None
            self.current_idx = (self.current_idx + 1) % len(self.active_upstreams)
            return self.active_upstreams[self.current_idx]

    def run(self):
        while not self._stop_event.is_set():
            try:
                client, addr = self.sock.accept()
                upstream_port = self.get_next_upstream()
                if not upstream_port:
                    # No active Tor instance, reject immediately
                    client.close()
                    continue
                
                relay = TCPRelay(client, ('127.0.0.1', upstream_port))
                relay.start()
            except OSError:
                break
        self.sock.close()

    def stop(self):
        self._stop_event.set()
        try:
            dummy = socket.create_connection(self.listen_addr, timeout=1)
            dummy.close()
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="TCP Load Balancer for Proxy Pool")
    parser.add_argument("--listen-port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--upstream-ports", type=str, required=True, help="Comma-separated upstream ports")
    parser.add_argument("--control-ports", type=str, required=False, help="Comma-separated control ports")
    args = parser.parse_args()

    socks_ports = [int(p.strip()) for p in args.upstream_ports.split(',')]
    control_ports = []
    if args.control_ports:
        control_ports = [int(p.strip()) for p in args.control_ports.split(',')]
    
    server = ProxyPoolServer(args.listen_port)
    
    if control_ports and len(control_ports) == len(socks_ports):
        # Start monitors
        for sp, cp in zip(socks_ports, control_ports):
            monitor = TorMonitor(sp, cp, server)
            monitor.start()
    else:
        # Fallback to blindly adding all if control ports are missing
        for sp in socks_ports:
            server.add_active(sp)

    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
