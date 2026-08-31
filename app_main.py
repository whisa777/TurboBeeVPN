import os
import sys
import threading

from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QObject
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush, QPen, QLinearGradient
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QLineEdit, QCheckBox, QRadioButton,
    QButtonGroup, QDialog, QMessageBox, QSizePolicy,
)

from app_core import (
    Profile, parse_vless, load_config, save_config, build_singbox_config,
    VpnEngine, SystemProxy, SOCKS_PORT, TunTrafficMonitor, format_rate, format_bytes,
    fetch_subscription, get_profile_total, add_profile_total,
)

LANG = {
    "ru": {
        "app_title": "TurboBee VPN",
        "status_off": "Отключено",
        "status_connecting": "Подключение…",
        "status_on": "Подключено",
        "status_failed": "Ошибка подключения",
        "current_key": "Текущий ключ",
        "no_key": "Нет ключа",
        "tap_to_connect": "Нажмите, чтобы подключиться",
        "tap_to_disconnect": "Нажмите, чтобы отключиться",
        "my_keys": "Мои ключи",
        "no_keys": "Нет ключей. Добавьте через «+ Добавить ключ».",
        "server_name_prefix": "Сервер",
        "add_key": "Добавить ключ",
        "settings": "Настройки",
        "routing_label": "Маршрутизация",
        "routing_summary": "Обходить VPN для российских сайтов",
        "language": "Язык",
        "theme": "Тема",
        "system_theme": "Системная",
        "light_theme": "Светлая",
        "dark_theme": "Тёмная",
        "ok": "OK",
        "cancel": "Отмена",
        "delete": "Удалить",
        "delete_title": "Удалить ключ",
        "delete_msg": "Удалить ключ «%s»?",
        "connect_error": "Ошибка подключения",
        "enter_link": "Вставьте vless-ссылку или ссылку подписки (http/https)",
        "invalid_link": "Неверная ссылка",
        "proxy_set": "VPN включён: весь трафик через туннель",
        "proxy_unset": "VPN выключен: трафик идёт напрямую",
        "tun_active": "VPN включён: TUN-режим",
        "add_key_btn": "+  Добавить ключ",
        "traffic_label": "Трафик",
        "traffic_down": "↓",
        "traffic_up": "↑",
        "traffic_total": "За сессию: ↓ %s · ↑ %s",
        "traffic_all": "Всего по ключу: ↓ %s · ↑ %s",
        "traffic_all_none": "Всего по ключу: ↓ 0 · ↑ 0",
        "sub_loading": "Загружаю подписку…",
        "sub_added": "Подписка добавлена: новых серверов — %d",
        "sub_error": "Ошибка подписки",
    },
    "en": {
        "app_title": "TurboBee VPN",
        "status_off": "Disconnected",
        "status_connecting": "Connecting…",
        "status_on": "Connected",
        "status_failed": "Connection failed",
        "current_key": "Current key",
        "no_key": "No key",
        "tap_to_connect": "Tap to connect",
        "tap_to_disconnect": "Tap to disconnect",
        "my_keys": "My keys",
        "no_keys": "No keys. Add one via «+ Add key».",
        "server_name_prefix": "Server",
        "add_key": "Add key",
        "settings": "Settings",
        "routing_label": "Routing",
        "routing_summary": "Bypass VPN for Russian sites",
        "language": "Language",
        "theme": "Theme",
        "system_theme": "System",
        "light_theme": "Light",
        "dark_theme": "Dark",
        "ok": "OK",
        "cancel": "Cancel",
        "delete": "Delete",
        "delete_title": "Delete key",
        "delete_msg": "Delete key «%s»?",
        "connect_error": "Connection error",
        "enter_link": "Paste vless or subscription link (http/https)",
        "invalid_link": "Invalid link",
        "proxy_set": "VPN on: all traffic through tunnel",
        "proxy_unset": "VPN off: traffic goes direct",
        "tun_active": "VPN on: TUN mode",
        "add_key_btn": "+  Add key",
        "traffic_label": "Traffic",
        "traffic_down": "↓",
        "traffic_up": "↑",
        "traffic_total": "Session: ↓ %s · ↑ %s",
        "traffic_all": "Total by key: ↓ %s · ↑ %s",
        "traffic_all_none": "Total by key: ↓ 0 · ↑ 0",
        "sub_loading": "Loading subscription…",
        "sub_added": "Subscription added: %d new servers",
        "sub_error": "Subscription error",
    },
}

# Тёплая палитра TurboBee (тёмная и светлая)
DARK = {
    "bg": "#1B1B22",
    "surface": "#26262F",
    "card": "#2E2E3A",
    "border": "#3A3A48",
    "text": "#F4F1E8",
    "text_secondary": "#9A97A6",
    "primary": "#F0A93C",   # мёдовый
    "primary_text": "#17130A",
    "accent": "#C8811F",
    "hover": "#E09734",
    "green": "#4CAF50",
}

LIGHT = {
    "bg": "#FAF6EE",
    "surface": "#FFFFFF",
    "card": "#F4EFE4",
    "border": "#E3DCCB",
    "text": "#24242B",
    "text_secondary": "#77727F",
    "primary": "#E6A23C",
    "primary_text": "#FFFFFF",
    "accent": "#C87F1C",
    "hover": "#D8912C",
    "green": "#3DA84C",
}


def _is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


_SINGLE_MUTEX_HANDLE = None


def _is_single_instance():
    global _SINGLE_MUTEX_HANDLE
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        handle = kernel32.CreateMutexW(None, False, "Local\\TurboBeeVPN_SingleInstance")
        if not handle:
            return True
        if ctypes.get_last_error() == 183:
            kernel32.CloseHandle(handle)
            hwnd = user32.FindWindowW(None, "TurboBee VPN")
            from PySide6.QtWidgets import qApp
            if hwnd:
                user32.ShowWindow(wintypes.HWND(hwnd), 9)
                user32.SetForegroundWindow(wintypes.HWND(hwnd))
            else:
                wins = qApp.topLevelWidgets()
                for w in wins:
                    if isinstance(w, QMainWindow):
                        w.showNormal(); w.raise_(); w.activateWindow()
            return False
        _SINGLE_MUTEX_HANDLE = handle
        return True
    except Exception:
        return True


def _elevate():
    try:
        if not getattr(sys, "frozen", False):
            return False
        global _SINGLE_MUTEX_HANDLE
        if _SINGLE_MUTEX_HANDLE:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(_SINGLE_MUTEX_HANDLE)
            except Exception:
                pass
            _SINGLE_MUTEX_HANDLE = None
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
        return True
    except Exception:
        return False


def _maybe_elevate():
    """Спрашивает пользователя о подъёме прав. Вызывать ПОСЛЕ создания QApplication.
    Возвращает True, если приложение нужно завершить (запущен elevated процесс)."""
    msg = (
        "TurboBee VPN запущен без прав администратора.\n"
        "В этом режиме VPN не сможет перехватывать весь трафик (режим TUN), "
        "и может не работать.\n\n"
        "Перезапустить от имени администратора?"
    )
    box = QMessageBox(QMessageBox.Question, "TurboBee VPN", msg)
    btn_yes = box.addButton("Да", QMessageBox.YesRole)
    box.addButton("Нет", QMessageBox.NoRole)
    box.setDefaultButton(btn_yes)
    box.exec()
    if box.clickedButton() is btn_yes:
        return _elevate()
    return False

def load_logo():
    """Ищет логотип рядом с exe/скриптом."""
    if getattr(sys, "_MEIPASS", None):
        p = os.path.join(sys._MEIPASS, "Logo.jpg")
        if os.path.exists(p):
            return p
    base = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    for name in ("Logo.jpg", "logo.jpg", "Logo.png", "logo.png", "app.ico"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


class RoundButton(QPushButton):
    """Современная кнопка с рамкой."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.bg = "#F0A93C"
        self.fg = "#17130A"
        self.hover_bg = "#E09734"
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_colors(self, bg, fg, hover):
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover
        self.update()

    def enterEvent(self, e):
        self.setStyleSheet(self._css(self.hover_bg))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setStyleSheet(self._css(self.bg))
        super().leaveEvent(e)

    def _css(self, bg):
        return f"""
        QPushButton {{
            background-color: {bg};
            color: {self.fg};
            border: none;
            border-radius: 22px;
            font-size: 15px;
            font-weight: 600;
            padding: 10px 20px;
        }}
        QPushButton:disabled {{
            background-color: #555; color: #bbb;
        }}
        """

    def showEvent(self, e):
        self.setStyleSheet(self._css(self.bg))
        super().showEvent(e)


class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected = False
        self.color = "#F0A93C"
        self.setFixedSize(96, 96)

    def set_state(self, connected, color):
        self.connected = connected
        self.color = color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        cx, cy = r.center().x(), r.center().y()
        # внешнее кольцо
        p.setBrush(QColor("#3A3A48" if not self.connected else "#2A2A33"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(cx, cy), 44, 44)
        c = self.color
        p.setBrush(QColor(c))
        p.drawEllipse(QPoint(cx, cy), 36, 36)
        # внутренняя точка
        p.setBrush(QColor("#1B1B22" if not self.connected else c))
        p.drawEllipse(QPoint(cx, cy), 20, 20)
        # символ
        p.setPen(QPen(QColor("#FFFFFF" if self.connected else "#1B1B22"), 3, Qt.SolidLine, Qt.RoundCap))
        f = QFont("Segoe UI Symbol", 22, QFont.Bold)
        p.setFont(f)
        glyph = "\u2714" if self.connected else "\u23FB"
        p.drawText(r, Qt.AlignCenter, glyph)


class KeyRow(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        self.marker = QLabel("○")
        self.marker.setFixedWidth(18)
        self.marker.setAlignment(Qt.AlignCenter)
        self.name = QLabel("")
        self.name.setStyleSheet("font-size: 14px;")
        self.del_btn = QLabel("✕")
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setStyleSheet("color: #C8811F; font-size: 14px;")
        layout.addWidget(self.marker)
        layout.addWidget(self.name, 1)
        layout.addWidget(self.del_btn)


class MyScrollArea(QScrollArea):
    pass


class TurboBeeWindow(QMainWindow):
    sig_refresh = Signal()
    sig_error = Signal(str)
    sig_sub_done = Signal(object, object)

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.cfg.setdefault("total_stats", {})
        self.engine = VpnEngine()
        self.engine.add_log_listener(self._on_engine_log)
        self.traffic = TunTrafficMonitor()
        self.connected = False
        self.proxy_mode = False
        self.session_down = 0
        self.session_up = 0
        self._last_sample = None
        self._build_ui()
        self.apply_theme()
        self.apply_language()
        self.refresh_profiles()
        self._update_status_ui()
        self._refresh_total_label()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(1000)
        self.sig_refresh.connect(self._on_sig_refresh)
        self.sig_error.connect(self._on_sig_error)
        self.sig_sub_done.connect(self._on_sig_sub_done)

    # ---------- helpers ----------
    def tr(self, key):
        return LANG.get(self.cfg.get("language", "ru"), LANG["ru"]).get(key, key)

    def colors(self):
        return DARK if self.cfg.get("theme", "dark") == "dark" else LIGHT

    def _current_profile(self):
        profiles = self.cfg.get("profiles", [])
        idx = self.cfg.get("current", 0)
        if 0 <= idx < len(profiles):
            return profiles[idx]
        return None

    # ---------- UI ----------
    def _build_ui(self):
        self.setWindowTitle("TurboBee VPN")
        self.setFixedSize(420, 640)
        self.setMinimumSize(380, 560)
        self.setWindowIcon(QIcon(load_logo() or ""))

        self.central = QWidget()
        self.central_layout = QVBoxLayout(self.central)
        self.central_layout.setContentsMargins(16, 14, 16, 12)
        self.central_layout.setSpacing(10)
        self.setCentralWidget(self.central)

        # Шапка: лого + название + настройки
        self.header = QHBoxLayout()
        self.header.setSpacing(10)
        logo_path = load_logo()
        self.logo_lbl = QLabel()
        pix = QPixmap(logo_path) if logo_path else QPixmap()
        if not pix.isNull():
            self.logo_lbl.setPixmap(pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_lbl.setFixedSize(40, 40)
        self.title_lbl = QLabel("TurboBee VPN")
        self.title_lbl.setStyleSheet("font-size: 19px; font-weight: 700;")
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet("QPushButton{border:none; font-size:20px;}")
        self.settings_btn.clicked.connect(self.open_settings)
        self.header.addWidget(self.logo_lbl)
        self.header.addWidget(self.title_lbl, 1)
        self.header.addWidget(self.settings_btn)
        self.central_layout.addLayout(self.header)

        # Статус-карточка
        self.status_card = QFrame()
        self.status_layout = QVBoxLayout(self.status_card)
        self.status_layout.setContentsMargins(0, 18, 0, 14)
        self.status_layout.setSpacing(4)
        self.central_layout.addWidget(self.status_card)

        self.status_dot = StatusDot()
        # клик по карточке переключает подключение
        self.status_dot.mousePressEvent = lambda e: self.toggle_connect()
        self.status_layout.addWidget(self.status_dot, alignment=Qt.AlignCenter)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet("font-size: 17px; font-weight: 700; background: transparent;")
        self.status_layout.addWidget(self.status_lbl)

        self.status_hint = QLabel("")
        self.status_hint.setAlignment(Qt.AlignCenter)
        self.status_hint.setStyleSheet("font-size: 10px; background: transparent;")
        self.status_layout.addWidget(self.status_hint)

        # скорость
        self.traffic_row = QHBoxLayout()
        self.traffic_up_lbl = QLabel("↑ 0 Б/с")
        self.traffic_down_lbl = QLabel("↓ 0 Б/с")
        self.traffic_up_lbl.setStyleSheet("font-weight:700; font-size:12px; background: transparent;")
        self.traffic_down_lbl.setStyleSheet("font-weight:700; font-size:12px; background: transparent;")
        self.traffic_row.addWidget(self.traffic_up_lbl)
        self.traffic_row.addStretch(1)
        self.traffic_row.addWidget(self.traffic_down_lbl)
        self.status_layout.addLayout(self.traffic_row)

        self.traffic_total_lbl = QLabel("")
        self.traffic_total_lbl.setAlignment(Qt.AlignCenter)
        self.traffic_total_lbl.setStyleSheet("font-size:11px; background: transparent;")
        self.status_layout.addWidget(self.traffic_total_lbl)
        self.traffic_all_lbl = QLabel("")
        self.traffic_all_lbl.setAlignment(Qt.AlignCenter)
        self.traffic_all_lbl.setStyleSheet("font-size:11px; background: transparent;")
        self.status_layout.addWidget(self.traffic_all_lbl)

        # Подпись header for keys
        self.keys_title_row = QHBoxLayout()
        self.keys_title_lbl = QLabel("")
        self.keys_title_lbl.setCursor(Qt.PointingHandCursor)
        self.keys_title_lbl.setStyleSheet("font-size:14px; font-weight:700;")
        self.keys_title_lbl.mousePressEvent = lambda e: self.toggle_keys_visible()
        self.keys_title_row.addWidget(self.keys_title_lbl)
        self.keys_title_row.addStretch(1)
        self.central_layout.addLayout(self.keys_title_row)

        # Кнопка добавить
        self.add_btn = RoundButton()
        self.add_btn.clicked.connect(self.open_add_dialog)
        self.central_layout.addWidget(self.add_btn)

        self.proxy_lbl = QLabel("")
        self.proxy_lbl.setStyleSheet("font-size:9px; color:#9A97A6;")
        self.proxy_lbl.setAlignment(Qt.AlignCenter)
        self.central_layout.addWidget(self.proxy_lbl)

        # Список ключей в scroll
        self.keys_scroll = MyScrollArea()
        self.keys_scroll.setWidgetResizable(True)
        self.keys_scroll.setFrameShape(QFrame.NoFrame)
        self.keys_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.keys_container = QWidget()
        self.keys_container_layout = QVBoxLayout(self.keys_container)
        self.keys_container_layout.setContentsMargins(0, 0, 4, 0)
        self.keys_container_layout.setSpacing(6)
        self.keys_container_layout.addStretch(1)
        self.keys_scroll.setWidget(self.keys_container)
        self.central_layout.addWidget(self.keys_scroll, 1)
        self.keys_visible = True

    def apply_theme(self):
        c = self.colors()
        self.central.setStyleSheet(f"""
            QWidget {{ background-color: {c['bg']}; color: {c['text']}; }}
            QFrame#statusCard {{ background: {c['surface']}; border-radius: 18px; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: {c['bg']}; width: 8px; }}
            QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            QPushButton {{ }}
        """)
        self.status_card.setObjectName("statusCard")
        self.status_card.setStyleSheet(f"#statusCard {{ background: {c['surface']}; border-radius: 18px; }}")
        self.status_lbl.setStyleSheet(f"font-size:17px; font-weight:700; color:{c['text']}; background: transparent;")
        self.status_hint.setStyleSheet(f"font-size:10px; color:{c['text_secondary']}; background: transparent;")
        self.traffic_up_lbl.setStyleSheet(f"font-weight:700; font-size:12px; color:{c['primary']}; background: transparent;")
        self.traffic_down_lbl.setStyleSheet(f"font-weight:700; font-size:12px; color:{c['primary']}; background: transparent;")
        self.traffic_total_lbl.setStyleSheet(f"font-size:11px; color:{c['text_secondary']}; background: transparent;")
        self.traffic_all_lbl.setStyleSheet(f"font-size:11px; color:{c['text_secondary']}; background: transparent;")
        self.keys_title_lbl.setStyleSheet(f"font-size:14px; font-weight:700; color:{c['text']};")
        self.title_lbl.setStyleSheet(f"font-size:19px; font-weight:700; color:{c['text']};")
        self.settings_btn.setStyleSheet(f"QPushButton{{border:none; font-size:20px; color:{c['text']};}} QPushButton:hover{{color:{c['primary']};}}")
        self.proxy_lbl.setStyleSheet(f"font-size:9px; color:{c['text_secondary']};")
        self.add_btn.set_colors(c["primary"], c["primary_text"], c["hover"])
        self.keys_title_lbl.setStyleSheet(f"font-size:14px; font-weight:700; color:{c['text']};")
        # обновить строки ключей
        for i in range(self.keys_container_layout.count()):
            item = self.keys_container_layout.itemAt(i)
            w = item.widget()
            if isinstance(w, KeyRow):
                self._theme_key_row(w, c)
            elif isinstance(w, QLabel) and w.text().startswith("—"):
                w.setStyleSheet(f"font-size:11px; color:{c['text_secondary']}; padding:10px;")
        self._draw_status_dot()

    def _theme_key_row(self, row, c):
        row.setStyleSheet(f"QFrame {{ background: {c['card']}; border-radius: 12px; }}")
        row.marker.setStyleSheet(f"font-size:13px; color:{c['primary']};")
        row.name.setStyleSheet(f"font-size:14px; color:{c['text']};")

    def apply_language(self):
        t = self.tr
        self.setWindowTitle(t("app_title"))
        self.title_lbl.setText(t("app_title"))
        self.add_btn.setText(t("add_key_btn"))
        self.keys_title_lbl.setText("%s (%d)" % (t("my_keys"), len(self.cfg.get("profiles", []))))
        self._update_status_ui()
        self.refresh_profiles()
        self.refresh_proxy_label()

    def _update_status_ui(self):
        t = self.tr
        if self.connected:
            self.status_lbl.setText(t("status_on"))
            self.status_hint.setText(t("tap_to_disconnect"))
        else:
            self.status_lbl.setText(t("status_off"))
            self.status_hint.setText(t("tap_to_connect"))
        self._draw_status_dot()

    def _draw_status_dot(self):
        c = self.colors()
        self.status_dot.set_state(self.connected, c["green"] if self.connected else c["primary"])

    # ---------- traffic ----------
    def _on_tick(self):
        if self.connected:
            self._update_traffic_ui()
        elif self._last_sample is not None:
            # после отключения — обновить суммарную строку и сбросить
            self._last_sample = None
            self._refresh_total_label()

    def _update_traffic_ui(self):
        try:
            t = self.tr
            sample = self.traffic.sample()
            if not sample:
                self.traffic_up_lbl.setText("↑ --")
                self.traffic_down_lbl.setText("↓ --")
                self.traffic_total_lbl.setText(t("traffic_total") % ("--", "--"))
                self._refresh_total_label()
                return
            up_total, down_total, up_bps, down_bps = sample
            self.traffic_up_lbl.setText("↑ " + format_rate(up_bps))
            self.traffic_down_lbl.setText("↓ " + format_rate(down_bps))
            self.traffic_total_lbl.setText(t("traffic_total") % (format_bytes(down_total), format_bytes(up_total)))
            if self.connected and self._last_sample is not None:
                l_up, l_down = self._last_sample
                self.session_down += max(0, down_total - l_down)
                self.session_up += max(0, up_total - l_up)
            self._last_sample = (up_total, down_total)
            self._refresh_total_label()
        except Exception:
            pass

    def _refresh_total_label(self):
        try:
            t = self.tr
            p = self._current_profile()
            if not p:
                self.traffic_all_lbl.setText("")
                return
            down0, up0 = get_profile_total(self.cfg, p)
            self.traffic_all_lbl.setText(t("traffic_all") % (format_bytes(down0 + self.session_down),
                                                             format_bytes(up0 + self.session_up)))
        except Exception:
            self.traffic_all_lbl.setText(self.tr("traffic_all_none"))

    def _commit_session(self):
        try:
            p = self._current_profile()
            if (self.session_down > 0 or self.session_up > 0) and p:
                add_profile_total(self.cfg, p, self.session_down, self.session_up)
            self.session_down = 0
            self.session_up = 0
            self._last_sample = None
        except Exception:
            pass

    # ---------- keys ----------
    def refresh_profiles(self):
        t = self.tr
        profiles = self.cfg.get("profiles", [])
        self.keys_title_lbl.setText("%s (%d)" % (t("my_keys"), len(profiles)))
        # очистить (кроме stretch)
        while self.keys_container_layout.count() > 1:
            item = self.keys_container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not profiles:
            empty = QLabel("— " + t("no_keys") + " —")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("font-size:11px; color:%s; padding:12px;" % self.colors()["text_secondary"])
            empty.setWordWrap(True)
            self.keys_container_layout.insertWidget(0, empty)
            return

        for i, p in enumerate(profiles):
            row = KeyRow()
            is_current = i == self.cfg.get("current", 0)
            row.marker.setText("●" if is_current else "○")
            row.name.setText(p.get("name", "?"))
            row.name.setCursor(Qt.PointingHandCursor)
            row.marker.setCursor(Qt.PointingHandCursor)
            row.marker.mousePressEvent = lambda e, idx=i: self.select_key(idx)
            row.name.mousePressEvent = lambda e, idx=i: self.select_key(idx)
            row.del_btn.mousePressEvent = lambda e, idx=i: self.delete_key(idx)
            self._theme_key_row(row, self.colors())
            self.keys_container_layout.insertWidget(self.keys_container_layout.count() - 1, row)

    def toggle_keys_visible(self):
        self.keys_visible = not self.keys_visible
        self.keys_scroll.setVisible(self.keys_visible)

    def select_key(self, idx):
        if idx == self.cfg.get("current", 0) and not self.connected:
            return
        self.cfg["current"] = idx
        save_config(self.cfg)
        self.refresh_profiles()
        if self.connected:
            self.reconnect()

    def delete_key(self, idx):
        t = self.tr
        profiles = self.cfg.get("profiles", [])
        if not (0 <= idx < len(profiles)):
            return
        if QMessageBox.question(self, t("delete_title"), t("delete_msg") % profiles[idx].get("name", "?"),
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        del profiles[idx]
        if self.cfg.get("current", 0) >= len(profiles):
            self.cfg["current"] = 0
        save_config(self.cfg)
        if self.connected:
            self.reconnect()
        self.refresh_profiles()
        self._refresh_total_label()

    # ---------- connect ----------
    def toggle_connect(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        t = self.tr
        profiles = self.cfg.get("profiles", [])
        if not profiles:
            QMessageBox.information(self, t("add_key"), t("no_keys"))
            return
        self.connected = False
        self.status_lbl.setText(t("status_connecting"))
        threading.Thread(target=self._do_connect, daemon=True).start()

    def _do_connect(self):
        self.proxy_mode = False
        self._last_sample = None
        try:
            profiles = self.cfg.get("profiles", [])
            p = profiles[self.cfg.get("current", 0)]
            profile = Profile(
                p.get("name", "?"), p.get("host"), int(p.get("port")),
                p.get("uuid"), p.get("path", "/"), p.get("security", "none"), p.get("transport", "tcp"))
            bypass_ru = self.cfg.get("bypass_ru", True)
            use_tun = _is_admin()

            config = build_singbox_config(profile, bypass_ru, use_tun=use_tun)
            self.engine.start(config)
            ok = False
            if use_tun:
                ok = self.engine.test_proxy()
                if not ok:
                    self.engine.stop()
                    config = build_singbox_config(profile, bypass_ru, use_tun=False)
                    self.engine.start(config)
                    ok = self.engine.test_proxy()
                    self.proxy_mode = True
            else:
                ok = self.engine.test_proxy()
                self.proxy_mode = True
            if ok:
                self.connected = True
                SystemProxy.set_proxy(True)
            else:
                self.engine.stop()
                SystemProxy.set_proxy(False)
        except Exception as e:
            self.engine.stop()
            SystemProxy.set_proxy(False)
            self.sig_error.emit(str(e))
        self.sig_refresh.emit()
        self.refresh_proxy_label()

    def disconnect(self):
        self.connected = False
        self.proxy_mode = False
        self._commit_session()
        self._clear_traffic_labels()
        self.engine.stop()
        SystemProxy.set_proxy(False)
        self._update_status_ui()
        self.refresh_proxy_label()
        self._refresh_total_label()

    def _clear_traffic_labels(self):
        self.traffic_up_lbl.setText("↑ 0 Б/с")
        self.traffic_down_lbl.setText("↓ 0 Б/с")
        self.traffic_total_lbl.setText(self.tr("traffic_total") % ("0 Б", "0 Б"))

    def reconnect(self):
        self.disconnect()
        self.connect()

    def refresh_proxy_label(self):
        t = self.tr
        if self.connected:
            self.proxy_lbl.setText(t("tun_active") if not self.proxy_mode else t("proxy_set"))
        else:
            self.proxy_lbl.setText(t("proxy_unset"))

    # ---------- signals from worker threads ----------
    def _on_sig_refresh(self):
        self._update_status_ui()
        self.refresh_proxy_label()

    def _on_sig_error(self, message):
        self._update_status_ui()
        QMessageBox.critical(self, self.tr("connect_error"), message)

    def _on_sig_sub_done(self, profiles, error):
        if error:
            QMessageBox.critical(self, self.tr("sub_error"), error)
        else:
            added = self._merge_profiles(profiles or [])
            QMessageBox.information(self, self.tr("add_key"),
                                    self.tr("sub_added") % added)

    # ---------- add ----------
    def open_add_dialog(self):
        t = self.tr
        dlg = QDialog(self)
        dlg.setWindowTitle(t("add_key"))
        dlg.setFixedWidth(400)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(10)

        hint = QLabel(t("enter_link"))
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size:12px; color:#9A97A6;")
        l.addWidget(hint)

        entry = QLineEdit(dlg)
        entry.setPlaceholderText("vless://… или http(s)://…")
        entry.setMinimumHeight(40)
        entry.setStyleSheet(f"QLineEdit {{ background:{self.colors()['card']}; "
                            f"color:{self.colors()['text']}; border-radius:8px; padding:8px; font-size:13px; }}")
        l.addWidget(entry)

        btns = QHBoxLayout()
        cancel = QPushButton(t("cancel"))
        cancel.setCursor(Qt.PointingHandCursor)
        ok = RoundButton(t("ok"))
        cancel.clicked.connect(dlg.reject)
        ok.clicked.connect(lambda: self._add_submit(entry.text(), dlg))
        btns.addWidget(cancel, 2)
        btns.addWidget(ok, 3)
        l.addLayout(btns)
        entry.returnPressed.connect(lambda: self._add_submit(entry.text(), dlg))
        entry.setFocus()
        dlg.exec()

    def _add_submit(self, raw, dlg):
        t = self.tr
        uri = raw.strip()
        if not uri:
            return
        low = uri.lower()
        if low.startswith("http://") or low.startswith("https://"):
            dlg.accept()
            self._import_subscription(uri)
            return
        try:
            p = parse_vless(uri)
        except ValueError:
            QMessageBox.warning(dlg, t("add_key"), t("invalid_link"))
            return
        profiles = self.cfg.get("profiles", [])
        for existing in profiles:
            if (existing.get("uuid") == p.uuid and existing.get("host") == p.host
                    and int(existing.get("port", 0)) == p.port):
                self.cfg["current"] = profiles.index(existing)
                save_config(self.cfg)
                dlg.accept()
                self.refresh_profiles()
                return
        if not p.name:
            p.name = "%s %d" % (t("server_name_prefix"), len(profiles) + 1)
        profiles.append({"name": p.name, "host": p.host, "port": p.port, "uuid": p.uuid,
                         "path": p.path, "security": p.security, "transport": p.transport})
        self.cfg["current"] = len(profiles) - 1
        save_config(self.cfg)
        dlg.accept()
        self.refresh_profiles()

    def _import_subscription(self, url):
        def worker():
            try:
                profiles = fetch_subscription(url)
                self.sig_sub_done.emit(profiles, None)
            except Exception as e:
                self.sig_sub_done.emit(None, str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _merge_profiles(self, parsed_list):
        profiles = self.cfg.get("profiles", [])
        had_profiles = bool(profiles)
        first_new_index = None
        added = 0
        for p in parsed_list:
            exists = any(existing.get("uuid") == p.uuid and existing.get("host") == p.host
                         and int(existing.get("port", 0)) == p.port for existing in profiles)
            if exists:
                continue
            if not p.name:
                p.name = "%s %d" % (self.tr("server_name_prefix"), len(profiles) + 1)
            profiles.append({"name": p.name, "host": p.host, "port": p.port, "uuid": p.uuid,
                             "path": p.path, "security": p.security, "transport": p.transport})
            if first_new_index is None:
                first_new_index = len(profiles) - 1
            added += 1
        if added > 0:
            if not had_profiles:
                self.cfg["current"] = first_new_index
            save_config(self.cfg)
            self.refresh_profiles()
        return added

    # ---------- settings ----------
    def open_settings(self):
        t = self.tr
        c = self.colors()
        dlg = QDialog(self)
        dlg.setWindowTitle(t("settings"))
        dlg.setFixedWidth(400)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(20, 18, 20, 16)
        l.setSpacing(6)

        lbl = QLabel(t("routing_label"))
        lbl.setStyleSheet("font-size:13px; font-weight:700;")
        l.addWidget(lbl)
        bypass = QCheckBox(t("routing_summary"))
        bypass.setChecked(self.cfg.get("bypass_ru", True))
        bypass.setCursor(Qt.PointingHandCursor)
        l.addWidget(bypass)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet("color:#3A3A48;")
        l.addWidget(sep)

        ll = QLabel(t("language")); ll.setStyleSheet("font-size:13px; font-weight:700;")
        l.addWidget(ll)
        lang_row = QHBoxLayout()
        lang_group = QButtonGroup(self)
        lang_group.setExclusive(True)
        for val, label in (("ru", "Русский"), ("en", "English")):
            rb = QRadioButton(label)
            rb.setCursor(Qt.PointingHandCursor)
            rb.setChecked(self.cfg.get("language", "ru") == val)
            lang_group.addButton(rb, 0 if val == "ru" else 1)
            lang_row.addWidget(rb)
        l.addLayout(lang_row)

        lt = QLabel(t("theme")); lt.setStyleSheet("font-size:13px; font-weight:700;")
        l.addWidget(lt)
        theme_row = QHBoxLayout()
        theme_group = QButtonGroup(self)
        theme_group.setExclusive(True)
        for val, key in (("dark", "dark_theme"), ("light", "light_theme")):
            rb = QRadioButton(t(key))
            rb.setCursor(Qt.PointingHandCursor)
            rb.setChecked(self.cfg.get("theme", "dark") == val)
            theme_group.addButton(rb, 0 if val == "dark" else 1)
            theme_row.addWidget(rb)
        l.addLayout(theme_row)

        ok = RoundButton(t("ok"))
        def save():
            self.cfg["bypass_ru"] = bypass.isChecked()
            if lang_group.checkedId() == 1:
                self.cfg["language"] = "en"
            else:
                self.cfg["language"] = "ru"
            if theme_group.checkedId() == 1:
                self.cfg["theme"] = "light"
            else:
                self.cfg["theme"] = "dark"
            save_config(self.cfg)
            dlg.accept()
            self.apply_theme()
            self.apply_language()
            if self.connected:
                self.reconnect()
        ok.clicked.connect(save)
        l.addWidget(ok)

        dlg.exec()

    def _on_engine_log(self, line):
        pass

    def closeEvent(self, e):
        try:
            self.engine.stop()
        except Exception:
            pass
        SystemProxy.set_proxy(False)
        super().closeEvent(e)


def main():
    if not _is_single_instance():
        return
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    if not _is_admin() and getattr(sys, "frozen", False):
        if _maybe_elevate():
            return
    w = TurboBeeWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
