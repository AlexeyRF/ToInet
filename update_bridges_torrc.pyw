import os
from pathlib import Path

def load_bridges(filename="bridges.txt"):
    path = Path.cwd() / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

def update_torrc(bridges, filename="torrc"):
    path = Path.cwd() / filename
    if not path.exists():
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        if not line.strip().startswith("Bridge "):
            new_lines.append(line.rstrip())
            
    # Remove UseBridges 1 if it's there to re-add it cleanly with bridges
    new_lines = [line for line in new_lines if line.strip() != "UseBridges 1"]
    
    if bridges:
        new_lines.append("UseBridges 1")
        for b in bridges:
            new_lines.append(f"Bridge {b}")
            
    with open(path, "w", encoding="utf-8") as f:
        f.write('\n'.join(new_lines))
    return True

if __name__ == "__main__":
    bridges = load_bridges()
    update_torrc(bridges)
