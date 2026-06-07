#!/usr/bin/env bash
# Refresh the VENDORED icon module (sonaloop/_icons.py) from the single source of
# truth in ../sonaloop-icons. The icons live there (icons.data.mjs -> scripts/gen.mjs
# -> py/sonaloop_icons/__init__.py); we vendor a copy so the published PyPI package
# has no local-path dependency. Run this after editing icons.data.mjs + regenerating.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$here/../sonaloop-icons/py/sonaloop_icons/__init__.py"
dst="$here/sonaloop/_icons.py"

if [[ ! -f "$src" ]]; then
  echo "error: source icons module not found at $src" >&2
  echo "       run 'node scripts/gen.mjs' in ../sonaloop-icons first." >&2
  exit 1
fi

note='"""sonaloop._icons — VENDORED COPY of the sonaloop-icons Python module.

Do not edit by hand. Single source of truth: ../sonaloop-icons (icons.data.mjs ->
scripts/gen.mjs). Refresh this vendored copy with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency.
'

# Replace the generated module's opening docstring line with the vendoring note.
{
  printf '%s\n' "$note"
  tail -n +2 "$src"
} > "$dst"

echo "synced $src -> $dst ($(wc -c < "$dst") bytes)"
