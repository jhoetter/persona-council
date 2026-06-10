"""Customer theme contract (ticket customer-theme-contract): the slim design-system schema
both products consume — allowlisted color tokens, --sl-sans/--sl-mono font stacks, brand
name/logo. Covers: the EXACT allowlist (pinned), strict validation (unknown keys named,
off-shape values rejected — the CSS-injection guard, loudly), brand-logo rules (data: URI
or DATA_DIR-contained path, deny-by-default like the share-bundle inliner), the contextvar
seam round-trip, the brand-logo lockup render, and export propagation (PDF + HTML bundle
accept `theme_overrides` and inject the override block AFTER the base CSS)."""
from __future__ import annotations

import pytest

from sonaloop import services
from sonaloop.theming import (
    COLOR_VARS, FONT_VARS, customer_theme_css, theme_override_vars, validate_customer_theme,
)


def _data_dir(tmp_path, monkeypatch):
    from sonaloop import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return tmp_path


_THEME = {
    "colors": {"--accent": "#0a7", "--bg": "#fffdf8", "--sidebar": "#f2efe8"},
    "fonts": {"--sl-sans": "Acme Sans, Sona, Geist, system-ui, sans-serif"},
    "brand": {"name": "Acme Research", "logo": "data:image/png;base64,iVBORw0KGgo="},
}


# ------------------------------------------------------------------- the contract: accept

def test_allowlist_is_the_exact_inspector_themeable_set():
    # The contract IS the allowlist — a change here is a breaking schema change for
    # cloud/research persisted themes, so it must be deliberate.
    assert COLOR_VARS == ("--accent", "--accent-ink", "--accent-weak", "--ink", "--ink-2",
                          "--muted", "--faint", "--bg", "--panel", "--sidebar", "--line",
                          "--green", "--amber", "--red")
    assert FONT_VARS == ("--sl-sans", "--sl-mono")


def test_validate_accepts_the_full_slim_schema_and_returns_the_canonical_dict():
    theme = validate_customer_theme(_THEME)
    assert theme == _THEME                                   # canonical == normalized input
    assert validate_customer_theme({}) == {}                 # everything is optional
    # every allowlisted var is individually accepted (values stripped)
    theme = validate_customer_theme({"colors": {v: "  #123456 " for v in COLOR_VARS},
                                     "fonts": {v: "Acme, Sona, sans-serif" for v in FONT_VARS}})
    assert theme["colors"] == {v: "#123456" for v in COLOR_VARS}
    assert set(theme["fonts"]) == set(FONT_VARS)


def test_theme_override_vars_flatten_into_the_contextvar_seam():
    from sonaloop.web import _ext
    flat = theme_override_vars(validate_customer_theme(_THEME))
    assert flat == {"--accent": "#0a7", "--bg": "#fffdf8", "--sidebar": "#f2efe8",
                    "--sl-sans": "Acme Sans, Sona, Geist, system-ui, sans-serif"}
    token = _ext.set_theme_overrides(flat)
    try:
        css = _ext.theme_override_css()                      # nothing validated gets dropped
        assert css.startswith('<style id="theme-overrides">:root{')
        for k, v in flat.items():
            assert f"{k}:{v}" in css
    finally:
        _ext.reset_theme_overrides(token)


# ------------------------------------------------------------------- the contract: reject

def test_unknown_keys_are_rejected_with_the_allowlist_named():
    with pytest.raises(ValueError, match=r"\['colors', 'fonts', 'brand'\]"):
        validate_customer_theme({"components": {}})
    with pytest.raises(ValueError, match="must be an object"):
        validate_customer_theme(["--accent"])
    # structural tokens are NOT customer-themeable — spacing/radius/type-scale/--paper
    for var in ("--paper", "--s-4", "--radius", "--t-body", "--sl-radius-lg"):
        with pytest.raises(ValueError, match="--accent"):    # the allowlist is named
            validate_customer_theme({"colors": {var: "#fff"}})
    with pytest.raises(ValueError, match="--sl-sans"):
        validate_customer_theme({"fonts": {"--sl-pixel": "Comic Sans"}})


def test_off_shape_values_are_rejected_not_silently_dropped():
    for evil in ("#fff;}body{display:none}", "url(javascript:alert(1))", "", "red!important"):
        with pytest.raises(ValueError, match="off-shape"):
            validate_customer_theme({"colors": {"--accent": evil}})
    with pytest.raises(ValueError, match="off-shape"):       # family names are UNQUOTED
        validate_customer_theme({"fonts": {"--sl-sans": '"Acme Sans", sans-serif'}})


def test_brand_rules(tmp_path, monkeypatch):
    data = _data_dir(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match=r"\['name', 'logo'\]"):
        validate_customer_theme({"brand": {"tagline": "x"}})
    with pytest.raises(ValueError, match="non-empty"):
        validate_customer_theme({"brand": {"name": "  "}})
    # logo: data: must be a base64 image/*; no external URLs; paths must stay in DATA_DIR
    with pytest.raises(ValueError, match="image"):
        validate_customer_theme({"brand": {"logo": "data:text/html;base64,PGI+"}})
    for url in ("https://evil.example/logo.png", "//cdn.example/logo.png", "javascript:alert(1)"):
        with pytest.raises(ValueError, match="external URLs"):
            validate_customer_theme({"brand": {"logo": url}})
    with pytest.raises(ValueError, match="escapes the data dir"):
        validate_customer_theme({"brand": {"logo": "../outside/logo.png"}})
    (data / "brand").mkdir()
    (data / "brand" / "logo.png").write_bytes(b"")
    theme = validate_customer_theme({"brand": {"logo": "brand/logo.png"}})
    assert theme["brand"]["logo"] == str(data / "brand" / "logo.png")    # resolved + contained


# ------------------------------------------------------- brand: the wordmark seam renders it

def test_brand_logo_replaces_the_wordmark_in_the_lockup(store, monkeypatch):
    from sonaloop.web import _ext
    from sonaloop.web._components import _layout
    monkeypatch.setattr(_ext, "_BRAND", _ext._BRAND)         # restore the process globals
    monkeypatch.setattr(_ext, "_BRAND_LOGO", None)
    uri = validate_customer_theme(_THEME)["brand"]["logo"]
    _ext.set_brand("Acme Research", logo=uri)
    html = _layout("T", "<p>x</p>", store)
    assert f'<img class="sl-logo__img" src="{uri}" alt="Acme Research">' in html
    assert "sl-logo__word" not in html.split("</head>", 1)[1]            # wordmark replaced


# --------------------------------------------------------------- exports carry the theme

def _synthesis(store):
    return services.record_synthesis(
        "Acme study", "hmw", [], {"gesamtbild": "Overall positive."},
        goal="Does it land?", store=store)


def test_html_bundle_injects_the_override_block_after_the_base_css(store, tmp_path, monkeypatch):
    _data_dir(tmp_path, monkeypatch)
    syn = _synthesis(store)
    out = services.export_synthesis_html(syn["id"], store=store, theme_overrides=_THEME)
    html = (tmp_path / "export" / "share" / out["token"] / "index.html").read_text(encoding="utf-8")
    block = '<style id="theme-overrides">:root{--accent:#0a7;--bg:#fffdf8;--sidebar:#f2efe8;' \
            "--sl-sans:Acme Sans, Sona, Geist, system-ui, sans-serif}</style>"
    assert block in html
    assert html.index(block) > html.index(":root{--bg:")     # AFTER the base tokens: cascade wins
    assert html.index(block) > html.index("</style>")
    assert html.index(block) < html.index("</head>")
    # no theme => bit-identical contract: no override block at all
    out2 = services.export_synthesis_html(syn["id"], store=store)
    html2 = (tmp_path / "export" / "share" / out2["token"] / "index.html").read_text(encoding="utf-8")
    assert "theme-overrides" not in html2


def test_exports_validate_theme_overrides_before_any_work(store, tmp_path, monkeypatch):
    _data_dir(tmp_path, monkeypatch)
    syn = _synthesis(store)
    bad = {"colors": {"--paper": "#fff"}}
    with pytest.raises(ValueError, match="themeable"):
        services.export_synthesis_html(syn["id"], store=store, theme_overrides=bad)
    # the PDF path validates BEFORE the browser gate — a bad theme fails the same way
    # whether or not chromium is installed
    with pytest.raises(ValueError, match="themeable"):
        services.export_synthesis_pdf(syn["id"], store=store, theme_overrides=bad)


def test_customer_theme_css_is_empty_for_a_brand_only_theme():
    assert customer_theme_css(validate_customer_theme({"brand": {"name": "Acme"}})) == ""
