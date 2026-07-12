#!/usr/bin/env python3
"""
LLM'siz browser smoke testi.

Playwright+CDP browser'ı doğrudan sürer (LLM yok): Chrome başlat -> example.com'a
git -> snapshot al -> bir ref'e tıkla -> screenshot -> her adımı doğrula.

Kullanım:
    pip install playwright && playwright install chromium
    python scripts/smoke_browser.py

Ollama DOWN olsa bile çalışır — sadece browser katmanını test eder.
"""

import os
import sys

# Paket dizinini yola ekle (ai_agent.1.2/)
_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PKG)

from computer import PlaywrightBrowser, PW_AVAILABLE


def main() -> int:
    if not PW_AVAILABLE:
        print("ATLANDI: playwright kurulu değil. `pip install playwright && playwright install chromium`")
        return 2

    browser = PlaywrightBrowser(headless=True)
    steps = []

    def check(name, res):
        ok = isinstance(res, dict) and res.get("success", False)
        steps.append((name, ok, res))
        status = "OK " if ok else "FAIL"
        print(f"[{status}] {name}: {res if not ok else _short(res)}")
        return ok

    def _short(res):
        d = {k: v for k, v in res.items() if k not in ("snapshot", "content")}
        if "snapshot" in res:
            d["snapshot_len"] = len(res["snapshot"])
        return d

    try:
        # 1) başlat
        start_res = browser.start()
        if isinstance(start_res, dict):
            check("start", start_res)
        else:
            print("[OK ] start (no dict returned)")

        # 2) navigate
        if not check("navigate example.com", browser.navigate("https://example.com")):
            return 1

        # 3) snapshot -> ref'ler
        snap = browser.snapshot(interactive=True)
        if not check("snapshot", snap):
            return 1
        ref_count = snap.get("ref_count", 0)
        print(f"     -> {ref_count} ref bulundu")

        # 4) get_content
        content = browser.get_content("text")
        check("get_content", content)
        if content.get("success"):
            txt = (content.get("content") or content.get("text") or "")
            print(f"     -> içerik: {txt[:80]!r}")

        # 5) screenshot
        shot = browser.screenshot(full_page=False)
        check("screenshot", shot)
        if shot.get("success"):
            print(f"     -> kaydedildi: {shot.get('path')}")

        # 6) bir ref'e tıkla (example.com'da 'More information...' linki var)
        #    ref formatı e1/e2... — ilk ref'i dene.
        if ref_count > 0:
            click = browser.act("click", ref="e1")
            # Tıklama başarısız olabilir (link yoksa) ama çağrı sözleşmesi çalışmalı.
            print(f"[{'OK ' if click.get('success') else 'INFO'}] click e1: {click}")

    finally:
        try:
            browser.close()
        except Exception as e:
            print(f"close hata: {e}")

    failed = [s for s in steps if not s[1]]
    print("\n=== SONUÇ ===")
    print(f"Toplam adım: {len(steps)}, başarısız: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
