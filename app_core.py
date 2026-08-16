import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import winreg

APP_NAME = "TurboBee VPN"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TurboBeeVPN")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SOCKS_PORT = 10808
HTTP_PORT = 10809
LOCALHOST_IP = "127.0.0.1"


def get_base_dir():
    if getattr(sys, "_MEIPASS", None):
        return sys._MEIPASS
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_engine_path():
    """Путь к sing-box.exe (основной движок Windows-версии)."""
    exe = os.path.join(get_base_dir(), "sing-box.exe")
    if not os.path.exists(exe):
        exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sing-box.exe")
    return exe


def ensure_config_dir():
    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)


class Profile:
    def __init__(self, name, host, port, uuid, path, security, transport):
        self.name = name
        self.host = host
        self.port = port
        self.uuid = uuid
        self.path = path
        self.security = security
        self.transport = transport


def parse_vless(uri):
    m = re.match(r"^vless://([0-9a-fA-F-]+)@([^:]+):(\d+)(.*)$", uri)
    if not m:
        raise ValueError("Неверная ссылка")
    uuid, host, port, rest = m.group(1), m.group(2), int(m.group(3)), m.group(4)
    params = {}
    name = ""
    if "?" in rest:
        q, frag = rest.split("?", 1)
        if "#" in frag:
            frag, name = frag.split("#", 1)
        for kv in frag.split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k] = v
    elif "#" in rest:
        name = rest.split("#", 1)[1]
    path = params.get("path", "/")
    security = params.get("security", "none")
    transport = params.get("type", "tcp")
    return Profile(name, host, port, uuid, path, security, transport)


def load_config():
    ensure_config_dir()
    default = {"profiles": [], "current": 0, "bypass_ru": True, "language": "ru", "theme": "dark"}
    if not os.path.exists(CONFIG_FILE):
        return default
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        merged = dict(default)
        merged.update(data)
        return merged
    except Exception:
        return default


def save_config(cfg):
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def build_singbox_config(profile, bypass_ru):
    """Строит конфиг sing-box по образцу KaPRO TUN: native TUN (gvisor, mtu 1400),
    авто-маршрутизация, системный DNS. Правила geoip-ru/geosite-ru берутся из
    скомпилированных rule-set файлов (.srs), которые кладёт VpnEngine."""
    routes = [
        {"action": "sniff"},
        {"protocol": "dns", "action": "hijack-dns"},
    ]
    rule_set = []
    if bypass_ru:
        routes.append({
            "action": "route",
            "rule_set": ["geoip-ru", "geosite-ru"],
            "outbound": "direct",
        })
        rule_set = [
            {"type": "local", "tag": "geoip-ru", "format": "binary", "path": "geoip-ru.srs"},
            {"type": "local", "tag": "geosite-ru", "format": "binary", "path": "geosite-ru.srs"},
        ]

    outbound = {
        "type": "vless",
        "tag": "proxy",
        "server": profile.host,
        "server_port": profile.port,
        "uuid": profile.uuid,
        "flow": "",
    }
    if profile.security == "tls":
        outbound["tls"] = {
            "enabled": True,
            "server_name": profile.host,
            "utls": {"enabled": True, "fingerprint": "chrome"},
            "alpn": ["http/1.1"],
        }
    if profile.transport == "ws":
        outbound["transport"] = {
            "type": "ws",
            "path": profile.path,
            "headers": {"Host": profile.host},
        }

    config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [{"type": "local", "tag": "dns-local"}],
            "final": "dns-local",
            "strategy": "ipv4_only",
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "turbobee",
                "address": ["10.0.0.1/16", "fc00::1/64"],
                "mtu": 1400,
                "auto_route": True,
                "strict_route": False,
                "stack": "gvisor",
                "endpoint_independent_nat": True,
            },
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": LOCALHOST_IP,
                "listen_port": SOCKS_PORT,
            },
        ],
        "outbounds": [
            outbound,
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
        ],
        "route": {
            "auto_detect_interface": True,
            "final": "proxy",
            "rules": routes,
            "rule_set": rule_set,
        },
    }
    return json.dumps(config, ensure_ascii=False)


class SystemProxy:
    PROXY_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    @staticmethod
    def set_proxy(enabled):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SystemProxy.PROXY_SETTINGS, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "127.0.0.1:%d" % SOCKS_PORT)
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
            else:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        _refresh_wininet()

    @staticmethod
    def get_proxy_state():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SystemProxy.PROXY_SETTINGS, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "ProxyEnable")
                return bool(val)
        except Exception:
            return False


def _refresh_wininet():
    try:
        import ctypes
        INTERNET_OPTION_SETTINGS_CHANGED = 39
        INTERNET_OPTION_REFRESH = 37
        internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
        internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
    except Exception:
        pass


class VpnEngine:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.log_listeners = []

    def add_log_listener(self, fn):
        self.log_listeners.append(fn)

    def _emit(self, line):
        for fn in list(self.log_listeners):
            try:
                fn(line)
            except Exception:
                pass

    def start(self, config_json):
        self.stop()
        engine = get_engine_path()
        if not os.path.exists(engine):
            raise FileNotFoundError("sing-box.exe не найден рядом с приложением")
        temp_dir = os.path.join(CONFIG_DIR, "runtime")
        os.makedirs(temp_dir, exist_ok=True)
        config_path = os.path.join(temp_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_json)
        for name in ("geoip-ru.srs", "geosite-ru.srs", "wintun.dll"):
            src = os.path.join(get_base_dir(), name)
            if os.path.exists(src) and not os.path.exists(os.path.join(temp_dir, name)):
                import shutil
                shutil.copy2(src, os.path.join(temp_dir, name))
        creationflags = 0
        try:
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
        except AttributeError:
            pass
        self.process = subprocess.Popen(
            [engine, "run", "-c", config_path],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        if not self.process or not self.process.stdout:
            return
        for raw in iter(self.process.stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line:
                self._emit(line)
        self._emit("[[process-exit]]")

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def test_proxy(self):
        try:
            import urllib.request
            with urllib.request.urlopen("https://api.ipify.org", timeout=10) as r:
                return r.status == 200
        except Exception:
            return False


def get_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=8) as r:
            return r.read().decode().strip()
    except Exception:
        return "?"