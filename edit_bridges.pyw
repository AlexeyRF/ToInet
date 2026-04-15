import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QMessageBox, QStatusBar, QDialog, QDialogButtonBox,
                             QFrame, QSplitter)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QTextCursor

class ActionDialog(QDialog):
    """Диалог выбора действия при наличии изменений"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор действия")
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#replaceBtn {
                background-color: #f44336;
            }
            QPushButton#replaceBtn:hover {
                background-color: #da190b;
            }
            QPushButton#leaveBtn {
                background-color: #2196F3;
            }
            QPushButton#leaveBtn:hover {
                background-color: #0b7dda;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Заголовок
        title_label = QLabel("⚠️ Внесены изменения в мосты")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff9800;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Описание
        desc_label = QLabel("Были внесены изменения в список мостов.\nВыберите действие перед запуском конфигуратора:")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.add_btn = QPushButton("➕ Добавить мосты")
        self.add_btn.clicked.connect(self.accept_add)
        button_layout.addWidget(self.add_btn)
        
        self.replace_btn = QPushButton("🔄 Заменить мосты")
        self.replace_btn.setObjectName("replaceBtn")
        self.replace_btn.clicked.connect(self.accept_replace)
        button_layout.addWidget(self.replace_btn)
        
        self.leave_btn = QPushButton("💾 Оставить как есть")
        self.leave_btn.setObjectName("leaveBtn")
        self.leave_btn.clicked.connect(self.accept_leave)
        button_layout.addWidget(self.leave_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.result = None
        
    def accept_add(self):
        self.result = "add"
        self.accept()
        
    def accept_replace(self):
        self.result = "replace"
        self.accept()
        
    def accept_leave(self):
        self.result = "leave"
        self.accept()
        
    def get_result(self):
        return self.result

class TorBridgeManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Менеджер Tor мостов")
        self.setMinimumSize(700, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #3c3c3c;
                border: 2px solid #555;
                border-radius: 5px;
                color: #e0e0e0;
                font-family: Consolas;
                font-size: 11px;
                selection-background-color: #4CAF50;
            }
            QTextEdit:focus {
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
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#replaceBtn {
                background-color: #f44336;
            }
            QPushButton#replaceBtn:hover {
                background-color: #da190b;
            }
            QPushButton#updateBtn {
                background-color: #ff9800;
            }
            QPushButton#updateBtn:hover {
                background-color: #fb8c00;
            }
            QPushButton#configBtn {
                background-color: #2196F3;
            }
            QPushButton#configBtn:hover {
                background-color: #0b7dda;
            }
            QStatusBar {
                background-color: #1e1e1e;
                color: #888;
                border-top: 1px solid #555;
            }
            QSplitter::handle {
                background-color: #555;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:vertical {
                height: 2px;
            }
        """)
        
        self.changes_made = False
        self.bridges_file = "bridges.txt"
        self.torrc_file = "torrc"
        self.maestro_file = "maestro.pyw"
        
        self.init_ui()
        self.load_existing_bridges()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel("🌐 Менеджер Tor мостов")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #4CAF50;
            padding: 10px;
            border-bottom: 2px solid #4CAF50;
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Информационная панель
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: #888;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        
        self.bridges_count_label = QLabel("📊 Загружено мостов: 0")
        info_layout.addWidget(self.bridges_count_label)
        
        info_layout.addStretch()
        
        self.file_status_label = QLabel("📁 Файл: bridges.txt")
        info_layout.addWidget(self.file_status_label)
        
        main_layout.addWidget(info_frame)
        
        # Основной текстовый редактор
        editor_label = QLabel("✏️ Введите мосты (каждый с новой строки):")
        editor_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(editor_label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Пример:\nobfs4 192.95.36.142:443 2C5BED3F2B2D4F2A8F0B5E6D9C8A7B4E5F6A7B8 cert=...\nobfs4 193.11.166.194:443 1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B cert=...")
        self.text_edit.textChanged.connect(self.on_text_changed)
        main_layout.addWidget(self.text_edit)
        
        # Кнопки управления
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(15)
        
        self.add_btn = QPushButton("➕ Добавить мосты")
        self.add_btn.clicked.connect(self.add_bridges)
        button_layout.addWidget(self.add_btn)
        
        self.replace_btn = QPushButton("🔄 Заменить мосты")
        self.replace_btn.setObjectName("replaceBtn")
        self.replace_btn.clicked.connect(self.replace_bridges)
        button_layout.addWidget(self.replace_btn)
        
        button_layout.addStretch()
        
        self.update_btn = QPushButton("🗑️ Обновить конфигурацию")
        self.update_btn.setObjectName("updateBtn")
        self.update_btn.clicked.connect(self.update_config)
        button_layout.addWidget(self.update_btn)
        
        self.config_btn = QPushButton("⚙️ Настроить конфигурацию")
        self.config_btn.setObjectName("configBtn")
        self.config_btn.clicked.connect(self.configure_tor)
        button_layout.addWidget(self.config_btn)
        
        main_layout.addWidget(button_frame)
        
        # Кнопка очистки
        clear_btn = QPushButton("🧹 Очистить поле ввода")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        clear_btn.clicked.connect(self.clear_text)
        
        clear_layout = QHBoxLayout()
        clear_layout.addStretch()
        clear_layout.addWidget(clear_btn)
        clear_layout.addStretch()
        main_layout.addLayout(clear_layout)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✅ Готов к работе")
        
    def load_existing_bridges(self):
        """Загрузка существующих мостов из файла"""
        if os.path.exists(self.bridges_file):
            try:
                with open(self.bridges_file, 'r', encoding='utf-8') as f:
                    bridges = [line.strip() for line in f if line.strip()]
                    count = len(bridges)
                    self.bridges_count_label.setText(f"📊 Загружено мостов: {count}")
                    if count > 0:
                        self.status_bar.showMessage(f"Загружено {count} мостов из {self.bridges_file}")
            except Exception as e:
                self.status_bar.showMessage(f"Ошибка при загрузке мостов: {str(e)}")
                
    def on_text_changed(self):
        """Обработчик изменения текста"""
        text = self.text_edit.toPlainText().strip()
        if text:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            count = len(lines)
            self.status_bar.showMessage(f"В поле ввода: {count} мостов (не сохранено)")
        else:
            self.status_bar.showMessage("Поле ввода пусто")
            
    def get_valid_bridges(self, text):
        """Получение списка валидных мостов из текста"""
        lines = text.split('\n')
        bridges = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):  # Игнорируем комментарии и пустые строки
                bridges.append(line)
        return bridges
        
    def add_bridges(self):
        """Добавление мостов в файл"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Пустой ввод", "Введите текст для добавления")
            return
            
        bridges = self.get_valid_bridges(text)
        if not bridges:
            QMessageBox.warning(self, "Нет валидных мостов", "Не найдено валидных мостов для добавления")
            return
            
        try:
            # Читаем существующие мосты
            existing_bridges = []
            if os.path.exists(self.bridges_file):
                with open(self.bridges_file, 'r', encoding='utf-8') as f:
                    existing_bridges = [line.strip() for line in f if line.strip()]
            
            # Добавляем новые мосты
            new_bridges = []
            for bridge in bridges:
                if bridge not in existing_bridges:
                    new_bridges.append(bridge)
                    
            if not new_bridges:
                QMessageBox.information(self, "Информация", "Все мосты уже существуют в файле")
                return
                
            # Записываем обновленный список
            with open(self.bridges_file, 'a', encoding='utf-8') as f:
                for bridge in new_bridges:
                    f.write(bridge + "\n")
                    
            self.changes_made = True
            self.text_edit.clear()
            self.load_existing_bridges()
            
            QMessageBox.information(self, "Успех", f"Добавлено {len(new_bridges)} новых мостов")
            self.status_bar.showMessage(f"✅ Добавлено {len(new_bridges)} мостов")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить мосты: {str(e)}")
            self.status_bar.showMessage(f"❌ Ошибка при добавлении мостов: {str(e)}")
            
    def replace_bridges(self):
        """Замена всех мостов в файле"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Пустой ввод", "Введите текст для замены")
            return
            
        bridges = self.get_valid_bridges(text)
        if not bridges:
            QMessageBox.warning(self, "Нет валидных мостов", "Не найдено валидных мостов для замены")
            return
            
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите заменить всё содержимое файла {self.bridges_file}?\n"
            f"Будет добавлено {len(bridges)} мостов.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with open(self.bridges_file, 'w', encoding='utf-8') as f:
                    for bridge in bridges:
                        f.write(bridge + "\n")
                        
                self.changes_made = True
                self.text_edit.clear()
                self.load_existing_bridges()
                
                QMessageBox.information(self, "Успех", f"Содержимое файла успешно заменено. Добавлено {len(bridges)} мостов.")
                self.status_bar.showMessage(f"✅ Заменено {len(bridges)} мостов")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось заменить содержимое: {str(e)}")
                self.status_bar.showMessage(f"❌ Ошибка при замене: {str(e)}")
                
    def update_config(self):
        """Обновление конфигурации (удаление torrc)"""
        try:
            if os.path.exists(self.torrc_file):
                reply = QMessageBox.question(
                    self, "Подтверждение",
                    f"Вы уверены, что хотите удалить файл {self.torrc_file}?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    os.remove(self.torrc_file)
                    self.status_bar.showMessage("✅ Файл torrc успешно удален")
                    QMessageBox.information(self, "Успех", "Файл torrc успешно удален")
            else:
                QMessageBox.information(self, "Информация", f"Файл {self.torrc_file} не существует в текущей папке")
                self.status_bar.showMessage("Файл torrc не найден")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить файл torrc: {str(e)}")
            self.status_bar.showMessage(f"❌ Ошибка при удалении torrc: {str(e)}")
            
    def configure_tor(self):
        """Настройка конфигурации Tor"""
        try:
            # Удаляем существующий torrc если есть
            if os.path.exists(self.torrc_file):
                os.remove(self.torrc_file)
                
            if self.changes_made:
                dialog = ActionDialog(self)
                if dialog.exec_() == QDialog.Accepted:
                    result = dialog.get_result()
                    if result == "add":
                        self.add_bridges()
                    elif result == "replace":
                        self.replace_bridges()
                    # Если "leave", ничего не делаем
                else:
                    return
                    
            self.launch_maestro()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось настроить конфигурацию: {str(e)}")
            self.status_bar.showMessage(f"❌ Ошибка при настройке: {str(e)}")
            
    def launch_maestro(self):
        """Запуск программы maestro.pyw"""
        try:
            if os.path.exists(self.maestro_file):
                subprocess.Popen(["pythonw", self.maestro_file], shell=True)
                self.status_bar.showMessage("✅ Программа maestro.pyw запущена")
                QMessageBox.information(self, "Успех", "Программа maestro.pyw успешно запущена")
            else:
                QMessageBox.warning(
                    self, "Файл не найден",
                    f"Файл {self.maestro_file} не найден в текущей папке\n"
                    f"Текущая директория: {os.getcwd()}"
                )
                self.status_bar.showMessage("❌ Файл maestro.pyw не найден")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить maestro.pyw: {str(e)}")
            self.status_bar.showMessage(f"❌ Ошибка при запуске: {str(e)}")
            
    def clear_text(self):
        """Очистка поля ввода"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите очистить поле ввода?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.text_edit.clear()
            self.status_bar.showMessage("Поле ввода очищено")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Установка иконки приложения (если есть)
    # app.setWindowIcon(QIcon('icon.png'))
    
    window = TorBridgeManager()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()