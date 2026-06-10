#!/usr/bin/env bash
# Refresh the VENDORED icon module (sonaloop/_icons.py) from the single source of
# truth in ../sonaloop-design (our design system). The icons live there (icons.data.mjs
# -> scripts/gen.mjs -> py/sonaloop_icons/__init__.py); we vendor a copy so the published
# PyPI package has no local-path dependency. Run this after editing icons.data.mjs + regenerating.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$here/../sonaloop-design/py/sonaloop_icons/__init__.py"
dst="$here/sonaloop/_icons.py"

if [[ ! -f "$src" ]]; then
  echo "error: source icons module not found at $src" >&2
  echo "       run 'node scripts/gen.mjs' in ../sonaloop-design first." >&2
  exit 1
fi

note='"""sonaloop._icons — VENDORED COPY of the sonaloop-design icon module.

Do not edit by hand. Single source of truth: ../sonaloop-design (icons.data.mjs ->
scripts/gen.mjs). Refresh this vendored copy with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency.
'

# Replace the generated module's opening docstring line with the vendoring note.
{
  printf '%s\n' "$note"
  tail -n +2 "$src"
} > "$dst"

echo "synced $src -> $dst ($(wc -c < "$dst") bytes)"

# Design tokens — generated CSS module, copied verbatim (it carries its own vendoring
# note). web_assets.py imports TOKENS_CSS from it. Single source: ../sonaloop-design.
tsrc="$here/../sonaloop-design/py/sonaloop_icons/tokens.py"
tdst="$here/sonaloop/_tokens.py"
if [[ -f "$tsrc" ]]; then
  cp "$tsrc" "$tdst"
  echo "synced $tsrc -> $tdst ($(wc -c < "$tdst") bytes)"
else
  echo "warn: tokens module not found at $tsrc (run 'node scripts/gen-tokens.mjs' in ../sonaloop-design)" >&2
fi

# Shared component layer (.sl-* classes), same generate→vendor path. web_assets.py prepends it.
csrc="$here/../sonaloop-design/py/sonaloop_icons/components_css.py"
cdst="$here/sonaloop/_components_css.py"
if [[ -f "$csrc" ]]; then
  cp "$csrc" "$cdst"
  echo "synced $csrc -> $cdst ($(wc -c < "$cdst") bytes)"
else
  echo "warn: components module not found at $csrc (run 'node scripts/gen-tokens.mjs' in ../sonaloop-design)" >&2
fi

# Chart components (.sl-chart/.sl-bar/.sl-pie/.sl-quad renderers), hand-authored in the design system.
# Vendored so the report renderer can embed charts (bar/pie/effort·impact). web/_report.py imports it.
chsrc="$here/../sonaloop-design/py/sonaloop_icons/charts.py"
chdst="$here/sonaloop/_charts.py"
if [[ -f "$chsrc" ]]; then
  note='"""sonaloop._charts — VENDORED COPY of the sonaloop-design chart components.

Do not edit by hand. Single source of truth: ../sonaloop-design (py/sonaloop_icons/charts.py +
styles/components.css `.sl-chart*`). Refresh with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency.
'
  {
    printf '%s\n' "$note"
    tail -n +2 "$chsrc"
  } > "$chdst"
  echo "synced $chsrc -> $chdst ($(wc -c < "$chdst") bytes)"
else
  echo "warn: charts module not found at $chsrc" >&2
fi

# App-shell behaviour (SHELL_JS) — the SSR counterpart of the React <AppShell>, hand-authored
# in the design system. web/_components.py emits it in the layout to drive the .sl-app-shell chrome.
shsrc="$here/../sonaloop-design/py/sonaloop_icons/shell.py"
shdst="$here/sonaloop/_shell.py"
if [[ -f "$shsrc" ]]; then
  note='"""sonaloop._shell — VENDORED COPY of the sonaloop-design app-shell behaviour.

Do not edit by hand. Single source of truth: ../sonaloop-design (py/sonaloop_icons/shell.py +
styles/components.css `.sl-app-shell`). Refresh with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency.
'
  {
    printf '%s\n' "$note"
    tail -n +2 "$shsrc"
  } > "$shdst"
  echo "synced $shsrc -> $shdst ($(wc -c < "$shdst") bytes)"
else
  echo "warn: shell module not found at $shsrc" >&2
fi

# Deck master template (palette/type/frame/layouts + placeholder SAMPLE_SLIDES), generated from
# deck.data.mjs (scripts/gen-deck.mjs). _pptx.py renders every layout from it; `sonaloop
# template-deck` renders SAMPLE_SLIDES into the demo deck.
dsrc="$here/../sonaloop-design/py/sonaloop_icons/deck.py"
ddst="$here/sonaloop/_deck.py"
if [[ -f "$dsrc" ]]; then
  note='"""sonaloop._deck — VENDORED COPY of the sonaloop-design deck master template.

Do not edit by hand. Single source of truth: ../sonaloop-design/deck.data.mjs ->
scripts/gen-deck.mjs. Refresh with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency."""'
  {
    printf '%s\n' "$note"
    tail -n +8 "$dsrc"
  } > "$ddst"
  echo "synced $dsrc -> $ddst ($(wc -c < "$ddst") bytes)"
else
  echo "warn: deck module not found at $dsrc (run 'node scripts/gen-deck.mjs' in ../sonaloop-design)" >&2
fi

# Deck brand assets (rasterized icons/logos/canvases as base64), generated alongside deck.py.
# Copied verbatim — its generated docstring already carries the vendoring note.
asrc="$here/../sonaloop-design/py/sonaloop_icons/deck_assets.py"
adst="$here/sonaloop/_deck_assets.py"
if [[ -f "$asrc" ]]; then
  cp "$asrc" "$adst"
  echo "synced $asrc -> $adst ($(wc -c < "$adst") bytes)"
else
  echo "warn: deck assets module not found at $asrc (run 'node scripts/gen-deck.mjs' in ../sonaloop-design)" >&2
fi
