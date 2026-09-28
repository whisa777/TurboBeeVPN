import os
import subprocess
import sys
import tempfile
import time
import urllib.request

from app_core import app_log

APP_VERSION = "2.41"
_BASE_UPDATE = "https://raw.githubusercontent.com/whisa777/TurboBeeVPN/main/"

CHANNEL_STABLE = "stable"
CHANNEL_TEST = "test"


def current_channel():
    """Канал обновлений из config.json: 'stable' (прод) или 'test' (предрелиз)."""
    try:
        from app_core import load_config
        cfg = load_config() or {}
        return cfg.get("channel", CHANNEL_STABLE)
    except Exception:
        return CHANNEL_STABLE


def update_url():
    ch = current_channel()
    f = "latest.json" if ch != CHANNEL_TEST else "latest-test.json"
    return _BASE_UPDATE + f + "?cb=" + str(int(time.time()))


def _parse_version(v):
    parts = []
    for part in str(v).strip().lstrip("v").split("."):
        try:
            parts.append(int("".join(ch for ch in part if ch.isdigit()) or "0"))
        except Exception:
            parts.append(0)
    return tuple(parts + [0] * (3 - len(parts)))


def _is_newer(remote, current):
    return _parse_version(remote) > _parse_version(current)


def fetch_latest():
    """���������� dict latest.json � ���� ��� None ��� ������."""
    try:
        url = update_url()
        req = urllib.request.Request(url, headers={"User-Agent": "TurboBeeVPN-Updater"})
        with urllib.request.urlopen(req, timeout=15) as r:
            import json
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def get_available_update():
    """���������� (new_version, url_setup, changelog) ���� ���� ����������, ����� None."""
    data = fetch_latest()
    if not data:
        app_log("update: fetch_latest returned None/error")
        return None
    win = data.get("windows") or {}
    # ������ ��������� ����� ����������� ������ � ���� ����� (windows.version).
    # fallback �� ����� "version" ��� ������ �������� �� ������ ��������.
    remote = win.get("version") or data.get("version")
    if not remote or not _is_newer(remote, APP_VERSION):
        app_log("update: no newer version (remote=%s, current=%s)" % (remote, APP_VERSION))
        return None
    url = win.get("url")
    if not url:
        app_log("update: windows url missing")
        return None
    changelog = win.get("changelog") or ""
    app_log("update: available %s -> %s" % (remote, url))
    return remote, url, changelog


def _download(url, dest, progress_cb=None):
    req = urllib.request.Request(url, headers={"User-Agent": "TurboBeeVPN-Updater"})
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        buf = r.read(65536)
        if not buf:
            raise IOError("������ �����")
        with open(dest, "wb") as f:
            while buf:
                f.write(buf)
                done += len(buf)
                if progress_cb and total > 0:
                    progress_cb(int(done * 100 / total))
                buf = r.read(65536)
    return dest


def download_and_install(url, progress_cb=None):
    """������ ���������� �� ��������� ����� � ��������� ��������� ������.
    ���������� ����������� � ������� ����� (�� silent), ����� ������������
    �������, ��� ����������. ���������� ����������� ����� ����� �������
    ����������� (���������� update_launched), ���������� ������ ����� ������
    � ����� [Run] ��� ��������� �."""
    tmp = os.path.join(tempfile.gettempdir(), "turbobee_setup_%s.exe" % APP_VERSION.replace(".", ""))
    app_log("update: downloading %s -> %s" % (url, tmp))
    _download(url, tmp, progress_cb)
    app_log("update: download done, size=%s" % os.path.getsize(tmp))
    if not getattr(sys, "frozen", False):
        # dev-�����: ������ ��� ��������� (��� ���������� �����)
        return subprocess.Popen([tmp, "/SP-", "/NORESTART"])
    # ��������� ���������� ����������� ������� ������������ (��� ��� ��������� ���������):
    # ������������ ����� ���� ������� ���������, � � ����� � ����������� �����
    # "��������� TurboBeeVPN" (������ [Run] postinstall), ������� � ���������
    # ����� ������. ��� /SILENT / /VERYSILENT � ����� ������ � [Run] �� ��������.
    # ��������� ���������� ������������ ����� os.startfile (ShellExecute verb=open),
    # �� �� �������� = explorer, � �� �� ������ ��������. ��� ���������
    # "security validation failure: parent process has different executable",
    # ������ ��� Inno ������� �������� ������ ����� ��� �������� ���������/�����
    # ���������. exploration.exe ������ ��� � �������� => �������� ��������.
    # ���������� ��� �������� UAC (PrivilegesRequired=admin) � ������� ������ � ������
    # "��������� TurboBeeVPN" � �����.
    try:
        subprocess.Popen(["explorer.exe", tmp], close_fds=True)
        app_log("update: installer launched INTERACTIVE via explorer, tmp=%s" % tmp)
    except Exception as e:
        app_log("update: explorer launch failed %r, falling back to os.startfile" % (e,))
        try:
            os.startfile(tmp)
        except Exception as e2:
            app_log("update: startfile failed %r" % (e2,))
    return None


def _install_dir():
    """���� ���������: ����� � ���������� exe."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()
