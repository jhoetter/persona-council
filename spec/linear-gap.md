# Linear Gap Analysis (L2) + L-exec outcome

> Compares the app's prior tokens/components to `linear-design-system.md` and records what L-exec
> changed. The app is token-driven, so the token rewrite re-skins every screen at once.

## Token deltas (before → after)
| token | before | after (Linear) |
|---|---|---|
| accent | teal-blue `#2f6f9f` / `#62a6d8` | **indigo** `#5e6ad2` (light) / `#7c84e8` (dark) — Linear's signature |
| light bg | warm gray `#f7f7f5` | neutral `#ffffff`; sidebar `#fbfbfb` |
| dark bg | `#141619` | deeper, bluer `#101113`; sidebar `#0d0e10`; panel `#16171a` |
| borders | `#e7e7e3` / `#2a2e34` | hairline `#ececed` / `#23252a` |
| new tokens | — | `--sidebar`, `--overlay`, `--sel`, `--faint`, `--accent-ink` |
| font | system sans 13.5px | **Inter** 13px, `letter-spacing:-0.003em` (loaded via Google Fonts) |
| nav active | accent-weak fill + left accent bar | subtle `--sel` bg + `--ink` (Linear's quiet selection) |
| buttons | one style | + `.btn.primary` (accent), 30px, 13/500; focus-visible ring |
| chips/pills | bordered pill | borderless `--panel-2` chip, `--muted`, 5px radius |

## L-exec — done
- Rewrote both `:root` token sets (light + dark) + the `[data-theme]` overrides to the Linear system.
- Switched the UI font to **Inter** (preconnect + Google Fonts link in `<head>`; system fallback).
- Tightened density (nav rows 30px, base 13px), hairline borders, Linear selection style.
- Restyled buttons (+ primary variant + focus ring), chips/pills, sidebar surface (`--sidebar`).
- Because every rule uses `var(--*)`, all screens (projects, graph, synthesis/council/persona detail,
  prototype viewer, plan view) inherit the Linear look in light + dark.

## Deferred (documented follow-ups — to protect the overnight showcase from over-scoping)
- **Cmd-K command palette** (read-only quick-nav to project/persona/synthesis): a self-contained
  feature; spec'd in `linear-design-system.md` §3; add as a focused follow-up.
- Per-screen micro-polish (issue-row hover affordances on every list, right-properties-rail layout
  on detail pages) — the global token/component pass covers the bulk; fine-grained per-screen
  matching is a follow-up tracked by the UX audit (Phase U).
