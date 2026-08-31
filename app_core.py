import base64
import json
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
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
    try:
        path = urllib.parse.unquote(path)
        name = urllib.parse.unquote(name)
    except Exception:
        pass
    return Profile(name, host, port, uuid, path, security, transport)


def load_config():
    ensure_config_dir()
    default = {"profiles": [], "current": 0, "bypass_ru": True, "language": "ru", "theme": "dark",
               "total_stats": {}}
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


def profile_key(p):
    """Стабильный ключ профиля для статистики (uuid+host+port)."""
    return "%s|%s|%s" % (p.get("uuid", ""), p.get("host", ""), p.get("port", 0))


def get_profile_total(cfg, p):
    """Возвращает (down, up) накопленных байт для профиля."""
    total_stats = cfg.get("total_stats") or {}
    k = profile_key(p)
    stats = total_stats.get(k) or {}
    return stats.get("down", 0), stats.get("up", 0)


def add_profile_total(cfg, p, down, up):
    """Добавляет байты к суммарной статистике профиля и возвращает новые (down, up)."""
    if down <= 0 and up <= 0:
        return get_profile_total(cfg, p)
    total_stats = cfg.get("total_stats") or {}
    k = profile_key(p)
    stats = total_stats.get(k) or {"down": 0, "up": 0}
    stats["down"] = int(stats.get("down", 0)) + int(down)
    stats["up"] = int(stats.get("up", 0)) + int(up)
    total_stats[k] = stats
    cfg["total_stats"] = total_stats
    save_config(cfg)
    return stats["down"], stats["up"]


HWID_FILE = os.path.join(CONFIG_DIR, "hwid.txt")


def get_hwid():
    """Стабильный идентификатор установки: случайный UUID из первого запуска,
    хранится рядом с конфигом (%APPDATA%\\TurboBeeVPN\\hwid.txt)."""
    ensure_config_dir()
    try:
        with open(HWID_FILE, "r", encoding="utf-8") as f:
            hwid = f.read().strip()
        if hwid:
            return hwid
    except Exception:
        pass
    hwid = str(uuid.uuid4())
    with open(HWID_FILE, "w", encoding="utf-8") as f:
        f.write(hwid)
    return hwid


def fetch_subscription(url, timeout=10, max_bytes=2 * 1024 * 1024):
    """Скачивает подписку (список vless:// или base64 от него) и возвращает
    список Profile. Шлёт x-hwid/x-device-model — привязка устройства на сервере."""
    req = urllib.request.Request(url.strip(), headers={
        "User-Agent": "TurboBeeVPN/1.0 (subscription)",
        "x-hwid": get_hwid(),
        "x-device-model": "Windows %s; %s" % (platform.release(), platform.machine()),
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if not (200 <= r.status < 300):
            raise ValueError("HTTP %d" % r.status)
        body = r.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError("Ответ подписки слишком большой")
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("Подписка вернула пустой ответ")
    content = _decode_if_base64(text)
    profiles = []
    for line in content.splitlines():
        l = line.strip()
        if not l.lower().startswith("vless://"):
            continue
        try:
            profiles.append(parse_vless(l))
        except Exception:
            pass
    if not profiles:
        raise ValueError("В подписке не найдено серверов vless")
    return profiles


def _decode_if_base64(text):
    compact = re.sub(r"\s+", "", text)
    if not compact or not re.fullmatch(r"[A-Za-z0-9+/=_-]+", compact):
        return text
    normalized = compact.replace("-", "+").replace("_", "/")
    normalized += "=" * (-len(normalized) % 4)
    try:
        decoded = base64.b64decode(normalized).decode("utf-8", errors="replace")
        if "vless://" in decoded:
            return decoded
    except Exception:
        pass
    return text


def build_singbox_config(profile, bypass_ru, use_tun=True):
    """Строит конфиг sing-box по образцу KaPRO.

    use_tun=True — native TUN (gvisor, mtu 1400), авто-маршрутизация (требуются
    права администратора). use_tun=False — только mixed-inbound на 127.0.0.1,
    работает без прав (трафик направляется через системный прокси).
    Правила geoip-ru/geosite-ru берутся из скомпилированных rule-set (.srs)."""
    routes = [
        {"action": "sniff"},
        # Белый список: сайты, не работающие с зарубежных IP (Сбер, Госуслуги, ВК и др.)
        # всегда уходят напрямую — и в TUN, и в прокси-режиме.
        {
            "action": "route",
            "domain": RU_WHITELIST,
            "outbound": "direct",
        },
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

    inbounds = [
        {
            "type": "mixed",
            "tag": "mixed-in",
            "listen": LOCALHOST_IP,
            "listen_port": SOCKS_PORT,
        },
    ]
    if use_tun:
        routes.insert(1, {"protocol": "dns", "action": "hijack-dns"})
        inbounds.insert(0, {
            "type": "tun",
            "tag": "tun-in",
            "interface_name": "turbobee",
            "address": ["10.0.0.1/16", "fc00::1/64"],
            "mtu": 1400,
            "auto_route": True,
            "strict_route": False,
            "stack": "gvisor",
            "endpoint_independent_nat": True,
        })

    config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [{"type": "local", "tag": "dns-local"}],
            "final": "dns-local",
            "strategy": "ipv4_only",
        },
        "inbounds": inbounds,
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

    def test_proxy(self, timeout=15, attempts=3):
        """Проверяет, что sing-box реально проксирует трафик, запросом через
        собственный mixed-inbound (127.0.0.1:SOCKS_PORT). Не зависит от TUN."""
        for _ in range(attempts):
            if not self.is_running():
                return False
            try:
                handler = urllib.request.ProxyHandler({
                    "http": "http://127.0.0.1:%d" % SOCKS_PORT,
                    "https": "http://127.0.0.1:%d" % SOCKS_PORT,
                })
                opener = urllib.request.build_opener(handler)
                with opener.open("https://api.ipify.org", timeout=timeout) as r:
                    if r.status == 200:
                        return True
            except Exception:
                pass
            time.sleep(1.5)
        return False


def get_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=8) as r:
            return r.read().decode().strip()
    except Exception:
        return "?"


TUN_IFACE_NAME = "turbobee"

# Белый список: домены, которые часто блокируют доступ с зарубежных IP
# (банки, госуслуги, госпорталы). Их трафик всегда идёт напрямую, в обход VPN.
RU_WHITELIST = [
    "sberbank.ru", "sber.ru", "sberbankid.ru", "online.sberbank.ru", "sberbank-insurance.ru",
    "gosuslugi.ru", "gosuslugi.online", "esia.gosuslugi.ru",
    "vk.com", "vk.ru", "ok.ru", "vkontakte.ru", "mail.ru", "mycdn.me",
    "mos.ru", "uslugi.mosreg.ru", "mosreg.ru", "moscow.gosuslugi.ru", "um.mos.ru",
    "nalog.ru", "zakupki.gov.ru", "government.ru", "kremlin.ru", "mintrud.gov.ru", "gosmonitor.ru",
    "rzd.ru", "rt.ru", "pochtabank.ru",
    "avito.ru", "ozon.ru", "wildberries.ru", "wildberries.by",
    "vtb.ru", "alfabank.ru", "tinkoff.ru", "gazprombank.ru", "raiffeisen.ru", "open.ru", "psbank.ru",
    "mk.ru", "rbc.ru", "kaspersky.ru",
]


class TunTrafficMonitor:
    """Считывает суммарные счётчики TUN-интерфейса (аналог KaPRO).

    KaPRO читает psutil.net_io_counters(pernic=True). Здесь то же самое
    делаем через Windows API GetIfTable2 (ctypes, без внешних зависимостей):
    находим сетевой адаптер sing-box TUN ("turbobee") и берём InOctets/
    OutOctets — это cumulative-счётчики за сессию подключения.
    """

    def __init__(self, iface_name=TUN_IFACE_NAME):
        self.iface_name = iface_name
        self.prev_up = None
        self.prev_down = None
        self.prev_ts = None

    def _if_table(self):
        import ctypes
        from ctypes import wintypes
        iphlpapi = ctypes.WinDLL("iphlpapi", use_last_error=True)
        iphlpapi.GetIfTable2.restype = wintypes.DWORD
        iphlpapi.GetIfTable2.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        iphlpapi.FreeMibTable.argtypes = [wintypes.LPVOID]

        # Структура MIB_IF_ROW2 (достаточно полей для вычисления смещений)
        class MIB_IF_ROW2(ctypes.Structure):
            _fields_ = [
                ("InterfaceLuid", ctypes.c_uint64),
                ("InterfaceIndex", ctypes.c_uint32),
                ("InterfaceGuid", ctypes.c_ubyte * 16),
                ("Alias", ctypes.c_wchar * 257),
                ("Description", ctypes.c_wchar * 257),
                ("PhysicalAddressLength", ctypes.c_uint32),
                ("PhysicalAddress", ctypes.c_ubyte * 32),
                ("PermanentPhysicalAddress", ctypes.c_ubyte * 32),
                ("Mtu", ctypes.c_uint32),
                ("Type", ctypes.c_uint32),
                ("TunnelType", ctypes.c_uint32),
                ("MediaType", ctypes.c_uint32),
                ("PhysicalMediumType", ctypes.c_uint32),
                ("AccessType", ctypes.c_uint32),
                ("DirectionType", ctypes.c_uint32),
                ("InterfaceAndOperStatusFlags", ctypes.c_ubyte),
                ("OperStatus", ctypes.c_uint32),
                ("AdminStatus", ctypes.c_uint32),
                ("MediaConnectState", ctypes.c_uint32),
                ("NetworkGuid", ctypes.c_ubyte * 16),
                ("ConnectionType", ctypes.c_uint32),
                ("TransmitLinkSpeed", ctypes.c_uint64),
                ("ReceiveLinkSpeed", ctypes.c_uint64),
                ("InOctets", ctypes.c_uint64),
                ("InUcastPkts", ctypes.c_uint64),
                ("InNUcastPkts", ctypes.c_uint64),
                ("InDiscards", ctypes.c_uint64),
                ("InErrors", ctypes.c_uint64),
                ("InUnknownProtos", ctypes.c_uint64),
                ("InUcastOctets", ctypes.c_uint64),
                ("InMulticastOctets", ctypes.c_uint64),
                ("InBroadcastOctets", ctypes.c_uint64),
                ("OutOctets", ctypes.c_uint64),
                ("OutUcastPkts", ctypes.c_uint64),
                ("OutNUcastPkts", ctypes.c_uint64),
                ("OutDiscards", ctypes.c_uint64),
                ("OutErrors", ctypes.c_uint64),
                ("OutUcastOctets", ctypes.c_uint64),
                ("OutMulticastOctets", ctypes.c_uint64),
                ("OutBroadcastOctets", ctypes.c_uint64),
                ("OutQLen", ctypes.c_uint64),
            ]

        class MIB_IF_TABLE2(ctypes.Structure):
            _fields_ = [
                ("NumEntries", ctypes.c_uint32),
                ("Table", MIB_IF_ROW2 * 1),
            ]

        table_ptr = ctypes.c_void_p()
        if iphlpapi.GetIfTable2(ctypes.byref(table_ptr)) != 0:
            return []
        try:
            table = ctypes.cast(table_ptr, ctypes.POINTER(MIB_IF_TABLE2)).contents
            n = table.NumEntries
            rows = (MIB_IF_ROW2 * n).from_address(ctypes.addressof(table.Table[0]))
            return [
                {"name": rows[i].Alias, "up": rows[i].OutOctets, "down": rows[i].InOctets}
                for i in range(n)
            ]
        finally:
            iphlpapi.FreeMibTable(table_ptr)

    def sample(self):
        """Возвращает (up_total, down_total, up_bps, down_bps) за последний интервал.
        up_total/down_total — cumulative байты за сессию; bps — текущая скорость.
        Возвращает None, если TUN-адаптер сейчас отсутствует (VPN выключен)."""
        try:
            table = self._if_table()
        except Exception:
            return None
        iface = None
        for i in table:
            if i["name"].lower() == self.iface_name.lower():
                iface = i
                break
        if iface is None:
            # Адаптер исчез (отключились) — сбрасываем базу, чтобы при следующем
            # подключении скорость считалась от нуля, а не "проскакивала" от старой.
            self.prev_up = None
            self.prev_down = None
            self.prev_ts = None
            return None
        up, down = iface["up"], iface["down"]
        up_bps = down_bps = 0.0
        if self.prev_ts is not None:
            dt = time.time() - self.prev_ts
            if dt > 0 and self.prev_up is not None and self.prev_down is not None:
                up_bps = max(0, up - self.prev_up) / dt
                down_bps = max(0, down - self.prev_down) / dt
        self.prev_up, self.prev_down, self.prev_ts = up, down, time.time()
        return up, down, up_bps, down_bps


def format_rate(bps):
    """Байты/сек → человекочитаемая строка."""
    if bps < 1024:
        return "%.0f Б/с" % bps
    if bps < 1024 * 1024:
        return "%.1f КБ/с" % (bps / 1024)
    return "%.1f МБ/с" % (bps / (1024 * 1024))


def format_bytes(total):
    """Суммарные байты → человекочитаемая строка."""
    if total < 1024:
        return "%d Б" % total
    if total < 1024 * 1024:
        return "%.1f КБ" % (total / 1024)
    if total < 1024 * 1024 * 1024:
        return "%.1f МБ" % (total / (1024 * 1024))
    return "%.2f ГБ" % (total / (1024 * 1024 * 1024))