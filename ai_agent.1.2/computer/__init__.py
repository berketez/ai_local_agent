"""computer paketi: ref-tabanlı Playwright + CDP tarayıcı otomasyonu.

openclaw'un Node/TypeScript tarayıcı katmanının Python portu.

Dışa açılan başlıca semboller:
  - PlaywrightBrowser: CDP üzerinden Chrome'u süren ana denetleyici.
  - PW_AVAILABLE: Playwright kurulu ve import edilebilir mi? (bool)

Import hataları paketi çökertmez; PlaywrightBrowser None, PW_AVAILABLE False
olur. Bu sayede UnifiedAgent tarayıcı olmadan da import edilebilir.
"""

try:
    from .pw_browser import PlaywrightBrowser, PW_AVAILABLE
except Exception:  # pragma: no cover - savunmacı import guard
    PlaywrightBrowser = None  # type: ignore
    PW_AVAILABLE = False

__all__ = ["PlaywrightBrowser", "PW_AVAILABLE"]
