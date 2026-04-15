import os
import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QListWidget, QListWidgetItem, QFileDialog, 
                             QMessageBox, QGroupBox, QGridLayout, QComboBox,
                             QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QIcon
import requests
from io import BytesIO

# Dictionary with countries and their flag emoji/code
countries = {
    "Австралия": ("au", "🇦🇺"),
    "Австрия": ("at", "🇦🇹"),
    "Болгария": ("bg", "🇧🇬"),
    "Бразилия": ("br", "🇧🇷"),
    "Великобритания": ("gb", "🇬🇧"),
    "Венгрия": ("hu", "🇭🇺"),
    "Германия": ("de", "🇩🇪"),
    "Дания": ("dk", "🇩🇰"),
    "Исландия": ("is", "🇮🇸"),
    "Испания": ("es", "🇪🇸"),
    "Канада": ("ca", "🇨🇦"),
    "Нидерланды": ("nl", "🇳🇱"),
    "Польша": ("pl", "🇵🇱"),
    "Россия": ("ru", "🇷🇺"),
    "Румыния": ("ro", "🇷🇴"),
    "Сингапур": ("sg", "🇸🇬"),
    "Словакия": ("sk", "🇸🇰"),
    "США": ("us", "🇺🇸"),
    "Финляндия": ("fi", "🇫🇮"),
    "Франция": ("fr", "🇫🇷"),
    "Чехия": ("cz", "🇨🇿"),
    "Швейцария": ("ch", "🇨🇭"),
    "Швеция": ("se", "🇸🇪"),
    "Япония": ("jp", "🇯🇵")
}

class CountryListWidget(QListWidget):
    """Custom list widget for displaying countries with flags"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.MultiSelection)
        self.setMinimumHeight(200)
        self.setFont(QFont("Segoe UI", 10))
        
    def add_country(self, name, flag_emoji, code):
        """Add a country item with flag"""
        item = QListWidgetItem(f"{flag_emoji} {name}")
        item.setData(Qt.UserRole, code)
        item.setData(Qt.UserRole + 1, name)
        self.addItem(item)
        
    def get_selected_countries(self):
        """Get list of selected country codes"""
        codes = []
        for item in self.selectedItems():
            codes.append(item.data(Qt.UserRole))
        return codes

class TorrcConfigurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Конфигуратор")
        self.setMinimumSize(800, 750)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 12px;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 11px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #3c3c3c;
                color: #e0e0e0;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#browseBtn {
                background-color: #555;
                padding: 5px 15px;
            }
            QPushButton#browseBtn:hover {
                background-color: #666;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
                color: #e0e0e0;
                font-size: 11px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #555;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #2b2b2b;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666;
            }
            QRadioButton {
                color: #e0e0e0;
                font-size: 11px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 13px;
                height: 13px;
            }
            QRadioButton::indicator:unchecked {
                border: 1px solid #555;
                border-radius: 7px;
                background-color: #3c3c3c;
            }
            QRadioButton::indicator:checked {
                border: 1px solid #4CAF50;
                border-radius: 7px;
                background-color: #4CAF50;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #3c3c3c;
                color: #e0e0e0;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-right: 5px;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
        """)
        
        # Set default paths
        self.current_dir = os.getcwd()
        self.data_dir = os.path.join(self.current_dir, "data")
        self.geoip_path = os.path.join(self.current_dir, "data", "geoip")
        self.geoipv6_path = os.path.join(self.current_dir, "data", "geoip6")
        self.bridges_path = os.path.join(self.current_dir, "bridges.txt")
        self.pt_config_path = os.path.join(self.current_dir, "tor", "pluggable_transports", "pt_config.json")
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Tor Exit Node Configuration")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #4CAF50;
            padding: 10px;
            border-bottom: 2px solid #4CAF50;
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Countries selection group
        countries_group = QGroupBox("Выбрать страны конечного ip")
        countries_layout = QVBoxLayout()
        countries_layout.setSpacing(10)
        
        # Country list
        self.country_list = CountryListWidget()
        for name, (code, flag) in sorted(countries.items()):
            self.country_list.add_country(name, flag, code)
        countries_layout.addWidget(self.country_list)
        
        # Selected countries display
        self.selected_label = QLabel("Выбрано: Ничего")
        self.selected_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.selected_label.setAlignment(Qt.AlignCenter)
        self.country_list.itemSelectionChanged.connect(self.update_selected_label)
        countries_layout.addWidget(self.selected_label)
        
        countries_group.setLayout(countries_layout)
        main_layout.addWidget(countries_group)
        
        # Bridges mode selection group
        bridges_mode_group = QGroupBox("Режим мостов")
        bridges_mode_layout = QVBoxLayout()
        
        # Radio buttons for bridge modes
        self.bridge_mode_group = QButtonGroup()
        
        self.normal_mode_rb = QRadioButton("Обычный режим (использовать bridges.txt)")
        self.normal_mode_rb.setChecked(True)
        self.obfs4_mode_rb = QRadioButton("Предустановленные obfs4 мосты")
        self.snowflake_mode_rb = QRadioButton("Предустановленные snowflake мосты")
        self.conjure_mode_rb = QRadioButton("Предустановленные conjure мосты")
        self.meek_mode_rb = QRadioButton("Предустановленные meek мосты")
        
        self.bridge_mode_group.addButton(self.normal_mode_rb, 0)
        self.bridge_mode_group.addButton(self.obfs4_mode_rb, 1)
        self.bridge_mode_group.addButton(self.snowflake_mode_rb, 2)
        self.bridge_mode_group.addButton(self.conjure_mode_rb, 3)
        self.bridge_mode_group.addButton(self.meek_mode_rb, 4)
        
        bridges_mode_layout.addWidget(self.normal_mode_rb)
        bridges_mode_layout.addWidget(self.obfs4_mode_rb)
        bridges_mode_layout.addWidget(self.snowflake_mode_rb)
        bridges_mode_layout.addWidget(self.conjure_mode_rb)
        bridges_mode_layout.addWidget(self.meek_mode_rb)
        
        # Connect radio buttons to update UI
        self.normal_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.obfs4_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.snowflake_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.conjure_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        self.meek_mode_rb.toggled.connect(self.on_bridge_mode_changed)
        
        bridges_mode_group.setLayout(bridges_mode_layout)
        main_layout.addWidget(bridges_mode_group)
        
        # Bridges file group (for normal mode)
        bridges_file_group = QGroupBox("Мосты (для обычного режима)")
        bridges_file_layout = QGridLayout()
        
        bridges_label = QLabel("Файл мостов (bridges.txt):")
        bridges_label.setStyleSheet("font-weight: normal;")
        bridges_file_layout.addWidget(bridges_label, 0, 0)
        
        self.bridges_edit = QLineEdit()
        self.bridges_edit.setText(self.bridges_path)
        self.bridges_edit.setReadOnly(True)
        bridges_file_layout.addWidget(self.bridges_edit, 0, 1)
        
        bridges_browse_btn = QPushButton("Выбрать")
        bridges_browse_btn.setObjectName("browseBtn")
        bridges_browse_btn.clicked.connect(self.browse_bridges)
        bridges_file_layout.addWidget(bridges_browse_btn, 0, 2)
        
        bridges_file_group.setLayout(bridges_file_layout)
        main_layout.addWidget(bridges_file_group)
        self.bridges_file_group = bridges_file_group
        
        # Tor directories group
        tor_group = QGroupBox("Файлы TOR")
        tor_layout = QGridLayout()
        
        # Data directory
        data_label = QLabel("Папка Data:")
        data_label.setStyleSheet("font-weight: normal;")
        tor_layout.addWidget(data_label, 0, 0)
        
        self.data_edit = QLineEdit()
        self.data_edit.setText(self.data_dir)
        tor_layout.addWidget(self.data_edit, 0, 1)
        
        data_browse_btn = QPushButton("Выбрать")
        data_browse_btn.setObjectName("browseBtn")
        data_browse_btn.clicked.connect(self.browse_data_dir)
        tor_layout.addWidget(data_browse_btn, 0, 2)
        
        # GeoIP file
        geoip_label = QLabel("GeoIP Файл:")
        geoip_label.setStyleSheet("font-weight: normal;")
        tor_layout.addWidget(geoip_label, 1, 0)
        
        self.geoip_edit = QLineEdit()
        self.geoip_edit.setText(self.geoip_path)
        tor_layout.addWidget(self.geoip_edit, 1, 1)
        
        geoip_browse_btn = QPushButton("Выбрать")
        geoip_browse_btn.setObjectName("browseBtn")
        geoip_browse_btn.clicked.connect(lambda: self.browse_file(self.geoip_edit))
        tor_layout.addWidget(geoip_browse_btn, 1, 2)
        
        # GeoIPv6 file
        geoipv6_label = QLabel("GeoIPv6 Файл:")
        geoipv6_label.setStyleSheet("font-weight: normal;")
        tor_layout.addWidget(geoipv6_label, 2, 0)
        
        self.geoipv6_edit = QLineEdit()
        self.geoipv6_edit.setText(self.geoipv6_path)
        tor_layout.addWidget(self.geoipv6_edit, 2, 1)
        
        geoipv6_browse_btn = QPushButton("Выбрать")
        geoipv6_browse_btn.setObjectName("browseBtn")
        geoipv6_browse_btn.clicked.connect(lambda: self.browse_file(self.geoipv6_edit))
        tor_layout.addWidget(geoipv6_browse_btn, 2, 2)
        
        tor_group.setLayout(tor_layout)
        main_layout.addWidget(tor_group)
        
        # Generate button
        generate_btn = QPushButton("Создать конфигурацию")
        generate_btn.setMinimumHeight(40)
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        generate_btn.clicked.connect(self.generate_torrc)
        main_layout.addWidget(generate_btn)
        
    def on_bridge_mode_changed(self):
        """Handle bridge mode change"""
        if self.normal_mode_rb.isChecked():
            self.bridges_file_group.setEnabled(True)
        else:
            self.bridges_file_group.setEnabled(False)
                
    def update_selected_label(self):
        """Update the selected countries label"""
        selected = self.country_list.selectedItems()
        if selected:
            countries_text = []
            for item in selected:
                name = item.data(Qt.UserRole + 1)
                countries_text.append(name)
            self.selected_label.setText(f"Выбрано: {', '.join(countries_text)}")
        else:
            self.selected_label.setText("Выбрано: Ничего")
            
    def browse_bridges(self):
        """Browse for bridges.txt file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл моста", "", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.bridges_edit.setText(path)
            
    def browse_data_dir(self):
        """Browse for data directory"""
        path = QFileDialog.getExistingDirectory(self, "Выбрать Data папку")
        if path:
            self.data_edit.setText(path)
            
    def browse_file(self, line_edit):
        """Browse for any file"""
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать Файл")
        if path:
            line_edit.setText(path)
    
    def load_pt_config(self):
        """Load pluggable transports configuration from JSON file"""
        try:
            if os.path.exists(self.pt_config_path):
                with open(self.pt_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Return default config if file not found
                return {
                    "pluggableTransports": {
                        "lyrebird": "ClientTransportPlugin meek_lite,obfs2,obfs3,obfs4,scramblesuit,webtunnel exec ${pt_path}lyrebird.exe",
                        "snowflake": "ClientTransportPlugin snowflake exec ${pt_path}lyrebird.exe",
                        "conjure": "ClientTransportPlugin conjure exec ${pt_path}conjure-client.exe -registerURL https://registration.refraction.network/api"
                    },
                    "bridges": {
                        "meek": [
                            "meek_lite 192.0.2.20:80 url=https://1603026938.rsc.cdn77.org front=www.phpmyadmin.net utls=HelloRandomizedALPN"
                        ],
                        "obfs4": [
                            "obfs4 37.218.245.14:38224 D9A82D2F9C2F65A18407B1D2B764F130847F8B5D cert=bjRaMrr1BRiAW8IE9U5z27fQaYgOhX1UCmOpg2pFpoMvo6ZgQMzLsaTzzQNTlm7hNcb+Sg iat-mode=0",
                            "obfs4 209.148.46.65:443 74FAD13168806246602538555B5521A0383A1875 cert=ssH+9rP8dG2NLDN2XuFw63hIO/9MNNinLmxQDpVa+7kTOa9/m+tGWT1SmSYpQ9uTBGa6Hw iat-mode=0",
                            "obfs4 146.57.248.225:22 10A6CD36A537FCE513A322361547444B393989F0 cert=K1gDtDAIcUfeLqbstggjIw2rtgIKqdIhUlHp82XRqNSq/mtAjp1BIC9vHKJ2FAEpGssTPw iat-mode=0",
                            "obfs4 45.145.95.6:27015 C5B7CD6946FF10C5B3E89691A7D3F2C122D2117C cert=TD7PbUO0/0k6xYHMPW3vJxICfkMZNdkRrb63Zhl5j9dW3iRGiCx0A7mPhe5T2EDzQ35+Zw iat-mode=0",
                            "obfs4 51.222.13.177:80 5EDAC3B810E12B01F6FD8050D2FD3E277B289A08 cert=2uplIpLQ0q9+0qMFrK5pkaYRDOe460LL9WHBvatgkuRr/SL31wBOEupaMMJ6koRE6Ld0ew iat-mode=0",
                            "obfs4 212.83.43.95:443 BFE712113A72899AD685764B211FACD30FF52C31 cert=ayq0XzCwhpdysn5o0EyDUbmSOx3X/oTEbzDMvczHOdBJKlvIdHHLJGkZARtT4dcBFArPPg iat-mode=1",
                            "obfs4 212.83.43.74:443 39562501228A4D5E27FCA4C0C81A01EE23AE3EE4 cert=PBwr+S8JTVZo6MPdHnkTwXJPILWADLqfMGoVvhZClMq/Urndyd42BwX9YFJHZnBB3H0XCw iat-mode=1"
                        ],
                        "snowflake": [
                            "snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://1098762253.rsc.cdn77.org/ fronts=app.datapacket.com,www.datapacket.com ice=stun:stun.epygi.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.mixvoip.com:3478,stun:stun.nextcloud.com:3478,stun:stun.bethesda.net:3478,stun:stun.nextcloud.com:443 utls-imitate=hellorandomizedalpn",
                            "snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA fingerprint=8838024498816A039FCBBAB14E6F40A0843051FA url=https://1098762253.rsc.cdn77.org/ fronts=app.datapacket.com,www.datapacket.com ice=stun:stun.epygi.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.mixvoip.com:3478,stun:stun.nextcloud.com:3478,stun:stun.bethesda.net:3478,stun:stun.nextcloud.com:443 utls-imitate=hellorandomizedalpn"
                        ]
                    }
                }
        except Exception as e:
            QMessageBox.warning(self, "Предупреждение", f"Не удалось загрузить pt_config.json: {e}")
            return None
    
    def get_bridges_and_transport(self):
        """Get bridges and transport plugin based on selected mode"""
        pt_config = self.load_pt_config()
        if not pt_config:
            return [], None
        
        bridges = []
        transport_plugin = None
        pt_path = os.path.join(self.current_dir, "tor", "pluggable_transports", "")
        
        if self.normal_mode_rb.isChecked():
            # Normal mode: read from bridges.txt
            bridges_path = self.bridges_edit.text()
            if os.path.exists(bridges_path):
                try:
                    with open(bridges_path, 'r', encoding='utf-8') as f:
                        bridges = [line.strip() for line in f if line.strip()]
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл мостов: {e}")
                    return [], None
            
            # For normal mode, use lyrebird for all transports
            if "pluggableTransports" in pt_config and "lyrebird" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["lyrebird"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.obfs4_mode_rb.isChecked():
            # Obfs4 preset bridges
            if "bridges" in pt_config and "obfs4" in pt_config["bridges"]:
                bridges = pt_config["bridges"]["obfs4"]
            if "pluggableTransports" in pt_config and "lyrebird" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["lyrebird"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.snowflake_mode_rb.isChecked():
            # Snowflake preset bridges
            if "bridges" in pt_config and "snowflake" in pt_config["bridges"]:
                bridges = pt_config["bridges"]["snowflake"]
            if "pluggableTransports" in pt_config and "snowflake" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["snowflake"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.conjure_mode_rb.isChecked():
            # Conjure preset bridges
            conjure_bridge = "conjure 143.110.214.222:80 url=https://registration.refraction.network.global.prod.fastly.net/api front=cdn.sstatic.net"
            bridges = [conjure_bridge]
            if "pluggableTransports" in pt_config and "conjure" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["conjure"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        elif self.meek_mode_rb.isChecked():
            # Meek preset bridges
            if "bridges" in pt_config and "meek" in pt_config["bridges"]:
                bridges = pt_config["bridges"]["meek"]
            if "pluggableTransports" in pt_config and "lyrebird" in pt_config["pluggableTransports"]:
                transport_plugin = pt_config["pluggableTransports"]["lyrebird"].replace("${pt_path}", pt_path)
            return bridges, transport_plugin
        
        return [], None
            
    def generate_torrc(self):
        """Generate the torrc configuration file"""
        # Get selected countries
        selected_countries = self.country_list.get_selected_countries()
        
        if not selected_countries:
            reply = QMessageBox.question(
                self, "Нет выбранных стран",
                "Вы не выбрали ни одной страны. Продолжить?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Get bridges and transport plugin based on mode
        bridges, transport_plugin = self.get_bridges_and_transport()
        
        # Check if we have bridges when needed
        if not self.normal_mode_rb.isChecked() and not bridges:
            reply = QMessageBox.question(
                self, "Нет мостов",
                "Не удалось загрузить предустановленные мосты. Продолжить без мостов?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Generate torrc content
        torrc_lines = [
            f"DataDirectory {self.data_edit.text()}",
            f"GeoIPFile {self.geoip_edit.text()}",
            f"GeoIPv6File {self.geoipv6_edit.text()}",
            "SocksPort 9051",
        ]
        
        # Add ExitNodes if countries are selected
        if selected_countries:
            exit_nodes = ','.join(f'{{{code}}}' for code in selected_countries)
            torrc_lines.append(f"ExitNodes {exit_nodes}")
        
        # Add bridges configuration
        if bridges:
            torrc_lines.append("UseBridges 1")
            torrc_lines.extend(f"Bridge {bridge}" for bridge in bridges)
            if transport_plugin:
                torrc_lines.append(transport_plugin)
        elif self.normal_mode_rb.isChecked():
            # Check if we're in normal mode but no bridges found
            bridges_path = self.bridges_edit.text()
            if os.path.exists(bridges_path):
                QMessageBox.warning(self, "Предупреждение", "Файл мостов пуст или содержит некорректные данные")
        
        # Add additional settings
        torrc_lines.extend([
            "AvoidDiskWrites 1",
            "HardwareAccel 1",
            "ClientOnly 1",
            "AutomapHostsOnResolve 1",
            "SafeLogging 1"
        ])
        
        # Write to file
        output_path = os.path.join(self.current_dir, "torrc")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(torrc_lines))
            
            # Show success message with mode info
            mode_text = ""
            if self.obfs4_mode_rb.isChecked():
                mode_text = " (obfs4)"
            elif self.snowflake_mode_rb.isChecked():
                mode_text = " (snowflake)"
            elif self.conjure_mode_rb.isChecked():
                mode_text = " (conjure)"
            elif self.meek_mode_rb.isChecked():
                mode_text = " (meek)"
            
            QMessageBox.information(
                self, "Успешно",
                f"Конфигурация успешно сохранена в {output_path}{mode_text}"
            )
            self.statusBar().showMessage(f"Configuration saved to {output_path}", 5000)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось записать конфигурацию, ошибка: {e}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application icon (if you have one)
    app.setWindowIcon(QIcon('icon.ico'))
    
    window = TorrcConfigurator()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()