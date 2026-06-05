"""i18n contract tests — keep the bilingual UI chrome honest.

These guard the invariants documented in persona_council/web/_i18n.py:
  - STRINGS covers exactly SUPPORTED_LANGUAGES.
  - every language defines the SAME key set with the SAME {placeholders}.
  - every t("literal") in the codebase resolves to a defined key.
  - no key is defined-but-unused (no legacy strings lingering).

The last two scan the source so the table cannot drift from its call sites.
"""
from __future__ import annotations

import re
import pathlib

from persona_council.config import SUPPORTED_LANGUAGES
from persona_council.web._i18n import STRINGS, FALLBACK_LANGUAGE, t, _UI_LANG

_PKG = pathlib.Path(__file__).resolve().parent.parent / "persona_council"
_PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")

# A real t("key") call: `t` not preceded by an identifier char (so `.get(`,
# `format(`, `dict(` don't match), one string literal, then `,` or `)`.
_LITERAL = re.compile(r'(?<![A-Za-z0-9_])t\(\s*f?["\']([a-z0-9_]+)["\']\s*[,)]')
# Dynamic keys built from a literal prefix: t("vote_" + x) / t(f"council_kicker_{m}").
_DYN_PREFIX = re.compile(r'(?<![A-Za-z0-9_])t\(\s*"([a-z0-9_]+)"\s*\+')
_DYN_FPREFIX = re.compile(r'(?<![A-Za-z0-9_])t\(\s*f"([a-z0-9_]+)\{')


def _placeholders(value: str) -> set[str]:
    return set(_PLACEHOLDER.findall(value))


def _scan_sources() -> tuple[set[str], set[str]]:
    """Return (literal keys, dynamic key-prefixes) used across the package."""
    literals: set[str] = set()
    prefixes: set[str] = set()
    for path in _PKG.rglob("*.py"):
        if path.name == "_i18n.py":
            continue
        src = path.read_text()
        literals |= set(_LITERAL.findall(src))
        prefixes |= set(_DYN_PREFIX.findall(src))
        prefixes |= set(_DYN_FPREFIX.findall(src))
    return literals, prefixes


def test_languages_match_supported():
    assert set(STRINGS) == set(SUPPORTED_LANGUAGES)
    assert FALLBACK_LANGUAGE in STRINGS


def test_all_languages_define_the_same_keys():
    ref = set(STRINGS[FALLBACK_LANGUAGE])
    for lang, table in STRINGS.items():
        keys = set(table)
        assert not (ref - keys), f"{lang} is missing keys: {sorted(ref - keys)}"
        assert not (keys - ref), f"{lang} has extra keys: {sorted(keys - ref)}"


def test_placeholders_match_across_languages():
    ref = STRINGS[FALLBACK_LANGUAGE]
    for lang, table in STRINGS.items():
        for key, value in table.items():
            assert _placeholders(value) == _placeholders(ref[key]), (
                f"placeholder mismatch for {key!r} in {lang!r}: "
                f"{_placeholders(value)} vs {_placeholders(ref[key])}")


def test_every_used_literal_key_is_defined():
    literals, _ = _scan_sources()
    defined = set(STRINGS[FALLBACK_LANGUAGE])
    missing = sorted(k for k in literals if k not in defined)
    assert not missing, f"t() called with undefined keys: {missing}"


def test_no_legacy_unused_keys():
    literals, prefixes = _scan_sources()
    defined = set(STRINGS[FALLBACK_LANGUAGE])

    def is_used(key: str) -> bool:
        if key in literals:
            return True
        return any(key != p and key.startswith(p) for p in prefixes)

    unused = sorted(k for k in defined if not is_used(k))
    assert not unused, f"defined but never used via t() (legacy — remove): {unused}"


def test_t_translates_formats_and_falls_back():
    token = _UI_LANG.set("de")
    try:
        assert t("settings") == "Einstellungen"
        assert t("n_nodes", n=5) == "5 Knoten"
        # missing key degrades to the raw key, never raises
        assert t("__does_not_exist__") == "__does_not_exist__"
    finally:
        _UI_LANG.reset(token)
    token = _UI_LANG.set("en")
    try:
        assert t("settings") == "Settings"
    finally:
        _UI_LANG.reset(token)
