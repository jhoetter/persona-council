# Keyboard conventions

The shared keyboard contract across the Sonaloop surfaces. The inspector implements it
in `sonaloop/web/_keymap.py` (one registry; the `?` cheat sheet and the client keymap
are both generated from it). The React apps (tracker / data / website) should mirror
the same chords and overlay behavior — declare bindings once, generate the cheat sheet
from that declaration, never hand-maintain the two in parallel.

## Bindings

| Keys      | Scope  | Action |
|-----------|--------|--------|
| `?`       | Global | Open/close the shortcuts cheat sheet |
| `⌘K` / `Ctrl+K` | Global | Open the command palette |
| `g` `h`   | Global | Go home |
| `g` `p`   | Global | Go to personas |
| `g` `c`   | Global | Go to councils |
| `g` `s`   | Global | Go to syntheses/reports |
| `g` `a`   | Global | Go to activity |
| `g` `r`   | Global | Go to runs |
| `g` `d`   | Global | Go to documentation |
| `Esc`     | Global | Close overlays; cancel a pending chord |
| `j` / `k` | Lists  | Move row focus down/up (visible focus style) |
| `Enter`   | Lists  | Open the focused row (slide-over with the full detail page; `Esc` closes it) |
| `o`       | Lists  | Open the focused row straight as a full page |
| `[` / `]` | Detail | Previous / next sibling record |

## Behavior rules

- **Typing guard**: every binding is disabled while focus is in an `input`, `textarea`,
  `select`, or `contenteditable` element. `Esc` is the one exception (it may close an
  overlay), and it must never clear the user's field content.
- **No modifier shadowing**: plain-key bindings never fire while `⌘`/`Ctrl`/`Alt` is
  held — `⌘K` (palette) and native browser shortcuts stay untouched.
- **Chords**: `g` opens a ~900 ms chord window; an unknown second key or `Esc` cancels
  silently. Chords are sequences, not held combinations.
- **Cheat sheet overlay**: opened by `?` (and by a visible "`?` for shortcuts" hint in
  the chrome + a command-palette entry). It is grouped by scope (Global / Lists /
  Detail), rendered from the binding registry, is `role="dialog" aria-modal="true"`,
  and closes on `Esc`, the backdrop, or its close button.
- **Platform modifier glyphs**: render `⌘` on macOS and `Ctrl` elsewhere (detect at
  runtime; the inspector swaps the glyph client-side).
- **List focus**: `j`/`k` operate on the page's declared rows container (the inspector
  marks it `data-keynav`); the focused row gets a visible focus style and `Enter`
  activates it. Pages without such a container ignore the keys.
- **Sibling navigation**: `[`/`]` only act when the page declares its prev/next sibling
  URLs (the inspector emits a hidden `#km-siblings` element with `data-prev`/`data-next`
  server-side). Pages that don't know their siblings skip gracefully — no error, no
  fallback guessing.

## Adding a binding (inspector)

Add ONE entry to `BINDINGS` in `sonaloop/web/_keymap.py` (keys, scope, i18n description
key in both languages, action: a URL to navigate or a named JS hook). The cheat sheet,
the client config, and the registry-completeness test all pick it up automatically.
