import sys
import math
import os
import platform
import subprocess
from PyQt5.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStackedWidget, QScrollArea, QFrame, QComboBox, QCheckBox, QMessageBox,
    QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush

class PowerButton(QPushButton):
    """
    Circular connect button styled according to Windows 11 Fluent Design.
    Features an authentic IEC 5009 power symbol: an open circular arc with
    the gap strictly at 12 o'clock and a centered vertical line.
    No emojis used.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 130)
        self.setCursor(Qt.PointingHandCursor)
        self._state = "off"  # "off", "starting", "on"
        self._hover = False
        self._anim_phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_anim_step)

    def set_state(self, state):
        if self._state == state:
            return
        self._state = state
        if state == "starting":
            if not self._timer.isActive():
                self._timer.start(40)
        else:
            if self._timer.isActive():
                self._timer.stop()
        self.update()

    def _on_anim_step(self):
        self._anim_phase += 0.09
        if self._anim_phase > 6.283:
            self._anim_phase = 0.0
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        radius = 55.0

        if self._state == "on":
            bg_color = QColor("#107C41") if not self._hover else QColor("#138747")
            ring_color = QColor("#0F7B0F")
            icon_color = QColor("#FFFFFF")
            glow_color = QColor(16, 124, 65, 50 if not self._hover else 80)
        elif self._state == "starting":
            pulse = (math.sin(self._anim_phase) + 1.0) / 2.0
            bg_color = QColor("#CA5010")
            ring_color = QColor("#E9641D")
            icon_color = QColor("#FFFFFF")
            glow_color = QColor(202, 80, 16, int(35 + 55 * pulse))
        else:  # "off"
            bg_color = QColor("#2b2b2b") if not self._hover else QColor("#353535")
            ring_color = QColor("#3c3c3c")
            icon_color = QColor("#cccccc")
            glow_color = QColor(0, 0, 0, 40 if not self._hover else 65)

        # Ambient drop shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(QPointF(cx, cy), radius + 5, radius + 5)

        # Main round button surface
        painter.setPen(QPen(ring_color, 4))
        painter.setBrush(QBrush(bg_color))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Authentic Power Symbol (IEC 5009):
        # Open arc at top (12 o'clock, 90 deg). Gap is from 60 to 120 deg.
        # Starts at 120 deg and sweeps counter-clockwise 300 deg to 60 deg.
        painter.setPen(QPen(icon_color, 5.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)

        r_icon = 20.0
        arc_rect = QRectF(cx - r_icon, cy - r_icon, r_icon * 2, r_icon * 2)
        painter.drawArc(arc_rect, int(120 * 16), int(300 * 16))
        # Centered vertical stroke passing through the open gap into center
        painter.drawLine(QPointF(cx, cy - r_icon - 4), QPointF(cx, cy - 1))


class Win11LinearProgress(QWidget):
    """
    Windows 11 styled indeterminate linear progress indicator (3px height)
    with smooth Fluent accent blue animation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self._pos = -0.35
        self._running = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self.hide()

    def start(self):
        self._running = True
        self.show()
        if not self._timer.isActive():
            self._timer.start(16)

    def stop(self):
        self._running = False
        self._timer.stop()
        self.hide()

    def _step(self):
        self._pos += 0.02
        if self._pos > 1.35:
            self._pos = -0.35
        self.update()

    def paintEvent(self, event):
        if not self._running:
            return
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor("#202020"))
        bar_len = w * 0.35
        x = int(self._pos * w)
        painter.fillRect(x, 0, int(bar_len), h, QColor("#0078D4"))


class CardRow(QFrame):
    """
    Windows 11 Fluent Card with 8px corner radius, #2b2b2b surface,
    and subtle #383838 borders. Guaranteed strictly dark background.
    """
    def __init__(self, title, description=None, control_widget=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            CardRow {
                background-color: #2b2b2b;
                border: 1px solid #383838;
                border-radius: 8px;
            }
            CardRow:hover {
                background-color: #323232;
                border-color: #484848;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        text_layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setFont(QFont("Segoe UI Variable Text", 8))
            desc_label.setStyleSheet("color: #9d9d9d; background: transparent;")
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        if control_widget:
            if type(control_widget) is QWidget or isinstance(control_widget, QFrame):
                control_widget.setStyleSheet("background: transparent; border: none;")
            ctrl_layout = QVBoxLayout()
            ctrl_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            ctrl_layout.addWidget(control_widget)
            layout.addLayout(ctrl_layout, 0)


class MainWindow(QMainWindow):
    """
    Spacious Desktop GUI for ToInet-MAX with Windows 11 Fluent Design theme,
    individual settings per provider, Telegram integration (including Gatik),
    rich tray-menu parameters integration, and strictly dark color palette.
    """
    def __init__(self, main_module):
        super().__init__()
        self.main_module = main_module
        self.setWindowTitle("ToInet-MAX")
        # Spacious window size: 620 x 700 px to comfortably fit all provider controls
        self.resize(560, 610)
        self.setMinimumSize(500, 550)

        # Strictly dark background across all widgets, views, and viewports
        self.setStyleSheet("""
            QMainWindow {
                background-color: #202020;
            }
            QWidget {
                background-color: transparent;
                color: #FFFFFF;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', Arial, sans-serif;
            }
            QStackedWidget {
                background-color: #202020;
            }
            QScrollArea {
                border: none;
                background-color: #202020;
            }
            QScrollBar:vertical {
                width: 6px;
                background: #202020;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #484848;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #606060;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Windows 11 DWM integration: Dark mode, titlebar color (#202020), and rounded corners
        if platform.system() == "Windows":
            try:
                import ctypes
                hwnd = int(self.winId())
                val_true = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val_true), ctypes.sizeof(val_true))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val_true), ctypes.sizeof(val_true))
                caption_color = ctypes.c_int(0x00202020)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
                corner_pref = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
            except Exception:
                pass

        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        self.connect_view = QWidget()
        self.provider_view = QWidget()
        self.settings_view = QWidget()

        self.stacked.addWidget(self.connect_view)
        self.stacked.addWidget(self.provider_view)
        self.stacked.addWidget(self.settings_view)

        self.build_connect_view()
        self.build_provider_view()
        self.build_settings_view()

        # Connect EVPN signals if available
        if hasattr(self.main_module, 'evpn_mgr'):
            try:
                self.main_module.evpn_mgr.status_changed.connect(self.set_status)
                self.main_module.evpn_mgr.error_occurred.connect(self.show_error)
            except Exception:
                pass

        self.update_ui_state()

    # -------------------------------------------------------------------------
    # Screen 0: Main Connect Screen (Windows 11 Fluent style, no emojis)
    # -------------------------------------------------------------------------
    def build_connect_view(self):
        layout = QVBoxLayout(self.connect_view)
        layout.setContentsMargins(24, 16, 24, 0)
        layout.setSpacing(0)

        # Top Title
        self.title_label = QLabel("ToInet-MAX")
        self.title_label.setFont(QFont("Segoe UI Variable Text", 22, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(self.title_label)

        layout.addSpacing(8)

        # Status Pill Badge (no emojis)
        chip_layout = QHBoxLayout()
        chip_layout.setAlignment(Qt.AlignCenter)
        self.status_chip = QLabel("Отключено")
        self.status_chip.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        self.status_chip.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                color: #9d9d9d;
                border: 1px solid #383838;
                border-radius: 12px;
                padding: 4px 16px;
            }
        """)
        chip_layout.addWidget(self.status_chip)
        layout.addLayout(chip_layout)

        layout.addStretch(1)

        # Center Power Button
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        self.power_btn = PowerButton()
        self.power_btn.clicked.connect(self.toggle_vpn)
        btn_layout.addWidget(self.power_btn)
        layout.addLayout(btn_layout)

        layout.addSpacing(8)

        # Status Description Label
        self.status_desc = QLabel("Нажмите для подключения")
        self.status_desc.setFont(QFont("Segoe UI Variable Text", 11))
        self.status_desc.setAlignment(Qt.AlignCenter)
        self.status_desc.setStyleSheet("color: #9d9d9d; background: transparent;")
        layout.addWidget(self.status_desc)

        layout.addSpacing(8)

        # Quick Switch Buttons on Main Screen (Tor circuit / EVPN server when active)
        next_layout = QHBoxLayout()
        next_layout.setAlignment(Qt.AlignCenter)
        next_layout.setSpacing(10)

        self.tor_switch_btn = QPushButton(T("Сменить узел Tor", "New Tor Circuit", "Changer de circuit Tor"))
        self.tor_switch_btn.setFixedHeight(34)
        self.tor_switch_btn.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        self.tor_switch_btn.setCursor(Qt.PointingHandCursor)
        self.tor_switch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #383838;
                border-radius: 6px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #0078D4;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        self.tor_switch_btn.clicked.connect(lambda: getattr(self.main_module, 'tor_manager', None) and self.main_module.tor_manager.new_circuit(self))
        self.tor_switch_btn.hide()
        next_layout.addWidget(self.tor_switch_btn)

        self.evpn_switch_btn = QPushButton(T("Сменить сервер EVPN", "Switch EVPN Server", "Changer de serveur EVPN"))
        self.evpn_switch_btn.setFixedHeight(34)
        self.evpn_switch_btn.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        self.evpn_switch_btn.setCursor(Qt.PointingHandCursor)
        self.evpn_switch_btn.setStyleSheet(self.tor_switch_btn.styleSheet())
        self.evpn_switch_btn.clicked.connect(self.next_server)
        self.evpn_switch_btn.hide()
        next_layout.addWidget(self.evpn_switch_btn)

        self.next_btn = self.evpn_switch_btn  # for backward compatibility
        layout.addLayout(next_layout)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Segoe UI Variable Text", 9))
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #FF5555; background: transparent;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        layout.addStretch(1)

        # Bottom Action Buttons in Windows 11 style (no emojis):
        # [ VPN Провайдер ] and [ Настройки ]
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setSpacing(16)

        win11_tonal_btn = """
            QPushButton {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #383838;
                border-radius: 8px;
                font-family: 'Segoe UI Variable Text', 'Segoe UI';
                font-size: 13px;
                font-weight: 600;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #4c4c4c;
            }
            QPushButton:pressed {
                background-color: #222222;
                border-color: #333333;
            }
        """

        self.btn_provider = QPushButton(T("VPN Провайдер", "VPN Providers", "Fournisseurs VPN"))
        self.btn_provider.setFixedHeight(38)
        self.btn_provider.setCursor(Qt.PointingHandCursor)
        self.btn_provider.setStyleSheet(win11_tonal_btn)
        self.btn_provider.clicked.connect(self.show_provider_view)

        self.btn_settings = QPushButton(T("Настройки", "Settings", "Paramètres"))
        self.btn_settings.setFixedHeight(38)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setStyleSheet(win11_tonal_btn)
        self.btn_settings.clicked.connect(self.show_settings_view)

        bottom_buttons_layout.addWidget(self.btn_provider, 1)
        bottom_buttons_layout.addWidget(self.btn_settings, 1)
        layout.addLayout(bottom_buttons_layout)

        layout.addSpacing(6)

        # Win11 Linear Progress Bar along bottom edge
        self.progress_bar = Win11LinearProgress()
        layout.addWidget(self.progress_bar)

    # -------------------------------------------------------------------------
    # Screen 1: VPN Provider Screen (Individual settings per provider)
    # -------------------------------------------------------------------------
    def build_provider_view(self):
        T = self.main_module.T
        m = self.main_module

        layout = QVBoxLayout(self.provider_view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header with back button (no emoji)
        header = QHBoxLayout()
        back_btn = QPushButton("←")
        back_btn.setFixedSize(32, 32)
        back_btn.setFont(QFont("Segoe UI Variable Text", 14, QFont.Bold))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        back_btn.clicked.connect(self.show_connect_view)

        header_title = QLabel(T("VPN Провайдер", "VPN Provider"))
        header_title.setFont(QFont("Segoe UI Variable Text", 15, QFont.Bold))
        header_title.setStyleSheet("color: #FFFFFF; background: transparent;")

        header.addWidget(back_btn)
        header.addWidget(header_title)
        header.addStretch()
        layout.addLayout(header)

        # Scroll area with strictly dark viewport
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #202020;")
        scroll.viewport().setStyleSheet("background-color: #202020; border: none;")

        content = QWidget()
        content.setStyleSheet("background-color: #202020;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(2, 2, 8, 2)
        c_layout.setSpacing(12)

        # Card 1: Routing Mode Selection
        mode_card = QFrame()
        mode_card.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #383838;
                border-radius: 8px;
                padding: 8px 10px;
            }
        """)
        mc_layout = QVBoxLayout(mode_card)
        mc_layout.setSpacing(8)

        mc_title = QLabel(T("Режим маршрутизации", "Routing Mode"))
        mc_title.setFont(QFont("Segoe UI Variable Text", 11, QFont.Bold))
        mc_title.setStyleSheet("border: none; color: #FFFFFF; background: transparent;")
        mc_layout.addWidget(mc_title)

        modes_btn_layout = QHBoxLayout()
        modes_btn_layout.setSpacing(8)

        self.mode_chips = {}
        for m_name in ["EMPTY", "INETCPL", "TUN", "EVPN"]:
            btn = QPushButton(m_name)
            btn.setFixedHeight(32)
            btn.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            def _make_mode_cb(m_val):
                return lambda: self.select_mode(m_val.lower())
            btn.clicked.connect(_make_mode_cb(m_name))
            self.mode_chips[m_name.lower()] = btn
            modes_btn_layout.addWidget(btn)

        mc_layout.addLayout(modes_btn_layout)

        self.mode_desc_label = QLabel("")
        self.mode_desc_label.setFont(QFont("Segoe UI Variable Text", 8))
        self.mode_desc_label.setStyleSheet("color: #9d9d9d; border: none; background: transparent;")
        self.mode_desc_label.setWordWrap(True)
        mc_layout.addWidget(self.mode_desc_label)

        c_layout.addWidget(mode_card)

        # Helper for provider action buttons
        def make_prov_btn(text, callback, is_primary=False, is_accent=False):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            if is_primary:
                bg = "#005FB8"
                h_bg = "#0078D4"
            elif is_accent:
                bg = "#107C41"
                h_bg = "#138747"
            else:
                bg = "#2d2d2d"
                h_bg = "#383838"

            b.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: #FFFFFF;
                    border: 1px solid #3c3c3c;
                    border-radius: 6px;
                    padding: 3px 9px;
                    font-size: 10.5px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {h_bg};
                    border-color: #484848;
                }}
                QPushButton:pressed {{
                    background-color: #222222;
                }}
            """)
            b.clicked.connect(callback)
            return b

        # Helper to create miniature 26x26 control buttons copying the tray menu pattern (↻ and ▶/■)
        def make_mini_btn(symbol, tooltip, callback):
            b = QPushButton(symbol)
            b.setToolTip(tooltip)
            b.setFixedSize(26, 26)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    font-size: 15px;
                    font-weight: bold;
                    color: #FFFFFF;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.22);
                }
            """)
            b.clicked.connect(callback)
            return b

        # Helper to create a compact, modern provider card with miniature control buttons in the top row
        def create_provider_card(title, port_desc, description, actions, mini_restart_btn=None, mini_toggle_btn=None):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #2b2b2b;
                    border: 1px solid #383838;
                    border-radius: 8px;
                    padding: 8px 10px;
                }
                QFrame:hover {
                    border-color: #484848;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(5)

            top_row = QHBoxLayout()
            lbl_title = QLabel(title)
            lbl_title.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
            lbl_title.setStyleSheet("border: none; color: #FFFFFF; background: transparent;")

            lbl_port = QLabel(port_desc)
            lbl_port.setFont(QFont("Segoe UI Variable Text", 9))
            lbl_port.setStyleSheet("border: none; color: #0078D4; background: transparent; font-weight: bold;")

            top_row.addWidget(lbl_title)
            top_row.addWidget(lbl_port)
            top_row.addStretch()

            if mini_restart_btn:
                top_row.addWidget(mini_restart_btn)
            if mini_toggle_btn:
                top_row.addWidget(mini_toggle_btn)

            card_layout.addLayout(top_row)

            lbl_desc = QLabel(description)
            lbl_desc.setFont(QFont("Segoe UI Variable Text", 8))
            lbl_desc.setStyleSheet("border: none; color: #9d9d9d; background: transparent;")
            lbl_desc.setWordWrap(True)
            card_layout.addWidget(lbl_desc)

            if actions:
                act_row = QHBoxLayout()
                act_row.setSpacing(6)
                for btn in actions:
                    act_row.addWidget(btn)
                act_row.addStretch()
                card_layout.addLayout(act_row)

            return card

        # Section Header: Providers
        prov_header = QLabel(T("Провайдеры и параметры шлюзов", "Providers & Gateway Configurations"))
        prov_header.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        prov_header.setStyleSheet("color: #9d9d9d; margin-top: 6px; background: transparent;")
        c_layout.addWidget(prov_header)

        # 1. ByeDPI
        bd_select_btn = make_prov_btn(T("Выбрать шлюзом", "Select Gateway"), lambda: self.select_gateway("byedpi"), is_primary=True)
        def open_bd_tester():
            subprocess.Popen([sys.executable, "ui/byedpi_tester_gui.pyw"])
        bd_test_btn = make_prov_btn(T("Тестер стратегий", "Strategy Tester"), open_bd_tester)
        def toggle_pip():
            cur = m.config.get("byedpi_pip_enabled", False)
            m.config["byedpi_pip_enabled"] = not cur
            m.config_manager.save_config(m.config)
            self.update_ui_state()
        bd_pip_btn = make_prov_btn("Pip (1781)", toggle_pip)
        def add_bd_tg():
            from managers import system_utils
            system_utils.add_proxy_to_telegram(1780)
        bd_tg_btn = make_prov_btn("В Telegram (1780)", add_bd_tg)

        def restart_bd():
            if getattr(m, 'byedpi_manager', None):
                m.byedpi_manager.stop()
                import time; time.sleep(1)
                m.byedpi_manager.start()
            self.update_ui_state()

        self.bd_restart_btn = make_mini_btn("↻", T("Перезапустить", "Restart", "Redemarrer"), restart_bd)
        self.bd_toggle_btn = make_mini_btn("▶", T("Запустить", "Start", "Demarrer"), lambda: (m.toggle_byedpi(), self.update_ui_state()))

        c_layout.addWidget(create_provider_card(
            "ByeDPI",
            "Порт 1780",
            T("Локальный обход блокировок DPI (YouTube, Discord и веб-сайты) без нагрузки на сервер.",
              "Local DPI packet bypass (YouTube, Discord, streaming) without remote server load."),
            [bd_select_btn, bd_test_btn, bd_pip_btn, bd_tg_btn],
            self.bd_restart_btn,
            self.bd_toggle_btn
        ))

        # 2. Tor
        tor_select_btn = make_prov_btn(T("Выбрать шлюзом", "Select Gateway"), lambda: self.select_gateway("tor"), is_primary=True)
        def open_tor_bridges():
            subprocess.Popen([sys.executable, "ui/edit_bridges.pyw"])
        tor_bridges_btn = make_prov_btn(T("Редактор мостов", "Bridges Config"), open_tor_bridges)
        tor_newnym_btn = make_prov_btn(T("Сменить IP (Newnym)", "New Circuit"), lambda: getattr(m, 'tor_manager', None) and m.tor_manager.new_circuit())
        def add_tor_tg():
            from managers import system_utils
            system_utils.add_proxy_to_telegram(9853)
        tor_tg_btn = make_prov_btn("В Telegram (9853)", add_tor_tg)

        def tor_restart_handler():
            mods = QApplication.keyboardModifiers()
            if (mods & Qt.ControlModifier) and hasattr(m, 'tor_manager'):
                m.tor_manager.new_circuit()
            elif hasattr(m, 'tor_manager'):
                m.tor_manager.restart()
            self.update_ui_state()

        self.tor_restart_btn = make_mini_btn("↻", T("Перезапуск (Ctrl + Клик = Новая цепь)", "Restart (Ctrl + Click = New Circuit)"), tor_restart_handler)
        self.tor_toggle_btn = make_mini_btn("▶", T("Запустить", "Start", "Demarrer"), lambda: (m.toggle_tor(), self.update_ui_state()))

        c_layout.addWidget(create_provider_card(
            "Tor",
            "Порт 9853 / HTTP 9854",
            T("Анонимная многоузловая луковая сеть. Поддержка мостов obfs4, snowflake, webtunnel.",
              "Anonymous multi-hop onion routing network with obfs4, snowflake, and webtunnel bridge support."),
            [tor_select_btn, tor_bridges_btn, tor_newnym_btn, tor_tg_btn],
            self.tor_restart_btn,
            self.tor_toggle_btn
        ))

        # 3. Opera Proxy
        opera_select_btn = make_prov_btn(T("Выбрать шлюзом", "Select Gateway"), lambda: self.select_gateway("opera"), is_primary=True)
        opera_cfg_btn = make_prov_btn(T("Настройки региона (EU/AM/AS)", "Region Options"), lambda: getattr(m, 'opera_mgr', None) and m.opera_mgr.open_settings())

        def restart_opera():
            if getattr(m, 'opera_mgr', None):
                m.opera_mgr.stop()
                import time; time.sleep(1)
                m.opera_mgr.start()
            self.update_ui_state()

        self.opera_restart_btn = make_mini_btn("↻", T("Перезапустить", "Restart", "Redemarrer"), restart_opera)
        self.opera_toggle_btn = make_mini_btn("▶", T("Запустить", "Start", "Demarrer"), lambda: (m.toggle_opera(), self.update_ui_state()))

        c_layout.addWidget(create_provider_card(
            "Opera Proxy",
            "Порт 1785",
            T("Высокоскоростной туннель через европейские, американские и азиатские серверы Opera.",
              "High-speed proxy tunnel through European, American, and Asian Opera infrastructure."),
            [opera_select_btn, opera_cfg_btn],
            self.opera_restart_btn,
            self.opera_toggle_btn
        ))

        # 4. SVPN / SSH Tunnel
        ssh_select_btn = make_prov_btn(T("Выбрать шлюзом", "Select Gateway"), lambda: self.select_gateway("ssh"), is_primary=True)
        ssh_cfg_btn = make_prov_btn(T("Настройки сервера VPS", "VPS Credentials"), lambda: getattr(m, 'ssh_mgr', None) and m.ssh_mgr.open_settings())
        def add_ssh_tg():
            from managers import system_utils
            ssh_p = int(m.config.get("ssh_socks_port", 1770))
            system_utils.add_proxy_to_telegram(ssh_p)
        ssh_p_str = str(m.config.get("ssh_socks_port", 1770))
        ssh_tg_btn = make_prov_btn(f"В Telegram ({ssh_p_str})", add_ssh_tg)

        def restart_ssh():
            if getattr(m, 'ssh_mgr', None):
                m.ssh_mgr.restart()
            self.update_ui_state()

        self.ssh_restart_btn = make_mini_btn("↻", T("Перезапустить", "Restart", "Redemarrer"), restart_ssh)
        self.ssh_toggle_btn = make_mini_btn("▶", T("Запустить", "Start", "Demarrer"), lambda: (m.toggle_ssh(), self.update_ui_state()))

        c_layout.addWidget(create_provider_card(
            "SVPN / SSH Туннель",
            f"Порт {ssh_p_str}",
            T("Высокоскоростной C++ SOCKS5 туннель к вашему личному VPS с безопасным хранением учетных данных.",
              "High-speed C++ SOCKS5 tunnel to your personal VPS with secure password management."),
            [ssh_select_btn, ssh_cfg_btn, ssh_tg_btn],
            self.ssh_restart_btn,
            self.ssh_toggle_btn
        ))

        # 5. VLESS / EVPN (hidden when mode is not evpn)
        vless_select_btn = make_prov_btn(T("Выбрать шлюзом", "Select Gateway"), lambda: self.select_gateway("vless"), is_primary=True)
        vless_cfg_btn = make_prov_btn(T("Настройки VLESS", "VLESS Settings"), lambda: getattr(m, 'vless_mgr', None) and m.vless_mgr.open_settings())

        def restart_vless():
            if getattr(m, 'vless_mgr', None):
                m.vless_mgr.stop()
                import time; time.sleep(1)
                m.vless_mgr.start()
            elif getattr(m, 'evpn_mgr', None):
                m.evpn_mgr.stop()
                import time; time.sleep(1)
                m.evpn_mgr.start()
            self.update_ui_state()

        self.vless_restart_btn = make_mini_btn("↻", T("Перезапустить", "Restart", "Redemarrer"), restart_vless)
        self.vless_toggle_btn = make_mini_btn("▶", T("Запустить", "Start", "Demarrer"), lambda: (m.toggle_vless(), self.update_ui_state()))

        self.vless_card = create_provider_card(
            "VLESS / EVPN",
            "Порт 1790",
            T("Ядро Sing-box: VLESS Reality, ShadowTLS, Trojan и динамическая ротация серверов.",
              "Sing-box core with VLESS Reality, ShadowTLS, Trojan, and subscription server rotation."),
            [vless_select_btn, vless_cfg_btn],
            self.vless_restart_btn,
            self.vless_toggle_btn
        )
        c_layout.addWidget(self.vless_card)

        # Store all gateway select buttons for mode-dependent visibility (hidden in empty mode)
        self.gateway_buttons = [bd_select_btn, tor_select_btn, opera_select_btn, ssh_select_btn, vless_select_btn]

        # 6. Telegram WebSocket Proxy (TGWS)
        def open_tgws_test():
            subprocess.Popen([sys.executable, "ui/tgws_tester_gui.pyw"])
        tgws_test_btn = make_prov_btn(T("Тестер TGWS", "TGWS Tester"), open_tgws_test)
        def add_tgws_socks():
            from managers import system_utils
            system_utils.add_proxy_to_telegram(int(m.config.get("tgws_port", 1480)))
        def add_tgws_mtproto():
            from managers import system_utils
            system_utils.add_mtproto_to_telegram(int(m.config.get("tgws_port", 1480)),
                                                 m.config.get("tgws_secret", "0"*32),
                                                 m.config.get("tgws_fake_tls", ""))
        tgws_s_btn = make_prov_btn("В Telegram (SOCKS5)", add_tgws_socks)
        tgws_m_btn = make_prov_btn("В Telegram (MTProto)", add_tgws_mtproto)

        def restart_tgws():
            if getattr(m, 'tgws_mgr', None):
                m.tgws_mgr.stop()
                import time; time.sleep(1)
                m.tgws_mgr.start()
            self.update_ui_state()

        self.tgws_restart_btn = make_mini_btn("↻", T("Перезапустить", "Restart", "Redemarrer"), restart_tgws)
        self.tgws_toggle_btn = make_mini_btn("▶", T("Запустить", "Start", "Demarrer"), lambda: (m.toggle_tgws(), self.update_ui_state()))

        c_layout.addWidget(create_provider_card(
            "Telegram WS Proxy (TGWS)",
            "Порт 1480",
            T("Мультиплексированный SOCKS5 и MTProto прокси с маскировкой Fake TLS для Telegram.",
              "Multiplexed SOCKS5 and MTProto proxy with Fake TLS obfuscation for Telegram Desktop."),
            [tgws_test_btn, tgws_s_btn, tgws_m_btn],
            self.tgws_restart_btn,
            self.tgws_toggle_btn
        ))

        # 7. Gatik Router
        def add_gatik_tg():
            from managers import system_utils
            system_utils.add_proxy_to_telegram(1777)
        gatik_tg_btn = make_prov_btn(T("Добавить Gatik в Telegram", "Add Gatik to Telegram"), add_gatik_tg, is_primary=True)

        self.gatik_restart_btn = make_mini_btn("↻", T("Перезапуск Gatik", "Restart Gatik"), lambda: (getattr(m, 'tgws_mgr', None) and m.tgws_mgr.start(), self.update_ui_state()))

        c_layout.addWidget(create_provider_card(
            "Умный шлюз Gatik",
            "Порт 1777",
            T("Нативный C++ балансировщик и акселератор для Telegram, оптимизирующий сетевые маршруты.",
              "Native C++ smart router and balancer for accelerating Telegram connections."),
            [gatik_tg_btn],
            self.gatik_restart_btn,
            None
        ))

        # Section: Split Tunneling & Proxifier
        sc_header = QLabel(T("Системный перехват и проксификация", "System Redirection & Proxification"))
        sc_header.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sc_header.setStyleSheet("color: #9d9d9d; margin-top: 8px; background: transparent;")
        c_layout.addWidget(sc_header)

        proxi_btn = make_prov_btn(T("Путь к проксификатору", "Path to Proxifier", "Chemin vers Proxifier"),
                                  lambda: getattr(m, 'mode_mgr', None) and m.mode_mgr.open_proxifier_config())
        tun_btn = make_prov_btn(T("Параметры TUN (Sing-box) →", "Sing-box TUN Config →", "Paramètres TUN (Sing-box) →"),
                                lambda: getattr(m, 'mode_mgr', None) and m.mode_mgr.open_advanced_tun_config())
        rules_btn = make_prov_btn(T("Редактировать правила", "Edit Rules", "Modifier les règles"),
                                  self.open_rules_editor)

        self.prox_restart_btn = make_mini_btn("↻", T("Перезапустить Proxifier", "Restart Proxifier"), lambda: (getattr(m, 'mode_mgr', None) and m.mode_mgr.restart_proxifier(), self.update_ui_state()))
        self.prox_toggle_btn = make_mini_btn("▶", T("Запустить Proxifier", "Start Proxifier"), lambda: (m.toggle_proxifier(), self.update_ui_state()))

        c_layout.addWidget(create_provider_card(
            T("Системный перехват и проксификатор", "System Redirection & Proxifier", "Redirection système et Proxifier"),
            "",
            T("Маршрутизация приложений и хостов через Toinet.ppx с гибкой фильтрацией.",
              "Application and hostname routing via Toinet.ppx with flexible filtering rules."),
            [proxi_btn, tun_btn, rules_btn],
            self.prox_restart_btn,
            self.prox_toggle_btn
        ))

        c_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    # -------------------------------------------------------------------------
    # Screen 2: Settings Screen (Rich parameters from tray menu, strictly dark)
    # -------------------------------------------------------------------------
    def build_settings_view(self):
        T = self.main_module.T
        m = self.main_module

        layout = QVBoxLayout(self.settings_view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header with back button (no emoji)
        header = QHBoxLayout()
        back_btn = QPushButton("←")
        back_btn.setFixedSize(32, 32)
        back_btn.setFont(QFont("Segoe UI Variable Text", 14, QFont.Bold))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        back_btn.clicked.connect(self.show_connect_view)

        header_title = QLabel(T("Настройки", "Settings"))
        header_title.setFont(QFont("Segoe UI Variable Text", 15, QFont.Bold))
        header_title.setStyleSheet("color: #FFFFFF; background: transparent;")

        header.addWidget(back_btn)
        header.addWidget(header_title)
        header.addStretch()
        layout.addLayout(header)

        # Scroll area with strictly dark viewport
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #202020;")
        scroll.viewport().setStyleSheet("background-color: #202020; border: none;")

        content = QWidget()
        content.setStyleSheet("background-color: #202020;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(2, 2, 8, 2)
        c_layout.setSpacing(10)

        def make_action_btn(text, callback, is_primary=False, is_danger=False):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            if is_danger:
                bg = "#C42B1C"
                h_bg = "#D83B01"
            elif is_primary:
                bg = "#005FB8"
                h_bg = "#0078D4"
            else:
                bg = "#2d2d2d"
                h_bg = "#383838"

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: #FFFFFF;
                    border: 1px solid #3c3c3c;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {h_bg};
                    border-color: #484848;
                }}
                QPushButton:pressed {{
                    background-color: #222222;
                }}
            """)
            btn.clicked.connect(callback)
            return btn

        # Group 1: Diagnostics & Logs (from tray menu)
        sec_label_diag = QLabel(T("Журнал и диагностика", "Logs & Diagnostics"))
        sec_label_diag.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sec_label_diag.setStyleSheet("color: #9d9d9d; margin-top: 4px; background: transparent;")
        c_layout.addWidget(sec_label_diag)

        log_btn = make_action_btn(T("Показать логи", "Show Logs"), lambda: m.app_log_window.show() if getattr(m, 'app_log_window', None) else None)
        c_layout.addWidget(CardRow(T("Журнал событий приложения", "Application Logs"),
                                   T("Консольный вывод, отладка процессов и статус сетевых служб.",
                                     "Process console output, debugging, and service status events."),
                                   log_btn))

        # Group 2: Autostart (from tray menu)
        sec_label_ast = QLabel(T("Параметры автозапуска", "Autostart Options"))
        sec_label_ast.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sec_label_ast.setStyleSheet("color: #9d9d9d; margin-top: 8px; background: transparent;")
        c_layout.addWidget(sec_label_ast)

        def open_ast_gui():
            subprocess.Popen([sys.executable, os.path.join(m.CURRENT_DIR, "ui/autostart_settings.pyw")],
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        ast_gui_btn = make_action_btn(T("Настроить службы", "Configure Services"), open_ast_gui)
        c_layout.addWidget(CardRow(T("Выбор служб для автозапуска", "Autostart Services Selection"),
                                   T("Выбор конкретных модулей (ByeDPI, Tor, SSH, Opera, Proxifier) при старте.",
                                     "Select individual services to boot on program startup."),
                                   ast_gui_btn))

        # Group 3: Pip (PyPI) Proxying (from tray menu)
        sec_label_pip = QLabel(T("Проксирование pip (PyPI)", "pip (PyPI) Proxying"))
        sec_label_pip.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sec_label_pip.setStyleSheet("color: #9d9d9d; margin-top: 8px; background: transparent;")
        c_layout.addWidget(sec_label_pip)

        cb_style = """
            QCheckBox { background: transparent; }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #555555;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover { border-color: #777777; }
            QCheckBox::indicator:checked { background-color: #005FB8; border-color: #005FB8; }
        """

        pip_cb = QCheckBox()
        pip_cb.setChecked(m.config.get("byedpi_pip_enabled", False))
        pip_cb.setCursor(Qt.PointingHandCursor)
        pip_cb.setStyleSheet(cb_style)
        def on_pip_change():
            m.config["byedpi_pip_enabled"] = pip_cb.isChecked()
            m.config_manager.save_config(m.config)
            if hasattr(m, 'update_menu'): m.update_menu()
        pip_cb.clicked.connect(on_pip_change)
        c_layout.addWidget(CardRow(T("Проксировать pip через ByeDPI (1781)", "Route pip through ByeDPI (1781)"),
                                   T("Ускоряет и разблокирует установку Python-пакетов через PyPI.",
                                     "Accelerate and unblock Python package installations from PyPI."),
                                   pip_cb))

        pip_tor_cb = QCheckBox()
        pip_tor_cb.setChecked(m.config.get("byedpi_pip_use_tor", False))
        pip_tor_cb.setCursor(Qt.PointingHandCursor)
        pip_tor_cb.setStyleSheet(cb_style)
        def on_pip_tor_change():
            m.config["byedpi_pip_use_tor"] = pip_tor_cb.isChecked()
            m.config_manager.save_config(m.config)
            if hasattr(m, 'update_menu'): m.update_menu()
        pip_tor_cb.clicked.connect(on_pip_tor_change)
        c_layout.addWidget(CardRow(T("Использовать Tor вместо ByeDPI для pip", "Use Tor instead of ByeDPI for pip"),
                                   T("Направляет установку пакетов pip через порт луковой сети 9853.",
                                     "Route pip package downloads through local Tor SOCKS port 9853."),
                                   pip_tor_cb))

        # Group 4: System DNS (Corrected addresses: Comms is 83.220.169.155, 212.109.195.93)
        sec_label_dns = QLabel(T("Системный DNS (требуются права администратора)", "System DNS (Admin rights required)"))
        sec_label_dns.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sec_label_dns.setStyleSheet("color: #9d9d9d; margin-top: 8px; background: transparent;")
        c_layout.addWidget(sec_label_dns)

        dns_widget = QWidget()
        dns_widget.setStyleSheet("background: transparent; border: none;")
        dw_layout = QHBoxLayout(dns_widget)
        dw_layout.setContentsMargins(0, 0, 0, 0)
        dw_layout.setSpacing(6)
        comms_dns_btn = make_action_btn("Comms DNS", lambda: m.set_dns("comms"), is_primary=True)
        reset_dns_btn = make_action_btn(T("Сброс", "Reset"), lambda: m.set_dns("reset"))
        dw_layout.addWidget(comms_dns_btn)
        dw_layout.addWidget(reset_dns_btn)
        c_layout.addWidget(CardRow(T("Comms DNS (83.220.169.155 / 212.109.195.93)", "Comms DNS (83.220.169.155 / 212.109.195.93)"),
                                   T("Надежный DNS без блокировок (Comms DNS) или сброс к DNS провайдера по умолчанию.",
                                     "Uncensored low-latency DNS (Comms DNS) or reset to network default."),
                                   dns_widget))

        # Group 5: Background Tools & Utilities (from tray menu)
        sec_label_tools = QLabel(T("Утилиты и обслуживание системы", "System Maintenance & Utilities"))
        sec_label_tools.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sec_label_tools.setStyleSheet("color: #9d9d9d; margin-top: 8px; background: transparent;")
        c_layout.addWidget(sec_label_tools)

        # SOCKS Rehab & Noisy
        misc_widget = QWidget()
        misc_widget.setStyleSheet("background: transparent; border: none;")
        mw_layout = QHBoxLayout(misc_widget)
        mw_layout.setContentsMargins(0, 0, 0, 0)
        mw_layout.setSpacing(6)
        def import_subprocess_and_rehab():
            subprocess.Popen([sys.executable, "small_actions/socks-reabilitator.pyw", "--silent"])
        rehab_btn = make_action_btn(T("Rehab", "Rehab"), import_subprocess_and_rehab)
        noisy_btn = make_action_btn(T("Noisy", "Noisy"), lambda: (m.toggle_noisy(), self.update_ui_state()))
        mw_layout.addWidget(rehab_btn)
        mw_layout.addWidget(noisy_btn)
        c_layout.addWidget(CardRow("SOCKS-реабилитатор и генератор Noisy",
                                   T("Восстановление зависших соединений и фоновый трафик для маскировки.",
                                     "Restore broken socks connections and generate background noise traffic."),
                                   misc_widget))

        # Clean Cache & Folder
        utils_widget = QWidget()
        utils_widget.setStyleSheet("background: transparent; border: none;")
        uw_layout = QHBoxLayout(utils_widget)
        uw_layout.setContentsMargins(0, 0, 0, 0)
        uw_layout.setSpacing(6)
        from managers import system_utils as sys_u
        clean_btn = make_action_btn(T("Очистить кэш", "Clear Cache"), lambda: sys_u.clean_data_directory())
        folder_btn = make_action_btn(T("Папка проекта", "Open Folder"), lambda: sys_u.open_project_folder(m.CURRENT_DIR))
        cpl_btn = make_action_btn(T("Свойства браузера", "Browser CPL"), lambda: sys_u.open_browser_properties())
        uw_layout.addWidget(clean_btn)
        uw_layout.addWidget(folder_btn)
        uw_layout.addWidget(cpl_btn)
        c_layout.addWidget(CardRow(T("Служебные утилиты", "Service Utilities"),
                                   T("Очистка временных файлов data, открытие папки программы и inetcpl.cpl.",
                                     "Clean data directory, open project directory, and browser properties."),
                                   utils_widget))

        # Desktop Shortcut
        shortcut_btn = make_action_btn(T("Создать ярлык", "Create Shortcut"),
                                       lambda: sys_u.create_shortcut("ToInet.exe" if getattr(sys, 'frozen', False) else "main.pyw"))
        c_layout.addWidget(CardRow(T("Ярлык на рабочем столе", "Desktop Shortcut"),
                                   T("Создать удобный ярлык быстрого запуска программы на рабочем столе Windows.",
                                     "Create a quick launch desktop shortcut for easy access."),
                                   shortcut_btn))

        # Ext Programs (from tray menu)
        def toggle_ext_progs():
            if m.ext_programs_manager.is_running():
                m.ext_programs_manager.stop_all()
            else:
                m.ext_programs_manager.start_all()
            self.update_ui_state()
        ext_btn = make_action_btn(T("Запуск/Стоп", "Start/Stop"), toggle_ext_progs)
        c_layout.addWidget(CardRow(T("Дополнительные фоновые программы (Ext)", "External Background Programs"),
                                   T("Запуск сторонних утилит и проксификаторов, прописанных в конфигурации.",
                                     "Launch custom background programs specified in configuration."),
                                   ext_btn))

        # Group 6: Application & Network Interface Settings
        sec_label_app = QLabel(T("Параметры интерфейса и сети", "Interface & Network Settings"))
        sec_label_app.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sec_label_app.setStyleSheet("color: #9d9d9d; margin-top: 8px; background: transparent;")
        c_layout.addWidget(sec_label_app)

        # UI Type (guaranteed strictly dark)
        ui_combo = QComboBox()
        ui_combo.addItems([T("Окно", "Window"), T("Трей", "Tray")])
        ui_combo.setCurrentIndex(0 if m.config.get("ui_type", "tray") == "window" else 1)
        ui_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QComboBox:hover {
                background-color: #383838;
                border-color: #484848;
            }
            QComboBox::drop-down { border: none; width: 16px; }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #383838;
                selection-background-color: #005FB8;
                selection-color: #FFFFFF;
                outline: none;
            }
        """)
        ui_combo.setCursor(Qt.PointingHandCursor)
        def on_ui_change(idx):
            m.config["ui_type"] = "window" if idx == 0 else "tray"
            m.config_manager.save_config(m.config)
            if hasattr(m, 'update_menu'):
                m.update_menu()
        ui_combo.currentIndexChanged.connect(on_ui_change)
        c_layout.addWidget(CardRow(T("Тип интерфейса", "Interface Type"),
                                   T("Режим отображения (графическое окно или меню в системном трее).",
                                     "Presentation mode: application window vs notification area tray menu."),
                                   ui_combo))

        # Language selection (from tray menu)
        lang_combo = QComboBox()
        lang_map = [("auto", T("Авто (Система)", "Auto (System)")),
                    ("ru", "Русский"),
                    ("en", "English"),
                    ("fr", "Français")]
        for code, label in lang_map:
            lang_combo.addItem(label, code)
        cur_l = m.config.get("language", "auto")
        for i, (code, _) in enumerate(lang_map):
            if code == cur_l:
                lang_combo.setCurrentIndex(i)
                break
        lang_combo.setStyleSheet(ui_combo.styleSheet())
        lang_combo.setCursor(Qt.PointingHandCursor)
        def on_lang_change(idx):
            selected_code = lang_combo.itemData(idx)
            m.config["language"] = selected_code
            m.config_manager.save_config(m.config)
            from managers import system_utils
            system_utils.set_language(selected_code)
            if hasattr(m, 'update_menu'):
                m.update_menu()
            self.retranslate_ui()
        lang_combo.currentIndexChanged.connect(on_lang_change)
        c_layout.addWidget(CardRow(T("Язык программы", "Application Language"),
                                   T("Выбор языка интерфейса окна и контекстного меню.",
                                     "Select display language for window and tray menus."),
                                   lang_combo))



        # Group 7: Exit & Restart
        sec_label_sys = QLabel(T("Системные команды", "System Actions"))
        sec_label_sys.setFont(QFont("Segoe UI Variable Text", 10, QFont.Bold))
        sec_label_sys.setStyleSheet("color: #9d9d9d; margin-top: 8px; background: transparent;")
        c_layout.addWidget(sec_label_sys)

        re_btn = make_action_btn(T("Перезапуск", "Restart"), m.restart_app)
        c_layout.addWidget(CardRow(T("Перезапуск ToInet-MAX", "Restart ToInet-MAX"),
                                   T("Перезапустить приложение и завершить все дочерние процессы.",
                                     "Restart the application and re-initialize background services."),
                                   re_btn))

        exit_btn = make_action_btn(T("Выход", "Exit"), m.exit_app, is_danger=True)
        c_layout.addWidget(CardRow(T("Выход из программы", "Exit Application"),
                                   T("Полностью закрыть ToInet-MAX и восстановить сетевые параметры.",
                                     "Completely terminate ToInet-MAX and restore network settings."),
                                   exit_btn))

        c_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    # -------------------------------------------------------------------------
    # Navigation between views
    # -------------------------------------------------------------------------
    def show_connect_view(self):
        self.stacked.setCurrentWidget(self.connect_view)
        self.update_ui_state()

    def show_provider_view(self):
        self.stacked.setCurrentWidget(self.provider_view)
        self.update_ui_state()

    def show_settings_view(self):
        self.stacked.setCurrentWidget(self.settings_view)
        self.update_ui_state()

    # -------------------------------------------------------------------------
    # Proxy Control & Mode Actions
    # -------------------------------------------------------------------------
    def toggle_vpn(self):
        self.error_label.setText("")
        self.main_module.toggle_all()
        self.update_ui_state()

    def next_server(self):
        if hasattr(self.main_module, 'evpn_mgr') and self.main_module.evpn_mgr.is_running:
            self.main_module.evpn_mgr.next_server()

    def select_mode(self, mode_str):
        self.main_module.set_mode_type(mode_str)
        self.update_ui_state()

    def select_gateway(self, gw_id):
        m = self.main_module
        cur_mode = getattr(m, 'mode_type', 'inetcpl')

        if cur_mode == "tun":
            if gw_id == "tor": m.toggle_singbox_tun_tor()
            elif gw_id == "byedpi": m.toggle_singbox_tun_bd()
            elif gw_id == "opera": m.toggle_singbox_tun_opera()
            elif gw_id == "ssh": m.toggle_singbox_tun_ssh()
        elif cur_mode == "inetcpl":
            if gw_id == "tor": m.toggle_inetcpl_tor()
            elif gw_id == "byedpi": m.toggle_inetcpl_bd()
            elif gw_id == "opera": m.toggle_inetcpl_opera()
            elif gw_id == "vless": m.toggle_inetcpl_vless()
            elif gw_id == "ssh": m.toggle_inetcpl_ssh()

        self.update_ui_state()

    # -------------------------------------------------------------------------
    # UI State Synchronization (Windows 11 Fluent style, no emojis)
    # -------------------------------------------------------------------------
    def set_status(self, text):
        if "VPN Включен" in text or "Подключено" in text or "Connected" in text:
            self.power_btn.set_state("on")
            self.status_desc.setText("Соединение защищено")
            self.status_desc.setStyleSheet("color: #107C41; font-weight: bold; background: transparent;")
            self.progress_bar.stop()

            cur_mode = getattr(self.main_module, 'mode_type', 'inetcpl').upper()
            self.status_chip.setText(f"Подключено • {cur_mode}")
            self.status_chip.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    color: #107C41;
                    border: 1px solid #107C41;
                    border-radius: 12px;
                    padding: 4px 16px;
                }
            """)

            if hasattr(self.main_module, 'evpn_mgr') and self.main_module.evpn_mgr.is_running:
                self.next_btn.show()
            else:
                self.next_btn.hide()

        elif "VPN Выключен" in text or "Отключено" in text or "Disconnected" in text:
            self.power_btn.set_state("off")
            self.status_desc.setText("Нажмите для подключения")
            self.status_desc.setStyleSheet("color: #9d9d9d; background: transparent;")
            self.progress_bar.stop()
            self.next_btn.hide()

            self.status_chip.setText("Отключено")
            self.status_chip.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    color: #9d9d9d;
                    border: 1px solid #383838;
                    border-radius: 12px;
                    padding: 4px 16px;
                }
            """)
        else:
            self.power_btn.set_state("starting")
            self.status_desc.setText(text)
            self.status_desc.setStyleSheet("color: #CA5010; background: transparent;")
            self.progress_bar.start()

            self.status_chip.setText("Подключение...")
            self.status_chip.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    color: #CA5010;
                    border: 1px solid #CA5010;
                    border-radius: 12px;
                    padding: 4px 16px;
                }
            """)

    def _update_mini_controls(self, restart_btn, toggle_btn, is_running):
        T = self.main_module.T
        if restart_btn:
            restart_btn.setVisible(bool(is_running))
        if toggle_btn:
            if is_running:
                toggle_btn.setText("■")
                toggle_btn.setToolTip(T("Остановить", "Stop", "Arreter"))
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: 1px solid transparent;
                        border-radius: 4px;
                        font-size: 14px;
                        font-weight: bold;
                        color: #ff5555;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 85, 85, 0.18);
                        border: 1px solid rgba(255, 85, 85, 0.4);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 85, 85, 0.28);
                    }
                """)
            else:
                toggle_btn.setText("▶")
                toggle_btn.setToolTip(T("Запустить", "Start", "Demarrer"))
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: 1px solid transparent;
                        border-radius: 4px;
                        font-size: 15px;
                        font-weight: bold;
                        color: #55ff55;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: rgba(85, 255, 85, 0.18);
                        border: 1px solid rgba(85, 255, 85, 0.4);
                    }
                    QPushButton:pressed {
                        background-color: rgba(85, 255, 85, 0.28);
                    }
                """)

    def open_rules_editor(self):
        try:
            from ui.rules_editor import RulesEditorDialog
            dialog = RulesEditorDialog(parent=self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, T("Ошибка", "Error", "Erreur"), f"Не удалось открыть редактор правил: {e}")

    def retranslate_ui(self):
        # Update mode descriptions and chips
        self._last_styled_mode = None
        self._last_status_text = None
        self.update_ui_state()

        # Update bottom buttons
        if hasattr(self, 'btn_provider'):
            self.btn_provider.setText(T("VPN Провайдер", "VPN Providers", "Fournisseurs VPN"))
        if hasattr(self, 'btn_settings'):
            self.btn_settings.setText(T("Настройки", "Settings", "Paramètres"))

        # Update main switch buttons
        if hasattr(self, 'tor_switch_btn'):
            self.tor_switch_btn.setText(T("Сменить узел Tor", "New Tor Circuit", "Changer de circuit Tor"))
        if hasattr(self, 'evpn_switch_btn'):
            self.evpn_switch_btn.setText(T("Сменить сервер EVPN", "Switch EVPN Server", "Changer de serveur EVPN"))

    def update_ui_state(self):
        m = self.main_module
        proxy_active = getattr(m, 'proxy_enabled', False)
        
        status_text = T("Подключено", "Connected", "Connecté") if proxy_active else T("Отключено", "Disconnected", "Déconnecté")
        if getattr(self, '_last_status_text', None) != status_text:
            self._last_status_text = status_text
            self.set_status(status_text)

        # Update provider live status miniature buttons (copy tray menu mechanism)
        if hasattr(self, 'bd_toggle_btn'):
            bd_on = getattr(m, 'byedpi_manager', None) and m.byedpi_manager.is_running()
            self._update_mini_controls(getattr(self, 'bd_restart_btn', None), self.bd_toggle_btn, bd_on)

        if hasattr(self, 'tor_toggle_btn'):
            tor_on = getattr(m, 'tor_manager', None) and m.tor_manager.is_running()
            self._update_mini_controls(getattr(self, 'tor_restart_btn', None), self.tor_toggle_btn, tor_on)

        if hasattr(self, 'opera_toggle_btn'):
            opera_on = getattr(m, 'opera_mgr', None) and m.opera_mgr.is_running()
            self._update_mini_controls(getattr(self, 'opera_restart_btn', None), self.opera_toggle_btn, opera_on)

        if hasattr(self, 'ssh_toggle_btn'):
            ssh_on = getattr(m, 'ssh_mgr', None) and m.ssh_mgr.is_running()
            self._update_mini_controls(getattr(self, 'ssh_restart_btn', None), self.ssh_toggle_btn, ssh_on)

        if hasattr(self, 'vless_toggle_btn'):
            vless_on = (getattr(m, 'vless_mgr', None) and m.vless_mgr.is_running()) or (getattr(m, 'evpn_mgr', None) and getattr(m.evpn_mgr, 'is_running', False))
            self._update_mini_controls(getattr(self, 'vless_restart_btn', None), self.vless_toggle_btn, vless_on)

        if hasattr(self, 'tgws_toggle_btn'):
            tgws_on = getattr(m, 'tgws_mgr', None) and getattr(m.tgws_mgr, 'running', False)
            self._update_mini_controls(getattr(self, 'tgws_restart_btn', None), self.tgws_toggle_btn, tgws_on)

        if hasattr(self, 'prox_toggle_btn'):
            prox_on = getattr(m, 'mode_mgr', None) and m.mode_mgr.proxifier_running()
            self._update_mini_controls(getattr(self, 'prox_restart_btn', None), self.prox_toggle_btn, prox_on)

        # Update quick server switch buttons on main screen (Tor circuit / EVPN server)
        tor_active = getattr(m, 'tor_manager', None) and m.tor_manager.tor_running
        evpn_active = getattr(m, 'evpn_mgr', None) and getattr(m.evpn_mgr, 'is_running', False)
        if hasattr(self, 'tor_switch_btn'):
            self.tor_switch_btn.setVisible(bool(tor_active))

        # Update mode chips only when mode changes
        cur_mode = getattr(m, 'mode_type', 'inetcpl').lower()

        # Hide EVPN card in providers if mode is not evpn
        if hasattr(self, 'vless_card'):
            self.vless_card.setVisible(cur_mode == "evpn")

        # EVPN switch button only visible if in evpn mode and actively running
        if hasattr(self, 'evpn_switch_btn'):
            self.evpn_switch_btn.setVisible(cur_mode == "evpn" and bool(evpn_active))

        # Hide 'Выбрать шлюзом' buttons in empty mode
        is_empty = (cur_mode == "empty")
        for g_btn in getattr(self, 'gateway_buttons', []):
            g_btn.setVisible(not is_empty)

        if getattr(self, '_last_styled_mode', None) != cur_mode:
            self._last_styled_mode = cur_mode
            mode_descriptions = {
                "empty": T(
                    "Локальные порты. Сетевые параметры Windows не изменяются (для ручной настройки).",
                    "Local ports. Windows system network settings are untouched (for manual configuration).",
                    "Ports locaux. Les paramètres réseau de Windows restent inchangés (configuration manuelle)."
                ),
                "inetcpl": T(
                    "Системный прокси Windows (браузеры Chrome, Edge, Yandex и др. работают через прокси).",
                    "System proxy for Windows (browsers Chrome, Edge, etc. route through proxy).",
                    "Proxy système Windows (Chrome, Edge, etc. passent par le proxy)."
                ),
                "tun": T(
                    "Глобальный сетевой перехват трафика системы (игры, Discord и др.) через Sing-box TUN.",
                    "Global system network traffic interception (games, Discord, etc.) via Sing-box TUN.",
                    "Interception globale du trafic système (jeux, Discord, etc.) via Sing-box TUN."
                ),
                "evpn": T(
                    "Глобальное подключение через пул VLESS Reality серверов с автопереключением узлов.",
                    "Global VPN connection through pool of VLESS Reality servers with auto-failover.",
                    "Connexion globale via un pool de serveurs VLESS Reality avec basculement automatique."
                )
            }
            self.mode_desc_label.setText(mode_descriptions.get(cur_mode, ""))

            for mode_val, btn in self.mode_chips.items():
                if mode_val == cur_mode:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #005FB8;
                            color: #FFFFFF;
                            border: 1px solid #005FB8;
                            border-radius: 6px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #0078D4;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2d2d2d;
                            color: #cccccc;
                            border: 1px solid #3c3c3c;
                            border-radius: 6px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #383838;
                            color: #FFFFFF;
                        }
                    """)

    def show_error(self, text):
        self.error_label.setText(text)

    def closeEvent(self, event):
        # Minimize to tray instead of quitting
        self.hide()
        event.ignore()
