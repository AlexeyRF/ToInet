import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QGroupBox, QSpinBox, QCheckBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon

from managers import system_utils as lang
from managers import config_manager
from managers import ssh_manager

CURRENT_DIR = lang.get_base_dir()

def T(ru_text, en_text, fr_text=None, fr=None):
    if hasattr(lang, 'T'):
        return lang.T(ru_text, en_text, fr_text, fr)
    cur = getattr(lang, '_current_lang', 'ru')
    if cur == 'fr':
        return fr or fr_text or en_text or ru_text
    elif cur == 'en':
        return en_text or ru_text
    return ru_text

class SSHSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("SSH SOCKS5 Туннель", "SSH SOCKS5 Tunnel", "Tunnel SSH SOCKS5"))
        self.setFixedSize(450, 370)

        # Dark Title Bar matching window background
        try:
            import ctypes
            hwnd = int(self.winId())
            val = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))
            color = ctypes.c_int(0x00181818)  # Matches #181818 background (0x00BBGGRR)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
        except Exception:
            pass

        icon_path = os.path.join(CURRENT_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.config = config_manager.load_config()
        self.mgr = ssh_manager.get_manager(self.config)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #181818;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 8px;
                font-weight: bold;
                color: #5dade2;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLabel {
                color: #cccccc;
            }
            QLineEdit, QSpinBox {
                background-color: #242424;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px 6px;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 1px solid #0078d4;
            }
            QCheckBox {
                color: #cccccc;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: #242424;
                border: 1px solid #444444;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #383838;
                border-color: #555555;
            }
            QPushButton:pressed {
                background-color: #1f1f1f;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(8)

        # 1. Header with Title & Master Visibility Toggle
        header_layout = QHBoxLayout()
        title_label = QLabel(T("Настройки SSH Туннеля", "SSH Tunnel Settings", "Paramètres du tunnel SSH"))
        title_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff;")
        
        self.btn_mask_all = QPushButton("👁 " + T("Скрыть всё", "Mask all"))
        self.btn_mask_all.setCheckable(True)
        self.btn_mask_all.setChecked(self.config.get("ssh_hide_credentials", True))
        self.btn_mask_all.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_mask_all.toggled.connect(self.toggle_mask_all)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_mask_all)
        main_layout.addLayout(header_layout)

        # 2. Server Group
        server_group = QGroupBox(T("Параметры SSH сервера", "SSH Server Credentials", "Identifiants du serveur SSH"))
        server_layout = QVBoxLayout(server_group)
        server_layout.setContentsMargins(10, 8, 10, 8)
        server_layout.setSpacing(6)

        # Host and Port row
        host_row = QHBoxLayout()
        host_label = QLabel(T("Хост / IP:", "Host / IP:", "Hôte / IP :"))
        host_label.setFixedWidth(75)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("example.com / 1.2.3.4")
        self.host_input.setText(self.config.get("ssh_host", ""))

        port_label = QLabel(T("SSH Порт:", "SSH Port:", "Port SSH :"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(self.config.get("ssh_port", 22)))
        self.port_spin.setFixedWidth(65)

        host_row.addWidget(host_label)
        host_row.addWidget(self.host_input)
        host_row.addWidget(port_label)
        host_row.addWidget(self.port_spin)
        server_layout.addLayout(host_row)

        # User row
        user_row = QHBoxLayout()
        user_label = QLabel(T("Логин:", "User:", "Utilisateur :"))
        user_label.setFixedWidth(75)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("root / ubuntu")
        self.user_input.setText(self.config.get("ssh_user", ""))
        user_row.addWidget(user_label)
        user_row.addWidget(self.user_input)
        server_layout.addLayout(user_row)

        # Password row
        pass_row = QHBoxLayout()
        pass_label = QLabel(T("Пароль:", "Password:", "Mot de passe :"))
        pass_label.setFixedWidth(75)
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText(T("Пароль SSH", "SSH Password", "Mot de passe SSH"))
        self.pass_input.setText(self.config.get("ssh_pass", ""))
        pass_row.addWidget(pass_label)
        pass_row.addWidget(self.pass_input)
        server_layout.addLayout(pass_row)

        main_layout.addWidget(server_group)

        # 3. Local SOCKS5 & LAN Sharing Group
        local_group = QGroupBox(T("Локальный прокси (SOCKS5)", "Local SOCKS5 Proxy", "Proxy local SOCKS5"))
        local_layout = QVBoxLayout(local_group)
        local_layout.setContentsMargins(10, 8, 10, 8)
        local_layout.setSpacing(6)

        local_row = QHBoxLayout()
        socks_label = QLabel(T("Порт:", "Port:", "Port :"))
        socks_label.setFixedWidth(75)
        self.socks_spin = QSpinBox()
        self.socks_spin.setRange(1024, 65535)
        self.socks_spin.setValue(int(self.config.get("ssh_socks_port", 1770)))
        self.socks_spin.setFixedWidth(75)

        self.auto_reconnect_cb = QCheckBox(T("Автопереподключение", "Auto reconnect", "Reconnexion automatique"))
        self.auto_reconnect_cb.setChecked(self.config.get("ssh_auto_reconnect", True))

        local_row.addWidget(socks_label)
        local_row.addWidget(self.socks_spin)
        local_row.addSpacing(15)
        local_row.addWidget(self.auto_reconnect_cb)
        local_row.addStretch()
        local_layout.addLayout(local_row)

        # LAN Share Row (0.0.0.0 instead of 127.0.0.1)
        self.share_lan_cb = QCheckBox(T("Раздавать в локальную сеть (0.0.0.0 вместо 127.0.0.1)", "Share to local network (0.0.0.0 instead of 127.0.0.1)", "Partager sur le réseau local (0.0.0.0 au lieu de 127.0.0.1)"))
        self.share_lan_cb.setChecked(self.config.get("ssh_share_lan", False))
        self.share_lan_cb.clicked.connect(self.on_share_lan_clicked)
        local_layout.addWidget(self.share_lan_cb)

        main_layout.addWidget(local_group)

        # 4. Compact Status Line
        self.status_label = QLabel(T("Статус: Проверка...", "Status: Checking...", "Statut : Vérification..."))
        self.status_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # 5. Bottom Buttons (Toggle Tunnel, Save, Close)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_toggle_tunnel = QPushButton(T("Запустить туннель", "Start Tunnel", "Démarrer le tunnel"))
        self.btn_toggle_tunnel.setFixedHeight(30)
        self.btn_toggle_tunnel.setStyleSheet("background-color: #218c53; color: white; border: none; border-radius: 4px; font-weight: bold;")
        self.btn_toggle_tunnel.clicked.connect(self.toggle_tunnel)

        save_btn = QPushButton(T("Сохранить", "Save", "Enregistrer"))
        save_btn.setFixedHeight(30)
        save_btn.setStyleSheet("background-color: #0078d4; color: white; border: none; border-radius: 4px; font-weight: bold;")
        save_btn.clicked.connect(self.save_settings)

        close_btn = QPushButton(T("Закрыть", "Close", "Fermer"))
        close_btn.setFixedHeight(30)
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_toggle_tunnel)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

        # Apply initial masking
        self.apply_masking(self.btn_mask_all.isChecked())

        # Status timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status_ui)
        self.timer.start(1000)
        self.update_status_ui()

    def toggle_mask_all(self, checked):
        self.apply_masking(checked)
        self.config["ssh_hide_credentials"] = checked
        config_manager.save_config(self.config)

    def apply_masking(self, mask):
        mode = QLineEdit.Password if mask else QLineEdit.Normal
        self.host_input.setEchoMode(mode)
        self.user_input.setEchoMode(mode)
        self.pass_input.setEchoMode(mode)
        self.btn_mask_all.setText("👁 " + (T("Скрыть всё", "Mask all", "Masquer tout") if not mask else T("Показать всё", "Show all", "Afficher tout")))

    def on_share_lan_clicked(self, checked):
        if checked:
            reply = QMessageBox.warning(
                self,
                T("Предупреждение безопасности", "Security Warning", "Avertissement de sécurité"),
                T(
                    "⚠️ Внимание!\n\n"
                    "Включение раздачи на 0.0.0.0 откроет доступ к вашему SOCKS5 прокси для всех устройств в локальной сети (Wi-Fi / LAN).\n"
                    "Любой компьютер, телефон или устройство в вашей сети сможет направлять трафик через ваш SSH туннель без авторизации.\n\n"
                    "Вы действительно хотите включить раздачу?",
                    "⚠️ Warning!\n\n"
                    "Enabling sharing on 0.0.0.0 will expose your SOCKS5 proxy to all devices in the local network (Wi-Fi / LAN).\n"
                    "Any computer or device in your local network will be able to route traffic through your SSH tunnel without authentication.\n\n"
                    "Are you sure you want to enable LAN sharing?",
                    "⚠️ Attention !\n\n"
                    "L'activation du partage sur 0.0.0.0 permettra à tous les appareils de votre réseau local (Wi-Fi / LAN) d'accéder à votre proxy SOCKS5.\n"
                    "N'importe quel appareil pourra acheminer du trafic sans authentification.\n\n"
                    "Voulez-vous vraiment activer le partage ?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self.share_lan_cb.setChecked(False)

    def update_status_ui(self):
        running = self.mgr.is_running()
        port = self.socks_spin.value()
        bind_host = "0.0.0.0" if self.share_lan_cb.isChecked() else "127.0.0.1"
        if running:
            self.status_label.setText(T(f"🟢 Подключено (SOCKS5 активен на {bind_host}:{port})", 
                                        f"🟢 Connected (SOCKS5 listening on {bind_host}:{port})",
                                        f"🟢 Connecté (SOCKS5 actif sur {bind_host}:{port})"))
            self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
            self.btn_toggle_tunnel.setText(T("Остановить туннель", "Stop Tunnel", "Arrêter le tunnel"))
            self.btn_toggle_tunnel.setStyleSheet("background-color: #c0392b; color: white; border: none; border-radius: 4px; font-weight: bold;")
        else:
            self.status_label.setText(T("⚪ Отключено", "⚪ Disconnected", "⚪ Déconnecté"))
            self.status_label.setStyleSheet("color: #888888; font-weight: bold;")
            self.btn_toggle_tunnel.setText(T("Запустить туннель", "Start Tunnel", "Démarrer le tunnel"))
            self.btn_toggle_tunnel.setStyleSheet("background-color: #218c53; color: white; border: none; border-radius: 4px; font-weight: bold;")

    def get_form_config(self):
        return {
            "ssh_host": self.host_input.text().strip(),
            "ssh_port": self.port_spin.value(),
            "ssh_user": self.user_input.text().strip(),
            "ssh_pass": self.pass_input.text(),
            "ssh_socks_port": self.socks_spin.value(),
            "ssh_share_lan": self.share_lan_cb.isChecked(),
            "ssh_auto_reconnect": self.auto_reconnect_cb.isChecked(),
            "ssh_hide_credentials": self.btn_mask_all.isChecked()
        }

    def save_settings(self, silent=False):
        cfg = self.get_form_config()
        self.config.update(cfg)
        config_manager.save_config(self.config)
        self.mgr.update_config(self.config)
        if not silent:
            QMessageBox.information(self, T("Сохранено", "Saved", "Enregistré"), T("Настройки SSH успешно сохранены!", "SSH settings saved successfully!", "Paramètres SSH enregistrés avec succès !"))

    def toggle_tunnel(self):
        self.save_settings(silent=True)
        if self.mgr.is_running():
            self.mgr.stop()
        else:
            self.mgr.start()
        self.update_status_ui()

def main():
    app = QApplication(sys.argv)
    window = SSHSettingsWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
