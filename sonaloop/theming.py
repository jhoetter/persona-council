"""Customer theme contract — the slim design-system schema (ticket customer-theme-contract).

Cloud and research re-skin the app per customer WITHOUT touching components. This module
is the ONE canonical contract of WHAT may be themed; both products validate against it
before persisting. Three sections, each optional:

  colors — allowlisted CSS custom properties (COLOR_VARS — the inspector's themeable
           set). Structural tokens (spacing / radius / type scale / --paper / the
           blueprint palette) are NOT accepted: components, layout and rhythm stay
           Sonaloop's.
  fonts  — --sl-sans / --sl-mono font-stack overrides (customer font first, Sona
           fallback). Family names are unquoted — the value shape check forbids quotes.
  brand  — `name` (flows through the web._ext.set_brand seam) and `logo` (a data: image
           URI or a DATA_DIR-contained path; rendered where the wordmark renders today).

The validated dict feeds web._ext.set_theme_overrides (the per-request contextvar
_layout() injects AFTER the base stylesheet) and the synthesis exports (PDF / HTML
bundle) via their `theme_overrides=` parameter. Known gap: the vendored _deck.py PALETTE
is not parametrized yet, so PPTX decks keep the Sonaloop palette — follow-up ticket.

Token names per sonaloop-design/tokens.data.mjs (vendored copy: sonaloop/_tokens.py).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# CSS-injection guard — the canonical shape checks (web._ext re-exports them): a key must
# be a custom property; a value a small, safe subset (colors / numeric tokens / unquoted
# font stacks). No `;`, `{`, `}`, `:` or quotes to break out of the declaration block.
_VAR_RE = re.compile(r"^--[a-z0-9-]+$")
_VAL_RE = re.compile(r"^[#a-zA-Z0-9_.,%()\s/-]+$")

# The exact themeable set. Everything else in _tokens.py is structural and stays ours.
COLOR_VARS = ("--accent", "--accent-ink", "--accent-weak", "--ink", "--ink-2",
              "--muted", "--faint", "--bg", "--panel", "--sidebar", "--line",
              "--green", "--amber", "--red")
FONT_VARS = ("--sl-sans", "--sl-mono")

_THEME_KEYS = ("colors", "fonts", "brand")
_BRAND_KEYS = ("name", "logo")
_DATA_URI_RE = re.compile(r"^data:image/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=\s]*$")


def validate_customer_theme(raw: Any) -> dict[str, Any]:
    """Validate a customer theme against the slim schema; returns the canonical dict
    cloud/research persist. Strict: unknown keys and off-shape values raise ValueError
    (developer-facing, the allowlist named so the fix is obvious)."""
    if not isinstance(raw, dict):
        raise ValueError("customer theme must be an object {colors?, fonts?, brand?}")
    unknown = sorted(set(map(str, raw)) - set(_THEME_KEYS))
    if unknown:
        raise ValueError(f"unknown customer-theme key(s) {unknown} — valid: {list(_THEME_KEYS)}")
    out: dict[str, Any] = {}
    if "colors" in raw:
        out["colors"] = _vars_section("colors", raw["colors"], COLOR_VARS)
    if "fonts" in raw:
        out["fonts"] = _vars_section("fonts", raw["fonts"], FONT_VARS)
    if "brand" in raw:
        out["brand"] = _brand_section(raw["brand"])
    return out


def _vars_section(section: str, mapping: Any, allowed: tuple[str, ...]) -> dict[str, str]:
    if not isinstance(mapping, dict):
        raise ValueError(f"{section} must be an object {{--var: value}}")
    bad = sorted(set(map(str, mapping)) - set(allowed))
    if bad:
        raise ValueError(f"unknown {section} variable(s) {bad} — themeable: {list(allowed)}")
    out: dict[str, str] = {}
    for k, v in mapping.items():
        val = str(v).strip()
        # Keys are allowlisted (so _VAR_RE-shaped by construction); values must pass the
        # same injection guard the live seam applies — but loudly, not silently dropped.
        if not val or not _VAL_RE.match(val):
            raise ValueError(f"{section}[{k!r}] value {v!r} is off-shape — allowed: "
                             "colors / numeric tokens / unquoted font stacks "
                             f"(must match {_VAL_RE.pattern})")
        out[str(k)] = val
    return out


def _brand_section(brand: Any) -> dict[str, str]:
    if not isinstance(brand, dict):
        raise ValueError("brand must be an object {name?, logo?}")
    unknown = sorted(set(map(str, brand)) - set(_BRAND_KEYS))
    if unknown:
        raise ValueError(f"unknown brand key(s) {unknown} — valid: {list(_BRAND_KEYS)}")
    out: dict[str, str] = {}
    if "name" in brand:
        name = str(brand["name"] or "").strip()
        if not name:
            raise ValueError("brand.name must be a non-empty string")
        out["name"] = name
    if "logo" in brand:
        out["logo"] = _validated_logo(brand["logo"])
    return out


def _validated_logo(logo: Any) -> str:
    """A data: image URI, or a path inside DATA_DIR (the only filesystem root the app
    serves). Anything else — external URLs included — is rejected, mirroring the
    deny-by-default share-bundle image inliner."""
    s = str(logo or "").strip()
    if not s:
        raise ValueError("brand.logo must be a data: image URI or a DATA_DIR-contained path")
    if s.startswith("data:"):
        if not _DATA_URI_RE.match(s):
            raise ValueError("brand.logo data: URI must be a base64-encoded image/* "
                             "(data:image/<type>;base64,…)")
        return s
    if s.startswith("//") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", s):
        raise ValueError("brand.logo must be a data: image URI or a DATA_DIR-contained "
                         "path — external URLs are not accepted")
    from .config import DATA_DIR    # late: tests repoint config.DATA_DIR
    data_root = DATA_DIR.resolve()
    fp = Path(s) if Path(s).is_absolute() else DATA_DIR / s
    if not fp.resolve().is_relative_to(data_root):
        raise ValueError(f"brand.logo path escapes the data dir ({data_root}): {s!r}")
    return str(fp)


def theme_override_vars(theme: dict[str, Any]) -> dict[str, str]:
    """Flatten a VALIDATED theme's colors + fonts into the {--var: value} mapping
    web._ext.set_theme_overrides takes. Brand rides its own seam (set_brand)."""
    return {**theme.get("colors", {}), **theme.get("fonts", {})}


def customer_theme_css(theme: dict[str, Any]) -> str:
    """The `<style>` override block for a VALIDATED theme, or "" when it carries no
    vars. Same id + cascade contract as web._ext.theme_override_css(): inject AFTER the
    base stylesheet so it wins by source order."""
    decls = [f"{k}:{v}" for k, v in theme_override_vars(theme).items()]
    if not decls:
        return ""
    return '<style id="theme-overrides">:root{' + ";".join(decls) + "}</style>"
