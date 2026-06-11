from __future__ import annotations

import contextvars
import re

from ..config import ui_language, SUPPORTED_LANGUAGES


# ===================================================================== #
# i18n: the inspector chrome is bilingual (de/en). The active UI language #
# is resolved per request (?lang= -> cookie -> persisted setting) and    #
# held in a contextvar so the module-level render helpers can read it     #
# without threading it through every function. Generated CONTENT keeps    #
# its own content_language; this only switches the surrounding UI.        #
#                                                                         #
# Contract (enforced by tests/test_i18n.py):                              #
#   - STRINGS covers exactly SUPPORTED_LANGUAGES.                          #
#   - every language defines the SAME key set with the SAME {placeholders}.#
#   - every t("literal") used in the codebase resolves to a defined key.   #
# Add a string by adding the key to EVERY language table, never inline.    #
# ===================================================================== #

# Extensions (sonaloop-cloud / sonaloop-research) register their OWN translated
# strings through register_strings() below — namespaced dotted keys ("cloud.usage_h")
# that can never shadow the core's flat keys. See docs/i18n.md.

# Ultimate fallback when a key is missing in the active language (should not
# happen — the parity test guards it — but keeps render robust in prod).
FALLBACK_LANGUAGE = "en"

_UI_LANG: contextvars.ContextVar[str | None] = contextvars.ContextVar("ui_lang", default=None)

from ._i18n_strings import STRINGS  # noqa: F401  (the catalog — data lives in its own module)


def _lang() -> str:
    """The active UI language: per-request contextvar, else the persisted setting."""
    return _UI_LANG.get() or ui_language()


# --------------------------------------------------------------- extension seam
# Downstream packages (sonaloop-cloud / sonaloop-research) ship their own UI
# strings. They never edit STRINGS: they call register_strings() from their web
# setup() (the same entry point that registers routes/nav), once per language.

# A namespaced extension key: "<namespace>.<key>", e.g. "cloud.usage_h". The dot is
# the guard — core keys are flat ([a-z0-9_]+), so an extension can never shadow one.
_EXT_KEY = re.compile(r"^[a-z0-9_]+\.[a-z0-9_.]+$")


def register_strings(lang: str, mapping: dict[str, str]) -> None:
    """Merge an extension's translated strings into the catalog (docs/i18n.md).

    `lang` must be one of SUPPORTED_LANGUAGES; every key in `mapping` must be
    NAMESPACED ("<ns>.<key>", e.g. "research.panel_h") so it cannot collide with —
    or override — a core key. Re-registering the same key is allowed (idempotent
    setup on reload); registering a flat/core key raises. Resolve with the normal
    t("ns.key"). Parity across languages is checked by extension_parity_problems()
    (asserted in tests/test_i18n.py — register for EVERY supported language)."""
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language {lang!r}; expected one of {SUPPORTED_LANGUAGES}")
    for key, value in mapping.items():
        if not _EXT_KEY.match(key):
            raise ValueError(
                f"extension string key {key!r} must be namespaced ('<ns>.<key>', e.g. "
                "'cloud.usage_h') — flat keys are reserved for the core catalog")
        if not isinstance(value, str):
            raise ValueError(f"extension string {key!r} must map to a str")
        STRINGS[lang][key] = value


def extension_parity_problems() -> list[str]:
    """Parity check over the REGISTERED extension strings (namespaced keys): every
    namespaced key must exist in every supported language with the same
    {placeholder}s — the same contract the core parity test enforces."""
    ph = re.compile(r"\{([a-z0-9_]+)\}")
    ext: dict[str, dict[str, str]] = {
        lang: {k: v for k, v in table.items() if "." in k} for lang, table in STRINGS.items()}
    all_keys = set().union(*(set(t_) for t_ in ext.values()))
    problems = []
    for key in sorted(all_keys):
        langs_with = {lang for lang, table in ext.items() if key in table}
        if langs_with != set(SUPPORTED_LANGUAGES):
            problems.append(f"{key!r} missing in: {sorted(set(SUPPORTED_LANGUAGES) - langs_with)}")
            continue
        ref = set(ph.findall(ext[FALLBACK_LANGUAGE][key]))
        for lang, table in ext.items():
            if set(ph.findall(table[key])) != ref:
                problems.append(f"{key!r}: placeholder mismatch in {lang!r}")
    return problems


def t(key: str, **kw: object) -> str:
    """Translate `key` into the active UI language, formatting any `{placeholder}`s.

    Falls back to FALLBACK_LANGUAGE, then to the raw key — so a missing string
    degrades visibly rather than raising. The parity test keeps this from ever
    firing in practice."""
    table = STRINGS.get(_lang(), STRINGS[FALLBACK_LANGUAGE])
    # Singular form: when count is 1 and a "<key>_one" variant exists, prefer it ("1 Projekt", "1 node").
    if kw.get("n") == 1 and (key + "_one") in table:
        key = key + "_one"
    value = table.get(key)
    if value is None:
        value = STRINGS[FALLBACK_LANGUAGE].get(key, key)
    return value.format(**kw) if kw else value


def _resolve_request_language(query_lang: str | None, cookie_lang: str | None) -> tuple[str, bool]:
    """Resolve the UI language for a request and whether it should be persisted.
    Precedence: explicit ?lang= (persist) -> cookie -> stored setting."""
    q = (query_lang or "").strip().lower()[:2]
    if q in SUPPORTED_LANGUAGES:
        return q, True
    c = (cookie_lang or "").strip().lower()[:2]
    if c in SUPPORTED_LANGUAGES:
        return c, False
    return ui_language(), False
