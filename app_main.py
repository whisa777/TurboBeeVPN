import os
import random
import sys
import threading

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QSize, QRectF, QVariantAnimation, Signal, QObject
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush, QPen, QLinearGradient, QMovie, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QLineEdit, QCheckBox, QRadioButton,
    QButtonGroup, QDialog, QMessageBox, QSizePolicy, QStackedWidget,
    QMenu, QSystemTrayIcon,
)

from app_core import (
    Profile, parse_vless, load_config, save_config, build_singbox_config,
    VpnEngine, SystemProxy, SOCKS_PORT, TunTrafficMonitor, format_rate, format_bytes,
    fetch_subscription, get_profile_total, add_profile_total, app_log,
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
        "refresh_tip": "Обновить ключи",
        "refresh_keys_loading": "Обновляю ключи…",
        "refresh_keys_none": "Подписок нет. Добавьте ссылку подписки через «Добавить ключ».",
        "refresh_keys_done": "Ключи обновлены (%d)",
        "refresh_keys_failed": "Не удалось обновить:",
        "delete_group_title": "Удалить ключ",
        "delete_group_msg": "Удалить подписку и все её серверы (%d)?",
        "unicorn_theme": "Unicorn",
        "dota2_theme": "Dota 2",
        "back": "← Назад",
        "updates_menu": "Обновления",
        "settings_exit": "Выход",
        "app_version": "Версия %s",
        "update_title": "Доступна новая версия",
        "update_check_title": "Проверка обновлений",
        "update_msg": "Вышла версия %s. Скачать и обновить сейчас?",
        "update_whats_new": "Что нового в %s?",
        "update_checking": "Проверка обновлений…",
        "update_none": "Установлена актуальная версия",
        "update_downloading": "Скачивание обновления…",
        "update_launched": "Обновление запущено. Приложение будет закрыто и перезапущено автоматически.",
        "update_failed": "Не удалось загрузить обновление",
        "check_update_btn": "Проверить обновление",
        "tray_menu_show": "Показать окно",
        "tray_menu_quit": "Выход",
        "tray_hint_body": "Приложение свернуто в трей. Закрыть: правый клик по иконке → Выход.",
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
        "refresh_tip": "Update keys",
        "refresh_keys_loading": "Updating keys…",
        "refresh_keys_none": "No subscriptions. Add a subscription link via «Add key».",
        "refresh_keys_done": "Keys updated (%d)",
        "refresh_keys_failed": "Failed to update:",
        "delete_group_title": "Delete key",
        "delete_group_msg": "Delete the subscription and all its servers (%d)?",
        "unicorn_theme": "Unicorn",
        "dota2_theme": "Dota 2",
        "back": "← Back",
        "updates_menu": "Updates",
        "settings_exit": "Exit",
        "app_version": "Version %s",
        "update_title": "Update available",
        "update_check_title": "Check for updates",
        "update_msg": "Version %s is available. Download and update now?",
        "update_whats_new": "What's new in %s?",
        "update_checking": "Checking for updates…",
        "update_none": "You have the latest version",
        "update_downloading": "Downloading update…",
        "update_launched": "Update launched. The application will close and restart automatically.",
        "update_failed": "Failed to download update",
        "check_update_btn": "Check for updates",
        "tray_menu_show": "Show window",
        "tray_menu_quit": "Exit",
        "tray_hint_body": "The app is minimized to tray. To close: right-click the icon → Exit.",
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

UNICORN = {
    "bg": "#FFF0F5",
    "surface": "#FFF0F5",
    "card": "#FFE4EE",
    "border": "#F5CFDF",
    "text": "#5A2A43",
    "text_secondary": "#B07B96",
    "primary": "#F48FB1",
    "primary_text": "#FFFFFF",
    "accent": "#EC6FA4",
    "hover": "#F06292",
    "green": "#66BB6A",
}

# Тёмная тема Dota 2 — цвета как на Android (dota2_bg / dota2_toolbar / dota2_title).
DOTA2 = {
    "bg": "#000000",
    "surface": "#141418",
    "card": "#1C1C22",
    "border": "#2A2A32",
    "text": "#D4D0CC",
    "text_secondary": "#7E7A76",
    "primary": "#F0A93C",
    "primary_text": "#17130A",
    "accent": "#C8811F",
    "hover": "#E09734",
    "green": "#4CAF50",
}

# Герои Dota 2 (как пул на Android). Имена файлов — в папке Dota2 (без суффикса UP/DOWN).
DOTA2_HEROES = [
    ("pudge", "pudge_hero"),
    ("bounty_hunter", "bounty_hero"),
    ("dark_willow", "willow_hero"),
    ("lina", "lina_hero"),
    ("lion", "lion_hero"),
    ("nevermore", "sf_hero"),
    ("skeleton_king", "wraithking_hero"),
]


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
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        handle = kernel32.CreateMutexW(None, False, "Global\\TurboBeeVPN_SingleInstance")
        if not handle:
            return True
        if ctypes.get_last_error() == 183:
            kernel32.CloseHandle(handle)
            for title in ("TurboBee VPN",):
                hwnd = user32.FindWindowW(None, title)
                if hwnd:
                    user32.ShowWindow(wintypes.HWND(hwnd), 9)
                    user32.SetForegroundWindow(wintypes.HWND(hwnd))
                    break
            return False
        _SINGLE_MUTEX_HANDLE = handle
        return True
    except Exception as e:
        try:
            with open(os.path.join(os.environ.get("TEMP", "."), "turbobee_single.log"), "a", encoding="utf-8") as f:
                import traceback
                f.write("SINGLE-INSTANCE ERROR: %r\n%s\n" % (e, traceback.format_exc()))
        except Exception:
            pass
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
        p.setBrush(QColor("#3A3A48" if not self.connected else "#2A2A33"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(cx, cy), 44, 44)
        c = self.color
        p.setBrush(QColor(c))
        p.drawEllipse(QPoint(cx, cy), 36, 36)
        p.setBrush(QColor("#1B1B22" if not self.connected else c))
        p.drawEllipse(QPoint(cx, cy), 20, 20)
        p.setPen(QPen(QColor("#FFFFFF" if self.connected else "#1B1B22"), 3, Qt.SolidLine, Qt.RoundCap))
        f = QFont("Segoe UI Symbol", 22, QFont.Bold)
        p.setFont(f)
        glyph = "✔" if self.connected else "⏻"
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
        layout.addWidget(self.del_btn)
        layout.addWidget(self.marker)
        layout.addWidget(self.name, 1)


class MyScrollArea(QScrollArea):
    pass


class ToggleSwitch(QWidget):
    """Тумблер в стиле iOS с плавной анимацией.

    visual_only=True — только индикация (клики надо вешать на родительскую строку)."""

    toggled = Signal(bool)

    def __init__(self, color_on="#4CAF50", color_track="#3A3A48", checked=False,
                 visual_only=False, parent=None):
        super().__init__(parent)
        self._on = bool(checked)
        self._t = 1.0 if self._on else 0.0
        self._anim = None
        self._visual = visual_only
        self._color_on = color_on
        self._color_track = color_track
        self.setFixedSize(50, 28)
        self.setCursor(Qt.ArrowCursor if visual_only else Qt.PointingHandCursor)

    def is_on(self):
        return self._on

    def set_colors(self, color_on, color_track):
        self._color_on = color_on
        self._color_track = color_track
        self.update()

    def set_on(self, on):
        if self._on == on:
            return
        self._on = on
        start, end = self._t, 1.0 if on else 0.0
        an = QVariantAnimation(self)
        an.setStartValue(start)
        an.setEndValue(end)
        an.setDuration(150)
        an.valueChanged.connect(self._on_anim)
        an.start()
        self._anim = an
        self.toggled.emit(self._on)

    def _on_anim(self, v):
        self._t = float(v)
        self.update()

    def mousePressEvent(self, e):
        if self._visual:
            e.ignore()
            return
        self.set_on(not self._on)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        track = QColor(self._color_on) if self._on else QColor(self._color_track)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(1, 1, w - 2, h - 2, h / 2 - 1, h / 2 - 1)
        knob = 22
        gap = 3
        x = gap + (w - knob - 2 * gap) * self._t
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, (h - knob) / 2, knob, knob))


class TurboBeeWindow(QMainWindow):
    sig_refresh = Signal()
    sig_error = Signal(str)
    sig_sub_done = Signal(object, object)
    sig_refresh_keys = Signal(object)
    sig_update = Signal(object)

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        if self.cfg.get("theme") == "pudge":
            # Тема Pudge заменена темой Dota 2 (как на Android).
            self.cfg["theme"] = "dota2"
            save_config(self.cfg)
        self.cfg.setdefault("total_stats", {})
        self.engine = VpnEngine()
        self.engine.add_log_listener(self._on_engine_log)
        self.traffic = TunTrafficMonitor()
        self.connected = False
        self.proxy_mode = False
        self.session_down = 0
        self.session_up = 0
        self._last_sample = None
        self._dota2_hero = None
        self._dota2_used = []
        self._build_ui()
        self.apply_theme()
        self.apply_language()
        self._setup_tray()
        self.refresh_profiles()
        self._update_status_ui()
        self._refresh_total_label()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(1000)
        self.sig_refresh.connect(self._on_sig_refresh)
        self.sig_error.connect(self._on_sig_error)
        self.sig_sub_done.connect(self._on_sig_sub_done)
        self.sig_refresh_keys.connect(self._on_sig_refresh_keys)
        self.sig_update.connect(self._on_sig_update)
        self.check_for_update_background()
        try:
            from updater import APP_VERSION as _ver
        except Exception:
            _ver = "?"
        app_log("app started v%s" % _ver)

    # ---------- helpers ----------
    def tr(self, key):
        return LANG.get(self.cfg.get("language", "ru"), LANG["ru"]).get(key, key)

    def _theme_key(self):
        theme = self.cfg.get("theme", "dark")
        return "dota2" if theme == "pudge" else theme

    def colors(self):
        theme = self._theme_key()
        if theme == "light":
            return LIGHT
        if theme == "unicorn":
            return UNICORN
        if theme == "dota2":
            return DOTA2
        return DARK

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
        self.settings_btn = QPushButton("☰")
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

        # Картинка для unicorn/dota2 тем (под статусом)
        self.unicorn_lbl = QLabel()
        self.unicorn_lbl.setAlignment(Qt.AlignCenter)
        self.unicorn_lbl.mousePressEvent = lambda e: self.toggle_connect()
        self.unicorn_lbl.setCursor(Qt.PointingHandCursor)
        self.status_layout.addWidget(self.unicorn_lbl, alignment=Qt.AlignCenter)
        self.unicorn_lbl.hide()

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
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_keys)
        self.keys_title_row.addWidget(self.refresh_btn)
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
        self.setStyleSheet(f"""
            QMainWindow {{ background: {c['bg']}; }}
            QWidget {{ background-color: {c['bg']}; color: {c['text']}; }}
            QFrame#statusCard {{ background: {c['surface']}; border-radius: 18px; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: {c['bg']}; width: 8px; }}
            QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            QPushButton {{ }}
        """)
        self.central.setStyleSheet("")
        self.status_card.setObjectName("statusCard")
        theme = self._theme_key()
        if theme in ("unicorn", "dota2"):
            self.status_card.setStyleSheet("#statusCard { background: transparent; border: none; }")
        else:
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
        self.refresh_btn.setStyleSheet(
            f"QPushButton{{border:1px solid {c['border']}; border-radius:14px; color:{c['text_secondary']};"
            f"background:transparent; font-size:15px;}}"
            f"QPushButton:hover{{color:{c['primary']}; border-color:{c['primary']};}}"
            f"QPushButton:disabled{{color:{c['border']}; border-color:{c['border']};}}")
        self.proxy_lbl.setStyleSheet(f"font-size:9px; color:{c['text_secondary']};")
        self.add_btn.set_colors(c["primary"], c["primary_text"], c["hover"])
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
        self.refresh_btn.setToolTip(t("refresh_tip"))
        self.keys_title_lbl.setText("%s (%d)" % (t("my_keys"), len(self.cfg.get("profiles", []))))
        self._update_status_ui()
        self.refresh_profiles()
        self.refresh_proxy_label()
        self._refresh_tray_labels()

    # ---------- system tray ----------
    def _setup_tray(self):
        t = self.tr
        self._really_quitting = False
        self._tray_hint_shown = False
        self.tray = QSystemTrayIcon(QIcon(load_logo() or ""), self)
        self.tray.setToolTip(t("app_title"))
        self.tray_menu = QMenu()
        self.tray_show_action = QAction(t("tray_menu_show"), self.tray_menu)
        self.tray_show_action.triggered.connect(self._show_window_from_tray)
        self.tray_menu.addAction(self.tray_show_action)
        self.tray_menu.addSeparator()
        self.tray_quit_action = QAction(t("tray_menu_quit"), self.tray_menu)
        self.tray_quit_action.triggered.connect(self._quit_from_tray)
        self.tray_menu.addAction(self.tray_quit_action)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _refresh_tray_labels(self):
        # Текст пунктов меняется вместе с языком (см. apply_language).
        if getattr(self, "tray", None) is None:
            return
        t = self.tr
        self.tray.setToolTip(t("app_title"))
        self.tray_show_action.setText(t("tray_menu_show"))
        self.tray_quit_action.setText(t("tray_menu_quit"))

    def _on_tray_activated(self, reason):
        # Левый клик / двойной клик по иконке — показать окно.
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window_from_tray()

    def _show_window_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self):
        self._really_quitting = True
        try:
            self.engine.stop()
        except Exception:
            pass
        SystemProxy.set_proxy(False)
        try:
            self.tray.hide()
        except Exception:
            pass
        QApplication.quit()

    def _update_status_ui(self):
        t = self.tr
        if self.connected:
            self.status_lbl.setText(t("status_on"))
            self.status_hint.setText(t("tap_to_disconnect"))
        else:
            self.status_lbl.setText(t("status_off"))
            self.status_hint.setText(t("tap_to_connect"))
        self._draw_status_dot()

    def _pick_dota2_hero(self):
        """Выбирает случайного неиспользуемого героя (как пул на Android)."""
        used = set(self._dota2_used)
        rest = [h for _, h in DOTA2_HEROES if h not in used]
        if not rest:
            self._dota2_used = []
            rest = [h for _, h in DOTA2_HEROES]
        hero = random.choice(rest)
        self._dota2_used.append(hero)
        self._dota2_hero = hero
        return hero

    def _theme_asset_path(self):
        """Ищет GIF/PNG картинку для темы Unicorn/Dota 2.

        Unicorn: <Stem>UP/DOWN. Dota 2: при подключении — анимация случайного
        героя (<hero>.gif), при отключении — статичная подсказка HelpDOWN."""
        theme = self._theme_key()
        exts = (".gif", ".png", ".jpg")
        if theme == "unicorn":
            folder = "Unicorn"
            state = "UP" if self.connected else "DOWN"
            stems = ["Unicorn" + state + e for e in exts]
        elif theme == "dota2":
            folder = "Dota2"
            if self.connected:
                if not self._dota2_hero:
                    self._pick_dota2_hero()
                stems = [self._dota2_hero + e for e in exts]
            else:
                stems = ["HelpDOWN.png"]
        else:
            return None
        p = os.path.dirname(os.path.abspath(__file__))
        bases = [p]
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", p)
            bases.insert(0, meipass)
        for base in bases:
            for stem in stems:
                cand = os.path.join(base, folder, stem)
                if os.path.exists(cand):
                    return cand
        return None

    def _draw_status_dot(self):
        c = self.colors()
        theme = self._theme_key()
        self.status_dot.set_state(self.connected, c["green"] if self.connected else c["primary"])
        if theme in ("unicorn", "dota2"):
            path = self._theme_asset_path()
            if not path:
                self.unicorn_lbl.hide()
                self.status_dot.show()
                return
            target = QSize(176, 176)
            if path.lower().endswith('.gif'):
                movie = QMovie(path)
                movie.setScaledSize(target)
                self.unicorn_lbl.setMovie(movie)
                movie.start()
            else:
                self.unicorn_lbl.setPixmap(QPixmap(path).scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.unicorn_lbl.setFixedSize(176, 176)
            self.unicorn_lbl.show()
            self.status_dot.hide()
        else:
            self.unicorn_lbl.hide()
            self.status_dot.show()

    # ---------- traffic ----------
    def _on_tick(self):
        if self.connected:
            self._update_traffic_ui()
        elif self._last_sample is not None:
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
        p = profiles[idx]
        src = p.get("source")
        if src:
            group = [x for x in profiles if x.get("source") == src]
            if QMessageBox.question(self, t("delete_group_title"),
                                    t("delete_group_msg") % len(group),
                                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
            self.cfg["profiles"] = [x for x in profiles if x.get("source") != src]
            app_log("key: remove group %s (%d keys)" % (src, len(group)))
        else:
            if QMessageBox.question(self, t("delete_title"), t("delete_msg") % p.get("name", "?"),
                                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
            del self.cfg["profiles"][idx]
            app_log("key: remove \"%s\"" % p.get("name", "?"))
        if self.cfg.get("current", 0) >= len(self.cfg["profiles"]):
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
                p.get("uuid"), p.get("path", "/"), p.get("security", "none"), p.get("transport", "tcp"),
                sni=p.get("sni", ""), fingerprint=p.get("fp", "chrome"),
                public_key=p.get("pbk", ""), short_id=p.get("sid", ""), mode=p.get("mode", "auto"))
            bypass_ru = self.cfg.get("bypass_ru", True)
            use_tun = _is_admin()
            app_log("connect: try \"%s\" %s:%s transport=%s mode=%s tun=%s"
                    % (profile.name, profile.host, profile.port, profile.transport, profile.mode, use_tun))

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
                app_log("connect: OK \"%s\" mode=%s" % (profile.name, "proxy" if self.proxy_mode else "tun"))
            else:
                self.engine.stop()
                SystemProxy.set_proxy(False)
                app_log("connect: FAIL test_proxy \"%s\"" % profile.name)
        except Exception as e:
            self.engine.stop()
            SystemProxy.set_proxy(False)
            app_log("connect: ERROR %r" % (e,))
            self.sig_error.emit(str(e))
        self.sig_refresh.emit()
        self.refresh_proxy_label()

    def disconnect(self):
        self.connected = False
        self.proxy_mode = False
        self._dota2_hero = None
        self._commit_session()
        self._clear_traffic_labels()
        self.engine.stop()
        SystemProxy.set_proxy(False)
        app_log("disconnect: off")
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
        app_log("error: %s" % message)
        QMessageBox.critical(self, self.tr("connect_error"), message)

    def _on_sig_sub_done(self, profiles, error):
        if error:
            app_log("sub: fetch ERROR %r" % (error,))
            QMessageBox.critical(self, self.tr("sub_error"), error)
        else:
            url = getattr(self, "_pending_sub_url", None)
            self._pending_sub_url = None
            added = self._merge_profiles(profiles or [], url)
            app_log("sub: imported %d profiles%s" % (added, " from %s" % url if url else ""))
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
        c = self.colors()
        cancel = RoundButton(t("cancel"))
        cancel.set_colors(c["card"], c["text"], c["border"])
        ok = RoundButton(t("ok"))
        cancel.clicked.connect(dlg.reject)
        ok.clicked.connect(lambda: self._add_submit(entry.text(), dlg))
        btns.addWidget(cancel, 1)
        btns.addWidget(ok, 1)
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
                         "path": p.path, "security": p.security, "transport": p.transport,
                         "sni": p.sni, "fp": p.fingerprint, "pbk": p.public_key,
                         "sid": p.short_id, "mode": p.mode})
        self.cfg["current"] = len(profiles) - 1
        save_config(self.cfg)
        dlg.accept()
        self.refresh_profiles()
        app_log("key: add \"%s\" %s:%s" % (p.name, p.host, p.port))

    def _import_subscription(self, url):
        self._pending_sub_url = url

        def worker():
            try:
                profiles = fetch_subscription(url)
                self.sig_sub_done.emit(profiles, None)
            except Exception as e:
                self.sig_sub_done.emit(None, str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _sources(self):
        seen = []
        for p in self.cfg.get("profiles", []):
            s = p.get("source")
            if s and s not in seen:
                seen.append(s)
        return seen

    def refresh_keys(self):
        t = self.tr
        sources = self._sources()
        if not sources:
            QMessageBox.information(self, t("refresh_tip"), t("refresh_keys_none"))
            return
        self.refresh_btn.setEnabled(False)
        self.keys_title_lbl.setText(t("refresh_keys_loading"))

        def worker():
            results = []
            for src in sources:
                try:
                    profiles = fetch_subscription(src)
                    app_log("refresh: %s -> %d keys" % (src, len(profiles)))
                    results.append((src, profiles, None))
                except Exception as e:
                    app_log("refresh: %s ERROR %r" % (src, (e,)))
                    results.append((src, None, str(e)))
            self.sig_refresh_keys.emit(results)
        threading.Thread(target=worker, daemon=True).start()

    def _replace_source(self, src, parsed):
        t = self.tr
        profiles = self.cfg.get("profiles", [])
        cur = self.cfg.get("current", 0)
        cur_gone = None
        new = []
        for i, p in enumerate(profiles):
            if p.get("source") == src:
                if i == cur:
                    cur_gone = (p.get("uuid"), p.get("host"), int(p.get("port", 0)))
            else:
                new.append(p)
        for p in parsed:
            if not p.name:
                p.name = "%s %d" % (t("server_name_prefix"), len(new) + 1)
            new.append({"name": p.name, "host": p.host, "port": p.port, "uuid": p.uuid,
                        "path": p.path, "security": p.security, "transport": p.transport,
                        "sni": p.sni, "fp": p.fingerprint, "pbk": p.public_key,
                        "sid": p.short_id, "mode": p.mode, "source": src})
        self.cfg["profiles"] = new
        if cur_gone and new:
            for i, p in enumerate(new):
                if (p.get("uuid"), p.get("host"), int(p.get("port", 0))) == cur_gone:
                    self.cfg["current"] = i
                    return
            self.cfg["current"] = cur if cur < len(new) else max(0, len(new) - 1)

    def _on_sig_refresh_keys(self, results):
        t = self.tr
        ok = 0
        fails = []
        for src, profiles, err in results:
            if err:
                fails.append("%s — %s" % (src, err))
            else:
                self._replace_source(src, profiles or [])
                ok += 1
        save_config(self.cfg)
        self.refresh_btn.setEnabled(True)
        self.refresh_profiles()
        self._refresh_total_label()
        if fails:
            QMessageBox.warning(self, t("refresh_keys_failed"), "\n".join(fails[:4]))
        elif ok > 0:
            QMessageBox.information(self, t("refresh_tip"), t("refresh_keys_done") % ok)

    def _merge_profiles(self, parsed_list, url=None):
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
            d = {"name": p.name, "host": p.host, "port": p.port, "uuid": p.uuid,
                 "path": p.path, "security": p.security, "transport": p.transport,
                 "sni": p.sni, "fp": p.fingerprint, "pbk": p.public_key,
                 "sid": p.short_id, "mode": p.mode}
            if url:
                d["source"] = url
            profiles.append(d)
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
    def _choice_row(self, text, checked, onclick):
        """Строка выбора с тумблером-индикатором (как в iOS).

        Возвращает (frame, label, toggle), чтобы обновлять состояние списка."""
        c = self.colors()
        row = QFrame()
        row.setStyleSheet("QFrame { background: transparent; border: none; }")
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 10, 4, 10)
        h.setSpacing(12)
        name = QLabel(text)
        name.setStyleSheet(f"font-size:15px; font-weight:500; color:{c['text']};")
        toggle = ToggleSwitch(color_on=c['green'], color_track=c['border'],
                              checked=checked, visual_only=True)
        h.addWidget(name)
        h.addStretch(1)
        h.addWidget(toggle, 0, Qt.AlignVCenter)
        row.mousePressEvent = lambda e, f=onclick: f()
        for w in (row, name, toggle):
            w.setCursor(Qt.PointingHandCursor)
            w.mousePressEvent = row.mousePressEvent
        return row, name, toggle

    def _make_menu_row(self, text, onclick):
        """Строка главного меню настроек с заголовком и стрелкой."""
        c = self.colors()
        row = QFrame()
        row.setStyleSheet(f"QFrame {{ background: {c['card']}; border-radius: 12px; }}")
        h = QHBoxLayout(row)
        h.setContentsMargins(16, 16, 16, 16)
        name = QLabel(text)
        name.setStyleSheet(f"font-size:14px; font-weight:700; color:{c['text']};")
        arrow = QLabel("›")
        arrow.setStyleSheet(f"font-size:22px; color:{c['primary']}; font-weight:bold;")
        h.addWidget(name)
        h.addStretch(1)
        h.addWidget(arrow)
        row.mousePressEvent = lambda e, f=onclick: f()
        for w in (row, name, arrow):
            w.setCursor(Qt.PointingHandCursor)
            w.mousePressEvent = row.mousePressEvent
        row.label = name
        return row

    def open_settings(self):
        t = self.tr
        c = self.colors()
        dlg = QDialog(self)
        dlg.setWindowTitle(t("settings"))
        dlg.setFixedWidth(400)
        dlg.setMinimumHeight(500)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(0, 0, 0, 0)
        dlg_layout.setSpacing(0)

        stack = QStackedWidget()
        dlg_layout.addWidget(stack)

        # Реестр виджетов диалога для живой перерисовки при смене темы/языка.
        refs = {
            "titles": [],     # (QLabel, key) — заголовки страниц
            "menus": [],      # (QLabel, key) — пункты главного меню
            "rows": [],       # (QLabel, key|None, ToggleSwitch) — строки выбора
            "pages": {},      # page_index -> [(val, QLabel, key, ToggleSwitch)]
            "bypass": None,   # (QLabel, ToggleSwitch)
            "backs": [],      # QPushButton
            "exit": None,     # QPushButton
            "version": None,  # QLabel
        }
        self._dlg_refs = refs
        stack_ref = [stack]

        # --- Страница 0: главное меню настроек ---
        page_main = QWidget()
        page_main_l = QVBoxLayout(page_main)
        page_main_l.setContentsMargins(20, 18, 20, 16)
        page_main_l.setSpacing(8)

        title = QLabel(t("settings"))
        title.setStyleSheet(f"font-size:20px; font-weight:700; color:{c['text']};")
        refs["titles"].append((title, "settings"))
        page_main_l.addWidget(title)
        page_main_l.addSpacing(8)

        for key, idx in (("routing_label", 1), ("language", 2), ("theme", 3), ("updates_menu", 4)):
            mr = self._make_menu_row(t(key), lambda i=idx: stack_ref[0].setCurrentIndex(i))
            refs["menus"].append((mr.label, key))
            page_main_l.addWidget(mr)
        page_main_l.addStretch(1)

        # Кнопка выхода
        exit_btn = RoundButton(t("settings_exit"))
        exit_btn.set_colors("#c0392b", "#FFFFFF", "#e74c3c")
        exit_btn.clicked.connect(dlg.close)
        refs["exit"] = exit_btn
        page_main_l.addWidget(exit_btn)

        stack.addWidget(page_main)

        # --- Страница 1: Маршрутизация ---
        page_routing = QWidget()
        page_routing_l = QVBoxLayout(page_routing)
        page_routing_l.setContentsMargins(20, 18, 20, 16)
        page_routing_l.setSpacing(10)

        rt_title = QLabel(t("routing_label"))
        rt_title.setStyleSheet(f"font-size:20px; font-weight:700; color:{c['text']};")
        refs["titles"].append((rt_title, "routing_label"))
        page_routing_l.addWidget(rt_title)
        page_routing_l.addSpacing(4)

        bypass_row = QFrame()
        bypass_row.setStyleSheet("QFrame { background: transparent; border: none; }")
        bypass_h = QHBoxLayout(bypass_row)
        bypass_h.setContentsMargins(4, 14, 4, 14)
        bypass_h.setSpacing(12)
        bypass_lbl = QLabel(t("routing_summary"))
        bypass_lbl.setWordWrap(True)
        bypass_lbl.setStyleSheet(f"font-size:16px; font-weight:600; color:{c['text']};")
        bypass = ToggleSwitch(color_on=c['green'], color_track=c['border'],
                              checked=self.cfg.get("bypass_ru", True))
        bypass_h.addWidget(bypass_lbl, 1)
        bypass_h.addWidget(bypass, 0, Qt.AlignVCenter)
        refs["bypass"] = (bypass_lbl, bypass)
        page_routing_l.addWidget(bypass_row)
        page_routing_l.addStretch(1)

        back_btn1 = RoundButton(t("back"))
        back_btn1.clicked.connect(lambda: stack.setCurrentIndex(0))
        refs["backs"].append(back_btn1)
        page_routing_l.addWidget(back_btn1)

        def save_routing():
            self.cfg["bypass_ru"] = bypass.is_on()
            save_config(self.cfg)
            if self.connected:
                self.reconnect()

        def click_bypass(e):
            bypass.set_on(not bypass.is_on())

        for w in (bypass_row, bypass_lbl):
            w.setCursor(Qt.PointingHandCursor)
            w.mousePressEvent = click_bypass
        bypass.toggled.connect(lambda _: save_routing())
        stack.addWidget(page_routing)

        # --- Страница 2: Язык ---
        page_lang = QWidget()
        page_lang_l = QVBoxLayout(page_lang)
        page_lang_l.setContentsMargins(20, 18, 20, 16)
        page_lang_l.setSpacing(8)

        lang_title = QLabel(t("language"))
        lang_title.setStyleSheet(f"font-size:20px; font-weight:700; color:{c['text']};")
        refs["titles"].append((lang_title, "language"))
        page_lang_l.addWidget(lang_title)
        page_lang_l.addSpacing(4)

        cur_lang = self.cfg.get("language", "ru")
        lang_rows = []

        def pick_lang(v):
            self.cfg["language"] = v
            save_config(self.cfg)
            self.apply_language()
            self.apply_theme()
            self._sync_choice_rows(lang_rows, self.cfg.get("language", "ru"))
            self._refresh_settings_dialog()

        for val, label in (("ru", "Русский"), ("en", "English")):
            row, name, toggle = self._choice_row(
                label, cur_lang == val, lambda v=val: pick_lang(v))
            lang_rows.append((val, name, None, toggle))
            refs["rows"].append((name, None, toggle))
            page_lang_l.addWidget(row)
        refs["pages"][2] = lang_rows

        page_lang_l.addStretch(1)
        back_btn2 = RoundButton(t("back"))
        back_btn2.clicked.connect(lambda: stack.setCurrentIndex(0))
        refs["backs"].append(back_btn2)
        page_lang_l.addWidget(back_btn2)
        stack.addWidget(page_lang)

        # --- Страница 3: Тема ---
        page_theme = QWidget()
        page_theme_l = QVBoxLayout(page_theme)
        page_theme_l.setContentsMargins(20, 18, 20, 16)
        page_theme_l.setSpacing(8)

        th_title = QLabel(t("theme"))
        th_title.setStyleSheet(f"font-size:20px; font-weight:700; color:{c['text']};")
        refs["titles"].append((th_title, "theme"))
        page_theme_l.addWidget(th_title)
        page_theme_l.addSpacing(4)

        cur_theme = self.cfg.get("theme", "dark")
        theme_options = [
            ("dark", t("dark_theme"), "dark_theme"),
            ("light", t("light_theme"), "light_theme"),
            ("unicorn", t("unicorn_theme"), "unicorn_theme"),
            ("dota2", t("dota2_theme"), "dota2_theme"),
        ]
        theme_rows = []

        def pick_theme(v):
            self.cfg["theme"] = v
            save_config(self.cfg)
            self.apply_theme()
            self.apply_language()
            self._sync_choice_rows(theme_rows, self.cfg.get("theme", "dark"))
            self._refresh_settings_dialog()

        for val, label, tkey in theme_options:
            row, name, toggle = self._choice_row(
                label, cur_theme == val, lambda v=val: pick_theme(v))
            theme_rows.append((val, name, tkey, toggle))
            refs["rows"].append((name, tkey, toggle))
            page_theme_l.addWidget(row)
        refs["pages"][3] = theme_rows

        page_theme_l.addStretch(1)
        back_btn3 = RoundButton(t("back"))
        back_btn3.clicked.connect(lambda: stack.setCurrentIndex(0))
        refs["backs"].append(back_btn3)
        page_theme_l.addWidget(back_btn3)
        stack.addWidget(page_theme)

        # --- Страница 4: Обновления ---
        page_updates = QWidget()
        page_updates_l = QVBoxLayout(page_updates)
        page_updates_l.setContentsMargins(20, 18, 20, 16)
        page_updates_l.setSpacing(10)

        up_title = QLabel(t("updates_menu"))
        up_title.setStyleSheet(f"font-size:20px; font-weight:700; color:{c['text']};")
        refs["titles"].append((up_title, "updates_menu"))
        page_updates_l.addWidget(up_title)
        page_updates_l.addSpacing(4)

        try:
            from updater import APP_VERSION
            ver_text = t("app_version") % APP_VERSION
        except ImportError:
            ver_text = t("app_version") % "?"

        ver_lbl = QLabel(ver_text)
        ver_lbl.setStyleSheet(f"font-size:13px; color:{c['text_secondary']};")
        refs["version"] = ver_lbl
        page_updates_l.addWidget(ver_lbl)
        page_updates_l.addSpacing(8)

        self._updater_btn = RoundButton(t("check_update_btn"))
        self._updater_btn.clicked.connect(self.check_for_update_now)
        page_updates_l.addWidget(self._updater_btn)

        page_updates_l.addStretch(1)
        back_btn4 = RoundButton(t("back"))
        back_btn4.clicked.connect(lambda: stack.setCurrentIndex(0))
        refs["backs"].append(back_btn4)
        page_updates_l.addWidget(back_btn4)
        stack.addWidget(page_updates)

        dlg.exec()

    def _sync_choice_rows(self, page_rows, current_val):
        """Выбранному пункту включаем тумблер, остальным — выключаем."""
        for val, _, _, toggle in page_rows:
            toggle.set_on(val == current_val)

    def _refresh_settings_dialog(self):
        """Перекраска и перевод текстов открытого диалога настроек."""
        t = self.tr
        c = self.colors()
        refs = getattr(self, "_dlg_refs", None)
        if not refs:
            return
        for w, key in refs["titles"]:
            w.setText(t(key))
            w.setStyleSheet(f"font-size:20px; font-weight:700; color:{c['text']};")
        for w, key in refs["menus"]:
            w.setText(t(key))
            w.setStyleSheet(f"font-size:14px; font-weight:700; color:{c['text']};")
        for w, key, toggle in refs["rows"]:
            if key is not None:
                w.setText(t(key))
            w.setStyleSheet(f"font-size:15px; font-weight:500; color:{c['text']};")
            toggle.set_colors(c['green'], c['border'])
        for b in refs["backs"]:
            b.setText(t("back"))
        if refs["exit"] is not None:
            refs["exit"].setText(t("settings_exit"))
        if refs["version"] is not None:
            try:
                from updater import APP_VERSION
                ver = APP_VERSION
            except ImportError:
                ver = "?"
            refs["version"].setText(t("app_version") % ver)
            refs["version"].setStyleSheet(f"font-size:13px; color:{c['text_secondary']};")
        if refs["bypass"] is not None:
            lbl, tg = refs["bypass"]
            lbl.setText(t("routing_summary"))
            lbl.setStyleSheet(f"font-size:16px; font-weight:600; color:{c['text']};")
            tg.set_colors(c['green'], c['border'])

    # ---------- обновления ----------
    def check_for_update_background(self):
        """Фоновая проверка обновлений при запуске."""
        def worker():
            try:
                from updater import get_available_update
            except Exception:
                return
            info = get_available_update()
            if info:
                self.sig_update.emit(info)
        threading.Thread(target=worker, daemon=True).start()

    def check_for_update_now(self):
        """Ручная проверка обновлений из настроек."""
        t = self.tr
        self._updater_btn.setText(t("update_checking"))

        def worker():
            try:
                from updater import get_available_update
            except Exception:
                self.sig_update.emit(("__failed__", None))
                return
            info = get_available_update()
            if info:
                self.sig_update.emit(info)
            else:
                self.sig_update.emit(("__none__", None))
        threading.Thread(target=worker, daemon=True).start()

    def _on_sig_update(self, info):
        """Обработка сигнала об обновлении."""
        t = self.tr
        if info is None:
            return
        if isinstance(info, tuple) and len(info) == 2 and info[0] == "__launched__":
            # Установщик запущен — закрываем приложение автоматически, без
            # ожидания клика. Иначе старый exe залочен и Inno не сможет его
            # перезаписать ("уже открыта").
            self.close()
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(0, app.quit)
            return
        if isinstance(info, tuple) and len(info) == 2 and info[0] == "__failed_dl__":
            err = info[1]
            box = t("update_failed")
            if err:
                box += "\n" + str(err)
            QMessageBox.warning(self, t("update_check_title"), box)
            return
        if isinstance(info, tuple) and len(info) == 2 and info[0] in ("__failed__", "__none__"):
            key = info[0]
            if key == "__failed__":
                QMessageBox.warning(self, t("update_check_title"), t("update_failed"))
                return
            if key == "__none__":
                QMessageBox.information(self, t("update_check_title"), t("update_none"))
                return
        new_version = info[0]
        url = info[1]
        changelog = info[2] if len(info) > 2 else ""
        msg = t("update_msg") % new_version
        if changelog:
            msg += "\n\n" + t("update_whats_new") % new_version + "\n- " + "\n- ".join(
                [ln for ln in changelog.split("\n") if ln.strip()])
        box = QMessageBox(QMessageBox.Question, t("update_title"), msg, parent=self)
        btn_yes = box.addButton("Да", QMessageBox.YesRole)
        box.addButton("Нет", QMessageBox.NoRole)
        box.setDefaultButton(btn_yes)
        box.exec()
        if box.clickedButton() is btn_yes:
            self._download_and_install(url)

    def _download_and_install(self, url):
        """Скачивание и установка обновления."""
        from updater import download_and_install

        def worker():
            def progress(pct):
                pass
            try:
                download_and_install(url, progress_cb=progress)
                self.sig_update.emit(("__launched__", None))
            except Exception as e:
                self.sig_update.emit(("__failed_dl__", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _on_engine_log(self, line):
        app_log("[engine] " + line)

    def closeEvent(self, e):
        if self._really_quitting or not QSystemTrayIcon.isSystemTrayAvailable():
            try:
                self.engine.stop()
            except Exception:
                pass
            SystemProxy.set_proxy(False)
            super().closeEvent(e)
            return
        # X / Alt+F4 — сворачиваем в трей. Реальный выход — только из трея.
        e.ignore()
        self.hide()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.showMessage(self.tr("app_title"), self.tr("tray_hint_body"),
                                  QIcon(load_logo() or ""), 4000)


def main():
    if not _is_single_instance():
        return
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
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
