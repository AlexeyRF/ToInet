import xml.etree.ElementTree as ET
import json

tree = ET.parse('D:\\Documents\\ToInet-MAX\\Toinet.ppx')
root = tree.getroot()

def parse_targets(target_str):
    if not target_str: return [], []
    targets = [t.strip() for t in target_str.replace('\n', ' ').split(';') if t.strip()]
    suffixes = []
    keywords = []
    for t in targets:
        if t.startswith('*.') and t.endswith('.*'):
            keywords.append(t[2:-2])
        elif t.startswith('*') and t.endswith('*'):
            keywords.append(t[1:-1])
        elif t.startswith('*.'):
            suffixes.append(t[2:])
        elif t.startswith('*'):
            suffixes.append(t[1:])
        elif t.endswith('*'):
            keywords.append(t[:-1])
        else:
            suffixes.append(t)
    return list(set(suffixes)), list(set(keywords))

def parse_apps(app_str):
    if not app_str: return [], []
    apps = [a.strip().strip('"') for a in app_str.replace('\n', ' ').split(';') if a.strip()]
    names = []
    for a in apps:
        a = a.split('\\')[-1] # take filename
        a = a.replace('*', '')
        if a:
            names.append(a)
    return list(set(names))

# Dynamically parse Proxies
outbounds = [
    {"type": "direct", "tag": "direct"},
    {"type": "block", "tag": "block"}
]
proxy_map = {}
for proxy in root.findall('./ProxyList/Proxy'):
    p_id = proxy.get('id')
    
    # User explicitly requested to remove proxy 103
    if p_id == '103': continue

    p_port = int(proxy.find('Port').text)
    p_addr = proxy.find('Address').text
    p_label = proxy.find('Label').text
    
    # Generate tag
    tag = p_label.lower().replace(' ', '_')
    if tag == 'bypass': tag = 'byedpi' # User explicitly calls it byedpi
    
    outbounds.append({
        "type": "socks",
        "tag": tag,
        "server": p_addr,
        "server_port": p_port
    })
    proxy_map[p_id] = tag

rules = []

for rule in root.findall('./RuleList/Rule'):
    if rule.get('enabled') != 'true': continue
    name = rule.find('Name').text
    action_elem = rule.find('Action')
    action_type = action_elem.get('type')
    
    outbound = 'direct'
    if action_type == 'Direct':
        outbound = 'direct'
    elif action_type == 'Block':
        outbound = 'block'
    elif action_type == 'Proxy':
        proxy_id = action_elem.text
        # Default proxy routes to direct if the proxy was deleted
        outbound = proxy_map.get(proxy_id, 'direct')
    
    # parse targets
    targets_elem = rule.find('Targets')
    ports_elem = rule.find('Ports')
    apps_elem = rule.find('Applications')
    
    sing_rule = {"outbound": outbound}
    has_condition = False
    
    if targets_elem is not None:
        if name == 'Localhost':
            sing_rule["ip_cidr"] = ["127.0.0.0/8", "::1/128", "192.168.0.0/24"]
            has_condition = True
        else:
            suffixes, keywords = parse_targets(targets_elem.text)
            if suffixes: sing_rule["domain_suffix"] = suffixes
            if keywords: sing_rule["domain_keyword"] = keywords
            has_condition = True
            
    if ports_elem is not None:
        ports = [int(p.strip()) for p in ports_elem.text.split(';') if p.strip()]
        if ports:
            sing_rule["port"] = ports
            has_condition = True
            
    if apps_elem is not None:
        apps = parse_apps(apps_elem.text)
        if apps:
            sing_rule["process_name"] = apps
            has_condition = True
            
    if name == 'Default':
        pass 
    elif has_condition:
        rules.append(sing_rule)

config = {
    "log": {
        "level": "info",
        "timestamp": True
    },
    "inbounds": [
        {
            "type": "tun",
            "tag": "tun-in",
            "interface_name": "singtun0",
            "inet4_address": "172.19.0.1/30",
            "auto_route": True,
            "strict_route": True,
            "stack": "system",
            "sniff": True
        }
    ],
    "outbounds": outbounds,
    "route": {
        "rules": rules,
        "auto_detect_interface": True,
        "final": "direct"
    }
}

with open('D:\\Documents\\ToInet-MAX\\config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
