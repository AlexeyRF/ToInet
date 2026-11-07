import os
import sys
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QLineEdit, QPlainTextEdit, QCheckBox, QWidget,
    QAbstractItemView, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

# Setup paths
CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from managers import system_utils
T = system_utils.T

def find_ppx_path():
    candidates = [
        os.path.join(CURRENT_DIR, "Toinet.ppx"),
        os.path.join(os.path.dirname(CURRENT_DIR), "Toinet.ppx")
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(CURRENT_DIR, "Toinet.ppx")


class SingleRuleDialog(QDialog):
    """Modal dialog to edit or create a single proxification rule."""
    def __init__(self, rule_data=None, proxy_options=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Редактирование правила", "Edit Rule", "Modifier la règle"))
        self.resize(550, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #202020;
                color: #FFFFFF;
            }
            QLabel {
                color: #cccccc;
                font-size: 12px;
                background: transparent;
            }
            QLineEdit, QPlainTextEdit {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #005FB8;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QComboBox:hover {
                background-color: #353535;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                color: #FFFFFF;
                selection-background-color: #005FB8;
            }
            QCheckBox {
                color: #FFFFFF;
                font-size: 12px;
                background: transparent;
            }
            QPushButton {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #0078D4;
            }
            QPushButton#primaryBtn {
                background-color: #005FB8;
                border-color: #005FB8;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0078D4;
            }
        """)

        self.proxy_options = proxy_options or [("Direct", "Direct"), ("Block", "Block")]
        rule = rule_data or {}

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Name
        layout.addWidget(QLabel(T("Название правила (Rule Name):", "Rule Name:", "Nom de la règle :")))
        self.name_edit = QLineEdit(rule.get("name", ""))
        layout.addWidget(self.name_edit)

        # Applications
        layout.addWidget(QLabel(T("Приложения (Applications) — через точку с запятой или 'Any':", 
                                  "Applications — semicolon separated or 'Any':", 
                                  "Applications — séparées par des points-virgules ou 'Any' :")))
        self.apps_edit = QLineEdit(rule.get("apps", "Any"))
        layout.addWidget(self.apps_edit)

        # Target Hosts
        layout.addWidget(QLabel(T("Целевые хосты/домены (Target Hosts) — через точку с запятой или 'Any':", 
                                  "Target Hosts — semicolon separated or 'Any':", 
                                  "Hôtes cibles — séparés par des points-virgules ou 'Any' :")))
        self.hosts_edit = QPlainTextEdit()
        self.hosts_edit.setPlainText(rule.get("targets", "Any"))
        self.hosts_edit.setFixedHeight(90)
        layout.addWidget(self.hosts_edit)

        # Target Ports
        layout.addWidget(QLabel(T("Целевые порты (Target Ports) — например: 80; 443 или 'Any':", 
                                  "Target Ports — e.g., 80; 443 or 'Any':", 
                                  "Ports cibles — ex. 80; 443 ou 'Any' :")))
        self.ports_edit = QLineEdit(rule.get("ports", "Any"))
        layout.addWidget(self.ports_edit)

        # Action dropdown
        layout.addWidget(QLabel(T("Действие (Action):", "Action:", "Action :")))
        self.action_combo = QComboBox()
        cur_act_key = rule.get("action_key", "Direct")
        sel_idx = 0
        for i, (act_label, act_key) in enumerate(self.proxy_options):
            self.action_combo.addItem(act_label, act_key)
            if act_key == cur_act_key:
                sel_idx = i
        self.action_combo.setCurrentIndex(sel_idx)
        layout.addWidget(self.action_combo)

        # Enabled Checkbox
        self.enabled_cb = QCheckBox(T("Включено (Rule Enabled)", "Rule Enabled", "Règle activée"))
        self.enabled_cb.setChecked(rule.get("enabled", True))
        layout.addWidget(self.enabled_cb)

        layout.addStretch()

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(T("Отмена", "Cancel", "Annuler"))
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton(T("OK", "OK", "OK"))
        ok_btn.setObjectName("primaryBtn")
        ok_btn.clicked.connect(self.accept_data)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def accept_data(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, T("Ошибка", "Error", "Erreur"), 
                                T("Укажите название правила.", "Please enter a rule name.", "Veuillez entrer un nom de règle."))
            return
        self.accept()

    def get_rule_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "apps": self.apps_edit.text().strip() or "Any",
            "targets": self.hosts_edit.toPlainText().strip() or "Any",
            "ports": self.ports_edit.text().strip() or "Any",
            "action_key": self.action_combo.currentData(),
            "action_label": self.action_combo.currentText(),
            "enabled": self.enabled_cb.isChecked()
        }


class AddProxyDialog(QDialog):
    """
    Dialog to add a new Proxy Provider to Toinet.ppx.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Добавить провайдер прокси", "Add Proxy Provider", "Ajouter un fournisseur proxy"))
        self.setFixedSize(400, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #202020;
                color: #FFFFFF;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #d0d0d0;
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #383838;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #005FB8;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #FFFFFF;
                selection-background-color: #005FB8;
            }
            QPushButton {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #383838;
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #383838;
                border-color: #484848;
            }
            QPushButton#primaryBtn {
                background-color: #005FB8;
                border-color: #005FB8;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0078D4;
                border-color: #0078D4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Label / Name
        lbl_h = QHBoxLayout()
        lbl_title = QLabel(T("Название / Метка:", "Label / Name:", "Libellé / Nom :"))
        lbl_title.setFixedWidth(120)
        self.inp_label = QLineEdit()
        self.inp_label.setPlaceholderText(T("Например: MyProxy", "e.g. MyProxy", "ex: MyProxy"))
        lbl_h.addWidget(lbl_title)
        lbl_h.addWidget(self.inp_label)
        layout.addLayout(lbl_h)

        # Protocol
        proto_h = QHBoxLayout()
        proto_title = QLabel(T("Протокол:", "Protocol:", "Protocole :"))
        proto_title.setFixedWidth(120)
        self.combo_proto = QComboBox()
        self.combo_proto.addItems(["SOCKS5", "HTTPS", "HTTP", "SOCKS4"])
        proto_h.addWidget(proto_title)
        proto_h.addWidget(self.combo_proto)
        layout.addLayout(proto_h)

        # Address / Host
        host_h = QHBoxLayout()
        host_title = QLabel(T("Адрес хоста:", "Host Address:", "Adresse :"))
        host_title.setFixedWidth(120)
        self.inp_host = QLineEdit("127.0.0.1")
        host_h.addWidget(host_title)
        host_h.addWidget(self.inp_host)
        layout.addLayout(host_h)

        # Port
        port_h = QHBoxLayout()
        port_title = QLabel(T("Порт:", "Port:", "Port :"))
        port_title.setFixedWidth(120)
        self.inp_port = QSpinBox()
        self.inp_port.setRange(1, 65535)
        self.inp_port.setValue(1080)
        port_h.addWidget(port_title)
        port_h.addWidget(self.inp_port)
        layout.addLayout(port_h)

        layout.addStretch()

        # Buttons
        btn_h = QHBoxLayout()
        btn_h.addStretch()
        cancel_btn = QPushButton(T("Отмена", "Cancel", "Annuler"))
        cancel_btn.clicked.connect(self.reject)
        btn_h.addWidget(cancel_btn)

        add_btn = QPushButton(T("Добавить", "Add", "Ajouter"))
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.accept_data)
        btn_h.addWidget(add_btn)

        layout.addLayout(btn_h)

    def accept_data(self):
        lbl = self.inp_label.text().strip()
        if not lbl:
            QMessageBox.warning(self, T("Внимание", "Warning", "Attention"), 
                                T("Укажите название прокси!", "Please specify a proxy label!", "Veuillez indiquer un nom de proxy !"))
            return
        host = self.inp_host.text().strip()
        if not host:
            QMessageBox.warning(self, T("Внимание", "Warning", "Attention"), 
                                T("Укажите адрес хоста!", "Please specify a host address!", "Veuillez indiquer une adresse hôte !"))
            return
        self.accept()

    def get_data(self):
        return {
            "label": self.inp_label.text().strip(),
            "type": self.combo_proto.currentText(),
            "address": self.inp_host.text().strip(),
            "port": str(self.inp_port.value()),
            "options": "48"
        }


class RulesEditorDialog(QDialog):
    """
    Graphical Proxification Rules Editor dialog styled after Proxifier's
    rule table with a modern Windows 11 Fluent dark theme.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("Правила проксификации (Toinet.ppx)", "Proxification Rules", "Règles de proxification"))
        self.resize(920, 620)
        self.ppx_path = find_ppx_path()
        self.proxies = []        # list of proxy dictionaries from <ProxyList>
        self.proxy_options = []  # list of (display_label, internal_action_key)
        self.proxy_id_to_label = {}
        self.rules = []

        self._init_ui()
        self.load_ppx()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #202020;
                color: #FFFFFF;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #cccccc;
                background: transparent;
            }
            QTableWidget {
                background-color: #252525;
                alternate-background-color: #2a2a2a;
                color: #FFFFFF;
                gridline-color: #383838;
                border: 1px solid #383838;
                border-radius: 6px;
                selection-background-color: #005FB8;
                selection-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 8px;
                border: 1px solid #383838;
            }
            QTableCornerButton::section {
                background-color: #2d2d2d;
                border: 1px solid #383838;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                color: #FFFFFF;
                selection-background-color: #005FB8;
            }
            QPushButton {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #0078D4;
            }
            QPushButton:pressed {
                background-color: #202020;
            }
            QPushButton#primaryBtn {
                background-color: #005FB8;
                border-color: #005FB8;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0078D4;
                border-color: #0078D4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header note
        top_layout = QHBoxLayout()
        header_lbl = QLabel(T(
            "Правила маршрутизации трафика (приоритет сверху вниз). Синхронизируются с Proxifier и Sing-box TUN.",
            "Traffic routing rules (processed top-down). Synchronized with Proxifier and Sing-box TUN.",
            "Règles de routage du trafic (traitées de haut en bas). Synchronisées avec Proxifier et Sing-box TUN."
        ))
        header_lbl.setStyleSheet("color: #9d9d9d; font-size: 12px;")
        top_layout.addWidget(header_lbl)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Rules Table
        self.table = QTableWidget(0, 5)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setHorizontalHeaderLabels([
            T("Rule Name", "Rule Name", "Nom de la règle"),
            T("Applications", "Applications", "Applications"),
            T("Target Hosts", "Target Hosts", "Hôtes cibles"),
            T("Target Ports", "Target Ports", "Ports cibles"),
            T("Action", "Action", "Action")
        ])
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Interactive)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Interactive)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.on_edit_rule)

        layout.addWidget(self.table)

        # Buttons Toolbar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.add_btn = QPushButton(T("Добавить правило", "Add Rule...", "Ajouter règle..."))
        self.add_btn.clicked.connect(self.on_add_rule)
        btn_bar.addWidget(self.add_btn)

        self.add_proxy_btn = QPushButton(T("Добавить прокси...", "Add Proxy...", "Ajouter proxy..."))
        self.add_proxy_btn.clicked.connect(self.on_add_proxy)
        btn_bar.addWidget(self.add_proxy_btn)

        self.edit_btn = QPushButton(T("Редактировать", "Edit...", "Modifier..."))
        self.edit_btn.clicked.connect(self.on_edit_rule)
        btn_bar.addWidget(self.edit_btn)

        self.del_btn = QPushButton(T("Удалить", "Delete", "Supprimer"))
        self.del_btn.clicked.connect(self.on_delete_rule)
        btn_bar.addWidget(self.del_btn)

        btn_bar.addSpacing(16)

        self.up_btn = QPushButton("▲ " + T("Вверх", "Up", "Haut"))
        self.up_btn.clicked.connect(self.on_move_up)
        btn_bar.addWidget(self.up_btn)

        self.down_btn = QPushButton("▼ " + T("Вниз", "Down", "Bas"))
        self.down_btn.clicked.connect(self.on_move_down)
        btn_bar.addWidget(self.down_btn)

        btn_bar.addStretch()

        self.cancel_btn = QPushButton(T("Отмена", "Cancel", "Annuler"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_bar.addWidget(self.cancel_btn)

        self.save_btn = QPushButton(T("Сохранить", "Save", "Enregistrer"))
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self.save_ppx)
        btn_bar.addWidget(self.save_btn)

        layout.addLayout(btn_bar)

    def load_ppx(self):
        if not os.path.exists(self.ppx_path):
            QMessageBox.critical(self, T("Ошибка", "Error", "Erreur"), 
                                 f"Файл профиля Toinet.ppx не найден:\n{self.ppx_path}")
            return

        try:
            tree = ET.parse(self.ppx_path)
            root = tree.getroot()

            # Parse ProxyList
            self.proxies = []
            self.proxy_options = [
                ("Direct", "Direct"),
                ("Block", "Block")
            ]
            self.proxy_id_to_label = {
                "Direct": "Direct",
                "Block": "Block"
            }

            proxy_list = root.find("ProxyList")
            if proxy_list is not None:
                for p in proxy_list.findall("Proxy"):
                    pid = p.attrib.get("id")
                    ptype = p.attrib.get("type", "SOCKS5")
                    lbl = p.find("Label").text if p.find("Label") is not None and p.find("Label").text else pid
                    addr = p.find("Address").text if p.find("Address") is not None and p.find("Address").text else "127.0.0.1"
                    port = p.find("Port").text if p.find("Port") is not None and p.find("Port").text else "1080"
                    opts = p.find("Options").text if p.find("Options") is not None and p.find("Options").text else "48"
                    self.proxies.append({
                        "id": pid,
                        "type": ptype,
                        "label": lbl,
                        "address": addr,
                        "port": port,
                        "options": opts
                    })
                    disp = f"Proxy {ptype} {lbl}"
                    self.proxy_options.append((disp, f"Proxy:{pid}"))
                    self.proxy_id_to_label[f"Proxy:{pid}"] = disp

            # Parse RuleList
            self.rules = []
            rule_list = root.find("RuleList")
            if rule_list is not None:
                for r in rule_list.findall("Rule"):
                    name = r.find("Name").text if r.find("Name") is not None else ""
                    enabled = r.attrib.get("enabled", "true").lower() == "true"
                    act_elem = r.find("Action")
                    act_type = act_elem.attrib.get("type") if act_elem is not None else "Direct"
                    act_val = act_elem.text if act_elem is not None and act_elem.text else ""
                    
                    if act_type == "Proxy":
                        act_key = f"Proxy:{act_val.strip()}"
                    else:
                        act_key = act_type

                    apps = r.find("Applications").text if r.find("Applications") is not None else "Any"
                    targets = r.find("Targets").text if r.find("Targets") is not None else "Any"
                    ports = r.find("Ports").text if r.find("Ports") is not None else "Any"

                    self.rules.append({
                        "name": name,
                        "enabled": enabled,
                        "action_key": act_key,
                        "action_label": self.proxy_id_to_label.get(act_key, act_key),
                        "apps": apps.strip() if apps else "Any",
                        "targets": targets.strip() if targets else "Any",
                        "ports": ports.strip() if ports else "Any"
                    })

            self.populate_table()

        except Exception as e:
            QMessageBox.critical(self, T("Ошибка XML", "XML Error", "Erreur XML"), f"Не удалось прочитать Toinet.ppx:\n{e}")

    def populate_table(self):
        self.table.setRowCount(0)
        for row_idx, r in enumerate(self.rules):
            self.table.insertRow(row_idx)

            # Col 0: CheckBox + Name
            name_item = QTableWidgetItem(r["name"])
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            name_item.setCheckState(Qt.Checked if r["enabled"] else Qt.Unchecked)
            self.table.setItem(row_idx, 0, name_item)

            # Col 1: Applications
            apps_item = QTableWidgetItem(r["apps"].replace("\n", " "))
            apps_item.setToolTip(r["apps"])
            self.table.setItem(row_idx, 1, apps_item)

            # Col 2: Target Hosts
            targets_item = QTableWidgetItem(r["targets"].replace("\n", " "))
            targets_item.setToolTip(r["targets"])
            self.table.setItem(row_idx, 2, targets_item)

            # Col 3: Target Ports
            ports_item = QTableWidgetItem(r["ports"].replace("\n", " "))
            ports_item.setToolTip(r["ports"])
            self.table.setItem(row_idx, 3, ports_item)

            # Col 4: Action ComboBox
            combo = QComboBox()
            sel_idx = 0
            for i, (disp_label, act_key) in enumerate(self.proxy_options):
                combo.addItem(disp_label, act_key)
                if act_key == r["action_key"]:
                    sel_idx = i
            combo.setCurrentIndex(sel_idx)
            combo.currentIndexChanged.connect(lambda idx, row=row_idx, cb=combo: self._on_combo_action_changed(row, cb))
            self.table.setCellWidget(row_idx, 4, combo)

    def _sync_rules_from_table(self):
        """Reads current state from table items and widgets back into self.rules."""
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            apps_item = self.table.item(row, 1)
            targets_item = self.table.item(row, 2)
            ports_item = self.table.item(row, 3)
            combo = self.table.cellWidget(row, 4)

            if row < len(self.rules):
                self.rules[row]["enabled"] = (name_item.checkState() == Qt.Checked)
                self.rules[row]["name"] = name_item.text().strip()
                if apps_item: self.rules[row]["apps"] = apps_item.toolTip() or apps_item.text()
                if targets_item: self.rules[row]["targets"] = targets_item.toolTip() or targets_item.text()
                if ports_item: self.rules[row]["ports"] = ports_item.toolTip() or ports_item.text()
                if combo:
                    self.rules[row]["action_key"] = combo.currentData()
                    self.rules[row]["action_label"] = combo.currentText()

    def _on_combo_action_changed(self, row, combo):
        if 0 <= row < len(self.rules):
            self.rules[row]["action_key"] = combo.currentData()
            self.rules[row]["action_label"] = combo.currentText()

    def on_add_proxy(self):
        dlg = AddProxyDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            existing_ids = []
            for p in self.proxies:
                try:
                    existing_ids.append(int(p["id"]))
                except (ValueError, TypeError):
                    pass
            new_id = str(max(existing_ids) + 1) if existing_ids else "100"
            data["id"] = new_id
            self.proxies.append(data)

            disp = f"Proxy {data['type']} {data['label']}"
            self.proxy_options.append((disp, f"Proxy:{new_id}"))
            self.proxy_id_to_label[f"Proxy:{new_id}"] = disp

            self._sync_rules_from_table()
            self.populate_table()

            QMessageBox.information(
                self,
                T("Провайдер добавлен", "Proxy Added", "Proxy ajouté"),
                T(f"Прокси '{data['label']}' ({data['type']} {data['address']}:{data['port']}) добавлен в список!\nТеперь вы можете выбрать его в столбце Action правил.",
                  f"Proxy '{data['label']}' ({data['type']} {data['address']}:{data['port']}) added!\nYou can now select it in the Action column.",
                  f"Proxy '{data['label']}' ({data['type']} {data['address']}:{data['port']}) ajouté !")
            )

    def on_add_rule(self):
        self._sync_rules_from_table()
        dlg = SingleRuleDialog(rule_data={"enabled": True, "apps": "Any", "targets": "Any", "ports": "Any"},
                               proxy_options=self.proxy_options, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            new_rule = dlg.get_rule_data()
            # Insert before Default rule if Default is at the bottom
            if self.rules and self.rules[-1].get("name", "").lower() == "default":
                self.rules.insert(len(self.rules) - 1, new_rule)
            else:
                self.rules.append(new_rule)
            self.populate_table()
            self.table.selectRow(len(self.rules) - (2 if self.rules[-1].get("name", "").lower() == "default" else 1))

    def on_edit_rule(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rules):
            return
        self._sync_rules_from_table()
        rule_data = self.rules[row]
        dlg = SingleRuleDialog(rule_data=rule_data, proxy_options=self.proxy_options, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            updated = dlg.get_rule_data()
            self.rules[row] = updated
            self.populate_table()
            self.table.selectRow(row)

    def on_delete_rule(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rules):
            return
        rule_name = self.rules[row].get("name", "")
        if rule_name.lower() == "default":
            QMessageBox.warning(self, T("Внимание", "Warning", "Attention"), 
                                T("Правило 'Default' нельзя удалить.", "Cannot delete 'Default' rule.", "Impossible de supprimer la règle 'Default'."))
            return
        
        reply = QMessageBox.question(self, T("Удаление правила", "Delete Rule", "Supprimer la règle"),
                                     T(f"Удалить правило '{rule_name}'?", f"Delete rule '{rule_name}'?", f"Supprimer la règle '{rule_name}' ?"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._sync_rules_from_table()
            del self.rules[row]
            self.populate_table()

    def on_move_up(self):
        row = self.table.currentRow()
        if row <= 0 or row >= len(self.rules):
            return
        self._sync_rules_from_table()
        self.rules[row], self.rules[row - 1] = self.rules[row - 1], self.rules[row]
        self.populate_table()
        self.table.selectRow(row - 1)

    def on_move_down(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rules) - 1:
            return
        # If moving down would displace Default from the bottom, prevent it
        if self.rules[row + 1].get("name", "").lower() == "default":
            return
        self._sync_rules_from_table()
        self.rules[row], self.rules[row + 1] = self.rules[row + 1], self.rules[row]
        self.populate_table()
        self.table.selectRow(row + 1)

    def save_ppx(self):
        self._sync_rules_from_table()

        if not os.path.exists(self.ppx_path):
            QMessageBox.critical(self, T("Ошибка", "Error", "Erreur"), f"Файл не найден: {self.ppx_path}")
            return

        try:
            tree = ET.parse(self.ppx_path)
            root = tree.getroot()

            # Save ProxyList
            proxy_list = root.find("ProxyList")
            if proxy_list is None:
                proxy_list = ET.SubElement(root, "ProxyList")
            else:
                proxy_list.clear()

            for p in self.proxies:
                p_elem = ET.SubElement(proxy_list, "Proxy", id=str(p["id"]), type=str(p.get("type", "SOCKS5")))
                opt_elem = ET.SubElement(p_elem, "Options")
                opt_elem.text = str(p.get("options", "48"))
                port_elem = ET.SubElement(p_elem, "Port")
                port_elem.text = str(p.get("port", "1080"))
                addr_elem = ET.SubElement(p_elem, "Address")
                addr_elem.text = str(p.get("address", "127.0.0.1"))
                lbl_elem = ET.SubElement(p_elem, "Label")
                lbl_elem.text = str(p.get("label", f"Proxy_{p['id']}"))

            rule_list = root.find("RuleList")
            if rule_list is None:
                rule_list = ET.SubElement(root, "RuleList")
            else:
                rule_list.clear()

            for r in self.rules:
                r_elem = ET.SubElement(rule_list, "Rule", enabled="true" if r.get("enabled", True) else "false")
                
                # Action
                act_key = r.get("action_key", "Direct")
                if act_key.startswith("Proxy:"):
                    pid = act_key.split(":")[1]
                    act_elem = ET.SubElement(r_elem, "Action", type="Proxy")
                    act_elem.text = pid
                elif act_key == "Block":
                    ET.SubElement(r_elem, "Action", type="Block")
                else:
                    ET.SubElement(r_elem, "Action", type="Direct")

                # Applications
                apps = r.get("apps", "").strip()
                if apps and apps != "Any":
                    apps_elem = ET.SubElement(r_elem, "Applications")
                    apps_elem.text = apps

                # Targets
                targets = r.get("targets", "").strip()
                if targets and targets != "Any":
                    targets_elem = ET.SubElement(r_elem, "Targets")
                    targets_elem.text = targets

                # Ports
                ports = r.get("ports", "").strip()
                if ports and ports != "Any":
                    ports_elem = ET.SubElement(r_elem, "Ports")
                    ports_elem.text = ports

                # Name
                name_elem = ET.SubElement(r_elem, "Name")
                name_elem.text = r.get("name", "Rule")

            ET.indent(tree, space="\t")
            tree.write(self.ppx_path, encoding="utf-8", xml_declaration=True)

            QMessageBox.information(
                self, 
                T("Успех", "Success", "Succès"),
                T("Правила успешно сохранены в Toinet.ppx!", 
                  "Rules successfully saved to Toinet.ppx!", 
                  "Règles enregistrées avec succès dans Toinet.ppx !")
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, T("Ошибка сохранения", "Save Error", "Erreur d'enregistrement"), 
                                 f"Не удалось сохранить Toinet.ppx:\n{e}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    editor = RulesEditorDialog()
    editor.show()
    sys.exit(app.exec())
