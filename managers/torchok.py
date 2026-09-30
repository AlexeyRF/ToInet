import lang
import sys
import os
import subprocess
import time
import psutil
from PyQt5.QtWidgets import QMessageBox

# РџСѓС‚Рё Рє С„Р°Р№Р»Р°Рј
import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TORRC_FILE = os.path.join(CURRENT_DIR, "torrc")
LAUNCHER_SCRIPT = os.path.join(CURRENT_DIR, "launcher.pyw")
CLOSER_SCRIPT = os.path.join(CURRENT_DIR, "closer.pyw")
AUTO_MAESTRO_SCRIPT = os.path.join(CURRENT_DIR, "auto_maestro.pyw")
UPDATE_BRIDGES_SCRIPT = os.path.join(CURRENT_DIR, "update_bridges_torrc.pyw")
MAESTRO_SCRIPT = os.path.join(CURRENT_DIR, "maestro.pyw")
TOR_EXE = os.path.join(CURRENT_DIR, "tor", "tor.exe")

class TorManager:
    def __init__(self):
        self.tor_running = False
        self.tor_process = None
        self.recreate_torrc = self._read_recreate_torrc()
        self.show_window = False

    def update_config(self, config):
        """РћР±РЅРѕРІР»СЏРµС‚ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ РёР· РѕСЃРЅРѕРІРЅРѕРіРѕ config"""
        self.show_window = config.get("tor_show_window", False)

    def _read_recreate_torrc(self):
        val = self.config.get("recreate_torrc", "none")
        if isinstance(val, bool): return "full" if val else "none"
        if val == "true": return "full"
        if val == "false": return "bridges"
        return str(val).lower()

    def _write_recreate_torrc(self, value):
        from managers import config_manager
        self.config["recreate_torrc"] = str(value).lower()
        config_manager.save_config(self.config)

    def _run_script(self, script_name):
        """Р—Р°РїСѓСЃРєР°РµС‚ СЃРєСЂРёРїС‚ РІ С„РѕРЅРµ"""
        if os.path.exists(script_name):
            subprocess.Popen([sys.executable, script_name], 
                           creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        return False

    def _run_script_blocking(self, script_name):
        """Р—Р°РїСѓСЃРєР°РµС‚ СЃРєСЂРёРїС‚ Рё Р¶РґРµС‚ РµРіРѕ Р·Р°РІРµСЂС€РµРЅРёСЏ"""
        if os.path.exists(script_name):
            subprocess.call([sys.executable, script_name])
            return True
        return False

    def _delete_torrc_files(self):
        """РЈРґР°Р»СЏРµС‚ С„Р°Р№Р»С‹ torrc"""
        torrc_paths = [TORRC_FILE, os.path.join(CURRENT_DIR, "for_servers/torrc")]
        
        for torrc_path in torrc_paths:
            if os.path.exists(torrc_path):
                try:
                    os.remove(torrc_path)
                except Exception as e:
                    pass

    def _start_tor_direct(self):
        """Р—Р°РїСѓСЃРєР°РµС‚ TOR РЅР°РїСЂСЏРјСѓСЋ С‡РµСЂРµР· tor.exe -f torrc СЃ Р°Р±СЃРѕР»СЋС‚РЅС‹РјРё РїСѓС‚СЏРјРё"""
        tor_exe_path = os.path.abspath(TOR_EXE)
        torrc_path = os.path.abspath(TORRC_FILE)
        
        # РџСЂРѕРІРµСЂСЏРµРј СЃСѓС‰РµСЃС‚РІРѕРІР°РЅРёРµ tor.exe
        if not os.path.exists(tor_exe_path):
            # РС‰РµРј tor.exe РІ РґСЂСѓРіРёС… РјРµСЃС‚Р°С…
            possible_paths = [
                os.path.join(CURRENT_DIR, "tor.exe"),
                os.path.join(CURRENT_DIR, "Tor", "tor.exe"),
                os.path.join(CURRENT_DIR, "bin", "tor.exe")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    tor_exe_path = os.path.abspath(path)
                    break
            else:
                log("tor.exe РЅРµ РЅР°Р№РґРµРЅ, РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ launcher.pyw")
                return self._run_script(LAUNCHER_SCRIPT)
        
        # РџСЂРѕРІРµСЂСЏРµРј СЃСѓС‰РµСЃС‚РІРѕРІР°РЅРёРµ torrc
        if not os.path.exists(torrc_path):
            log("torrc РЅРµ РЅР°Р№РґРµРЅ, Р·Р°РїСѓСЃРєР°РµРј auto_maestro РґР»СЏ СЃРѕР·РґР°РЅРёСЏ")
            self._run_script_blocking(AUTO_MAESTRO_SCRIPT)
            
            if not os.path.exists(torrc_path):
                log("РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕР·РґР°С‚СЊ torrc, РёСЃРїРѕР»СЊР·СѓРµРј launcher.pyw")
                return self._run_script(LAUNCHER_SCRIPT)
        
        # Р—Р°РїСѓСЃРєР°РµРј tor.exe
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if not self.show_window else subprocess.CREATE_NEW_CONSOLE
            
            if self.show_window:
                # РЎРѕР·РґР°РµРј РЅРѕРІРѕРµ РѕРєРЅРѕ РєРѕРЅСЃРѕР»Рё
                self.tor_process = subprocess.Popen(
                    [tor_exe_path, "-f", torrc_path],
                    creationflags=creation_flags,
                    cwd=CURRENT_DIR  # РЇРІРЅРѕ Р·Р°РґР°РµРј СЂР°Р±РѕС‡СѓСЋ РґРёСЂРµРєС‚РѕСЂРёСЋ
                )
            else:
                # Р‘РµР· РѕРєРЅР°
                self.tor_process = subprocess.Popen(
                    [tor_exe_path, "-f", torrc_path],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=CURRENT_DIR  # РЇРІРЅРѕ Р·Р°РґР°РµРј СЂР°Р±РѕС‡СѓСЋ РґРёСЂРµРєС‚РѕСЂРёСЋ
                )
            
            # РќРµР±РѕР»СЊС€Р°СЏ РїР°СѓР·Р° РґР»СЏ Р·Р°РїСѓСЃРєР° РїСЂРѕС†РµСЃСЃР°
            time.sleep(2)
            
            # РџСЂРѕРІРµСЂСЏРµРј, Р·Р°РїСѓСЃС‚РёР»СЃСЏ Р»Рё РїСЂРѕС†РµСЃСЃ
            if self.tor_process.poll() is None:
                log(f"TOR Р·Р°РїСѓС‰РµРЅ РЅР°РїСЂСЏРјСѓСЋ С‡РµСЂРµР· {tor_exe_path}")
                return True
            else:
                log("РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РїСѓСЃС‚РёС‚СЊ TOR РЅР°РїСЂСЏРјСѓСЋ, РёСЃРїРѕР»СЊР·СѓРµРј launcher.pyw")
                self.tor_process = None
                return self._run_script(LAUNCHER_SCRIPT)
                
        except Exception as e:
            log(f"РћС€РёР±РєР° Р·Р°РїСѓСЃРєР° TOR РЅР°РїСЂСЏРјСѓСЋ: {e}")
            self.tor_process = None
            return self._run_script(LAUNCHER_SCRIPT)

    def _stop_tor_direct(self):
        """РћСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ TOR, Р·Р°РїСѓС‰РµРЅРЅС‹Р№ РЅР°РїСЂСЏРјСѓСЋ"""
        if self.tor_process:
            try:
                # РџС‹С‚Р°РµРјСЃСЏ Р·Р°РІРµСЂС€РёС‚СЊ РїСЂРѕС†РµСЃСЃ
                self.tor_process.terminate()
                try:
                    self.tor_process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass
                if self.tor_process.poll() is None:
                    self.tor_process.kill()
                self.tor_process = None
                log("TOR РїСЂРѕС†РµСЃСЃ РѕСЃС‚Р°РЅРѕРІР»РµРЅ")
                return True
            except Exception as e:
                log(f"РћС€РёР±РєР° РѕСЃС‚Р°РЅРѕРІРєРё TOR РїСЂРѕС†РµСЃСЃР°: {e}")
        
        # Р•СЃР»Рё РЅРµ РїРѕР»СѓС‡РёР»РѕСЃСЊ С‡РµСЂРµР· РїСЂРѕС†РµСЃСЃ, РёСЃРїРѕР»СЊР·СѓРµРј closer.pyw
        return self._run_script(CLOSER_SCRIPT)

    def start(self):
        """Р—Р°РїСѓСЃРє TOR"""
        if self.tor_running:
            return True

        if self.recreate_torrc == "full":
            self._delete_torrc_files()
            self._run_script_blocking(AUTO_MAESTRO_SCRIPT)
        elif self.recreate_torrc == "bridges":
            self._run_script_blocking(UPDATE_BRIDGES_SCRIPT)
        # if "none", do nothing

        if not os.path.exists(TORRC_FILE):
            self._run_script_blocking(AUTO_MAESTRO_SCRIPT)
        
        # РўРѕР»СЊРєРѕ С‡РµСЂРµР· launcher.pyw, РєР°Рє РїСЂРѕСЃРёР» РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ
        if self._run_script(LAUNCHER_SCRIPT):
            self.tor_running = True
            return True

        return False

    def stop(self):
        """РћСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ TOR"""
        if not self.tor_running:
            return
        
        # РџС‹С‚Р°РµРјСЃСЏ РѕСЃС‚Р°РЅРѕРІРёС‚СЊ РЅР°РїСЂСЏРјСѓСЋ
        self._stop_tor_direct()
        self.tor_running = False

    def restart(self, parent=None):
        """РџРµСЂРµР·Р°РїСѓСЃРєР°РµС‚ TOR"""
        if self.tor_running:
            self.stop()
            time.sleep(2)
        
        if self.start():
            if parent:
                QMessageBox.information(parent, "РџРµСЂРµР·Р°РїСѓСЃРє TOR", 
                                      "TOR СѓСЃРїРµС€РЅРѕ РїРµСЂРµР·Р°РїСѓС‰РµРЅ!")
            return True
        else:
            if parent:
                QMessageBox.critical(parent, T("РћС€РёР±РєР°", "Error"), 
                                   "РќРµ СѓРґР°Р»РѕСЃСЊ РїРµСЂРµР·Р°РїСѓСЃС‚РёС‚СЊ TOR")
            return False

    def new_circuit(self, parent=None):
        """Р—Р°РїСЂР°С€РёРІР°РµС‚ РЅРѕРІСѓСЋ С†РµРїРѕС‡РєСѓ (NEWNYM) Сѓ TOR"""
        if not self.tor_running:
            if parent:
                QMessageBox.warning(parent, T("РћС€РёР±РєР°", "Error"), "TOR РЅРµ Р·Р°РїСѓС‰РµРЅ.")
            return False

        try:
            import socket
            import json
            pool_enabled = False
            pool_size = 3
            try:
                with open(os.path.join(CURRENT_DIR, "config.json"), "r", encoding="utf-8") as f:
                    config = json.load(f)
                    pool_enabled = config.get("tor_pool_enabled", False)
                    pool_size = int(config.get("tor_pool_size", 3))
            except:
                pass
                
            if pool_enabled and pool_size > 1:
                socks_port = 9853
                try:
                    with open(TORRC_FILE, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith("SocksPort "):
                                socks_port = int(line.split()[1])
                except: pass
                control_ports = [socks_port + 2000 + i for i in range(pool_size)]
            else:
                control_ports = [9851]
                
            success = True
            errors = []
            for cp in control_ports:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    s.connect(('127.0.0.1', cp))
                    s.sendall(b'AUTHENTICATE "toinet"\r\n')
                    resp = s.recv(1024).decode('utf-8')
                    if not resp.startswith('250'):
                        errors.append(f"Auth {cp}: {resp}")
                        success = False
                    else:
                        s.sendall(b'SIGNAL NEWNYM\r\n')
                        resp = s.recv(1024).decode('utf-8')
                        if not resp.startswith('250'):
                            errors.append(f"NEWNYM {cp}: {resp}")
                            success = False
                    s.close()
                except Exception as e:
                    errors.append(f"Port {cp}: {e}")
                    success = False
            
            if success:
                log("РЈСЃРїРµС€РЅРѕ Р·Р°РїСЂРѕС€РµРЅР° РЅРѕРІР°СЏ С†РµРїРѕС‡РєР° TOR")
                if parent:
                    QMessageBox.information(parent, "TOR", "РќРѕРІР°СЏ С†РµРїРѕС‡РєР° СѓСЃРїРµС€РЅРѕ Р·Р°РїСЂРѕС€РµРЅР°!")
                return True
            else:
                err_str = "\n".join(errors)
                log(f"РћС€РёР±РєР° РїСЂРё Р·Р°РїСЂРѕСЃРµ NEWNYM: {err_str}")
                if parent:
                    QMessageBox.warning(parent, T("РћС€РёР±РєР°", "Error"), f"РћС€РёР±РєР° РїСЂРё Р·Р°РїСЂРѕСЃРµ РЅРѕРІРѕР№ С†РµРїРѕС‡РєРё:\n{err_str}")
                return False
        except Exception as e:
            log(f"Р’РЅСѓС‚СЂРµРЅРЅСЏСЏ РѕС€РёР±РєР°: {e}")
            if parent:
                QMessageBox.warning(parent, T("РћС€РёР±РєР°", "Error"), f"Р’РЅСѓС‚СЂРµРЅРЅСЏСЏ РѕС€РёР±РєР°:\n{e}")
            return False

    def is_running(self):
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃС‚Р°С‚СѓСЃ СЂР°Р±РѕС‚С‹ TOR"""
        # РџСЂРѕРІРµСЂСЏРµРј, Р¶РёРІ Р»Рё РїСЂРѕС†РµСЃСЃ, РµСЃР»Рё Р·Р°РїСѓСЃРєР°Р»Рё РЅР°РїСЂСЏРјСѓСЋ
        if self.tor_running and self.tor_process:
            if self.tor_process.poll() is not None:
                self.tor_running = False
        return self.tor_running

    def toggle_recreate(self):
        """Р¦РёРєР»РёС‡РЅРѕРµ РїРµСЂРµРєР»СЋС‡РµРЅРёРµ СЂРµР¶РёРјР° РїРµСЂРµСЃРѕР·РґР°РЅРёСЏ torrc"""
        if self.recreate_torrc == "full": self.recreate_torrc = "bridges"
        elif self.recreate_torrc == "bridges": self.recreate_torrc = "none"
        else: self.recreate_torrc = "full"
        self._write_recreate_torrc(self.recreate_torrc)

    def get_recreate_mode(self):
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃС‚Р°С‚СѓСЃ С„Р»Р°РіР° РїРµСЂРµСЃРѕР·РґР°РЅРёСЏ torrc"""
        return self.recreate_torrc

    def delete_config(self):
        """РЈРґР°Р»СЏРµС‚ РєРѕРЅС„РёРіСѓСЂР°С†РёРѕРЅРЅС‹Рµ С„Р°Р№Р»С‹ TOR"""
        self._delete_torrc_files()

    def open_settings(self):
        """РћС‚РєСЂС‹РІР°РµС‚ РЅР°СЃС‚СЂРѕР№РєРё TOR (maestro.pyw, РќР• auto_maestro)"""
        # РЎРЅР°С‡Р°Р»Р° РїСЂРѕРІРµСЂСЏРµРј РЅР°Р»РёС‡РёРµ maestro.pyw
        if os.path.exists(MAESTRO_SCRIPT):
            try:
                # Р—Р°РїСѓСЃРєР°РµРј maestro.pyw СЃ РѕР±С‹С‡РЅС‹Рј РѕРєРЅРѕРј (РЅРµ СЃРєСЂС‹С‚С‹Рј)
                subprocess.Popen([sys.executable, MAESTRO_SCRIPT])
                log(f"Р—Р°РїСѓС‰РµРЅ {MAESTRO_SCRIPT}")
                return True
            except Exception as e:
                log(f"РћС€РёР±РєР° Р·Р°РїСѓСЃРєР° {MAESTRO_SCRIPT}: {e}")
        
        # Р•СЃР»Рё maestro.pyw РЅРµ РЅР°Р№РґРµРЅ, РїСЂРѕР±СѓРµРј auto_maestro.pyw
        if os.path.exists(AUTO_MAESTRO_SCRIPT):
            try:
                subprocess.Popen([sys.executable, AUTO_MAESTRO_SCRIPT])
                log(f"Р—Р°РїСѓС‰РµРЅ {AUTO_MAESTRO_SCRIPT} (РєР°Рє Р·Р°РїР°СЃРЅРѕР№ РІР°СЂРёР°РЅС‚)")
                return True
            except Exception as e:
                log(f"РћС€РёР±РєР° Р·Р°РїСѓСЃРєР° {AUTO_MAESTRO_SCRIPT}: {e}")
        
        # Р•СЃР»Рё РЅРёС‡РµРіРѕ РЅРµ СЃСЂР°Р±РѕС‚Р°Р»Рѕ
        QMessageBox.critical(None, T("РћС€РёР±РєР°", "Error"), 
                           f"РќРµ РЅР°Р№РґРµРЅС‹ С„Р°Р№Р»С‹ РЅР°СЃС‚СЂРѕРµРє TOR:\n"
                           f"{MAESTRO_SCRIPT}\n"
                           f"РёР»Рё\n{AUTO_MAESTRO_SCRIPT}")
        return False


def log(msg):
    print(f"[TOR Manager] {msg}")

def get_manager():
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЌРєР·РµРјРїР»СЏСЂ РјРµРЅРµРґР¶РµСЂР° TOR"""
    return TorManager()



