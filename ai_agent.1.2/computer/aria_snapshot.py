"""ARIA snapshot -> rol tabanlı ref ağacı dönüştürücü.

openclaw `src/browser/pw-role-snapshot.ts` içindeki
`buildRoleSnapshotFromAriaSnapshot` fonksiyonunun birebir Python portu.

Saf string işleme yapar; Playwright'a bağımlılığı YOKTUR (import etmez).
Playwright'ın `locator.aria_snapshot()` çıktısı (YAML benzeri girintili metin)
verilir, geriye LLM'e sunulacak açıklamalı ağaç + ref haritası döner.

ref haritası: {"e1": {"role": str, "name": str|None, "nth": int}}
  - "nth" anahtarı YALNIZCA aynı role+name birden fazla kez geçtiğinde bulunur
    (tekil elemanlardan silinir). Bu, openclaw'daki `removeNthFromNonDuplicates`
    davranışını korur ve `_ref_locator` içinde `nth is not None` kontrolüyle
    eşleşir.
"""

from __future__ import annotations

import re

# --- Rol kümeleri (kaynak pw-role-snapshot.ts ile birebir) -------------------

INTERACTIVE_ROLES = frozenset({
    "button",
    "link",
    "textbox",
    "checkbox",
    "radio",
    "combobox",
    "listbox",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "option",
    "searchbox",
    "slider",
    "spinbutton",
    "switch",
    "tab",
    "treeitem",
})

CONTENT_ROLES = frozenset({
    "heading",
    "cell",
    "gridcell",
    "columnheader",
    "rowheader",
    "listitem",
    "article",
    "region",
    "main",
    "navigation",
})

STRUCTURAL_ROLES = frozenset({
    "generic",
    "group",
    "list",
    "table",
    "row",
    "rowgroup",
    "grid",
    "treegrid",
    "menu",
    "menubar",
    "toolbar",
    "tablist",
    "tree",
    "directory",
    "document",
    "application",
    "presentation",
    "none",
})

# Satır formatı: "  - button "Ara" [ref=..]" gibi girintili YAML benzeri satır.
#   grup1: prefix (girinti + "- "), grup2: rol, grup3: isim (opsiyonel), grup4: suffix
_LINE_RE = re.compile(r'^(\s*-\s*)(\w+)(?:\s+"([^"]*)")?(.*)$')
_E_REF_RE = re.compile(r"^e\d+$")


def _indent_level(line: str) -> int:
    """Girinti seviyesi = baştaki boşluk sayısı // 2 (kaynaktaki getIndentLevel)."""
    match = re.match(r"^(\s*)", line)
    return len(match.group(1)) // 2 if match else 0


class _RoleNameTracker:
    """role+name kombinasyonlarını sayar; tekrar (duplicate) tespiti yapar.

    createRoleNameTracker + removeNthFromNonDuplicates mantığını taşır.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._refs_by_key: dict[str, list[str]] = {}

    @staticmethod
    def _key(role: str, name: str | None) -> str:
        # JS: `${role}:${name ?? ""}` — None de "" de aynı anahtara düşer.
        return f"{role}:{name if name else ''}"

    def next_index(self, role: str, name: str | None) -> int:
        key = self._key(role, name)
        current = self._counts.get(key, 0)
        self._counts[key] = current + 1
        return current

    def track_ref(self, role: str, name: str | None, ref: str) -> None:
        key = self._key(role, name)
        self._refs_by_key.setdefault(key, []).append(ref)

    def duplicate_keys(self) -> set[str]:
        return {key for key, refs in self._refs_by_key.items() if len(refs) > 1}

    def remove_nth_from_non_duplicates(self, refs: dict[str, dict]) -> None:
        """Tekil (tek geçen) role+name'lerden 'nth' anahtarını sil.

        Böylece _ref_locator yalnızca gerçek tekrarlarda .nth(...) uygular.
        """
        duplicates = self.duplicate_keys()
        for data in refs.values():
            key = self._key(data["role"], data.get("name"))
            if key not in duplicates:
                data.pop("nth", None)


def parse_role_ref(raw: str) -> str | None:
    """'@e5', 'ref=e5', 'e5' gibi girdilerden 'e5' çıkarır; geçersizse None.

    Kaynak: parseRoleRef.
    """
    trimmed = raw.strip()
    if not trimmed:
        return None
    if trimmed.startswith("@"):
        normalized = trimmed[1:]
    elif trimmed.startswith("ref="):
        normalized = trimmed[4:]
    else:
        normalized = trimmed
    return normalized if _E_REF_RE.match(normalized) else None


def _compact_tree(tree: str) -> str:
    """İçinde ref bulunmayan yapısal dalları buda (compactTree portu)."""
    lines = tree.split("\n")
    result: list[str] = []

    for i, line in enumerate(lines):
        if "[ref=" in line:
            result.append(line)
            continue
        # ":" içeren ama ":" ile bitmeyen satırlar (değer taşıyan) korunur.
        if ":" in line and not line.rstrip().endswith(":"):
            result.append(line)
            continue

        current_indent = _indent_level(line)
        has_relevant_children = False
        for j in range(i + 1, len(lines)):
            child_indent = _indent_level(lines[j])
            if child_indent <= current_indent:
                break
            if "[ref=" in lines[j]:
                has_relevant_children = True
                break
        if has_relevant_children:
            result.append(line)

    return "\n".join(result)


def _process_line(
    line: str,
    refs: dict[str, dict],
    interactive: bool,
    compact: bool,
    max_depth: int | None,
    tracker: _RoleNameTracker,
    next_ref,
) -> str | None:
    """Tam-ağaç modundaki tek satır işleme (processLine portu)."""
    depth = _indent_level(line)
    if max_depth is not None and depth > max_depth:
        return None

    match = _LINE_RE.match(line)
    if not match:
        return None if interactive else line

    prefix, role_raw, name, suffix = match.groups()
    if role_raw.startswith("/"):
        return None if interactive else line

    role = role_raw.lower()
    is_interactive = role in INTERACTIVE_ROLES
    is_content = role in CONTENT_ROLES
    is_structural = role in STRUCTURAL_ROLES

    if interactive and not is_interactive:
        return None
    if compact and is_structural and not name:
        return None

    should_have_ref = is_interactive or (is_content and name)
    if not should_have_ref:
        return line

    ref = next_ref()
    nth = tracker.next_index(role, name)
    tracker.track_ref(role, name, ref)
    refs[ref] = {"role": role, "name": name, "nth": nth}

    enhanced = f"{prefix}{role_raw}"
    if name:
        enhanced += f' "{name}"'
    enhanced += f" [ref={ref}]"
    if nth > 0:
        enhanced += f" [nth={nth}]"
    if suffix:
        enhanced += suffix
    return enhanced


def build_role_snapshot(
    aria_snapshot: str,
    interactive: bool = False,
    max_depth: int | None = None,
    compact: bool = False,
) -> tuple[str, dict]:
    """ARIA snapshot metnini açıklamalı ağaç + ref haritasına çevirir.

    Kaynak: buildRoleSnapshotFromAriaSnapshot.

    Dönüş: (annotated_tree, refs)
      refs = {"e1": {"role": str, "name": str|None, "nth": int?}}
    """
    lines = aria_snapshot.split("\n")
    refs: dict[str, dict] = {}
    tracker = _RoleNameTracker()

    counter = [0]

    def next_ref() -> str:
        counter[0] += 1
        return f"e{counter[0]}"

    # --- Interactive mod: yalnızca etkileşimli elemanlar, girinti düzleştirilir.
    if interactive:
        result: list[str] = []
        for line in lines:
            depth = _indent_level(line)
            if max_depth is not None and depth > max_depth:
                continue

            match = _LINE_RE.match(line)
            if not match:
                continue
            _prefix, role_raw, name, suffix = match.groups()
            if role_raw.startswith("/"):
                continue

            role = role_raw.lower()
            if role not in INTERACTIVE_ROLES:
                continue

            ref = next_ref()
            nth = tracker.next_index(role, name)
            tracker.track_ref(role, name, ref)
            refs[ref] = {"role": role, "name": name, "nth": nth}

            enhanced = f"- {role_raw}"
            if name:
                enhanced += f' "{name}"'
            enhanced += f" [ref={ref}]"
            if nth > 0:
                enhanced += f" [nth={nth}]"
            # Sadece köşeli parantezli ek nitelikler korunur (örn. [checked]).
            if "[" in suffix:
                enhanced += suffix
            result.append(enhanced)

        tracker.remove_nth_from_non_duplicates(refs)

        snapshot = "\n".join(result) or "(no interactive elements)"
        return snapshot, refs

    # --- Tam ağaç modu.
    result = []
    for line in lines:
        processed = _process_line(
            line, refs, interactive, compact, max_depth, tracker, next_ref
        )
        if processed is not None:
            result.append(processed)

    tracker.remove_nth_from_non_duplicates(refs)

    tree = "\n".join(result) or "(empty)"
    return (_compact_tree(tree) if compact else tree), refs


def get_role_snapshot_stats(snapshot: str, refs: dict) -> dict:
    """Ağaç istatistikleri (getRoleSnapshotStats portu)."""
    interactive = sum(
        1 for r in refs.values() if r.get("role") in INTERACTIVE_ROLES
    )
    return {
        "lines": len(snapshot.split("\n")),
        "chars": len(snapshot),
        "refs": len(refs),
        "interactive": interactive,
    }
