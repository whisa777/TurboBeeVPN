import tkinter as tk
from tkinter import messagebox, ttk
import threading
import webbrowser

from app_core import (
    Profile, parse_vless, load_config, save_config, build_singbox_config,
    VpnEngine, SystemProxy, SOCKS_PORT, TunTrafficMonitor, format_rate, format_bytes,
    fetch_subscription,
)

LANG = {
    "ru": {
        "app_title": "TurboBee VPN",
        "status_off": "Отключено",
        "status_on": "Подключено",
        "status_connecting": "Подключение...",
        "status_failed": "Ошибка подключения",
        "current_key": "Текущий ключ",
        "no_key": "Нет ключа",
        "tap_to_connect": "Нажмите, чтобы подключиться",
        "tap_to_disconnect": "Нажмите, чтобы отключиться",
        "my_keys": "Мои ключи",
        "no_keys": "Нет ключей. Добавьте через «Добавить ключ».",
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
        "sub_loading": "Загружаю подписку...",
        "sub_added": "Подписка добавлена: новых серверов — %d",
        "sub_error": "Ошибка подписки",
    },
    "en": {
        "app_title": "TurboBee VPN",
        "status_off": "Disconnected",
        "status_on": "Connected",
        "status_connecting": "Connecting...",
        "status_failed": "Connection failed",
        "current_key": "Current key",
        "no_key": "No key",
        "tap_to_connect": "Tap to connect",
        "tap_to_disconnect": "Tap to disconnect",
        "my_keys": "My keys",
        "no_keys": "No keys. Add one via «Add key».",
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
        "sub_loading": "Loading subscription...",
        "sub_added": "Subscription added: %d new servers",
        "sub_error": "Subscription error",
    },
}

LIGHT = {
    "bg": "#FDF9F0",
    "surface": "#FFFFFF",
    "card": "#F5F1E8",
    "text": "#2B2B2B",
    "text_secondary": "#6B6B6B",
    "primary": "#E6A23C",
    "primary_text": "#FFFFFF",
    "accent": "#C87F1C",
    "border": "#E8E2D5",
    "badge_bg": "#F0E6CF",
    "badge_text": "#7A5410",
    "hover": "#EAE3D2",
}

DARK = {
    "bg": "#121212",
    "surface": "#1E1E1E",
    "card": "#262626",
    "text": "#F5F5F5",
    "text_secondary": "#A8A8A8",
    "primary": "#E8B55E",
    "primary_text": "#1A1507",
    "accent": "#C87F1C",
    "border": "#3F3F46",
    "badge_bg": "#2A2416",
    "badge_text": "#E6B86A",
    "hover": "#2C2C2C",
}


class RoundedFrame(tk.Canvas):
    def __init__(self, master, radius=14, fill="", outline="", **kw):
        self._radius = radius
        self._fill = fill
        self._outline = outline
        self._inner = None
        kw.setdefault("height", 1)
        super().__init__(master, highlightthickness=0, bd=0, bg=master.cget("bg"), **kw)
        self.bind("<Configure>", self._draw)
        self._inner = tk.Frame(self, bg=fill)
        self._win = self.create_window(0, 0, window=self._inner, anchor="nw")
        self.after(50, self._sync_height)

    def _sync_height(self, event=None):
        reqh = self._inner.winfo_reqheight()
        if reqh and reqh != self.winfo_height():
            try:
                self.configure(height=reqh)
            except Exception:
                pass

    def _rounded_points(self, w, h, r):
        return [
            r, 0,  w - r, 0,  w, 0,  w, r,
            w, h - r,  w, h,  w - r, h,  r, h,
            0, h,  0, h - r,  0, r,  0, 0,
        ]

    def _draw(self, event=None):
        try:
            reqh = self._inner.winfo_reqheight()
            if reqh > 2 and reqh != self.winfo_height():
                self.configure(height=reqh)
        except Exception:
            pass
        self.delete("shape")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 2 or h <= 2:
            return
        r = min(self._radius, w // 2, h // 2)
        self.create_polygon(self._rounded_points(w, h, r), smooth=True,
                            fill=self._fill, outline=self._outline, tags=("shape",))
        self.tag_lower("shape")
        self.coords(self._win, 0, 0)
        self.itemconfigure(self._win, width=w, height=h)

    def inner(self):
        return self._inner

    def set_bg(self, color):
        self._fill = color
        self._inner.configure(bg=color)
        self._draw()

    def get_bg(self):
        return self._fill


class TurboBeeApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.engine = VpnEngine()
        self.engine.add_log_listener(self._on_engine_log)
        self.traffic = TunTrafficMonitor()
        self.connected = False
        self.proxy_mode = False
        self._build_ui()
        self.apply_theme()
        self.apply_language()
        self.refresh_profiles()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._poll_traffic_loop()

    def tr(self, key):
        return LANG.get(self.cfg.get("language", "ru"), LANG["ru"]).get(key, key)

    def colors(self):
        return DARK if self.cfg.get("theme", "dark") == "dark" else LIGHT

    def _apply_titlebar(self, c):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            dark = 1 if c is DARK else 0
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(dark)), ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass

    def _build_ui(self):
        self.root.title("TurboBee VPN")
        self.root.geometry("420x640")
        self.root.minsize(380, 560)
        self.bg = tk.Frame(self.root)
        self.bg.pack(fill="both", expand=True)

        self.header = tk.Frame(self.bg)
        self.header.pack(fill="x", pady=(14, 6))
        self.title_lbl = tk.Label(self.header, text="TurboBee VPN", font=("Segoe UI", 18, "bold"))
        self.title_lbl.pack(side="left", padx=18)
        self.settings_btn = tk.Button(self.header, text="⚙", font=("Segoe UI", 16), relief="flat",
                                      cursor="hand2", command=self.open_settings)
        self.settings_btn.pack(side="right", padx=14)

        self.sep = tk.Frame(self.bg, height=1)
        self.sep.pack(fill="x", padx=16)

        self.status_card = RoundedFrame(self.bg, radius=16, fill=self.colors()["surface"])
        self.status_card.pack(fill="x", padx=16, pady=(16, 6))
        self.status_card.bind("<Button-1>", lambda e: self.toggle_connect())
        self.status_dot = tk.Canvas(self.status_card.inner(), width=92, height=92, highlightthickness=0,
                                    bg=self.colors()["surface"], cursor="hand2")
        self.status_dot.pack(pady=(18, 6))
        self.status_lbl = tk.Label(self.status_card.inner(), text="", font=("Segoe UI", 15, "bold"))
        self.status_lbl.pack(pady=(0, 2))
        self.status_hint = tk.Label(self.status_card.inner(), text="", font=("Segoe UI", 9))
        self.status_hint.pack(pady=(0, 8))

        self.traffic_frame = tk.Frame(self.status_card.inner(), bg=self.colors()["surface"])
        self.traffic_frame.pack(fill="x", padx=14, pady=(0, 12))
        self.traffic_up_lbl = tk.Label(self.traffic_frame, text="↑ 0 Б/с", font=("Segoe UI", 10, "bold"),
                                       bg=self.colors()["surface"])
        self.traffic_up_lbl.pack(side="left", padx=4)
        self.traffic_down_lbl = tk.Label(self.traffic_frame, text="↓ 0 Б/с", font=("Segoe UI", 10, "bold"),
                                         bg=self.colors()["surface"])
        self.traffic_down_lbl.pack(side="right", padx=4)
        self.traffic_total_lbl = tk.Label(self.status_card.inner(), text="", font=("Segoe UI", 8),
                                          bg=self.colors()["surface"])
        self.traffic_total_lbl.pack(pady=(0, 10))

        for w in (self.status_card.inner(), self.status_dot, self.status_lbl, self.status_hint,
                  self.traffic_frame, self.traffic_up_lbl, self.traffic_down_lbl, self.traffic_total_lbl):
            w.bind("<Button-1>", lambda e: self.toggle_connect())
        self._draw_status_dot()

        self.keys_title = tk.Frame(self.bg)
        self.keys_title.pack(fill="x", padx=16, pady=(10, 2))
        self.keys_title_lbl = tk.Label(self.keys_title, text="", font=("Segoe UI", 12, "bold"), cursor="hand2")
        self.keys_title_lbl.pack(side="left", padx=4)
        self.keys_title_lbl.bind("<Button-1>", lambda e: self.toggle_keys_visible())

        self.add_btn = RoundedFrame(self.bg, radius=12, fill=self.colors()["primary"], cursor="hand2")
        self.add_btn.pack(fill="x", padx=16, pady=(6, 12))
        self.add_btn_lbl = tk.Label(self.add_btn.inner(), text="", font=("Segoe UI", 11, "bold"),
                                    bg=self.colors()["primary"], fg=self.colors()["primary_text"], cursor="hand2")
        self.add_btn_lbl.pack(pady=10)
        self.add_btn.bind("<Button-1>", lambda e: self.open_add_dialog())
        self.add_btn_lbl.bind("<Button-1>", lambda e: self.open_add_dialog())
        self.add_btn.bind("<Enter>", lambda e: self._btn_hover(True))
        self.add_btn.bind("<Leave>", lambda e: self._btn_hover(False))
        self.add_btn_lbl.bind("<Enter>", lambda e: self._btn_hover(True))
        self.add_btn_lbl.bind("<Leave>", lambda e: self._btn_hover(False))

        self.proxy_lbl = tk.Label(self.bg, text="", font=("Segoe UI", 8))
        self.proxy_lbl.pack(fill="x", padx=16, pady=(0, 8))

        self.keys_frame = tk.Frame(self.bg)
        self.keys_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        self.keys_canvas = tk.Canvas(self.keys_frame, highlightthickness=0)
        self.keys_scroll = ttk.Scrollbar(self.keys_frame, orient="vertical", command=self.keys_canvas.yview)
        self.keys_inner = tk.Frame(self.keys_canvas)
        self.keys_inner.bind("<Configure>", lambda e: self.keys_canvas.configure(scrollregion=self.keys_canvas.bbox("all")))
        self.keys_canvas.create_window((0, 0), window=self.keys_inner, anchor="nw")
        self.keys_canvas.configure(yscrollcommand=self.keys_scroll.set)
        self.keys_canvas.pack(side="left", fill="both", expand=True)
        self.keys_scroll.pack(side="right", fill="y")

        def _on_wheel(e):
            self.keys_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

        self.keys_canvas.bind("<MouseWheel>", _on_wheel)
        self.keys_inner.bind("<MouseWheel>", _on_wheel)
        self.keys_frame.bind("<MouseWheel>", _on_wheel)

    def _btn_hover(self, on):
        c = self.colors()
        fill = c["accent"] if on else c["primary"]
        try:
            self.add_btn.set_bg(fill)
            self.add_btn_lbl.configure(bg=fill)
        except Exception:
            pass

    def apply_theme(self):
        c = self.colors()
        self.root.configure(bg=c["bg"])
        self._apply_titlebar(c)
        for w in (self.bg,):
            w.configure(bg=c["bg"])
        self.header.configure(bg=c["bg"])
        self.sep.configure(bg=c["border"])
        self.keys_title.configure(bg=c["bg"])
        self.title_lbl.configure(bg=c["bg"], fg=c["text"])
        self.settings_btn.configure(bg=c["bg"], fg=c["primary"], activebackground=c["hover"], activeforeground=c["primary"])
        self.status_card.set_bg(c["surface"])
        self.status_dot.configure(bg=c["surface"])
        self.status_lbl.configure(bg=c["surface"], fg=c["text"])
        self.status_hint.configure(bg=c["surface"], fg=c["text_secondary"])
        self.traffic_frame.configure(bg=c["surface"])
        for w in (self.traffic_up_lbl, self.traffic_down_lbl):
            w.configure(bg=c["surface"], fg=c["primary"])
        self.traffic_total_lbl.configure(bg=c["surface"], fg=c["text_secondary"])
        self._draw_status_dot()
        self.add_btn.set_bg(c["primary"])
        self.add_btn_lbl.configure(bg=c["primary"], fg=c["primary_text"])
        self.keys_title_lbl.configure(bg=c["bg"], fg=c["text"])
        self.keys_frame.configure(bg=c["bg"])
        self.keys_canvas.configure(bg=c["bg"])
        self.keys_inner.configure(bg=c["bg"])
        self.proxy_lbl.configure(bg=c["bg"], fg=c["text_secondary"])
        for child in self.keys_inner.winfo_children():
            self._theme_key_row(child)
        self._style_scrollbar()

    def _style_scrollbar(self):
        c = self.colors()
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TScrollbar", background=c["surface"], troughcolor=c["bg"],
                        bordercolor=c["bg"], arrowcolor=c["text_secondary"])

    def apply_language(self):
        t = self.tr
        self.root.title(t("app_title"))
        self.title_lbl.configure(text=t("app_title"))
        self.settings_btn.configure(text="⚙")
        self.add_btn_lbl.configure(text=t("add_key_btn"))
        self._update_status_ui()
        self.keys_title_lbl.configure(text="%s (%d)" % (t("my_keys"), len(self.cfg.get("profiles", []))))
        for child in self.keys_inner.winfo_children():
            child.destroy()
        self.refresh_profiles()
        self.refresh_proxy_label()

    def _update_status_ui(self):
        t = self.tr
        if self.connected:
            self.status_lbl.configure(text=t("status_on"))
            self.status_hint.configure(text=t("tap_to_disconnect"))
        else:
            self.status_lbl.configure(text=t("status_off"))
            self.status_hint.configure(text=t("tap_to_connect"))
        self._draw_status_dot()

    def _draw_status_dot(self):
        try:
            c = self.colors()
            cv = self.status_dot
            cv.delete("all")
            bg = c["surface"]
            fill = "#4CAF50" if self.connected else c["primary"]
            ring = c["border"]
            cv.configure(bg=bg)
            cv.create_oval(8, 8, 84, 84, fill=ring, outline="")
            cv.create_oval(14, 14, 78, 78, fill=fill, outline="")
            cv.create_oval(26, 26, 66, 66, fill=fill, outline=fill)
            label = "✔" if self.connected else "⏻"
            cv.create_text(46, 46, text=label, fill="#1A1507" if not self.connected else "#FFFFFF",
                           font=("Segoe UI", 30, "bold"))
        except Exception:
            pass

    def _poll_traffic_loop(self):
        if self.connected:
            self._update_traffic_ui()
        self.root.after(1000, self._poll_traffic_loop)

    def _update_traffic_ui(self):
        try:
            t = self.tr
            sample = self.traffic.sample()
            if not sample:
                self.traffic_up_lbl.configure(text="↑ --")
                self.traffic_down_lbl.configure(text="↓ --")
                self.traffic_total_lbl.configure(text=t("traffic_total") % ("--", "--"))
                return
            up_total, down_total, up_bps, down_bps = sample
            self.traffic_up_lbl.configure(text="↑ " + format_rate(up_bps))
            self.traffic_down_lbl.configure(text="↓ " + format_rate(down_bps))
            self.traffic_total_lbl.configure(
                text=t("traffic_total") % (format_bytes(down_total), format_bytes(up_total)))
        except Exception:
            pass

    def refresh_profiles(self):
        t = self.tr
        profiles = self.cfg.get("profiles", [])
        self.keys_title_lbl.configure(text="%s (%d)" % (t("my_keys"), len(profiles)))
        for child in self.keys_inner.winfo_children():
            child.destroy()
        if not profiles:
            lbl = tk.Label(self.keys_inner, text=t("no_keys"), font=("Segoe UI", 9), wraplength=340, justify="left")
            lbl.pack(fill="x", padx=8, pady=6)
            lbl.configure(bg=self.colors()["bg"], fg=self.colors()["text_secondary"])
            lbl.bind("<MouseWheel>", self._on_key_wheel)
        for i, p in enumerate(profiles):
            self._add_key_row(i, p)
        self.apply_theme()

    def _add_key_row(self, idx, p):
        c = self.colors()
        row = RoundedFrame(self.keys_inner, radius=10, fill=c["surface"])
        row.pack(fill="x", padx=2, pady=3)
        inner = row.inner()
        is_current = idx == self.cfg.get("current", 0)
        marker = "●" if is_current else "○"
        marker_lbl = tk.Label(inner, text=marker, font=("Segoe UI", 10), width=2)
        marker_lbl.pack(side="left", padx=(10, 4), pady=8)
        marker_lbl.configure(bg=c["surface"], fg=c["primary"] if is_current else c["text_secondary"])
        name_lbl = tk.Label(inner, text=p.get("name", "?"), font=("Segoe UI", 10), anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True, pady=8)
        name_lbl.configure(bg=c["surface"], fg=c["text"])
        for w in (inner, marker_lbl, name_lbl):
            w.bind("<Button-1>", lambda e, i=idx: self.select_key(i))
            w.bind("<MouseWheel>", self._on_key_wheel)
        del_btn = tk.Label(inner, text="✕", font=("Segoe UI", 10), cursor="hand2")
        del_btn.pack(side="right", padx=12, pady=8)
        del_btn.configure(bg=c["surface"], fg=c["accent"])
        del_btn.bind("<Button-1>", lambda e, i=idx: self.delete_key(i))
        del_btn.bind("<MouseWheel>", self._on_key_wheel)

    def _on_key_wheel(self, e):
        try:
            self.keys_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        except Exception:
            pass

    def _theme_key_row(self, row):
        c = self.colors()
        try:
            if hasattr(row, "set_bg"):
                row.set_bg(c["surface"])
                inner = row.inner()
                for w in inner.winfo_children():
                    w.configure(bg=c["surface"])
            else:
                row.configure(bg=c["surface"])
                for w in row.winfo_children():
                    w.configure(bg=c["surface"])
        except Exception:
            pass

    def toggle_keys_visible(self):
        if self.keys_frame.winfo_ismapped():
            self.keys_frame.pack_forget()
        else:
            self.keys_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

    def select_key(self, idx):
        self.cfg["current"] = idx
        save_config(self.cfg)
        self.refresh_profiles()
        if self.connected:
            self.reconnect()

    def delete_key(self, idx):
        t = self.tr
        profiles = self.cfg.get("profiles", [])
        if not messagebox.askyesno(t("delete_title"), t("delete_msg") % profiles[idx].get("name", "?")):
            return
        del profiles[idx]
        if self.cfg.get("current", 0) >= len(profiles):
            self.cfg["current"] = 0
        save_config(self.cfg)
        if self.connected:
            self.reconnect()
        self.refresh_profiles()

    def toggle_connect(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        t = self.tr
        profiles = self.cfg.get("profiles", [])
        if not profiles:
            messagebox.showinfo(t("add_key"), t("no_keys"))
            return
        self.connected = False
        self.status_lbl.configure(text=t("status_connecting"))
        threading.Thread(target=self._do_connect, daemon=True).start()

    def _do_connect(self):
        self.proxy_mode = False
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
                    # TUN не взлетел (напр. драйвер wintun) — откатываемся на прокси-режим
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
            self._emit_error(str(e))
        self.root.after(0, self._update_status_ui)
        self.refresh_proxy_label()

    def disconnect(self):
        self.connected = False
        self.proxy_mode = False
        self.engine.stop()
        SystemProxy.set_proxy(False)
        self._update_status_ui()
        self.refresh_proxy_label()

    def reconnect(self):
        self.disconnect()
        self.connect()

    def refresh_proxy_label(self):
        t = self.tr
        if self.connected:
            if self.proxy_mode:
                self.proxy_lbl.configure(text=t("proxy_set"))
            else:
                self.proxy_lbl.configure(text=t("tun_active"))
        else:
            self.proxy_lbl.configure(text=t("proxy_unset"))

    def _on_engine_log(self, line):
        pass

    def _emit_error(self, msg):
        t = self.tr
        def show():
            self.status_lbl.configure(text=t("status_failed"))
            messagebox.showerror(t("connect_error"), msg)
        self.root.after(0, show)

    def open_add_dialog(self):
        t = self.tr
        dlg = tk.Toplevel(self.root)
        dlg.title(t("add_key"))
        dlg.configure(bg=self.colors()["bg"])
        dlg.geometry("380x140")
        dlg.transient(self.root)
        dlg.grab_set()
        tk.Label(dlg, text=t("enter_link"), font=("Segoe UI", 10), bg=self.colors()["bg"], fg=self.colors()["text"]).pack(padx=14, pady=(14, 6))
        entry = tk.Entry(dlg, font=("Consolas", 9), bg=self.colors()["surface"], fg=self.colors()["text"],
                         insertbackground=self.colors()["text"])
        entry.pack(fill="x", padx=14, pady=(0, 10))
        entry.focus_set()
        def submit():
            uri = entry.get().strip()
            if not uri:
                return
            low = uri.lower()
            if low.startswith("http://") or low.startswith("https://"):
                dlg.destroy()
                self._import_subscription(uri)
                return
            try:
                p = parse_vless(uri)
            except ValueError:
                messagebox.showerror(t("add_key"), t("invalid_link"))
                return
            profiles = self.cfg.get("profiles", [])
            for existing in profiles:
                if (existing.get("uuid") == p.uuid and existing.get("host") == p.host
                        and int(existing.get("port", 0)) == p.port):
                    self.cfg["current"] = profiles.index(existing)
                    save_config(self.cfg)
                    dlg.destroy()
                    self.refresh_profiles()
                    return
            if not p.name:
                p.name = "%s %d" % (t("server_name_prefix"), len(profiles) + 1)
            profiles.append({"name": p.name, "host": p.host, "port": p.port, "uuid": p.uuid,
                             "path": p.path, "security": p.security, "transport": p.transport})
            self.cfg["current"] = len(profiles) - 1
            save_config(self.cfg)
            dlg.destroy()
            self.refresh_profiles()
        tk.Button(dlg, text=t("ok"), command=submit, bg=self.colors()["primary"],
                  fg=self.colors()["primary_text"], relief="flat", padx=24, pady=6, cursor="hand2").pack(pady=(4, 12))
        dlg.bind("<Return>", lambda e: submit())

    def _import_subscription(self, url):
        t = self.tr
        self.status_lbl.configure(text=t("sub_loading"))
        self.root.configure(cursor="wait")
        def worker():
            try:
                profiles = fetch_subscription(url)
                def done():
                    self.root.configure(cursor="")
                    added = self._merge_profiles(profiles)
                    messagebox.showinfo(t("add_key"), t("sub_added") % added)
                self.root.after(0, done)
            except Exception as e:
                msg = str(e)
                def fail():
                    self.root.configure(cursor="")
                    self._update_status_ui()
                    messagebox.showerror(t("sub_error"), msg)
                self.root.after(0, fail)
        threading.Thread(target=worker, daemon=True).start()

    def _merge_profiles(self, parsed_list):
        """Добавляет профили без дублей (uuid+host+port). Возвращает число новых."""
        profiles = self.cfg.get("profiles", [])
        had_profiles = bool(profiles)
        first_new_index = None
        added = 0
        for p in parsed_list:
            exists = False
            for existing in profiles:
                if (existing.get("uuid") == p.uuid and existing.get("host") == p.host
                        and int(existing.get("port", 0)) == p.port):
                    exists = True
                    break
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

    def open_settings(self):
        t = self.tr
        dlg = tk.Toplevel(self.root)
        dlg.title(t("settings"))
        dlg.configure(bg=self.colors()["bg"])
        dlg.geometry("380x320")
        dlg.transient(self.root)
        dlg.grab_set()

        row1 = tk.Frame(dlg, bg=self.colors()["bg"])
        row1.pack(fill="x", padx=18, pady=(16, 4))
        tk.Label(row1, text=t("routing_label"), font=("Segoe UI", 11, "bold"),
                 bg=self.colors()["bg"], fg=self.colors()["text"]).pack(side="left")
        bypass = tk.BooleanVar(value=self.cfg.get("bypass_ru", True))
        cb = tk.Checkbutton(row1, variable=bypass, bg=self.colors()["bg"], activebackground=self.colors()["bg"],
                            selectcolor=self.colors()["surface"], fg=self.colors()["text"])
        cb.pack(side="right")
        tk.Label(dlg, text=t("routing_summary"), font=("Segoe UI", 8),
                 bg=self.colors()["bg"], fg=self.colors()["text_secondary"]).pack(anchor="w", padx=20)

        lang_var = tk.StringVar(value=self.cfg.get("language", "ru"))
        tk.Label(dlg, text=t("language"), font=("Segoe UI", 11, "bold"),
                 bg=self.colors()["bg"], fg=self.colors()["text"]).pack(anchor="w", padx=20, pady=(12, 2))
        lang_frame = tk.Frame(dlg, bg=self.colors()["bg"])
        lang_frame.pack(fill="x", padx=20)
        for val, label in (("ru", "Русский"), ("en", "English")):
            rb = tk.Radiobutton(lang_frame, text=label, variable=lang_var, value=val,
                                bg=self.colors()["bg"], activebackground=self.colors()["bg"],
                                selectcolor=self.colors()["surface"], fg=self.colors()["text"])
            rb.pack(side="left", padx=(0, 18))

        theme_var = tk.StringVar(value=self.cfg.get("theme", "dark"))
        tk.Label(dlg, text=t("theme"), font=("Segoe UI", 11, "bold"),
                 bg=self.colors()["bg"], fg=self.colors()["text"]).pack(anchor="w", padx=20, pady=(12, 2))
        theme_frame = tk.Frame(dlg, bg=self.colors()["bg"])
        theme_frame.pack(fill="x", padx=20)
        for val, key in (("dark", "dark_theme"), ("light", "light_theme")):
            rb = tk.Radiobutton(theme_frame, text=t(key), variable=theme_var, value=val,
                                bg=self.colors()["bg"], activebackground=self.colors()["bg"],
                                selectcolor=self.colors()["surface"], fg=self.colors()["text"])
            rb.pack(side="left", padx=(0, 18))

        def save():
            self.cfg["bypass_ru"] = bypass.get()
            if self.cfg["language"] != lang_var.get():
                self.cfg["language"] = lang_var.get()
            if self.cfg["theme"] != theme_var.get():
                self.cfg["theme"] = theme_var.get()
            save_config(self.cfg)
            dlg.destroy()
            self.apply_theme()
            self.apply_language()
            if self.connected:
                self.reconnect()
        tk.Button(dlg, text=t("ok"), command=save, bg=self.colors()["primary"],
                  fg=self.colors()["primary_text"], relief="flat", padx=28, pady=6, cursor="hand2").pack(pady=(14, 14))

    def on_close(self):
        try:
            self.engine.stop()
        except Exception:
            pass
        SystemProxy.set_proxy(False)
        self.root.destroy()


def _is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


_SINGLE_MUTEX_HANDLE = None


def _is_single_instance():
    """Возвращает True, если это единственный экземпляр. Если приложение
    уже запущено, показывает существующее окно и возвращает False."""
    global _SINGLE_MUTEX_HANDLE
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        handle = kernel32.CreateMutexW(None, False, "Local\\TurboBeeVPN_SingleInstance")
        if not handle:
            return True
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            hwnd = user32.FindWindowW(None, "TurboBee VPN")
            if hwnd:
                user32.ShowWindow(wintypes.HWND(hwnd), 9)  # SW_RESTORE
                user32.SetForegroundWindow(wintypes.HWND(hwnd))
            return False
        _SINGLE_MUTEX_HANDLE = handle
        return True
    except Exception:
        return True


def _elevate():
    try:
        import ctypes
        import sys
        if not getattr(sys, "frozen", False):
            return True
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
        return False
    except Exception:
        return True


def _maybe_elevate():
    import os
    cfg = load_config()
    if cfg.get("elevate_prompted", False):
        return
    cfg["elevate_prompted"] = True
    save_config(cfg)
    from tkinter import messagebox
    from tkinter import Tk
    root = Tk()
    root.withdraw()
    want = messagebox.askyesno(
        "TurboBee VPN",
        "VPN уже работает без прав администратора (системный прокси).\n"
        "Для режима TUN (весь трафик перехватывается автоматически) можно "
        "запустить приложение от имени администратора.\n\n"
        "Перезапустить с правами администратора?",
    )
    root.destroy()
    if want:
        _elevate()


def main():
    if not _is_single_instance():
        return
    if not _is_admin():
        import sys
        if getattr(sys, "frozen", False):
            # Можно работать и без прав (прокси-режим). Перезапуск от имени
            # администратора даёт TUN-режим. Предлагаем один раз.
            try:
                _maybe_elevate()
            except Exception:
                pass
    root = tk.Tk()
    app = TurboBeeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()