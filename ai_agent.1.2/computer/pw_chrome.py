"""Chrome yaşam döngüsü yönetimi (CDP / remote-debugging).

openclaw `src/browser/chrome.ts` + `chrome.executables.ts` mantığının Python
portu. Yalnızca standart kütüphane kullanır (subprocess, urllib, json, time,
os, signal, shutil, platform) — Playwright'a bağımlılığı YOKTUR.

Kullanım:
    chrome = ChromeProcess()
    ws_url = chrome.start(port=18800)   # CDP webSocketDebuggerUrl
    ...
    chrome.stop()

Zaten çalışan bir Chrome (aynı portta CDP açık) varsa yeni process başlatılmaz;
mevcut ws_url döndürülür ve stop() o process'i öldürmez ("attached" modu).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import signal
import subprocess
import time
import urllib.request

# --- Sabitler ----------------------------------------------------------------

DEFAULT_PORT = 18800
DEFAULT_USER_DATA_DIR = os.path.expanduser("~/.ai_helper/browser/user-data")

_STARTUP_TIMEOUT_SEC = 20.0     # CDP hazır olana dek maksimum bekleme
_POLL_INTERVAL_SEC = 0.2        # /json/version yoklama aralığı
_VERSION_FETCH_TIMEOUT_SEC = 0.5
_SIGTERM_GRACE_SEC = 3.0        # SIGTERM sonrası SIGKILL'e kadar bekleme

# macOS tarayıcı adayları (öncelik sırası: Chrome > Brave > Chromium > Edge).
_MAC_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

# Linux'ta PATH üzerinden aranacak isimler.
_LINUX_CANDIDATES = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "brave-browser",
    "microsoft-edge",
]


def find_chrome() -> str | None:
    """Sistemde çalıştırılabilir bir Chromium tabanlı tarayıcı bulur.

    macOS'ta bilinen .app yollarını, Linux'ta PATH'i tarar. Bulamazsa None.
    """
    system = platform.system()
    if system == "Darwin":
        for path in _MAC_CANDIDATES:
            if os.path.exists(path):
                return path
        # Yedek: PATH'te olabilir.
        for name in _LINUX_CANDIDATES:
            found = shutil.which(name)
            if found:
                return found
        return None

    # Linux ve diğerleri.
    for name in _LINUX_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _fetch_version(port: int, timeout: float = _VERSION_FETCH_TIMEOUT_SEC) -> dict | None:
    """http://127.0.0.1:<port>/json/version JSON'ını çeker; erişilemezse None."""
    url = f"http://127.0.0.1:{port}/json/version"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def _get_ws_url(port: int, timeout: float = _VERSION_FETCH_TIMEOUT_SEC) -> str | None:
    """CDP webSocketDebuggerUrl'i döndürür; hazır değilse None."""
    data = _fetch_version(port, timeout)
    if not data:
        return None
    ws_url = str(data.get("webSocketDebuggerUrl") or "").strip()
    return ws_url or None


def is_chrome_reachable(port: int, timeout: float = _VERSION_FETCH_TIMEOUT_SEC) -> bool:
    """Belirtilen portta CDP endpoint'i cevap veriyor mu?"""
    return _fetch_version(port, timeout) is not None


class ChromeProcess:
    """Bir Chrome/Chromium örneğinin yaşam döngüsünü yönetir."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.port: int = DEFAULT_PORT
        self.user_data_dir: str | None = None
        self.ws_url: str | None = None
        # True ise process'i biz başlattık, stop() öldürebilir.
        # False ise dışarıda çalışan Chrome'a bağlandık, stop() dokunmaz.
        self._own_process: bool = False

    def start(
        self,
        port: int = DEFAULT_PORT,
        user_data_dir: str | None = None,
        headless: bool = False,
    ) -> str:
        """Chrome'u başlatır (veya mevcut örneğe bağlanır) ve ws_url döndürür.

        Aynı portta zaten CDP açıksa yeni process başlatılmaz.
        """
        self.port = port

        # 1) Zaten çalışan Chrome var mı? Varsa ona bağlan.
        existing = _get_ws_url(port)
        if existing:
            self.ws_url = existing
            self._own_process = False
            return existing

        # 2) Tarayıcı çalıştırılabilirini bul.
        exe = find_chrome()
        if not exe:
            raise RuntimeError(
                "Desteklenen tarayıcı bulunamadı "
                "(macOS/Linux'ta Chrome/Brave/Chromium/Edge)."
            )

        # 3) Kullanıcı veri dizinini hazırla.
        self.user_data_dir = user_data_dir or DEFAULT_USER_DATA_DIR
        os.makedirs(self.user_data_dir, exist_ok=True)

        # 4) Bayrakları kur (kaynak chrome.ts spawnOnce ile uyumlu).
        args = [
            exe,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={self.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-features=Translate",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--password-store=basic",
        ]
        if headless:
            args.append("--headless=new")
            args.append("--disable-gpu")
        if platform.system() == "Linux":
            args.append("--disable-dev-shm-usage")
        # Bir hedef (target) var olsun diye boş sekme.
        args.append("about:blank")

        # 5) Process'i başlat. stdout/stderr yut (gürültüyü bastır).
        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "HOME": os.path.expanduser("~")},
        )
        self._own_process = True

        # 6) CDP hazır olana dek /json/version yokla.
        deadline = time.monotonic() + _STARTUP_TIMEOUT_SEC
        while time.monotonic() < deadline:
            # Process erken öldüyse hata ver.
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"Chrome beklenmedik şekilde kapandı "
                    f"(exit={self.proc.returncode})."
                )
            ws_url = _get_ws_url(port)
            if ws_url:
                self.ws_url = ws_url
                return ws_url
            time.sleep(_POLL_INTERVAL_SEC)

        # Zaman aşımı: başlattığımız process'i temizle.
        self._kill_now()
        raise RuntimeError(
            f"Chrome CDP {port} portunda {_STARTUP_TIMEOUT_SEC:.0f}sn içinde hazır olmadı."
        )

    def _kill_now(self) -> None:
        """Process'i hemen SIGKILL ile öldür (best-effort)."""
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.kill()
            except Exception:
                pass

    def stop(self) -> None:
        """Chrome'u durdur: SIGTERM, ardından süre dolunca SIGKILL.

        Attached modda (dışarıdaki Chrome'a bağlandıysak) hiçbir şey yapmaz.
        """
        if not self._own_process or self.proc is None:
            self.proc = None
            return

        if self.proc.poll() is not None:
            self.proc = None
            return

        # Nazik kapanma denemesi.
        try:
            self.proc.send_signal(signal.SIGTERM)
        except Exception:
            pass

        deadline = time.monotonic() + _SIGTERM_GRACE_SEC
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                self.proc = None
                return
            time.sleep(0.1)

        # Hâlâ hayattaysa zorla öldür.
        self._kill_now()
        try:
            self.proc.wait(timeout=2)
        except Exception:
            pass
        self.proc = None

    def __enter__(self) -> "ChromeProcess":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
