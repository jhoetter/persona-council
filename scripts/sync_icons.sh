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
