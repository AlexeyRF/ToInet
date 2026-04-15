from pathlib import Path
def load_bridges(filename="bridges.txt"):
    path = Path.cwd() / filename
    if not path.exists(): raise FileNotFoundError(f"Файл {filename} не найден.")
    with open(path, "r", encoding="utf-8") as f: return [line.strip() for line in f if line.strip()]
def generate_torrc(bridges):
    return [
        f"DataDirectory {Path.cwd() / 'data'}",
        f"GeoIPFile {Path.cwd()}\data\geoip",
        f"GeoIPv6File {Path.cwd()}\data\geoip6",
        "SocksPort 9051",
        "ExitNodes {us},{de},{fr},{nl},{se}",
        "UseBridges 1",
        *[f"Bridge {bridge}" for bridge in bridges],
        f"ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec {Path.cwd()}"'\\tor\\pluggable_transports\\lyrebird.exe',
        "AvoidDiskWrites 1",
        "HardwareAccel 1",
        "ClientOnly 1",
        "AutomapHostsOnResolve 1",
        "SafeLogging 1",
    ]
def write_torrc(torrc_lines, filename="torrc"):
    with open(filename, "w", encoding="utf-8") as f: f.write('\n'.join(torrc_lines))
    print(f"Файл {filename} успешно создан.")
try:
    bridges = load_bridges()
    torrc = generate_torrc(bridges)
    write_torrc(torrc)
except Exception as e: print(f"Ошибка: {e}")