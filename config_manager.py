import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CURRENT_DIR, "config.json")

DEFAULT_CONFIG = {
    "use_custom_settings": True,
    "byedpi_params": "--split 1 --disorder 3+s --mod-http=h,d --auto=torst --tlsrec 1+s",
    "tgws_enabled": True,
    "tgws_port": 1480,
    "tgws_host": "127.0.0.1",
    "tgws_dc_ip": ["2:149.154.167.220", "4:149.154.167.220"],
    "tgws_verbose": False,
    "mode_type": "inetcpl",
    "auto_start": False,
    "auto_connect_last_mode": False,
    "tor_show_window": False
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except:
            pass
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
