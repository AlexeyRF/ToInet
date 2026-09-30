import sys, os
import re
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QCheckBox
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from system_utils import T

class OutputLogger(QObject):
    log_signal = pyqtSignal(str)
    def __init__(self, original_stream):
        super().__init__()
        self.original_stream = original_stream
        import os
        if not os.path.exists('logs'): os.makedirs('logs')
        self.log_file = os.path.join('logs', 'app.log')

    def write(self, text):
        if self.original_stream:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except: pass
        if text.strip():
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(text)
            except: pass
        self.log_signal.emit(text)

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except: pass

class AppLogWindow(QDialog):
    def __init__(self, title="Логи приложения", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)
        
        # Dark Title Bar for Windows
        try:
            import ctypes
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            hwnd = int(self.winId())
            rendering_policy = ctypes.c_int(1)
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy))
        except:
            pass
        
        # Dark Theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #555;
                font-family: Consolas, monospace;
            }
            QPushButton {
                background-color: #005FB8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #0078D4;
            }
            QCheckBox {
                color: #e0e0e0;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        
        # Checkboxes for categories
        self.filter_layout = QHBoxLayout()
        self.categories = {}
        # Pre-populate known categories
        for pre_cat in ["LOG", "TOR Manager", "ByeDPI", "OperaProxy", "TGWS", "MODE"]:
            self._add_category_checkbox(pre_cat)
        self.layout.addLayout(self.filter_layout)
        
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)
        
        self.clear_btn = QPushButton(T("Очистить", "Clear"), self)
        self.clear_btn.clicked.connect(self.clear_logs)
        self.layout.addWidget(self.clear_btn)
        
        self.all_logs = []  # Store raw tuples of (category, text)
        self.current_category = "Other"

    def clear_logs(self):
        self.all_logs = []
        self.text_edit.clear()
        
    def _get_category(self, text):
        import re
        match = re.search(r'^\[(.*?)\]', text.strip())
        if match:
            return match.group(1)
        return None

    def _add_category_checkbox(self, cat):
        if cat not in self.categories:
            cb = QCheckBox(cat)
            cb.setChecked(True)
            cb.stateChanged.connect(self.refresh_logs)
            self.filter_layout.addWidget(cb)
            self.categories[cat] = cb

    def refresh_logs(self):
        self.text_edit.clear()
        for cat, text in self.all_logs:
            if cat == "Other" or (cat in self.categories and self.categories[cat].isChecked()):
                self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(self.text_edit.textCursor().End)

    def append_log(self, text):
        cat = self._get_category(text)
        if cat:
            self.current_category = cat
            self._add_category_checkbox(cat)
        else:
            cat = self.current_category
            
        self.all_logs.append((cat, text))
        
        # If the category is checked (or it's "Other"), append to text edit
        if cat == "Other" or (cat in self.categories and self.categories[cat].isChecked()):
            self.text_edit.moveCursor(self.text_edit.textCursor().End)
            self.text_edit.insertPlainText(text)
            self.text_edit.moveCursor(self.text_edit.textCursor().End)

app_log_window = None
def setup_logging():
    global app_log_window
    app_log_window = AppLogWindow('Логи приложения')
    sys.stdout = OutputLogger(sys.stdout)
    sys.stderr = OutputLogger(sys.stderr)
    sys.stdout.log_signal.connect(app_log_window.append_log)
    sys.stderr.log_signal.connect(app_log_window.append_log)
    print('[LOG] Система логирования инициализирована.')
    return app_log_window
