import os
import sys
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QComboBox, QCheckBox, 
                             QWidget, QHeaderView, QMessageBox, QAbstractItemView)
from PyQt5.QtCore import Qt

CURRENT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(CURRENT_DIR, "tun_rules.json")

def get_default_rules():
    return [
        {
            "enabled": True,
            "name": "Localhost",
            "applications": "Any",
            "hosts": "localhost; 127.0.0.0/8; %ComputerName%; ::1; 192.168.0.0/24",
            "ports": "Any",
            "action": "Direct"
        },
        {
            "enabled": True,
            "name": "Default",
            "applications": "Any",
            "hosts": "Any",
            "ports": "Any",
            "action": "Proxy BD"
        }
    ]

class RulesEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Правила маршрутизации (Proxifier Style)")
        self.resize(850, 400)
        
        self.rules = self.load_rules()
        
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Имя правила", "Приложения", "Хосты", "Порты", "Действие"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        del_btn = QPushButton("Удалить")
        up_btn = QPushButton("Вверх")
        down_btn = QPushButton("Вниз")
        save_btn = QPushButton("Сохранить и закрыть")
        
        add_btn.clicked.connect(self.add_rule)
        del_btn.clicked.connect(self.delete_rule)
        up_btn.clicked.connect(self.move_up)
        down_btn.clicked.connect(self.move_down)
        save_btn.clicked.connect(self.save_and_close)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        self.populate_table()
        
    def load_rules(self):
        if os.path.exists(RULES_FILE):
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return get_default_rules()
        
    def populate_table(self):
        self.table.setRowCount(0)
        for rule in self.rules:
            self.add_row_to_table(rule)
            
    def add_row_to_table(self, rule):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Name + Checkbox
        name_widget = QWidget()
        h_layout = QHBoxLayout(name_widget)
        h_layout.setContentsMargins(5, 0, 5, 0)
        chk = QCheckBox()
        chk.setChecked(rule.get("enabled", True))
        
        name_item = QTableWidgetItem(rule.get("name", "New Rule"))
        
        h_layout.addWidget(chk)
        # We store the checkbox in the table using setCellWidget but we also need the text.
        # Actually it's easier to use the built-in ItemIsUserCheckable
        
        item_name = QTableWidgetItem(rule.get("name", "New Rule"))
        item_name.setFlags(item_name.flags() | Qt.ItemIsUserCheckable)
        item_name.setCheckState(Qt.Checked if rule.get("enabled", True) else Qt.Unchecked)
        self.table.setItem(row, 0, item_name)
        
        self.table.setItem(row, 1, QTableWidgetItem(rule.get("applications", "Any")))
        self.table.setItem(row, 2, QTableWidgetItem(rule.get("hosts", "Any")))
        self.table.setItem(row, 3, QTableWidgetItem(rule.get("ports", "Any")))
        
        combo = QComboBox()
        combo.addItems(["Direct", "Block", "Proxy TOR", "Proxy BD", "Proxy Opera", "Proxy VLESS"])
        combo.setCurrentText(rule.get("action", "Direct"))
        self.table.setCellWidget(row, 4, combo)
        
        if rule.get("name") == "Default":
            # Default rule shouldn't be disabled or renamed easily, but let's just make it read-only for name/apps/hosts/ports
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsUserCheckable)
            for col in range(1, 4):
                it = self.table.item(row, col)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)

    def add_rule(self):
        rule = {
            "enabled": True,
            "name": f"Rule {self.table.rowCount()}",
            "applications": "Any",
            "hosts": "Any",
            "ports": "Any",
            "action": "Proxy TOR"
        }
        # Insert before Default
        row = self.table.rowCount() - 1
        if row < 0: row = 0
        self.rules.insert(row, rule)
        
        # Re-render
        self.populate_table()
        self.table.selectRow(row)

    def delete_rule(self):
        row = self.table.currentRow()
        if row < 0: return
        item = self.table.item(row, 0)
        if item and item.text() == "Default":
            QMessageBox.warning(self, "Ошибка", "Правило Default нельзя удалить.")
            return
            
        self.table.removeRow(row)

    def move_up(self):
        row = self.table.currentRow()
        if row <= 0: return
        item = self.table.item(row, 0)
        if item and item.text() == "Default": return
        
        self.swap_rows(row, row - 1)
        self.table.selectRow(row - 1)

    def move_down(self):
        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount() - 2: return # Can't move below Default
        
        self.swap_rows(row, row + 1)
        self.table.selectRow(row + 1)

    def swap_rows(self, row1, row2):
        # We need to save the current state before swapping
        self.sync_table_to_rules()
        self.rules[row1], self.rules[row2] = self.rules[row2], self.rules[row1]
        self.populate_table()

    def sync_table_to_rules(self):
        new_rules = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            combo = self.table.cellWidget(row, 4)
            
            rule = {
                "enabled": name_item.checkState() == Qt.Checked if name_item.flags() & Qt.ItemIsUserCheckable else True,
                "name": name_item.text(),
                "applications": self.table.item(row, 1).text(),
                "hosts": self.table.item(row, 2).text(),
                "ports": self.table.item(row, 3).text(),
                "action": combo.currentText() if combo else "Direct"
            }
            new_rules.append(rule)
        self.rules = new_rules

    def save_and_close(self):
        self.sync_table_to_rules()
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, indent=2, ensure_ascii=False)
        self.accept()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    d = RulesEditorDialog()
    d.show()
    sys.exit(app.exec_())
