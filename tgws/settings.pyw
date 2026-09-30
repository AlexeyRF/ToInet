import sys
import os

# Р”РѕР±Р°РІР»СЏРµРј СЂРѕРґРёС‚РµР»СЊСЃРєСѓСЋ РґРёСЂРµРєС‚РѕСЂРёСЋ РІ sys.path
import sys, os; CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import lang
import json
import socket
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QCheckBox, 
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt

from tgws import config as tgws_config

from lang import T

from managers import config_manager

class TGWSSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = config_manager.load_config()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(T("РќР°СЃС‚СЂРѕР№РєРё TGWS Proxy", "TGWS Proxy Settings"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QLabel { color: white; }
            QLineEdit, QTextEdit { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 5px; }
            QCheckBox { color: white; }
            QPushButton { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 5px 15px; }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton:pressed { background-color: #1d1d1d; }
        """)
        
        layout = QVBoxLayout()
        
        # IP Р°РґСЂРµСЃ
        layout.addWidget(QLabel("IP-Р°РґСЂРµСЃ РїСЂРѕРєСЃРё:"))
        self.host_edit = QLineEdit(self.config.get("tgws_host", "127.0.0.1"))
        layout.addWidget(self.host_edit)
        
        # РџРѕСЂС‚
        layout.addWidget(QLabel("РџРѕСЂС‚ РїСЂРѕРєСЃРё:"))
        self.port_edit = QLineEdit(str(self.config.get("tgws_port", 1480)))
        layout.addWidget(self.port_edit)
        
        # DC РјР°РїРїРёРЅРіРё
        layout.addWidget(QLabel("DC в†’ IP РјР°РїРїРёРЅРіРё (РїРѕ РѕРґРЅРѕРјСѓ РЅР° СЃС‚СЂРѕРєСѓ, С„РѕСЂРјР°С‚ DC:IP):"))
        self.dc_text = QTextEdit()
        self.dc_text.setPlainText("\n".join(self.config.get("tgws_dc_ip", ["2:149.154.167.220", "4:149.154.167.220"])))
        self.dc_text.setMaximumHeight(100)
        layout.addWidget(self.dc_text)
        
        # MTProto Secret
        layout.addWidget(QLabel("MTProto РЎРµРєСЂРµС‚ (32 hex СЃРёРјРІРѕР»Р°):"))
        self.secret_edit = QLineEdit(self.config.get("tgws_secret", ""))
        layout.addWidget(self.secret_edit)

        # Fake TLS Domain
        layout.addWidget(QLabel("Fake TLS Р”РѕРјРµРЅ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ):"))
        self.fake_tls_edit = QLineEdit(self.config.get("tgws_fake_tls", ""))
        layout.addWidget(self.fake_tls_edit)
        
        layout.addWidget(QLabel(T("Domain Fronting SNI (РЈСЃС‚Р°СЂРµР»Рѕ):", "Domain Fronting SNI (Obsolete):")))
        self.fronting_edit = QLineEdit(self.config.get("tgws_fronting_sni", ""))
        self.fronting_edit.setPlaceholderText("РќР°РїСЂРёРјРµСЂ: sprinthost.ru")
        self.fronting_edit.setToolTip(T("Р’РєР»СЋС‡РёС‚СЊ СЃС‚Р°СЂС‹Р№ С„РѕР»Р»Р±СЌРє СЃ РїРѕРґРјРµРЅРѕР№ SNI. РћСЃС‚Р°РІСЊС‚Рµ РїСѓСЃС‚С‹Рј РґР»СЏ РѕС‚РєР»СЋС‡РµРЅРёСЏ.", "Enable old fallback with SNI masking. Leave empty to disable."))
        layout.addWidget(self.fronting_edit)
        
        # Verbose Р»РѕРіРёСЂРѕРІР°РЅРёРµ
        self.verbose_check = QCheckBox("РџРѕРґСЂРѕР±РЅРѕРµ Р»РѕРіРёСЂРѕРІР°РЅРёРµ (verbose)")
        self.verbose_check.setChecked(self.config.get("tgws_verbose", False))
        layout.addWidget(self.verbose_check)
        

        
        # РРЅС„РѕСЂРјР°С†РёСЏ
        info_label = QLabel(
            "TGWS Proxy Р±СѓРґРµС‚ СЂР°Р±РѕС‚Р°С‚СЊ РЅР° СѓРєР°Р·Р°РЅРЅРѕРј РїРѕСЂС‚Сѓ.\n"
            f"SOCKS5: {self.config.get('tgws_host', '127.0.0.1')}:{self.config.get('tgws_port', 1480)} (Р±РµР· Р»РѕРіРёРЅР°/РїР°СЂРѕР»СЏ)\n"
            f"MTProto: РЎРµРєСЂРµС‚ РЅР°С‡РёРЅР°РµС‚СЃСЏ СЃ ee/dd Рё СЃРѕРґРµСЂР¶РёС‚ РІР°С€ РґРѕРјРµРЅ\n\n"
            "РџСЂРёРјРµС‡Р°РЅРёРµ: РџРѕСЃР»Рµ СЃРѕС…СЂР°РЅРµРЅРёСЏ РЅР°СЃС‚СЂРѕРµРє РјРѕР¶РµС‚ РїРѕС‚СЂРµР±РѕРІР°С‚СЊСЃСЏ\n"
            "РїРµСЂРµР·Р°РїСѓСЃРє TGWS Proxy РґР»СЏ РїСЂРёРјРµРЅРµРЅРёСЏ РёР·РјРµРЅРµРЅРёР№."
        )
        info_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(info_label)
        
        # РљРЅРѕРїРєРё
        
        # РљРЅРѕРїРєР° РґР»СЏ С‚РµСЃС‚Р° СЃС‚СЂР°С‚РµРіРёР№ РІСЂРµРјРµРЅРЅРѕ Р·Р°РєРѕРјРјРµРЅС‚РёСЂРѕРІР°РЅР°, С‚Р°Рє РєР°Рє РїРѕРєР° РЅРµС‚ РЅРµРѕР±С…РѕРґРёРјРѕСЃС‚Рё
        # self.tester_btn = QPushButton("РўРµСЃС‚ СЃС‚СЂР°С‚РµРіРёР№ TGWS")
        # def run_tester():
        #     import subprocess, sys, os
        #     subprocess.Popen([sys.executable, "tgws/tester_gui.pyw"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        # self.tester_btn.clicked.connect(run_tester)
        # layout.addWidget(self.tester_btn)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(T("РЎРѕС…СЂР°РЅРёС‚СЊ", "Save"))
        self.cancel_btn = QPushButton(T("РћС‚РјРµРЅР°", "Cancel"))
        
        self.save_btn.clicked.connect(self.validate_and_save)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def validate_and_save(self):
        """РџСЂРѕРІРµСЂРєР° Рё СЃРѕС…СЂР°РЅРµРЅРёРµ РЅР°СЃС‚СЂРѕРµРє"""
        host = self.host_edit.text().strip()
        
        # РџСЂРѕРІРµСЂРєР° IP
        try:
            socket.inet_aton(host)
        except OSError:
            QMessageBox.critical(self, T("РћС€РёР±РєР°", "Error"), "РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ IP-Р°РґСЂРµСЃ.")
            return
        
        # РџСЂРѕРІРµСЂРєР° РїРѕСЂС‚Р°
        try:
            port = int(self.port_edit.text().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, T("РћС€РёР±РєР°", "Error"), "РџРѕСЂС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ С‡РёСЃР»РѕРј РѕС‚ 1 РґРѕ 65535")
            return
        
        # РџСЂРѕРІРµСЂРєР° DC РјР°РїРїРёРЅРіРѕРІ
        lines = [l.strip() for l in self.dc_text.toPlainText().strip().splitlines() if l.strip()]
        try:
            tgws_config.parse_dc_ip_list(lines)
        except ValueError as e:
            QMessageBox.critical(self, T("РћС€РёР±РєР°", "Error"), str(e))
            return
            
        secret = self.secret_edit.text().strip()
        if len(secret) != 32 or not all(c in '0123456789abcdefABCDEF' for c in secret):
            QMessageBox.critical(self, T("РћС€РёР±РєР°", "Error"), "РЎРµРєСЂРµС‚ РґРѕР»Р¶РµРЅ СЃРѕСЃС‚РѕСЏС‚СЊ РёР· 32 С€РµСЃС‚РЅР°РґС†Р°С‚РµСЂРёС‡РЅС‹С… СЃРёРјРІРѕР»РѕРІ")
            return
        
        # РЎРѕС…СЂР°РЅСЏРµРј РЅР°СЃС‚СЂРѕР№РєРё
        self.config["tgws_host"] = host
        self.config["tgws_port"] = port
        self.config["tgws_dc_ip"] = lines
        self.config["tgws_secret"] = secret
        self.config["tgws_fake_tls"] = self.fake_tls_edit.text().strip()
        self.config["tgws_fronting_sni"] = self.fronting_edit.text().strip()
        self.config["tgws_verbose"] = self.verbose_check.isChecked()

        config_manager.save_config(self.config)
        
        QMessageBox.information(self, T("РЈСЃРїРµС…", "Success"), "РќР°СЃС‚СЂРѕР№РєРё TGWS Proxy СЃРѕС…СЂР°РЅРµРЅС‹!")
        self.accept()

def main():
    app = QApplication(sys.argv)
    dialog = TGWSSettingsDialog()
    dialog.exec_()

if __name__ == "__main__":
    main()



