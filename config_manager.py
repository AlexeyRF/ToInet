import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CURRENT_DIR, "config.json")

DEFAULT_CONFIG = {
    "use_custom_settings": True,
    "byedpi_params": "-p 1780 -o1 -o25+s -T3 -At -d1+s -O1 -s29+s -t 5 -An -Ku -a5 -s443+s -d80+s -s80+s -d53+s -s53+s -d443+s --fake -1 --fake-sni max.ru",
    "byedpi_pip_enabled": False,
    "byedpi_pip_use_tor": False,
    "byedpi_pip_params": "-p 1781 -o1 -o25+s -T3 -At -d1+s -O1 -s29+s -t 5 -An -Ku -a5 -s443+s -d80+s -s80+s -d53+s -s53+s -d443+s --fake -1 --fake-sni max.ru",
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
