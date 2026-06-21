import sys
import os
import json
import subprocess
import platform
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox, QGroupBox, QCheckBox)
from PyQt5.QtCore import Qt, QProcess
import re
import webbrowser

CONFIG_FILE = "vk_turn_proxy_config.json"

class VKTurnProxyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.process = None
        self.initUI()
        self.load_config()

    def initUI(self):
        self.setWindowTitle("VK Turn Proxy Launcher")
        self.resize(500, 350)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: Arial;
                font-size: 12px;
            }
            QLineEdit, QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                padding: 4px;
                border-radius: 3px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QGroupBox {
                border: 1px solid #555555;
                margin-top: 15px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                color: #ffffff;
            }
            QCheckBox {
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout()

        # Settings Group
        settings_group = QGroupBox("Настройки (Settings)")
        settings_layout = QVBoxLayout()

        # Listen
        listen_layout = QHBoxLayout()
        listen_layout.addWidget(QLabel("Listen (IP:Port):"))
        self.listen_input = QLineEdit("127.0.0.1:9000")
        listen_layout.addWidget(self.listen_input)
        settings_layout.addLayout(listen_layout)

        # Peer
        peer_layout = QHBoxLayout()
        peer_layout.addWidget(QLabel("WG Peer (IP:Port):"))
        self.peer_input = QLineEdit("")
        self.peer_input.setPlaceholderText("IP_Сервера:56000")
        peer_layout.addWidget(self.peer_input)
        settings_layout.addLayout(peer_layout)

        # Provider
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Провайдер (Provider):"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["VK", "Yandex"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_change)
        provider_layout.addWidget(self.provider_combo)
        settings_layout.addLayout(provider_layout)

        # Link
        link_layout = QHBoxLayout()
        link_layout.addWidget(QLabel("Ссылка (Link):"))
        self.link_input = QLineEdit()
        link_layout.addWidget(self.link_input)
        settings_layout.addLayout(link_layout)

        # Additional Arguments
        args_layout = QHBoxLayout()
        self.vless_check = QCheckBox("VLESS (-vless)")
        self.nodtls_check = QCheckBox("No DTLS (-no-dtls)")
        args_layout.addWidget(self.vless_check)
        args_layout.addWidget(self.nodtls_check)
        settings_layout.addLayout(args_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Status
        self.status_label = QLabel("Статус: Остановлен (Stopped)")
        self.status_label.setStyleSheet("color: #ff5555; font-weight: bold;")
        layout.addWidget(self.status_label)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.start_btn = QPushButton("Запустить (Start)")
        self.start_btn.clicked.connect(self.start_proxy)
        self.stop_btn = QPushButton("Остановить (Stop)")
        self.stop_btn.clicked.connect(self.stop_proxy)
        self.stop_btn.setEnabled(False)

        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.on_provider_change(self.provider_combo.currentText())

    def on_provider_change(self, text):
        if text == "VK":
            self.link_input.setPlaceholderText("https://vk.com/call/join/...")
        else:
            self.link_input.setPlaceholderText("https://telemost.yandex.ru/j/...")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.listen_input.setText(config.get("listen", "127.0.0.1:9000"))
                    self.peer_input.setText(config.get("peer", ""))
                    self.provider_combo.setCurrentText(config.get("provider", "VK"))
                    self.link_input.setText(config.get("link", ""))
                    self.vless_check.setChecked(config.get("vless", False))
                    self.nodtls_check.setChecked(config.get("nodtls", False))
            except Exception as e:
                print(e)

    def save_config(self):
        config = {
            "listen": self.listen_input.text(),
            "peer": self.peer_input.text(),
            "provider": self.provider_combo.currentText(),
            "link": self.link_input.text(),
            "vless": self.vless_check.isChecked(),
            "nodtls": self.nodtls_check.isChecked()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(e)

    def get_executable(self):
        machine = platform.machine().lower()
        if "arm" in machine or "aarch64" in machine:
            exe = "client-windows-arm64.exe"
        else:
            exe = "client-windows-amd64.exe"
        
        # fallback
        if not os.path.exists(exe):
            if exe == "client-windows-arm64.exe" and os.path.exists("client-windows-amd64.exe"):
                return "client-windows-amd64.exe"
            elif exe == "client-windows-amd64.exe" and os.path.exists("client-windows-arm64.exe"):
                return "client-windows-arm64.exe"
        return exe

    def start_proxy(self):
        exe = self.get_executable()
        if not os.path.exists(exe):
            QMessageBox.critical(self, "Ошибка", f"Исполняемый файл {exe} не найден!")
            return

        listen = self.listen_input.text().strip()
        peer = self.peer_input.text().strip()
        provider = self.provider_combo.currentText()
        link = self.link_input.text().strip()
        vless = self.vless_check.isChecked()
        nodtls = self.nodtls_check.isChecked()

        if not peer or not link:
            QMessageBox.warning(self, "Ошибка", "Заполните параметры Peer и Ссылка!")
            return

        self.save_config()

        args = [exe, "-listen", listen, "-peer", peer]
        if provider == "VK":
            args.extend(["-vk-link", link])
        else:
            args.extend(["-udp", "-turn", "5.255.211.241", "-yandex-link", link])

        if vless:
            args.append("-vless")
        if nodtls:
            args.append("-no-dtls")

        try:
            self.process = QProcess(self)
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)
            self.process.finished.connect(self.stop_proxy)
            self.process.start(exe, args[1:])
            self.status_label.setText("Статус: Запущен (Running)")
            self.status_label.setStyleSheet("color: #55ff55; font-weight: bold;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.listen_input.setEnabled(False)
            self.peer_input.setEnabled(False)
            self.provider_combo.setEnabled(False)
            self.link_input.setEnabled(False)
            self.vless_check.setEnabled(False)
            self.nodtls_check.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить процесс:\n{e}")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        self.check_for_links(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
        self.check_for_links(data)

    def check_for_links(self, text):
        urls = re.findall(r'(?:http|https)://[^\s]+', text)
        for url in urls:
            webbrowser.open(url)

    def stop_proxy(self):
        if self.process:
            try:
                self.process.readyReadStandardOutput.disconnect()
                self.process.readyReadStandardError.disconnect()
                self.process.finished.disconnect()
            except: pass
            self.process.terminate()
            self.process.waitForFinished()
            self.process = None
        self.status_label.setText("Статус: Остановлен (Stopped)")
        self.status_label.setStyleSheet("color: #ff5555; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.listen_input.setEnabled(True)
        self.peer_input.setEnabled(True)
        self.provider_combo.setEnabled(True)
        self.link_input.setEnabled(True)
        self.vless_check.setEnabled(True)
        self.nodtls_check.setEnabled(True)

    def closeEvent(self, event):
        self.stop_proxy()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VKTurnProxyGUI()
    window.show()
    sys.exit(app.exec_())
