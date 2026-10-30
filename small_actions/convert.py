import os
import sys
import json
import xml.etree.ElementTree as ET
import re

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPX_PATH = os.path.join(CURRENT_DIR, "Toinet.ppx")

def parse_targets(target_str):
    if not target_str:
        return [], [], []
    target_str = re.sub(r'(\*)\s+(\*)', r'\1;\2', target_str)
    raw_targets = [t.strip() for t in target_str.replace('\n', ' ').split(';') if t.strip()]
    
    suffixes = set()
    keywords = set()
    ip_cidrs = set()
    
    for t in raw_targets:
        if t.startswith('%') and t.endswith('%'):
            continue
        if t.lower() == 'localhost':
            keywords.add('localhost')
            continue
        if re.match(r'^[\d\.:/]+$', t):
            if '/' not in t:
                if ':' in t: t += '/128'
                else: t += '/32'
            ip_cidrs.add(t)
            continue
            
        if t.startswith('*.') and t.endswith('.*'):
            keywords.add(t[2:-2] + '.')
        elif t.startswith('*.') and t.endswith('*'):
            keywords.add(t[2:-1])
        elif t.startswith('*') and t.endswith('.*'):
            keywords.add(t[1:-2] + '.')
        elif t.startswith('*') and t.endswith('*'):
            keywords.add(t[1:-1])
        elif t.endswith('.*'):
            keywords.add(t[:-2] + '.')
        elif t.endswith('*'):
            keywords.add(t[:-1])
        elif t.startswith('*.'):
            suffixes.add(t[2:].lower())
        elif t.startswith('*'):
            sub = t[1:].lower()
            if '*' in sub:
                keywords.add(sub.replace('*', ''))
            else:
                suffixes.add(sub)
        else:
            if '*' in t:
                keywords.add(t.lower().replace('*', ''))
            else:
                suffixes.add(t.lower())
                
    return sorted(list(suffixes)), sorted(list(keywords)), sorted(list(ip_cidrs))

def parse_apps(app_str):
    if not app_str:
        return []
    raw = [a.strip().strip('"\'') for a in app_str.replace('\n', ' ').split(';') if a.strip()]
    names = set()
    for a in raw:
        clean = a.replace('/', '\\').split('\\')[-1].replace('*', '').strip('.').strip()
        if clean:
            names.add(clean)
            if not clean.endswith('.exe') and '.' not in clean:
                names.add(clean + '.exe')
    return sorted(list(names))

def convert_ppx_to_singbox(ppx_path=PPX_PATH):
    tree = ET.parse(ppx_path)
    root = tree.getroot()
    
    proxy_map = {}
    outbounds = [
        {"type": "direct", "tag": "direct"},
        {"type": "block", "tag": "block"}
    ]
    
    for proxy in root.findall('./ProxyList/Proxy'):
        p_id = proxy.get('id')
        p_port = int(proxy.find('Port').text)
        p_addr = proxy.find('Address').text
        p_label = proxy.find('Label').text if proxy.find('Label') is not None else f"Proxy_{p_id}"
        
        tag = p_label.lower().replace(' ', '_')
        if tag in ('bypass', 'byedpi', 'bd'):
            tag = 'byedpi'
        elif tag in ('hosting', 'ssh'):
            tag = 'ssh'
        elif 'tor' in tag:
            tag = 'tor'
        elif 'opera' in tag:
            tag = 'opera'
            
        proxy_map[p_id] = tag
        
        if not any(o.get('tag') == tag for o in outbounds):
            outbounds.append({
                "type": "socks",
                "tag": tag,
                "server": p_addr,
                "server_port": p_port
            })
            
    standard_tags = {
        "byedpi": 1780,
        "tor": 9853,
        "opera": 1785,
        "ssh": 1770
    }
    for st, sp in standard_tags.items():
        if not any(o.get('tag') == st for o in outbounds):
            outbounds.append({
                "type": "socks",
                "tag": st,
                "server": "127.0.0.1",
                "server_port": sp
            })
            
    rules = []
    for r in root.findall('./RuleList/Rule'):
        if r.get('enabled') != 'true':
            continue
        name = r.find('Name').text if r.find('Name') is not None else ''
        if name in ('Default', 'Localhost'):
            continue
            
        act_elem = r.find('Action')
        act_type = act_elem.get('type') if act_elem is not None else 'Direct'
        if act_type == 'Direct':
            outbound = 'direct'
        elif act_type == 'Block':
            outbound = 'block'
        elif act_type == 'Proxy':
            pid = act_elem.text.strip() if act_elem.text else ''
            outbound = proxy_map.get(pid, 'direct')
        else:
            outbound = 'direct'
            
        t_elem = r.find('Targets')
        a_elem = r.find('Applications')
        p_elem = r.find('Ports')
        
        t_text = t_elem.text if t_elem is not None else ''
        a_text = a_elem.text if a_elem is not None else ''
        p_text = p_elem.text if p_elem is not None else ''
        
        suffixes, keywords, cidrs = parse_targets(t_text)
        apps = parse_apps(a_text)
        ports = []
        if p_text:
            for p in p_text.replace('\n', ' ').split(';'):
                p = p.strip()
                if p.isdigit():
                    ports.append(int(p))
                    
        if apps and not suffixes and not keywords and not cidrs and not ports:
            rules.append({
                "outbound": outbound,
                "process_name": apps
            })
        elif ports and not apps and not suffixes and not keywords and not cidrs:
            rules.append({
                "outbound": outbound,
                "port": ports
            })
        elif (suffixes or keywords or cidrs) and not apps and not ports:
            r_obj = {"outbound": outbound}
            if suffixes: r_obj["domain_suffix"] = suffixes
            if keywords: r_obj["domain_keyword"] = keywords
            if cidrs: r_obj["ip_cidr"] = cidrs
            rules.append(r_obj)
        else:
            if apps and (suffixes or keywords or cidrs):
                rules.append({
                    "outbound": outbound,
                    "process_name": apps
                })
                r_obj = {"outbound": outbound}
                if suffixes: r_obj["domain_suffix"] = suffixes
                if keywords: r_obj["domain_keyword"] = keywords
                if cidrs: r_obj["ip_cidr"] = cidrs
                if ports: r_obj["port"] = ports
                rules.append(r_obj)
            else:
                r_obj = {"outbound": outbound}
                if apps: r_obj["process_name"] = apps
                if suffixes: r_obj["domain_suffix"] = suffixes
                if keywords: r_obj["domain_keyword"] = keywords
                if cidrs: r_obj["ip_cidr"] = cidrs
                if ports: r_obj["port"] = ports
                rules.append(r_obj)

    yt_cidrs_file = os.path.join(CURRENT_DIR, "data", "google_cidrs.json")
    yt_cidrs = []
    if os.path.exists(yt_cidrs_file):
        try:
            with open(yt_cidrs_file, "r", encoding="utf-8") as f:
                raw_cidrs = json.load(f)
                yt_cidrs = [c for c in raw_cidrs if ":" not in c]
        except Exception:
            pass
    if not yt_cidrs:
        yt_cidrs = [
            "142.250.0.0/15", "172.217.0.0/16", "173.194.0.0/16", "74.125.0.0/16",
            "108.177.0.0/17", "216.58.192.0/19", "64.233.160.0/19", "66.102.0.0/20",
            "209.85.128.0/17", "172.253.0.0/16", "192.178.0.0/15", "216.239.32.0/19"
        ]

    base_rules = [
        {
            "action": "sniff",
            "sniffer": ["http", "tls", "quic", "dns"],
            "timeout": "300ms"
        },
        {
            "ip_version": 6,
            "action": "reject"
        },
        {
            "port": [443],
            "network": ["udp"],
            "action": "reject"
        },
        {
            "port": [53],
            "action": "hijack-dns"
        },
        {
            "outbound": "direct",
            "process_name": [
                "sing-box.exe",
                "ciadpi.exe",
                "tor.exe",
                "lyrebird.exe",
                "obfs4proxy.exe",
                "opera-proxy.exe",
                "plink.exe",
                "ssh.exe",
                "python.exe",
                "pythonw.exe",
                "ToInet.exe"
            ]
        },
        {
            "outbound": "direct",
            "ip_cidr": [
                "127.0.0.0/8",
                "::1/128",
                "10.0.0.0/8",
                "172.16.0.0/12",
                "192.168.0.0/16",
                "169.254.0.0/16"
            ]
        }
    ]

    all_rules = base_rules + rules
    if yt_cidrs:
        all_rules.append({
            "outbound": "tor",
            "ip_cidr": yt_cidrs
        })

    config = {
        "log": {
            "level": "info",
            "timestamp": True
        },
        "dns": {
            "servers": [
                {
                    "tag": "dns-primary",
                    "type": "udp",
                    "server": "77.88.8.8"
                },
                {
                    "tag": "dns-backup",
                    "type": "udp",
                    "server": "1.1.1.1"
                }
            ],
            "strategy": "ipv4_only",
            "reverse_mapping": True
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "toinet-tun",
                "address": [
                    "172.19.0.1/30"
                ],
                "mtu": 1500,
                "auto_route": True,
                "strict_route": False,
                "endpoint_independent_nat": True,
                "stack": "mixed"
            }
        ],
        "outbounds": outbounds,
        "route": {
            "default_domain_resolver": "dns-primary",
            "rules": all_rules,
            "auto_detect_interface": True,
            "final": "direct"
        }
    }
    
    return config

if __name__ == '__main__':
    cfg = convert_ppx_to_singbox()
    output_paths = [
        os.path.join(CURRENT_DIR, 'config.json'),
        os.path.join(CURRENT_DIR, 'small_actions', 'config.json'),
        os.path.join(CURRENT_DIR, 'data', 'tun_config.json')
    ]
    for out_path in output_paths:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("Updated sing-box configurations successfully!")
