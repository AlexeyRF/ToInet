#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QProgressBar, QSpinBox, QDoubleSpinBox, 
                             QGroupBox, QFileDialog, QMessageBox, QTabWidget, QTabBar)
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Import project config manager
try:
    import config_manager
except ImportError:
    config_manager = None

# Import byedpi_tester functions
try:
    import byedpi_tester
except ImportError:
    byedpi_tester = None
BYEDPI_EXE_DEFAULT = os.path.join(CURRENT_DIR, r"byedpi\ciadpi.exe")
BYEDPI_CUSTOM_FILE = os.path.join(CURRENT_DIR, "byedpi_custom.txt")
SITES_FILE = os.path.join(CURRENT_DIR, "byedpi_tester_sites.txt")
STRATEGIES_FILE = os.path.join(CURRENT_DIR, "byedpi_tester_strategies.txt")
PRIORITY_SITES_FILE = os.path.join(CURRENT_DIR, "byedpi_tester_priority_sites.txt")

# Stylesheet for premium dark mode
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1a1a1a;
}
QWidget {
    color: #d0d0d0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px;
    background-color: #222222;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #a0a0a0;
}
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #555555;
}
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3d3d3d;
    border-color: #555555;
}
QPushButton:pressed {
    background-color: #202020;
}
QPushButton#start_btn {
    background-color: #2b3d2e;
    border-color: #3e5842;
}
QPushButton#start_btn:hover {
    background-color: #354c39;
    border-color: #4a6a50;
}
QPushButton#start_btn:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}
QPushButton#stop_btn {
    background-color: #3d2b2b;
    border-color: #583e3e;
}
QPushButton#stop_btn:hover {
    background-color: #4c3535;
    border-color: #6a4a4a;
}
QPushButton#stop_btn:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}
QPushButton#apply_btn {
    background-color: #2e3b4e;
    border-color: #3e506a;
    font-size: 11pt;
    padding: 10px;
}
QPushButton#apply_btn:hover {
    background-color: #35455c;
    border-color: #4a6182;
}
QPushButton#apply_btn:disabled {
    background-color: #222222;
    color: #666666;
    border-color: #2a2a2a;
}
QListWidget {
    background-color: #222222;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    padding: 5px;
}
QListWidget::item {
    padding: 4px;
    border-bottom: 1px solid #282828;
}
QListWidget::item:selected {
    background-color: #333333;
    color: #ffffff;
    border-radius: 4px;
}
QTableWidget {
    background-color: #222222;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    gridline-color: #282828;
}
QTableWidget::item {
    padding: 5px;
}
QTableWidget::item:selected {
    background-color: #333333;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #2d2d2d;
    color: #d0d0d0;
    padding: 5px;
    border: 1px solid #222222;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #2d2d2d;
    border-radius: 4px;
    text-align: center;
    background-color: #222222;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #3a3a3a;
    border-radius: 3px;
}
QLabel#title_lbl {
    font-size: 16pt;
    font-weight: bold;
    color: #ffffff;
    padding: 5px 0px;
}
QLabel#status_desc_lbl {
    font-style: italic;
    color: #888888;
}

/* Стилизация скроллбаров под темную тему */
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 10px;
    margin: 0px 0 0px 0;
}
QScrollBar::handle:vertical {
    background: #3d3d3d;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: #1e1e1e;
    height: 10px;
    margin: 0px 0 0px 0;
}
QScrollBar::handle:horizontal {
    background: #3d3d3d;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #555555;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Стилизация QTabWidget и QTabBar */
QTabWidget::panel {
    border: 1px solid #2d2d2d;
    background-color: #222222;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #1a1a1a;
    border: 1px solid #2d2d2d;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 12px;
    color: #a0a0a0;
}
QTabBar::tab:selected, QTabBar::tab:hover {
    background-color: #222222;
    color: #ffffff;
}
QTabBar::tab:selected {
    border-bottom: 1px solid #222222;
}
"""

class WorkerThread(QThread):
    progress_changed = pyqtSignal(int, int, str)  # current, total, strategy_cmd
    strategy_completed = pyqtSignal(str, float, int, int, dict)  # strategy, success_rate, success_count, total, details
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, byedpi_path, strategies, sites, options):
        super().__init__()
        self.byedpi_path = byedpi_path
        self.strategies = strategies
        self.sites = sites
        self.options = options
        self.is_cancelled = False

    def run(self):
        results = []
        total = len(self.strategies)
        
        # Extract options
        sni = self.options.get('sni', 'google.com')
        proxy_ip = self.options.get('ip', '127.0.0.1')
        proxy_port = int(self.options.get('port', 1080))
        concurrency = self.options.get('concurrency', 10)
        timeout = self.options.get('timeout', 4.0)
        delay = self.options.get('delay', 0.2)

        if not byedpi_tester:
            self.error.emit("Модуль byedpi_tester не может быть импортирован.")
            return

        for idx, strategy_template in enumerate(self.strategies):
            if self.is_cancelled:
                break
            
            # Format SNI in the strategy
            strategy_cmd = strategy_template.replace("{sni}", f'"{sni}"')
            self.progress_changed.emit(idx + 1, total, strategy_cmd)

            # Parse command line to list of args
            parsed_args = byedpi_tester.shell_split(strategy_cmd)
            
            # Detect if ip/port already defined in the command
            cmd_ip, cmd_port = byedpi_tester.check_ip_and_port_in_cmd(parsed_args)
            
            p_ip = cmd_ip or proxy_ip
            p_port = int(cmd_port or proxy_port)
            
            # Prepend IP and Port if not defined in the cmd
            final_args = []
            if cmd_ip is None:
                final_args.extend(["--ip", p_ip])
            if cmd_port is None:
                final_args.extend(["--port", str(p_port)])
                
            final_args.extend(parsed_args)

            # Start daemon
            proc = byedpi_tester.start_byedpi(self.byedpi_path, final_args)
            if not proc:
                err_details = {site: (False, "Ошибка запуска демона ciadpi") for site in self.sites}
                self.strategy_completed.emit(strategy_template, 0.0, 0, len(self.sites), err_details)
                results.append((strategy_template, 0.0, 0, len(self.sites), err_details))
                continue

            # Wait for port to open
            if not byedpi_tester.wait_for_proxy_port(p_ip, p_port, timeout=3.0):
                byedpi_tester.stop_byedpi(proc)
                err_details = {site: (False, f"Порт {p_ip}:{p_port} не открылся") for site in self.sites}
                self.strategy_completed.emit(strategy_template, 0.0, 0, len(self.sites), err_details)
                results.append((strategy_template, 0.0, 0, len(self.sites), err_details))
                continue

            if self.is_cancelled:
                byedpi_tester.stop_byedpi(proc)
                break

            # Give daemon additional breathing room
            time.sleep(delay)

            # Parallel test sites
            success_count = 0
            checked_details = {}
            
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(
                        byedpi_tester.check_url, 
                        p_ip, 
                        p_port, 
                        f"https://{site}", 
                        timeout=timeout
                    ): site
                    for site in self.sites
                }
                
                for future in as_completed(futures):
                    if self.is_cancelled:
                        break
                    site = futures[future]
                    try:
                        success, msg = future.result()
                        checked_details[site] = (success, msg)
                        if success:
                            success_count += 1
                    except Exception as e:
                        checked_details[site] = (False, str(e))

             # Stop daemon
            pypi_domains = ["pypi.org", "files.pythonhosted.org", "pypi.python.org", "pythonhosted.org"]
            pypi_accessible = True
            for domain in pypi_domains:
                if domain in self.sites:
                    if domain not in checked_details or not checked_details[domain][0]:
                        pypi_accessible = False
                        break
                        
            pip_success = False
            pip_msg = "Не проверялось"
            
            if pypi_accessible and not self.is_cancelled:
                import tempfile
                import shutil
                import subprocess
                import sys
                
                temp_dir = tempfile.mkdtemp()
                try:
                    cmd = [
                        sys.executable, "-m", "pip", "download",
                        "--proxy", f"socks5://127.0.0.1:{p_port}",
                        "--no-cache-dir",
                        "--dest", temp_dir,
                        "pytz",
                        "--only-binary=:all:"
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=15.0,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    if result.returncode == 0:
                        pip_success = True
                        pip_msg = "Успешное скачивание pytz через pip!"
                    else:
                        err_str = result.stderr.decode('utf-8', errors='ignore').strip()
                        if len(err_str) > 100:
                            err_str = err_str[:100] + "..."
                        pip_msg = f"Ошибка pip: {err_str}"
                except subprocess.TimeoutExpired:
                    pip_msg = "Таймаут скачивания через pip (15 сек)"
                except Exception as e:
                    pip_msg = f"Ошибка теста pip: {e}"
                finally:
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                        
            checked_details["__pip_test__"] = (pip_success, pip_msg)

            byedpi_tester.stop_byedpi(proc)
            time.sleep(0.3)  # wait for port to completely unbind

            if self.is_cancelled:
                break

            pct = (success_count / len(self.sites)) * 100
            self.strategy_completed.emit(strategy_template, pct, success_count, len(self.sites), checked_details)
            results.append((strategy_template, pct, success_count, len(self.sites), checked_details))

        self.finished.emit(results)

    def cancel(self):
        self.is_cancelled = True


class ByeDPITesterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.results_data = [] # Stores (strat, pct, succ, total, details)
        self.load_domains()
        self.load_strategies()
        self.load_priority_sites()
        self.init_ui()

    def load_domains(self):
        """Load domains from file or set defaults if file not exists."""
        self.domains = []
        if os.path.exists(SITES_FILE):
            try:
                with open(SITES_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.domains.append(line)
            except Exception as e:
                print(f"Ошибка загрузки доменов: {e}")
        
        if not self.domains:
            if byedpi_tester and hasattr(byedpi_tester, 'DEFAULT_SITES'):
                self.domains = list(byedpi_tester.DEFAULT_SITES)
            else:
                self.domains = ['youtube.com', 'rutracker.org', 'nyaa.si', 'speedtest.net']
            self.save_domains()

    def save_domains(self):
        """Save domains list to file."""
        try:
            with open(SITES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Список сайтов/доменов для проверки ByeDPI стратегий\n")
                f.write("# Вы можете редактировать этот файл вручную\n\n")
                for domain in self.domains:
                    f.write(f"{domain}\n")
        except Exception as e:
            print(f"Ошибка сохранения доменов: {e}")

    def load_strategies(self):
        """Load strategies from file or set defaults if file not exists."""
        self.strategies = []
        if os.path.exists(STRATEGIES_FILE):
            try:
                with open(STRATEGIES_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.strategies.append(line)
            except Exception as e:
                print(f"Ошибка загрузки стратегий: {e}")
        
        if not self.strategies:
            if byedpi_tester and hasattr(byedpi_tester, 'DEFAULT_STRATEGIES'):
                self.strategies = list(byedpi_tester.DEFAULT_STRATEGIES)
            else:
                self.strategies = [
                    '-d1 -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -r1+s -S -a1',
                    '-o1 -d1 -a1 -At,r,s -s1 -d1 -s5+s -s10+s -s15+s -s20+s -r1+s -S -a1',
                    '-s1 -q1 -a1 -Y -Ar -a1 -s5 -o2 -At -f-1 -r1+s -a1'
                ]
            self.save_strategies()

    def save_strategies(self):
        """Save strategies list to file."""
        try:
            with open(STRATEGIES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Список стратегий ByeDPI для тестирования\n")
                f.write("# Вы можете добавлять или удалять стратегии вручную\n\n")
                for strat in self.strategies:
                    f.write(f"{strat}\n")
        except Exception as e:
            print(f"Ошибка сохранения стратегий: {e}")

    def load_priority_sites(self):
        """Load priority sites from file or set defaults if file not exists."""
        self.priority_sites = []
        if os.path.exists(PRIORITY_SITES_FILE):
            try:
                with open(PRIORITY_SITES_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.priority_sites.append(line)
            except Exception as e:
                print(f"Ошибка загрузки приоритетных сайтов: {e}")
        
        # If empty, default to checking all domains
        if not self.priority_sites:
            self.priority_sites = list(self.domains)
            self.save_priority_sites()

    def save_priority_sites(self):
        """Save priority sites list to file."""
        try:
            with open(PRIORITY_SITES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Список приоритетных сайтов для проверки\n")
                f.write("# Эти сайты отмечены галочками в списке доменов\n\n")
                for site in self.priority_sites:
                    f.write(f"{site}\n")
        except Exception as e:
            print(f"Ошибка сохранения приоритетных сайтов: {e}")

    def init_ui(self):
        self.setWindowTitle("Тестер стратегий ByeDPI")
        self.setFixedSize(1000, 700)
        self.setStyleSheet(DARK_STYLESHEET)
        
        # Main widget and layouts
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header Row
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Тестер стратегий ByeByeDPI")
        title_lbl.setObjectName("title_lbl")
        header_layout.addWidget(title_lbl)
        
        # Optional: project icon
        main_layout.addLayout(header_layout)
        
        # Fixed layout container to prevent resizing panels
        panels_container = QWidget()
        panels_layout = QHBoxLayout()
        panels_layout.setContentsMargins(0, 0, 0, 0)
        panels_layout.setSpacing(15)
        
        # --- LEFT PANEL (Settings & Domains) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # 1. Tester Settings Group
        settings_group = QGroupBox("Параметры проверки")
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(8)
        
        # Path to executable
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(BYEDPI_EXE_DEFAULT)
        self.path_edit.setToolTip("Путь к исполняемому файлу ciadpi.exe / byedpi")
        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.clicked.connect(self.browse_executable)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addWidget(QLabel("Путь к ciadpi.exe:"))
        settings_layout.addLayout(path_layout)
        
        # SNI and Port
        sni_port_layout = QHBoxLayout()
        vbox_sni = QVBoxLayout()
        self.sni_edit = QLineEdit("google.com")
        vbox_sni.addWidget(QLabel("SNI для {sni}:"))
        vbox_sni.addWidget(self.sni_edit)
        
        vbox_port = QVBoxLayout()
        self.port_edit = QLineEdit("1080")
        vbox_port.addWidget(QLabel("Порт SOCKS5:"))
        vbox_port.addWidget(self.port_edit)
        
        sni_port_layout.addLayout(vbox_sni)
        sni_port_layout.addLayout(vbox_port)
        settings_layout.addLayout(sni_port_layout)
        
        # Numeric parameters row
        num_layout = QHBoxLayout()
        vbox_conc = QVBoxLayout()
        self.conc_spin = QSpinBox()
        self.conc_spin.setRange(1, 50)
        self.conc_spin.setValue(10)
        vbox_conc.addWidget(QLabel("Потоков:"))
        vbox_conc.addWidget(self.conc_spin)
        
        vbox_timeout = QVBoxLayout()
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.5, 30.0)
        self.timeout_spin.setSingleStep(0.5)
        self.timeout_spin.setValue(4.0)
        vbox_timeout.addWidget(QLabel("Таймаут (сек):"))
        vbox_timeout.addWidget(self.timeout_spin)
        
        vbox_delay = QVBoxLayout()
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 5.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(0.2)
        vbox_delay.addWidget(QLabel("Задержка (сек):"))
        vbox_delay.addWidget(self.delay_spin)
        
        num_layout.addLayout(vbox_conc)
        num_layout.addLayout(vbox_timeout)
        num_layout.addLayout(vbox_delay)
        settings_layout.addLayout(num_layout)
        
        settings_group.setLayout(settings_layout)
        left_layout.addWidget(settings_group)
        
        # 2. Domains Manager Group (with checkable priority checkboxes)
        domains_group = QGroupBox("Проверяемые домены (отметьте приоритетные)")
        domains_layout = QVBoxLayout()
        domains_layout.setSpacing(8)
        
        self.domains_list = QListWidget()
        self.domains_list.itemChanged.connect(self.on_domain_check_changed)
        self.refresh_domains_list()
        domains_layout.addWidget(self.domains_list)
        
        # Add domain row
        add_layout = QHBoxLayout()
        self.new_domain_edit = QLineEdit()
        self.new_domain_edit.setPlaceholderText("Добавить новый домен...")
        self.new_domain_edit.returnPressed.connect(self.add_domain)
        self.add_domain_btn = QPushButton("Добавить")
        self.add_domain_btn.clicked.connect(self.add_domain)
        add_layout.addWidget(self.new_domain_edit)
        add_layout.addWidget(self.add_domain_btn)
        domains_layout.addLayout(add_layout)
        
        # Remove and Reset buttons
        btn_row = QHBoxLayout()
        self.remove_domain_btn = QPushButton("Удалить выбранный")
        self.remove_domain_btn.clicked.connect(self.remove_domain)
        self.reset_domains_btn = QPushButton("Сброс")
        self.reset_domains_btn.setToolTip("Восстановить список по умолчанию")
        self.reset_domains_btn.clicked.connect(self.reset_domains)
        btn_row.addWidget(self.remove_domain_btn)
        btn_row.addWidget(self.reset_domains_btn)
        domains_layout.addLayout(btn_row)
        
        domains_group.setLayout(domains_layout)
        left_layout.addWidget(domains_group)
        
        left_widget.setLayout(left_layout)
        panels_layout.addWidget(left_widget)
        
        # --- RIGHT PANEL (Results & Operations) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Real-time Controller Block
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Запустить проверку")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.clicked.connect(self.start_testing)
        
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_testing)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        right_layout.addLayout(control_layout)
        
        # Progress Indicators
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Готов к тестированию")
        right_layout.addWidget(self.progress_bar)
        
        self.status_desc = QLabel("Нажмите 'Запустить проверку' для старта. В списке %d стратегий." % len(self.strategies))
        self.status_desc.setObjectName("status_desc_lbl")
        right_layout.addWidget(self.status_desc)
        
        # Results Layout to prevent resizing panels
        results_container = QWidget()
        results_vlayout = QVBoxLayout()
        results_vlayout.setContentsMargins(0, 0, 0, 0)
        results_vlayout.setSpacing(10)
        
        # Strategies results Table
        table_group = QGroupBox("Таблица результатов (сортировка по клику на заголовок)")
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(5, 5, 5, 5)
        
        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels(["#", "Успешность (все)", "Успешность (приор.)", "Успешно", "Тест PIP", "Параметры стратегии"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.results_table.itemSelectionChanged.connect(self.strategy_selection_changed)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        table_layout.addWidget(self.results_table)
        table_group.setLayout(table_layout)
        table_group.setFixedHeight(300)
        results_vlayout.addWidget(table_group)
        
        # Domain Detail View
        detail_group = QGroupBox("Подробный лог доменов для выбранной стратегии")
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(5, 5, 5, 5)
        
        self.detail_list = QListWidget()
        self.detail_list.setSelectionMode(QListWidget.NoSelection)
        detail_layout.addWidget(self.detail_list)
        detail_group.setLayout(detail_layout)
        detail_group.setFixedHeight(180)
        results_vlayout.addWidget(detail_group)
        
        results_container.setLayout(results_vlayout)
        right_layout.addWidget(results_container)
        
        # Bottom Actions
        self.apply_btn = QPushButton("Применить выбранную стратегию как основную для ByeDPI")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_selected_strategy)
        right_layout.addWidget(self.apply_btn)
        
        right_widget.setLayout(right_layout)
        panels_layout.addWidget(right_widget)
        
        # Fixed column widths instead of splitter to lock panel sizes
        left_widget.setFixedWidth(330)
        panels_container.setLayout(panels_layout)
        main_layout.addWidget(panels_container)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Verify ByeDPI binary
        if not os.path.exists(self.path_edit.text()):
            self.status_desc.setText("Внимание: Файл ciadpi.exe не найден по умолчанию. Пожалуйста, укажите верный путь.")
            self.path_edit.setStyleSheet("border: 1.5px solid #e74c3c;")

    def browse_executable(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл ByeDPI", "", "Executables (*.exe);;All Files (*)"
        )
        if file_path:
            self.path_edit.setText(os.path.normpath(file_path))
            self.path_edit.setStyleSheet("")
            self.status_desc.setText("Путь к ByeDPI обновлен.")

    def refresh_domains_list(self):
        self.domains_list.blockSignals(True)
        self.domains_list.clear()
        for domain in self.domains:
            item = QListWidgetItem(domain)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if domain in self.priority_sites:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.domains_list.addItem(item)
        self.domains_list.blockSignals(False)

    def on_domain_check_changed(self, item):
        domain = item.text()
        if item.checkState() == Qt.Checked:
            if domain not in self.priority_sites:
                self.priority_sites.append(domain)
        else:
            if domain in self.priority_sites:
                self.priority_sites.remove(domain)
        self.save_priority_sites()
        self.recalculate_table_priority_percentages()

    def recalculate_table_priority_percentages(self):
        if not self.results_data:
            return
            
        for row in range(self.results_table.rowCount()):
            # Column 5 contains strategy parameters in the results table now
            strategy = self.results_table.item(row, 5).text()
            # Find matching result in results_data
            for strat, pct, succ, tot, details in self.results_data:
                if strat == strategy:
                    # Calculate priority success
                    priority_succ = 0
                    priority_tot = 0
                    for site in self.priority_sites:
                        if site in self.domains:
                            priority_tot += 1
                            if site in details and details[site][0]:
                                priority_succ += 1
                                
                    if priority_tot > 0:
                        pri_pct = (priority_succ / priority_tot) * 100
                        text = "%.1f%% (%d/%d)" % (pri_pct, priority_succ, priority_tot)
                    else:
                        text = "-"
                        pri_pct = 0.0
                        
                    item_pri = self.results_table.item(row, 2)
                    if item_pri:
                        item_pri.setText(text)
                        # Color highlight (muted shades)
                        if pri_pct >= 80.0:
                            item_pri.setForeground(QColor("#a8c3a8"))
                        elif pri_pct >= 40.0:
                            item_pri.setForeground(QColor("#c3b5a8"))
                        else:
                            item_pri.setForeground(QColor("#c3a8a8"))
                    break

    def add_domain(self):
        domain = self.new_domain_edit.text().strip().lower()
        if not domain:
            return
        
        # Basic validation
        if '.' not in domain or len(domain) < 4:
            QMessageBox.warning(self, "Неверный домен", "Пожалуйста, введите корректное доменное имя (например, google.com).")
            return
            
        if domain in self.domains:
            QMessageBox.information(self, "Домен уже есть", "Этот домен уже добавлен в список.")
            return
            
        self.domains.append(domain)
        self.priority_sites.append(domain)
        self.save_domains()
        self.save_priority_sites()
        self.refresh_domains_list()
        self.new_domain_edit.clear()
        self.status_desc.setText("Домен %s добавлен." % domain)
        self.recalculate_table_priority_percentages()

    def remove_domain(self):
        selected_items = self.domains_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Выберите домен", "Пожалуйста, выберите домен из списка для удаления.")
            return
            
        for item in selected_items:
            domain = item.text()
            if domain in self.domains:
                self.domains.remove(domain)
            if domain in self.priority_sites:
                self.priority_sites.remove(domain)
            
        self.save_domains()
        self.save_priority_sites()
        self.refresh_domains_list()
        self.status_desc.setText("Выбранный домен удален.")
        self.recalculate_table_priority_percentages()

    def reset_domains(self):
        reply = QMessageBox.question(
            self, "Сбросить домены", 
            "Вы уверены, что хотите сбросить список доменов к списку по умолчанию?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if byedpi_tester and hasattr(byedpi_tester, 'DEFAULT_SITES'):
                self.domains = list(byedpi_tester.DEFAULT_SITES)
            else:
                self.domains = ['youtube.com', 'rutracker.org', 'nyaa.si', 'speedtest.net']
            self.priority_sites = list(self.domains)
            self.save_domains()
            self.save_priority_sites()
            self.refresh_domains_list()
            self.status_desc.setText("Список доменов сброшен к настройкам по умолчанию.")
            self.recalculate_table_priority_percentages()

    def start_testing(self):
        byedpi_path = self.path_edit.text().strip()
        if not os.path.exists(byedpi_path):
            QMessageBox.critical(self, "Ошибка", "Исполняемый файл ciadpi.exe не найден по указанному пути:\n%s" % byedpi_path)
            return

        if not self.domains:
            QMessageBox.warning(self, "Нет доменов", "Список проверяемых доменов пуст. Добавьте хотя бы один домен.")
            return

        # Prepare UI
        self.results_data = []
        self.results_table.setRowCount(0)
        self.detail_list.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Инициализация...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.apply_btn.setEnabled(False)
        
        # Disable settings to prevent editing during run
        self.path_edit.setEnabled(False)
        self.sni_edit.setEnabled(False)
        self.port_edit.setEnabled(False)
        self.conc_spin.setEnabled(False)
        self.timeout_spin.setEnabled(False)
        self.delay_spin.setEnabled(False)
        self.new_domain_edit.setEnabled(False)
        self.add_domain_btn.setEnabled(False)
        self.remove_domain_btn.setEnabled(False)
        self.reset_domains_btn.setEnabled(False)

        # Collect options
        options = {
            'sni': self.sni_edit.text().strip(),
            'ip': '127.0.0.1',
            'port': self.port_edit.text().strip(),
            'concurrency': self.conc_spin.value(),
            'timeout': self.timeout_spin.value(),
            'delay': self.delay_spin.value()
        }

        # Start thread
        self.worker = WorkerThread(byedpi_path, self.strategies, self.domains, options)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.strategy_completed.connect(self.on_strategy_completed)
        self.worker.finished.connect(self.on_testing_finished)
        self.worker.error.connect(self.on_testing_error)
        self.worker.start()

    def stop_testing(self):
        if self.worker and self.worker.isRunning():
            self.progress_bar.setFormat("Остановка...")
            self.worker.cancel()
            self.stop_btn.setEnabled(False)

    def on_progress_changed(self, current, total, strategy_cmd):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current - 1)
        self.progress_bar.setFormat("Проверка: %d из %d" % (current, total))
        self.status_desc.setText("Активная стратегия: %s" % strategy_cmd)

    def on_strategy_completed(self, strategy, success_rate, success_count, total, details):
        # Insert into results table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Column 0: Index
        item_idx = QTableWidgetItem(str(row + 1))
        item_idx.setTextAlignment(Qt.AlignCenter)
        self.results_table.setItem(row, 0, item_idx)
        
        # Column 1: Успешность (все)
        item_pct = QTableWidgetItem("%.1f%%" % success_rate)
        item_pct.setTextAlignment(Qt.AlignCenter)
        if success_rate >= 80.0:
            item_pct.setForeground(QColor("#a8c3a8")) # soft muted gray-green
        elif success_rate >= 40.0:
            item_pct.setForeground(QColor("#c3b5a8")) # soft muted gray-orange
        else:
            item_pct.setForeground(QColor("#c3a8a8")) # soft muted gray-red
        self.results_table.setItem(row, 1, item_pct)
        
        # Column 2: Успешность (приор.)
        priority_succ = 0
        priority_tot = 0
        for site in self.priority_sites:
            if site in self.domains:
                priority_tot += 1
                if site in details and details[site][0]:
                    priority_succ += 1
                    
        if priority_tot > 0:
            pri_pct = (priority_succ / priority_tot) * 100
            pri_text = "%.1f%% (%d/%d)" % (pri_pct, priority_succ, priority_tot)
        else:
            pri_text = "-"
            pri_pct = 0.0
            
        item_pri = QTableWidgetItem(pri_text)
        item_pri.setTextAlignment(Qt.AlignCenter)
        if pri_pct >= 80.0:
            item_pri.setForeground(QColor("#a8c3a8"))
        elif pri_pct >= 40.0:
            item_pri.setForeground(QColor("#c3b5a8"))
        else:
            item_pri.setForeground(QColor("#c3a8a8"))
        self.results_table.setItem(row, 2, item_pri)
        
        # Column 3: Успешно
        item_succ = QTableWidgetItem("%d / %d" % (success_count, total))
        item_succ.setTextAlignment(Qt.AlignCenter)
        self.results_table.setItem(row, 3, item_succ)
        
        # Column 4: Тест PIP
        pip_res = details.get("__pip_test__", (False, "Не проверялось"))
        pip_ok, pip_msg = pip_res
        item_pip = QTableWidgetItem("OK" if pip_ok else ("Ошибка" if "Ошибка" in pip_msg or "Таймаут" in pip_msg else "-"))
        item_pip.setTextAlignment(Qt.AlignCenter)
        if pip_ok:
            item_pip.setForeground(QColor("#a8c3a8")) # soft green
        else:
            item_pip.setForeground(QColor("#c3a8a8")) # soft red
        self.results_table.setItem(row, 4, item_pip)
        
        # Column 5: Параметры стратегии
        item_strat = QTableWidgetItem(strategy)
        self.results_table.setItem(row, 5, item_strat)
        
        # Save results in list
        self.results_data.append((strategy, success_rate, success_count, total, details))
        
        # Scroll to bottom row automatically
        self.results_table.scrollToBottom()

    def refresh_results_table(self):
        """Redraw results table from self.results_data."""
        self.results_table.setRowCount(0)
        for idx, (strategy, success_rate, success_count, total, details) in enumerate(self.results_data):
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # Column 0: Index
            item_idx = QTableWidgetItem(str(row + 1))
            item_idx.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 0, item_idx)
            
            # Column 1: Успешность (все)
            item_pct = QTableWidgetItem("%.1f%%" % success_rate)
            item_pct.setTextAlignment(Qt.AlignCenter)
            if success_rate >= 80.0:
                item_pct.setForeground(QColor("#a8c3a8")) # soft muted gray-green
            elif success_rate >= 40.0:
                item_pct.setForeground(QColor("#c3b5a8")) # soft muted gray-orange
            else:
                item_pct.setForeground(QColor("#c3a8a8")) # soft muted gray-red
            self.results_table.setItem(row, 1, item_pct)
            
            # Column 2: Успешность (приор.)
            priority_succ = 0
            priority_tot = 0
            for site in self.priority_sites:
                if site in self.domains:
                    priority_tot += 1
                    if site in details and details[site][0]:
                        priority_succ += 1
                        
            if priority_tot > 0:
                pri_pct = (priority_succ / priority_tot) * 100
                pri_text = "%.1f%% (%d/%d)" % (pri_pct, priority_succ, priority_tot)
            else:
                pri_text = "-"
                pri_pct = 0.0
                
            item_pri = QTableWidgetItem(pri_text)
            item_pri.setTextAlignment(Qt.AlignCenter)
            if pri_pct >= 80.0:
                item_pri.setForeground(QColor("#a8c3a8"))
            elif pri_pct >= 40.0:
                item_pri.setForeground(QColor("#c3b5a8"))
            else:
                item_pri.setForeground(QColor("#c3a8a8"))
            self.results_table.setItem(row, 2, item_pri)
            
            # Column 3: Успешно
            item_succ = QTableWidgetItem("%d / %d" % (success_count, total))
            item_succ.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 3, item_succ)
            
            # Column 4: Тест PIP
            pip_res = details.get("__pip_test__", (False, "Не проверялось"))
            pip_ok, pip_msg = pip_res
            item_pip = QTableWidgetItem("OK" if pip_ok else ("Ошибка" if "Ошибка" in pip_msg or "Таймаут" in pip_msg else "-"))
            item_pip.setTextAlignment(Qt.AlignCenter)
            if pip_ok:
                item_pip.setForeground(QColor("#a8c3a8")) # soft green
            else:
                item_pip.setForeground(QColor("#c3a8a8")) # soft red
            self.results_table.setItem(row, 4, item_pip)
            
            # Column 5: Параметры стратегии
            item_strat = QTableWidgetItem(strategy)
            self.results_table.setItem(row, 5, item_strat)

    def on_testing_finished(self, results):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Проверка завершена!")
        
        # Re-enable inputs
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.path_edit.setEnabled(True)
        self.sni_edit.setEnabled(True)
        self.port_edit.setEnabled(True)
        self.conc_spin.setEnabled(True)
        self.timeout_spin.setEnabled(True)
        self.delay_spin.setEnabled(True)
        self.new_domain_edit.setEnabled(True)
        self.add_domain_btn.setEnabled(True)
        self.remove_domain_btn.setEnabled(True)
        self.reset_domains_btn.setEnabled(True)

        if not results:
            self.status_desc.setText("Проверка остановлена или не дала результатов.")
            return

        # Sort results: primary key = priority success %, secondary key = overall success %
        def get_sort_score(item):
            strat, overall_pct, succ, tot, details = item
            priority_succ = 0
            priority_tot = 0
            for site in self.priority_sites:
                if site in self.domains:
                    priority_tot += 1
                    if site in details and details[site][0]:
                        priority_succ += 1
            pri_pct = (priority_succ / priority_tot * 100) if priority_tot > 0 else 0.0
            return (pri_pct, overall_pct)
            
        self.results_data.sort(key=get_sort_score, reverse=True)
        
        # Redraw table in sorted order
        self.refresh_results_table()

        # Find best strategy (now it is the first one in sorted results_data)
        best_strat, overall_pct, succ, tot, details = self.results_data[0]
        
        # Calculate best priority success %
        priority_succ = 0
        priority_tot = 0
        for site in self.priority_sites:
            if site in self.domains:
                priority_tot += 1
                if site in details and details[site][0]:
                    priority_succ += 1
        best_pri_pct = (priority_succ / priority_tot * 100) if priority_tot > 0 else 0.0
                
        if best_pri_pct > 0.0 or overall_pct > 0.0:
            self.status_desc.setText("Лучшая стратегия: %s (Приоритет: %.1f%%, Всего: %.1f%%)" % (
                best_strat, best_pri_pct, overall_pct
            ))
            self.apply_btn.setEnabled(True)
            
            # Select the first row (the best strategy) automatically
            self.results_table.selectRow(0)
        else:
            self.status_desc.setText("Ни одна из проверенных стратегий не сработала.")
            self.apply_btn.setEnabled(False)

        QMessageBox.information(self, "Проверка завершена", "Тестирование всех стратегий успешно завершено!")

    def on_testing_error(self, err_msg):
        QMessageBox.critical(self, "Ошибка", "Произошла ошибка при тестировании:\n%s" % err_msg)
        self.on_testing_finished([])

    def strategy_selection_changed(self):
        # Update detailed list of domain statuses
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            self.detail_list.clear()
            self.apply_btn.setEnabled(False)
            return

        row = selected_ranges[0].topRow()
        if row >= len(self.results_data):
            return
            
        strategy, pct, succ, tot, details = self.results_data[row]
        self.detail_list.clear()
        
        # Populate details list
        for site, (success, msg) in details.items():
            prefix = "OK" if success else "ERR"
            item_text = "[%s]  %s   :   %s" % (prefix, site, msg)
            self.detail_list.addItem(item_text)
            
            # Color list item with extremely muted tones
            list_item = self.detail_list.item(self.detail_list.count() - 1)
            if success:
                list_item.setForeground(QColor("#a8c3a8")) # soft gray-green
            else:
                list_item.setForeground(QColor("#c3a8a8")) # soft gray-red
                
        self.apply_btn.setEnabled(True)

    def apply_selected_strategy(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Выберите стратегию", "Пожалуйста, выберите стратегию из таблицы результатов для применения.")
            return

        row = selected_ranges[0].topRow()
        if row >= len(self.results_data):
            return
            
        strategy, pct, succ, tot, details = self.results_data[row]
        
        # Re-inject current SNI back into the template command if {sni} is written
        # Since strategy from self.results_data has template form, let's format it or save as is
        # Actually, in ToInet-MAX, byedpi is run directly with parameters from BYEDPI_CUSTOM_FILE
        # Let's format the strategy with the user-defined SNI for writing
        sni = self.sni_edit.text().strip()
        final_params = strategy.replace("{sni}", sni)
        
        # Ensure SOCKS5 port 1780 is added if not present in parameters
        params_list = final_params.split()
        has_port = False
        for arg in params_list:
            if arg == '-p' or arg == '--port':
                has_port = True
                break
            elif arg.startswith('-p') and len(arg) > 2 and arg[2].isdigit():
                has_port = True
                break
        if not has_port:
            final_params = "-p 1780 " + final_params
            
        pip_res = details.get("__pip_test__", (False, "Не проверялось"))
        pip_ok, pip_msg = pip_res
        
        try:
            # Save strategy to byedpi_custom.txt
            with open(BYEDPI_CUSTOM_FILE, 'w', encoding='utf-8') as f:
                f.write("# Установлено автоматически тестером стратегий ByeDPI\n")
                f.write("# Успешность проверки: %.1f%% (%d из %d сайтов)\n" % (pct, succ, tot))
                f.write("# Дата установки: %s\n\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write(final_params + "\n")
                
            # Update configuration to use custom settings
            if config_manager:
                config = config_manager.load_config()
                config["use_custom_settings"] = True
                
                if pip_ok:
                    reply = QMessageBox.question(
                        self, "Проксирование pip (PyPI)",
                        "Эта стратегия успешно обходит блокировку PyPI (pip работает)!\n\n"
                        "Желаете настроить отдельный ByeDPI для автоматического проксирования pip "
                        "через эту стратегию (порт 1781)? Режим будет автоматически запускаться с приложением.",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                    )
                    if reply == QMessageBox.Yes:
                        config["byedpi_pip_enabled"] = True
                        config["byedpi_pip_use_tor"] = False
                        
                        pip_custom_file = os.path.join(os.path.dirname(BYEDPI_CUSTOM_FILE), "byedpi_pip_custom.txt")
                        pip_params = strategy.replace("{sni}", sni)
                        pip_params_list = pip_params.split()
                        pip_has_port = False
                        for arg in pip_params_list:
                            if arg == '-p' or arg == '--port':
                                pip_has_port = True
                                break
                            elif arg.startswith('-p') and len(arg) > 2 and arg[2].isdigit():
                                pip_has_port = True
                                break
                        if not pip_has_port:
                            pip_params = "-p 1781 " + pip_params
                            
                        with open(pip_custom_file, 'w', encoding='utf-8') as f_pip:
                            f_pip.write("# Установлено автоматически тестером стратегий ByeDPI для PIP\n")
                            f_pip.write("# Успешность проверки: %.1f%%\n" % pct)
                            f_pip.write("# Дата установки: %s\n\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
                            f_pip.write(pip_params + "\n")
                            
                        import bdsher
                        bdsher.set_pip_proxy("socks5://127.0.0.1:1781")
                        
                        try:
                            pip_mgr = bdsher.get_pip_manager(config)
                            pip_mgr.stop()
                            pip_mgr.start()
                        except Exception as e:
                            print(f"Error starting pip manager: {e}")
                            
                        QMessageBox.information(
                            self, "Успех",
                            "Проксирование pip через отдельный ByeDPI (1781) успешно настроено и запущено!"
                        )
                else:
                    reply = QMessageBox.question(
                        self, "Проксирование pip через TOR",
                        "Эта стратегия не смогла восстановить доступ к PyPI для pip.\n\n"
                        "Желаете настроить автоматическое проксирование pip через сеть TOR (socks5://127.0.0.1:9853)?\n"
                        "Скачивание пакетов будет работать при запущенном TOR.",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                    )
                    if reply == QMessageBox.Yes:
                        config["byedpi_pip_enabled"] = True
                        config["byedpi_pip_use_tor"] = True
                        
                        import bdsher
                        pip_mgr = bdsher.get_pip_manager(config)
                        pip_mgr.stop()
                        bdsher.set_pip_proxy("socks5://127.0.0.1:9853")
                        
                        QMessageBox.information(
                            self, "Успех",
                            "Проксирование pip через TOR (9853) успешно настроено и включено!"
                        )
                        
                config_manager.save_config(config)
                
            QMessageBox.information(
                self, "Успех", 
                "Выбранная стратегия успешно записана в файл %s!\n\n"
                "Параметры: %s\n\n"
                "В настройках ToInet-MAX включен режим кастомных настроек ByeDPI.\n"
                "Пожалуйста, перезапустите ByeDPI из трея для применения изменений." % (
                    os.path.basename(BYEDPI_CUSTOM_FILE), final_params
                )
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", "Не удалось применить стратегию:\n%s" % e)


def main():
    app = QApplication(sys.argv)
    window = ByeDPITesterGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
