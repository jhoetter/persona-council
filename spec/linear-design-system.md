# Linear Design System — extracted via Mobbin (L1)

> **Status:** SPEC (authored from real Linear references on Mobbin). Authority for L-exec (restyle).
> **Sources (Mobbin, app=Linear, web):** issue list + sidebar (dark): `e142df2a…`, `cc5d476b…`,
> board `720724d3…`; command palette `c8989882…`; context menu `9dc8318f…`; issue detail + right
> properties rail (light) `6cd65ea1…`, `0f43a4ae…`; decline modal `6fbf9c9f…`; dark-mode detail
> `178f8c31…`. All `curated by Mobbin`.

## 1. Essence (what makes it read as Linear)
Quiet, dense, keyboard-first. Near-monochrome surfaces with ONE restrained indigo accent. Tiny type
(13px UI), tight rows, hairline dividers, generous left padding, muted secondary text, soft elevation
on menus/modals. Color appears only as small status/label dots and the accent on the primary action.

## 2. Tokens

### 2.1 Color — DARK (default; Linear's signature)
```
--bg:        #101113   /* app background (very dark, faintly blue-gray) */
--sidebar:   #0d0e10   /* sidebar, slightly darker than content */
--panel:     #16171a   /* content surface / cards */
--panel-2:   #1c1d21   /* elevated surface (menus, hover fills) */
--overlay:   #1a1b1e   /* modal / command palette surface */
--line:      #23252a   /* hairline borders/dividers */
--line-2:    #1b1d21   /* faint inner dividers */
--ink:       #e6e7ea   /* primary text */
--muted:     #8a8f98   /* secondary text (Linear's exact gray family) */
--faint:     #6b7076   /* tertiary text, ids, timestamps */
--accent:    #7c84e8   /* indigo accent for dark (brand #5E6AD2 lifted for contrast) */
--accent-ink:#ffffff
--accent-weak:#1d2030 /* selected/hover tint of accent */
--hover:     #1a1b1f   /* row/nav hover */
--sel:       #1f2128   /* selected row */
--green:#4cb782 --amber:#d9a23b --red:#e0566a --violet:#9a8cff --blue:#5e9fe0
```

### 2.2 Color — LIGHT
```
--bg:#ffffff --sidebar:#fbfbfb --panel:#ffffff --panel-2:#f6f6f7 --overlay:#ffffff
--line:#ececed --line-2:#f1f1f2 --ink:#1a1c1f --muted:#6b7076 --faint:#9098a0
--accent:#5e6ad2 --accent-ink:#ffffff --accent-weak:#eef0fb --hover:#f5f5f6 --sel:#f0f1f4
--green:#3d9b6b --amber:#b87a25 --red:#cf4d5f --violet:#7a5ed1 --blue:#3d7fc4
```

### 2.3 Typography
```
font: "Inter", -apple-system, "Segoe UI", system-ui, sans-serif;   /* Linear = Inter */
--fs-12:11.5px  --fs-13:13px(base UI)  --fs-14:14px  --fs-15:15px
--fs-title:21px (issue/page title, weight 600, letter-spacing -0.01em)
--fs-h:26px (top page heading, weight 600, -0.015em)
weights: 400 body, 500 labels/nav, 600 titles/primary.  line-height ~1.45 body, ~1.25 titles.
ids/keys/shortcuts: same Inter, --faint, slightly tabular.
```

### 2.4 Spacing / radius / elevation / motion
```
space scale: 2,4,6,8,12,16,20,24,32  (px)
row height: 34px (list), 30px (sidebar nav), 28px (menu item)
radii: --r-1:6px (buttons/inputs/chips) --r-2:8px (cards/menus) --r-3:10px (modals/palette)
borders: 1px hairline --line; focus ring: 0 0 0 2px color-mix(--accent 45%, transparent)
shadow-pop (menus/palette/modals): 0 8px 28px rgba(0,0,0,.28), 0 1px 2px rgba(0,0,0,.2)
transition: 120ms ease (hover/bg/border), 150ms for popovers
density: tight. horizontal page padding 24px; content max-width ~ 720px (detail), lists full-bleed.
```

## 3. Components
- **Sidebar (~232px):** `--sidebar` bg, no border or a hairline right border. Workspace switcher row
  at top (avatar + name + chevron) and a search + compose icon. Section headers tiny, `--faint`,
  500, letter-spacing .02em ("Your teams", "Workspace"). Nav rows: 30px, icon(16) + label(13/500),
  6px radius, hover `--hover`, selected `--sel` + `--ink` (not accent-filled). Collapsible groups.
- **Top bar / breadcrumbs:** crumb = `team › ID › title`, `--muted` with `--ink` last segment;
  right side: small ghost icon buttons + a "View" control. 13px.
- **List rows (34px):** leading status glyph (●/◔/✓ in status color), ID in `--faint`, title in
  `--ink`(13/400→500 on hover), right cluster: label pills (dot+text, `--panel-2` bg, `--muted`),
  assignee avatar(18px circle), date `--faint`. Row hover `--hover`; selected `--sel`. Hairline
  `--line-2` row separators OR none (group headers carry the structure). Group headers: small,
  `--muted`, with a count chip.
- **Buttons:** primary = `--accent` bg / `--accent-ink`, 13/500, 6px radius, 28px tall, no/!subtle
  shadow. secondary = transparent + `--line` border, `--ink`. ghost/icon = transparent, hover
  `--hover`. destructive = `--red`.
- **Chips / labels / badges:** pill, 11.5px, `--panel-2` bg, `--muted` text, a 6px colored dot;
  no border. Status badges use the status color dot + label.
- **Inputs / menus / dropdowns:** input = `--panel` bg, `--line` border, 6px radius, focus ring.
  menu = `--panel-2`/`--overlay` surface, 8px radius, shadow-pop, items 28px with icon + label +
  right-aligned shortcut hint in `--faint`.
- **Command palette (Cmd-K):** centered modal ~560px, `--overlay`, 10px radius, shadow-pop, a
  context line at top ("Issue · JOH-11 …"), a search input "Type a command or search…", then a list
  of actions (icon + label + right-aligned single-letter/⌘ shortcut). Read-only NAVIGATION only here.
- **Detail view:** breadcrumb header; centered content column (~720px) with a large 21/600 title;
  a **right properties rail** (Status/Priority/Assignee/Labels/Due) as icon+value rows, `--muted`
  labels. Activity/comment area below.
- **Empty states:** centered, muted icon + one line + a subtle primary action. **Toasts:** bottom,
  small `--overlay` card + shadow-pop, optional "View" link.
- **Focus & keyboard:** visible focus ring everywhere; Cmd-K palette; arrow/J-K row nav feel.

## 4. Mapping to our app (what each Linear pattern becomes here)
- Linear sidebar ⇒ our left nav (Projects / Personas / Favorites) — restyle to the sidebar spec.
- Linear issue list ⇒ our Projects list, Personas list, synthesis/council lists — the row spec.
- Linear issue detail + properties rail ⇒ our synthesis/council/persona detail (right rail for
  meta: councils, status, segments, dates).
- Linear Cmd-K ⇒ a read-only quick-nav palette (jump to project/persona/synthesis).
- Linear badges ⇒ our tag chips (already data-driven; restyle to the chip spec).
- The project graph stays, but its chrome (controls, minimap, hints) adopts the dark surfaces +
  hairlines + accent.

## 5. Non-negotiables carried over
Light + dark parity (dark is the signature). Presentation-from-data preserved (methodology/artifact
colors stay data-driven; this is the app *chrome*). Web UI stays read-only (Cmd-K navigates only).
