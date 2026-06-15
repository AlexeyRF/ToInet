import lang
import os
import sys
import subprocess
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import socket
import struct
import time

# ---------------------------------------------------------------------------
CONFIG_FILE = Path(__file__).parent / "socks_reabilitator_config.json"
PID_FILE = Path(__file__).parent / "socks_layer_pid.txt"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass

def is_process_running(pid: int) -> bool:
    try:
        if os.name == 'nt':
            out = subprocess.check_output(f'tasklist /FI "PID eq {pid}" /NH', shell=True, text=True)
            return str(pid) in out
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    except Exception:
        return False
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Поток проверки стратегии (асинхронный)
# ---------------------------------------------------------------------------

class StrategyVerifier(QThread):
    result = pyqtSignal(bool, str)  # флаг успеха, сообщение

    def __init__(self, script_path: Path, strat_index: int, upstream_host: str, upstream_port: int, username: str, password: str, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.strat_index = strat_index
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.username = username
        self.password = password
        self.listen_port = 1080
        self.byedpi_port = 1788
        self.process = None
        self.sock = None

    def run(self) -> None:
        cmd = [sys.executable, str(self.script_path),
               "--strategy-index", str(self.strat_index),
               "--upstream-host", self.upstream_host,
               "--upstream-port", str(self.upstream_port),
               "--listen-port", str(self.listen_port),
               "--byedpi-port", str(self.byedpi_port)]
        if self.username:
            cmd.extend(["--username", self.username])
        if self.password:
            cmd.extend(["--password", self.password])
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
            )
        except Exception as e:
            self.result.emit(False, f"Не удалось запустить слой: {e}")
            return
        
        # Дать слою время на запуск
        time.sleep(2)
        try:
            self.sock = socket.create_connection(("127.0.0.1", self.listen_port), timeout=5)
            self.sock.sendall(b"\x05\x01\x00")
            resp = self.sock.recv(2)
            if len(resp) != 2 or resp[0] != 5 or resp[1] != 0:
                raise Exception("SOCKS5 greeting failed")
            req = b"\x05\x01\x00\x01" + socket.inet_aton("1.1.1.1") + struct.pack("!H", 80)
            self.sock.sendall(req)
            resp = self.sock.recv(10)
            if len(resp) < 10 or resp[1] != 0:
                raise Exception("Upstream connection via proxy failed")
        except Exception as e:
            self.process.terminate()
            self.result.emit(False, f"Не удалось проверить SOCKS5: {e}")
            return
            
        # Удерживать соединение 60 секунд
        try:
            time.sleep(60)
            self.sock.sendall(b"GET / HTTP/1.1\r\nHost: 1.1.1.1\r\n\r\n")
            reply = self.sock.recv(1024)
            if not reply:
                raise Exception("Connection dropped")
        except Exception as e:
            self.process.terminate()
            self.result.emit(False, f"Соединение разорвано: {e}")
            return
        finally:
            try:
                self.sock.close()
            except Exception:
                pass
            self.process.terminate()
        self.result.emit(True, "Стратегия прошла проверку (соединение держалось 60 сек).")


class AllStrategyVerifier(QThread):
    # Отправка результата по каждой стратегии: индекс, успех, сообщение
    per_result = pyqtSignal(int, bool, str)
    finished = pyqtSignal()

    def __init__(self, script_path: Path, strategies: list, upstream_host: str, upstream_port: int, username: str, password: str, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.strategies = strategies
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.username = username
        self.password = password
        self.process = None
        self.sock = None

    def run(self) -> None:
        for idx, _ in enumerate(self.strategies):
            l_port = 40000 + idx
            b_port = 50000 + idx
            cmd = [sys.executable, str(self.script_path),
                   "--strategy-index", str(idx),
                   "--upstream-host", self.upstream_host,
                   "--upstream-port", str(self.upstream_port),
                   "--listen-port", str(l_port),
                   "--byedpi-port", str(b_port)]
            if self.username:
                cmd.extend(["--username", self.username])
            if self.password:
                cmd.extend(["--password", self.password])
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=creationflags,
                )
            except Exception as e:
                self.per_result.emit(idx, False, f"Не удалось запустить слой: {e}")
                continue
            
            # Дать слою время на запуск
            time.sleep(2)
            try:
                self.sock = socket.create_connection(("127.0.0.1", l_port), timeout=5)
                self.sock.sendall(b"\x05\x01\x00")
                resp = self.sock.recv(2)
                if len(resp) != 2 or resp[0] != 5 or resp[1] != 0:
                    raise Exception("SOCKS5 greeting failed")
                req = b"\x05\x01\x00\x01" + socket.inet_aton("1.1.1.1") + struct.pack("!H", 80)
                self.sock.sendall(req)
                resp = self.sock.recv(10)
                if len(resp) < 10 or resp[1] != 0:
                    raise Exception("Upstream connection via proxy failed")
            except Exception as e:
                self.process.terminate()
                self.per_result.emit(idx, False, f"Не удалось проверить SOCKS5: {e}")
                continue
                
            # Удерживать соединение 60 секунд
            try:
                time.sleep(60)
                self.sock.sendall(b"GET / HTTP/1.1\r\nHost: 1.1.1.1\r\n\r\n")
                reply = self.sock.recv(1024)
                if not reply:
                    raise Exception("Connection dropped")
            except Exception as e:
                self.process.terminate()
                self.per_result.emit(idx, False, f"Соединение разорвано: {e}")
                continue
            finally:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.process.terminate()
            self.per_result.emit(idx, True, f"Стратегия {idx} прошла проверку (соединение держалось 60 сек).")
        self.finished.emit()

# Вспомогательные функции
# ---------------------------------------------------------------------------

def load_strategies(strategies_path: Path) -> list:
    """Чтение строк стратегий из указанного файла, игнорируя комментарии и пустые строки."""
    if not strategies_path.is_file():
        return []
    with strategies_path.open(encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

# ---------------------------------------------------------------------------
# Главное окно
# ---------------------------------------------------------------------------

class Socks5Gui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BYEDPROSLOYKA")
        self.setFixedSize(480, 340)

        # --- Элементы UI ----------------------------------------------------
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Выбор стратегии
        strat_label = QLabel("Стратегия ByeDPI:")
        self.strat_combo = QComboBox()
        layout.addWidget(strat_label)
        layout.addWidget(self.strat_combo)

        # Удаленный SOCKS5 прокси
        upstream_label = QLabel("Удалённый SOCKS5‑прокси (host:port):")
        upstream_layout = QHBoxLayout()
        self.upstream_host_edit = QLineEdit("127.0.0.1")
        self.upstream_port_edit = QLineEdit("1080")
        upstream_layout.addWidget(self.upstream_host_edit)
        upstream_layout.addWidget(QLabel(":"))
        upstream_layout.addWidget(self.upstream_port_edit)
        # Поля авторизации
        auth_layout = QHBoxLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("username")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(QLabel("Логин:"))
        auth_layout.addWidget(self.username_edit)
        auth_layout.addWidget(QLabel("Пароль:"))
        auth_layout.addWidget(self.password_edit)
        layout.addWidget(upstream_label)
        layout.addLayout(upstream_layout)
        layout.addLayout(auth_layout)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton(T("Запустить", "Start"))
        self.start_btn.setObjectName("start_btn")
        self.start_btn.clicked.connect(self.start_layer)
        self.stop_btn = QPushButton(T("Остановить", "Stop"))
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_layer)
        self.verify_all_btn = QPushButton("Проверить все стратегии")
        self.verify_all_btn.clicked.connect(self.verify_all_strategies)
        self.close_btn = QPushButton("Закрыть окно")
        self.close_btn.clicked.connect(self.close_window)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.verify_all_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        # Область вывода логов
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(120)
        layout.addWidget(self.log_edit)

        # Внутреннее состояние
        self.process = None
        self.base_dir = Path(__file__).parent
        self.strategies_path = self.base_dir / "byedpi_tester_strategies.txt"
        self._populate_strategies()

        # Load last config
        config = load_config()
        if "host" in config:
            self.upstream_host_edit.setText(config["host"])
        if "port" in config:
            self.upstream_port_edit.setText(str(config["port"]))
        if "strat" in config and 0 <= config["strat"] < self.strat_combo.count():
            self.strat_combo.setCurrentIndex(config["strat"])
        if "username" in config:
            self.username_edit.setText(config["username"])
        if "password" in config:
            self.password_edit.setText(config["password"])
            
        self._check_if_running()

    # -------------------------------------------------------------------
    def _check_if_running(self):
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text("utf-8").strip())
                if is_process_running(pid):
                    # Try to reconstruct process object enough to kill it later
                    # On Windows we can use taskkill to kill it
                    self.running_pid = pid
                    self.start_btn.setEnabled(False)
                    self.stop_btn.setEnabled(True)
                    self.log_edit.append(f"Слой уже запущен (PID {pid}).")
            except Exception:
                pass

    def save_current_config(self):
        config = {
            "host": self.upstream_host_edit.text().strip(),
            "port": self.upstream_port_edit.text().strip(),
            "strat": self.strat_combo.currentIndex(),
            "username": self.username_edit.text(),
            "password": self.password_edit.text()
        }
        save_config(config)

    def _populate_strategies(self):
        strategies = load_strategies(self.strategies_path)
        if not strategies:
            QMessageBox.critical(self, T("Ошибка", "Error"), "Не найдено стратегий в файле " + str(self.strategies_path))
            return
        self.strat_combo.addItems([f"{i}: {s}" for i, s in enumerate(strategies)])
        self.strategies = strategies

    # -------------------------------------------------------------------
    def start_layer(self):
        if hasattr(self, "running_pid") and is_process_running(self.running_pid):
            QMessageBox.information(self, T("Запуск", "Start"), "Процесс уже запущен.")
            return
            
        self.save_current_config()
            
        # Сбор параметров
        host = self.upstream_host_edit.text().strip()
        port_text = self.upstream_port_edit.text().strip()
        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "Неправильный порт", "Порт должен быть числом.")
            return
        strat_index = self.strat_combo.currentIndex()
        username = self.username_edit.text()
        password = self.password_edit.text()
        # Сборка команды – используется упрощенный socks5_layer.py
        script_path = self.base_dir / "socks5_layer.py"
        cmd = [sys.executable, str(script_path),
               "--strategy-index", str(strat_index),
               "--upstream-host", host,
               "--upstream-port", str(port)]
        if username:
            cmd.extend(["--username", username])
        if password:
            cmd.extend(["--password", password])
        # Запуск без консольного окна на Windows
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
            )
            self.running_pid = self.process.pid
            PID_FILE.write_text(str(self.running_pid), "utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка запуска", f"Не удалось запустить слой: {e}")
            self.process = None
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        QMessageBox.information(self, T("Запуск", "Start"), "Слой запущен в фоновом режиме.")
        self.log_edit.append(f"Запущен слой (PID {self.running_pid})")

    # -------------------------------------------------------------------
    def stop_layer(self):
        if not hasattr(self, "running_pid"):
            QMessageBox.information(self, "Остановка", "Процесс не запущен.")
            return
            
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None
        else:
            # Kill by PID
            if os.name == 'nt':
                subprocess.call(f'taskkill /F /PID {self.running_pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                try:
                    os.kill(self.running_pid, 9)
                except OSError:
                    pass
                    
        if PID_FILE.exists():
            PID_FILE.unlink()
        
        if hasattr(self, "running_pid"):
            delattr(self, "running_pid")
            
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.information(self, "Остановка", "Слой остановлен.")
        self.log_edit.append("Слой остановлен.")

    def verify_strategy(self):
        """Запуск StrategyVerifier для проверки того, удерживает ли выбранная стратегия соединение с удаленным сервером 60 сек."""
        host = self.upstream_host_edit.text().strip()
        port_text = self.upstream_port_edit.text().strip()
        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "Неправильный порт", "Порт должен быть числом.")
            return
        strat_index = self.strat_combo.currentIndex()
        username = self.username_edit.text()
        password = self.password_edit.text()
        script_path = self.base_dir / "socks5_layer.py"
        self.verifier = StrategyVerifier(script_path, strat_index, host, port, username, password)
        self.verifier.result.connect(self._handle_verifier_result)
        self.verifier.start()
        QMessageBox.information(self, "Проверка", "Запуск проверки стратегии. Ожидание 60 сек.")

    def _handle_verifier_result(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, "Проверка стратегии", message)
        else:
            QMessageBox.warning(self, "Проверка стратегии", message)

    def verify_all_strategies(self):
        """Запуск AllStrategyVerifier для последовательной проверки каждой стратегии."""
        host = self.upstream_host_edit.text().strip()
        port_text = self.upstream_port_edit.text().strip()
        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "Неправильный порт", "Порт должен быть числом.")
            return
        username = self.username_edit.text()
        password = self.password_edit.text()
        script_path = self.base_dir / "socks5_layer.py"
        self.all_verifier = AllStrategyVerifier(script_path, self.strategies, host, port, username, password)
        self.all_verifier.per_result.connect(self._handle_all_result)
        self.all_verifier.finished.connect(self._handle_all_finished)
        self.all_verifier.start()
        self.log_edit.append("Запуск массовой проверки стратегий...")

    def _handle_all_result(self, idx: int, success: bool, message: str):
        prefix = f"[Стратегия {idx}] "
        self.log_edit.append(prefix + message)
        if not success:
            self.log_edit.append(prefix + "⚠️ Ошибка.")

    def _handle_all_finished(self):
        self.log_edit.append("Массовая проверка завершена.")

    # -------------------------------------------------------------------
    def close_window(self):
        # Скрыть окно, но оставить фоновый процесс работать (если он есть)
        self.save_current_config()
        self.hide()
        QMessageBox.information(self, "Окно закрыто", "GUI закрыто, слой продолжает работу в фоне.")

    # -------------------------------------------------------------------
    def closeEvent(self, event):
        self.save_current_config()
        # При реальном выходе – спросить, нужно ли остановить фоновый процесс
        if hasattr(self, "running_pid"):
            reply = QMessageBox.question(
                self, T("Выход", "Exit"), "Слой всё ещё работает. Остановить его перед выходом?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stop_layer()
        event.accept()

# ---------------------------------------------------------------------------
DARK_THEME_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #f1f1f1;
    font-family: Segoe UI, sans-serif;
    font-size: 10pt;
}
QLineEdit, QComboBox, QTextEdit {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
}
QPushButton {
    background-color: #4a4a4a;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px;
}
QPushButton:hover {
    background-color: #5a5a5a;
}
QPushButton:pressed {
    background-color: #3a3a3a;
}
QPushButton:disabled {
    background-color: #333333;
    color: #777777;
}
QLabel {
    color: #dddddd;
}
"""

def handle_cli_args():
    # If --stop is provided, kill the existing process and exit
    if "--stop" in sys.argv:
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text("utf-8").strip())
                if is_process_running(pid):
                    if os.name == 'nt':
                        subprocess.call(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        os.kill(pid, 9)
                PID_FILE.unlink()
            except Exception:
                pass
        sys.exit(0)

    # If --silent is provided
    if "--silent" in sys.argv:
        # Check if already running
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text("utf-8").strip())
                if is_process_running(pid):
                    # Already running -> open window!
                    return
            except Exception:
                pass
                
        # Not running. Load config and start silently if valid
        config = load_config()
        if "host" in config and "port" in config and "strat" in config:
            script_path = Path(__file__).parent / "socks5_layer.py"
            cmd = [sys.executable, str(script_path),
                   "--strategy-index", str(config["strat"]),
                   "--upstream-host", config["host"],
                   "--upstream-port", str(config["port"])]
            if config.get("username"):
                cmd.extend(["--username", config["username"]])
            if config.get("password"):
                cmd.extend(["--password", config["password"]])
            
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            try:
                process = subprocess.Popen(cmd, creationflags=creationflags)
                PID_FILE.write_text(str(process.pid), "utf-8")
            except Exception:
                pass
            sys.exit(0)
        # If no config, it will just drop through and open the window

if __name__ == "__main__":
    handle_cli_args()
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME_STYLESHEET)
    window = Socks5Gui()
    window.show()
    sys.exit(app.exec_())
