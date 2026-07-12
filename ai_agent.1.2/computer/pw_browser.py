"""Playwright + CDP tabanlı tarayıcı denetleyicisi (ref-tabanlı otomasyon).

openclaw `pw-session.ts` (refLocator) + `pw-tools-core.interactions.ts`
(click/hover/type/fill/select/press) davranışının Python (SYNC API) portu.

Tasarım:
  - Chrome'u `ChromeProcess` ile başlatır, `connect_over_cdp` ile bağlanır.
  - `snapshot()` sayfanın ARIA ağacını alıp `build_role_snapshot` ile
    ref'lere (e1, e2, ...) çevirir; ref haritası sayfa bazında saklanır.
  - `act()` bir ref'i `page.get_by_role(...).nth(...)` ile locator'a çözer.
  - Tüm public metotlar `{"success": bool, ...}` sözlüğü döndürür
    (UnifiedAgent sözleşmesi). İstisnalar `{"success": False, "error": ...}`
    olarak yakalanır.

Playwright kurulu değilse modül yine import edilebilir; `PW_AVAILABLE=False`
olur ve `start()` anlamlı bir hata döndürür.
"""

from __future__ import annotations

import os
import time

from .aria_snapshot import build_role_snapshot, parse_role_ref

# --- Playwright import guard --------------------------------------------------
try:
    from playwright.sync_api import sync_playwright

    PW_AVAILABLE = True
except Exception:  # ImportError ve olası runtime hataları
    sync_playwright = None  # type: ignore
    PW_AVAILABLE = False

# --- Sabitler ----------------------------------------------------------------

DEFAULT_PORT = 18800
TIMEOUT_MIN_MS = 500
TIMEOUT_MAX_MS = 60_000
DEFAULT_TIMEOUT_MS = 8_000

MAX_CONTENT_CHARS = 200_000        # get_content üst sınırı
MAX_SCREENSHOT_EDGE = 2_000        # ekran görüntüsü uzun kenar üst sınırı (px)
MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024  # 5 MB
_JPEG_QUALITY_LADDER = [90, 80, 70, 60, 50, 40]

SCREENSHOT_DIR = os.path.expanduser("~/.ai_helper/screenshots")

# Geçerli etkileşim türleri.
_ACT_KINDS = frozenset({"click", "type", "fill", "hover", "select", "press"})


def _clamp_timeout(timeout_ms: int | None) -> int:
    """Timeout'u [500, 60000] ms aralığına sıkıştır (kaynak clamp mantığı)."""
    if timeout_ms is None:
        timeout_ms = DEFAULT_TIMEOUT_MS
    return max(TIMEOUT_MIN_MS, min(TIMEOUT_MAX_MS, int(timeout_ms)))


def _to_ai_friendly_error(err: Exception, selector: str) -> str:
    """Playwright hatasını LLM'in anlayıp düzeltebileceği mesaja çevirir.

    Kaynak: toAIFriendlyError.
    """
    message = str(err)

    if "strict mode violation" in message:
        import re

        m = re.search(r"resolved to (\d+) elements", message)
        count = m.group(1) if m else "birden fazla"
        return (
            f'"{selector}" seçicisi {count} elemanla eşleşti. '
            f"Yeni bir snapshot al ve güncel ref kullan, ya da farklı ref dene."
        )

    if ("Timeout" in message or "waiting for" in message) and (
        "to be visible" in message or "not visible" in message
    ):
        return (
            f'"{selector}" elemanı bulunamadı veya görünür değil. '
            f"Sayfanın güncel elemanlarını görmek için yeni bir snapshot al."
        )

    if (
        "intercepts pointer events" in message
        or "not visible" in message
        or "not receive pointer events" in message
    ):
        return (
            f'"{selector}" elemanı etkileşime kapalı (gizli veya üstü örtülü). '
            f"Görünüre kaydır, açılır pencereleri kapat veya yeni snapshot al."
        )

    return message


class PlaywrightBrowser:
    """CDP üzerinden Chrome'u süren ana denetleyici (SYNC API).

    Tüm public metotlar {"success": bool, ...} döndürür.
    """

    def __init__(self, headless: bool = False, port: int = DEFAULT_PORT) -> None:
        # Lazy: gerçek başlatma start() ile yapılır.
        self.headless = headless
        self.port = port

        self._chrome = None            # ChromeProcess (lazy import)
        self._pw = None                # sync_playwright context manager sonucu
        self._browser = None           # connect_over_cdp sonucu
        self._context = None           # aktif BrowserContext
        self._page = None              # aktif Page
        self._started = False
        # {page_id: {"refs": {...}, "mode": "role"}}
        self._page_state: dict[int, dict] = {}

    # --- Yaşam döngüsü -------------------------------------------------------

    def start(self) -> dict:
        """Chrome başlat, CDP'ye bağlan, aktif sayfayı hazırla."""
        if not PW_AVAILABLE:
            return {
                "success": False,
                "error": "Playwright kurulu değil. `pip install playwright` "
                "ve `playwright install chromium` gerekir.",
            }
        if self._started:
            return {"success": True, "already_started": True}

        try:
            # ChromeProcess'i lazy import et (pw_chrome stdlib, her zaman mevcut).
            from .pw_chrome import ChromeProcess

            self._chrome = ChromeProcess()
            ws_url = self._chrome.start(port=self.port, headless=self.headless)

            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.connect_over_cdp(ws_url)

            # Mevcut context'i al ya da yeni aç.
            contexts = self._browser.contexts
            if contexts:
                self._context = contexts[0]
            else:
                self._context = self._browser.new_context()

            # Aktif sayfayı al ya da yeni aç.
            pages = self._context.pages
            self._page = pages[0] if pages else self._context.new_page()

            self._started = True
            return {"success": True, "ws_url": ws_url}
        except Exception as e:
            # Kısmi başlatmayı temizle.
            self._safe_teardown()
            return {"success": False, "error": str(e)}

    def close(self) -> dict:
        """Playwright bağlantısını kapat ve Chrome'u durdur."""
        try:
            self._safe_teardown()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _safe_teardown(self) -> None:
        """Kaynakları best-effort serbest bırak (hata yutulur)."""
        # CDP üzerinden bağlanınca browser.close() bağlantıyı koparır,
        # Chrome process'i ayrıca ChromeProcess.stop() ile öldürülür.
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
        if self._chrome is not None:
            try:
                self._chrome.stop()
            except Exception:
                pass
        self._browser = None
        self._pw = None
        self._context = None
        self._page = None
        self._chrome = None
        self._started = False
        self._page_state.clear()

    # --- Yardımcılar ---------------------------------------------------------

    def _require_page(self):
        """Aktif sayfayı döndürür; yoksa hata fırlatır."""
        if not self._started or self._page is None:
            raise RuntimeError("Tarayıcı başlatılmadı. Önce start() çağır.")
        return self._page

    def _state_for(self, page) -> dict:
        """Sayfa için ref durumu sözlüğünü döndürür (yoksa oluşturur)."""
        key = id(page)
        if key not in self._page_state:
            self._page_state[key] = {"refs": {}, "mode": "role"}
        return self._page_state[key]

    def _ref_locator(self, ref: str):
        """Bir ref'i (e1, @e1, ref=e1) Playwright Locator'a çözer.

        Kaynak: refLocator (role mode dalı).
        """
        page = self._require_page()
        # Normalize et (@, ref= önekleri temizlenir; geçersizse ham kullan).
        normalized = parse_role_ref(ref) or ref.strip()

        state = self._state_for(page)
        refs = state.get("refs", {})
        info = refs.get(normalized)
        if not info:
            raise ValueError(
                f'Bilinmeyen ref "{normalized}". Yeni bir snapshot al ve '
                f"o snapshot'tan bir ref kullan."
            )

        name = info.get("name")
        if name:
            loc = page.get_by_role(info["role"], name=name, exact=True)
        else:
            loc = page.get_by_role(info["role"])

        # nth yalnızca duplicate'larda mevcuttur (0 dahil geçerlidir).
        nth = info.get("nth")
        if nth is not None:
            loc = loc.nth(nth)
        return loc

    # --- Gezinme / içerik ----------------------------------------------------

    def navigate(self, url: str) -> dict:
        """URL'e git (domcontentloaded'a kadar bekle)."""
        try:
            page = self._require_page()
            page.goto(url, wait_until="domcontentloaded")
            return {
                "success": True,
                "url": page.url,
                "title": page.title(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_content(self, format: str = "text") -> dict:
        """Sayfa içeriğini metin veya HTML olarak döndür (MAX_CONTENT_CHARS cap)."""
        try:
            page = self._require_page()
            if format == "html":
                content = page.content()
            else:
                content = page.inner_text("body")

            full_len = len(content)
            truncated = full_len > MAX_CONTENT_CHARS
            if truncated:
                content = content[:MAX_CONTENT_CHARS]
            return {
                "success": True,
                "format": format,
                "content": content,
                "length": full_len,
                "truncated": truncated,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Snapshot ------------------------------------------------------------

    def snapshot(
        self,
        interactive: bool = True,
        max_depth: int | None = None,
        compact: bool = True,
    ) -> dict:
        """Sayfanın ARIA ağacını ref-tabanlı snapshot'a çevir ve sakla."""
        try:
            page = self._require_page()
            root = page.locator(":root")
            try:
                aria = root.aria_snapshot()
            except AttributeError:
                return {
                    "success": False,
                    "error": "aria_snapshot() bu Playwright sürümünde yok. "
                    "playwright'ı güncelle.",
                }

            tree, refs = build_role_snapshot(
                aria,
                interactive=interactive,
                max_depth=max_depth,
                compact=compact,
            )

            state = self._state_for(page)
            state["refs"] = refs
            state["mode"] = "role"

            return {
                "success": True,
                "snapshot": tree,
                "ref_count": len(refs),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Etkileşim -----------------------------------------------------------

    def act(
        self,
        kind: str,
        ref: str | None = None,
        text: str | None = None,
        value: str | None = None,
        key: str | None = None,
        timeout: int | None = None,
        **kw,
    ) -> dict:
        """Tek bir etkileşim uygula: click/type/fill/hover/select/press.

        Kaynak: pw-tools-core.interactions.ts.
        """
        try:
            page = self._require_page()
            kind = (kind or "").strip().lower()
            if kind not in _ACT_KINDS:
                return {
                    "success": False,
                    "error": f"Bilinmeyen etkileşim: {kind!r}. "
                    f"Geçerli: {sorted(_ACT_KINDS)}",
                }

            timeout_ms = _clamp_timeout(timeout)

            # press: ref gerekmez, klavye üzerinden çalışır.
            if kind == "press":
                if not key:
                    return {"success": False, "error": "press için 'key' gerekli."}
                page.keyboard.press(key)
                return {"success": True, "kind": kind, "key": key}

            # Diğer tüm türler bir ref ister.
            if not ref:
                return {"success": False, "error": f"{kind} için 'ref' gerekli."}

            try:
                loc = self._ref_locator(ref)
            except ValueError as ve:
                # Bilinmeyen ref -> LLM-dostu, aynen ilet.
                return {"success": False, "error": str(ve)}

            selector_label = str(ref)
            try:
                if kind == "click":
                    loc.click(timeout=timeout_ms)
                elif kind == "type":
                    if text is None:
                        return {"success": False, "error": "type için 'text' gerekli."}
                    loc.type(text, timeout=timeout_ms)
                elif kind == "fill":
                    if text is None:
                        return {"success": False, "error": "fill için 'text' gerekli."}
                    loc.fill(text, timeout=timeout_ms)
                elif kind == "hover":
                    loc.hover(timeout=timeout_ms)
                elif kind == "select":
                    if value is None:
                        return {"success": False, "error": "select için 'value' gerekli."}
                    loc.select_option(value, timeout=timeout_ms)
            except Exception as inner:
                return {
                    "success": False,
                    "error": _to_ai_friendly_error(inner, selector_label),
                }

            return {"success": True, "kind": kind, "ref": ref}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Ekran görüntüsü -----------------------------------------------------

    def screenshot(self, path: str | None = None, full_page: bool = False) -> dict:
        """PNG ekran görüntüsü al, normalize et, diske yaz, yol döndür.

        Pillow varsa: uzun kenar MAX_SCREENSHOT_EDGE'e küçültülür; dosya
        MAX_SCREENSHOT_BYTES üstündeyse kademeli JPEG'e düşülür. Pillow yoksa
        ham PNG kaydedilir.
        """
        try:
            page = self._require_page()
            raw = page.screenshot(full_page=full_page)  # PNG bytes

            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            if path is None:
                path = os.path.join(SCREENSHOT_DIR, f"screenshot_{int(time.time())}.png")

            try:
                from PIL import Image  # type: ignore
                import io

                img = Image.open(io.BytesIO(raw))
                width, height = img.size

                # Uzun kenarı sınırla.
                longest = max(width, height)
                if longest > MAX_SCREENSHOT_EDGE:
                    scale = MAX_SCREENSHOT_EDGE / float(longest)
                    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                    img = img.resize(new_size, Image.LANCZOS)
                    width, height = img.size

                # Önce PNG dene.
                png_path = path if path.lower().endswith(".png") else path + ".png"
                img.save(png_path, format="PNG", optimize=True)

                if os.path.getsize(png_path) <= MAX_SCREENSHOT_BYTES:
                    return {
                        "success": True,
                        "path": png_path,
                        "width": width,
                        "height": height,
                        "format": "png",
                    }

                # Çok büyük -> kademeli JPEG.
                jpeg_path = os.path.splitext(png_path)[0] + ".jpg"
                rgb = img.convert("RGB")
                final_quality = _JPEG_QUALITY_LADDER[-1]
                for quality in _JPEG_QUALITY_LADDER:
                    rgb.save(jpeg_path, format="JPEG", quality=quality, optimize=True)
                    final_quality = quality
                    if os.path.getsize(jpeg_path) <= MAX_SCREENSHOT_BYTES:
                        break
                try:
                    os.remove(png_path)
                except Exception:
                    pass
                return {
                    "success": True,
                    "path": jpeg_path,
                    "width": width,
                    "height": height,
                    "format": "jpeg",
                    "quality": final_quality,
                }
            except ImportError:
                # Pillow yok -> ham PNG yaz.
                png_path = path if path.lower().endswith(".png") else path + ".png"
                with open(png_path, "wb") as f:
                    f.write(raw)
                return {
                    "success": True,
                    "path": png_path,
                    "format": "png",
                    "normalized": False,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Context manager -----------------------------------------------------

    def __enter__(self) -> "PlaywrightBrowser":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
