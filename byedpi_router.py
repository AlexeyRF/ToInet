import sys
import os
import time
import json
import socket
import struct
import threading
import subprocess
import psutil
import select

def extract_domain(data):
    if len(data) < 16:
        return None
        
    try:
        method = data[:8].decode('ascii', errors='ignore')
        if any(method.startswith(m) for m in ["GET ", "POST ", "CONNECT ", "PUT ", "HEAD ", "OPTIONS "]):
            http_data = data.decode('ascii', errors='ignore')
            for line in http_data.split('\r\n'):
                if line.lower().startswith("host: "):
                    return line[6:].strip().split(':')[0]
    except:
        pass

    if data[0] == 0x16 and data[1] == 0x03 and data[5] == 0x01:
        try:
            offset = 43
            if offset + 1 > len(data): return None
            session_id_len = data[offset]
            offset += 1 + session_id_len
            if offset + 2 > len(data): return None
            cipher_suites_len = (data[offset] << 8) | data[offset+1]
            offset += 2 + cipher_suites_len
            if offset + 1 > len(data): return None
            comp_methods_len = data[offset]
            offset += 1 + comp_methods_len
            if offset + 2 > len(data): return None
            extensions_len = (data[offset] << 8) | data[offset+1]
            offset += 2
            
            end_offset = min(offset + extensions_len, len(data))
            while offset + 4 <= end_offset:
                ext_type = (data[offset] << 8) | data[offset+1]
                ext_len = (data[offset+2] << 8) | data[offset+3]
                offset += 4
                if ext_type == 0 and offset + ext_len <= end_offset:
                    sni_offset = offset + 2
                    if sni_offset + 1 <= end_offset:
                        name_type = data[sni_offset]
                        if name_type == 0:
                            sni_offset += 1
                            if sni_offset + 2 <= end_offset:
                                name_len = (data[sni_offset] << 8) | data[sni_offset+1]
                                sni_offset += 2
                                if sni_offset + name_len <= end_offset:
                                    return data[sni_offset:sni_offset+name_len].decode('utf-8', errors='ignore')
                offset += ext_len
        except:
            pass
    return None

def handle_client(client_socket, domain_to_port, default_port):
    up_socket = None
    try:
        greeting = client_socket.recv(2)
        if len(greeting) < 2 or greeting[0] != 5:
            return
        nmethods = greeting[1]
        client_socket.recv(nmethods)
        
        client_socket.sendall(b'\x05\x00')
        
        req_header = client_socket.recv(4)
        if len(req_header) < 4 or req_header[1] != 1:
            return
            
        atyp = req_header[3]
        target_domain = ""
        dst_addr_bytes = b''
        if atyp == 1:
            dst_addr_bytes = client_socket.recv(4)
        elif atyp == 3:
            len_byte = client_socket.recv(1)
            domain_bytes = client_socket.recv(len_byte[0])
            target_domain = domain_bytes.decode('utf-8', errors='ignore')
            dst_addr_bytes = len_byte + domain_bytes
        elif atyp == 4:
            dst_addr_bytes = client_socket.recv(16)
        else:
            return
            
        port_bytes = client_socket.recv(2)
        
        client_socket.sendall(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
        
        client_socket.settimeout(0.5)
        first_chunk = b''
        try:
            first_chunk = client_socket.recv(16384)
        except:
            pass
        client_socket.settimeout(None)
        
        if not first_chunk:
            return
            
        if not target_domain:
            extracted = extract_domain(first_chunk)
            if extracted:
                target_domain = extracted
                
        target_port = default_port
        if target_domain:
            for d, p in domain_to_port.items():
                if target_domain.lower() == d.lower() or target_domain.lower().endswith("." + d.lower()):
                    target_port = p
                    break
                    
        up_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        up_socket.settimeout(5.0)
        up_socket.connect(("127.0.0.1", target_port))
        up_socket.settimeout(None)
        
        up_socket.sendall(b'\x05\x01\x00')
        up_socket.recv(2)
        
        up_req = struct.pack('!BBBB', 5, 1, 0, atyp) + dst_addr_bytes + port_bytes
        up_socket.sendall(up_req)
        
        up_resp = up_socket.recv(4)
        if len(up_resp) < 4: return
        bnd_atyp = up_resp[3]
        if bnd_atyp == 1: up_socket.recv(6)
        elif bnd_atyp == 3: 
            l = up_socket.recv(1)
            up_socket.recv(l[0] + 2)
        elif bnd_atyp == 4: up_socket.recv(18)
        
        up_socket.sendall(first_chunk)
        
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(16384)
                    if not data: break
                    dst.sendall(data)
            except:
                pass
            finally:
                try: src.close()
                except: pass
                try: dst.close()
                except: pass

        t1 = threading.Thread(target=forward, args=(client_socket, up_socket), daemon=True)
        t2 = threading.Thread(target=forward, args=(up_socket, client_socket), daemon=True)
        t1.start()
        t2.start()
        
    except Exception as e:
        pass

def shell_split(string):
    tokens = []
    quote_char = ' '
    escaping = False
    quoting = False
    last_close_quote_index = -999999
    current = []

    for i, c in enumerate(string):
        if escaping:
            current.append(c)
            escaping = False
        elif c == '\\' and quoting:
            if i + 1 < len(string) and string[i + 1] == quote_char:
                escaping = True
            else:
                current.append(c)
        elif quoting and c == quote_char:
            quoting = False
            last_close_quote_index = i
        elif not quoting and (c == "'" or c == '"'):
            quoting = True
            quote_char = c
        elif not quoting and c.isspace():
            if current or last_close_quote_index == i - 1:
                tokens.append("".join(current))
                current = []
        else:
            current.append(c)

    if current or last_close_quote_index == len(string) - 1:
        tokens.append("".join(current))
    return tokens

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
        
    listen_port = int(sys.argv[1])
    json_str = sys.argv[2]
    
    try:
        config = json.loads(json_str)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        sys.exit(1)
        
    unique_cmds = list(set(config.values()))
    instances = []
    cmd_to_port = {}
    
    current_port = listen_port + 10000
    byedpi_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"byedpi\ciadpi.exe")
    
    for cmd in unique_cmds:
        if cmd.upper() == "TOR":
            cmd_to_port[cmd] = 9853
            continue
            
        args = shell_split(cmd)
        filtered_args = []
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg == '-p' or arg == '--port' or arg == '-i' or arg == '--ip':
                skip_next = True
                continue
            if arg.startswith('-p') or arg.startswith('--port=') or arg.startswith('-i') or arg.startswith('--ip='):
                continue
            filtered_args.append(arg)
            
        final_cmd = [byedpi_exe] + filtered_args + ["-i", "127.0.0.1", "-p", str(current_port)]
        
        try:
            proc = subprocess.Popen(final_cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            instances.append(proc)
            cmd_to_port[cmd] = current_port
            current_port += 1
        except Exception as e:
            print(f"Failed to start instance: {e}")
            
    domain_to_port = {d: cmd_to_port[c] for d, c in config.items() if c in cmd_to_port}
    default_port = next(iter(cmd_to_port.values())) if cmd_to_port else 1780
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", listen_port))
    server_socket.listen(100)
    
    print(f"ByeDPI Router listening on 127.0.0.1:{listen_port}")
    
    ppid = os.getppid()
    
    def monitor_parent():
        while True:
            if not psutil.pid_exists(ppid):
                os._exit(0)
            time.sleep(1)
            
    threading.Thread(target=monitor_parent, daemon=True).start()
    
    try:
        while True:
            r, _, _ = select.select([server_socket], [], [], 1.0)
            if server_socket in r:
                client, addr = server_socket.accept()
                threading.Thread(target=handle_client, args=(client, domain_to_port, default_port), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        for p in instances:
            try: p.terminate()
            except: pass
            
if __name__ == "__main__":
    main()
