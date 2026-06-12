#!/usr/bin/env python3
"""Visual-regression harness for the inspector (spec/ux-contract.md §5 item 2): `make ux`.

Seeds a TEMP data dir with the two bundled example projects (services.load_example — the same
deterministic record_* replay the tests use), boots the app on a free port, and screenshots the
canonical screens (SCREENS below) in light AND dark at 1440x900 via Playwright.

Modes:
  --update    write the shots as goldens to tests/ux_goldens/<name>.png (commit them)
  (default)   compare fresh shots against the goldens: a small per-pixel tolerance absorbs
              antialiasing; a screen fails when more than DIFF_RATIO of its pixels move.
              Failing diffs (golden | current | heat overlay) land in /tmp/ux-diff/; exit 1.

Determinism notes: the seed is replayed fresh on every run (stable ids; council/synthesis
timestamps come from the fixtures). Entities stamped at LOAD time (project created/updated,
activity events) render "today"/"just now" relative dates — those drift inside the pixel
tolerance day-to-day; refresh with --update if a date rollover ever trips the threshold.
Pixel comparison uses Pillow, which ships as a hard transitive dependency (python-pptx).
The SSE stream (/api/events) keeps the network busy forever — wait for 'load' + a settle,
NEVER 'networkidle'.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "tests" / "ux_goldens"
DIFF_DIR = Path("/tmp/ux-diff")
VIEWPORT = {"width": 1440, "height": 900}
PIXEL_TOLERANCE = 24      # per-channel delta treated as "same" (antialiasing / font hinting)
DIFF_RATIO = 0.005        # fail when > 0.5% of pixels move beyond the tolerance
SETTLE_MS = 600           # post-load settle (SSE keeps the network busy; never networkidle)

# ---------------------------------------------------------------- seed (env BEFORE import)

_TMP = Path(tempfile.mkdtemp(prefix="sonaloop-ux-"))
# DATA_DIR = _TMP/data and (seed-side) services.ROOT = _TMP — the source-checkout layout
# (DATA_DIR == ROOT/data), so asset binaries written under ROOT/data/assets are served by
# the app's /data mount.
os.environ["SONALOOP_DATA_DIR"] = str(_TMP / "data")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'sonaloop.db'}"
os.environ["PERSONA_COUNCIL_DISABLE_EMBEDDINGS"] = "1"
os.environ["PERSONA_COUNCIL_CONTENT_LANGUAGE"] = "en"
os.environ["PERSONA_COUNCIL_UI_LANGUAGE"] = "en"

sys.path.insert(0, str(ROOT))


def seed() -> dict[str, str]:
    """Load both bundled examples through the real record_* layer and resolve the detail-page
    ids for the screen list. Deterministic: every entity id is stable per fixture key."""
    from sonaloop import services
    from sonaloop.storage import Store

    # Asset binaries write under services.ROOT/data/assets (the conftest pattern): point it at
    # the temp dir so the seed never touches the repo's real asset store — and the server
    # subprocess serves the same files from its /data mount (DATA_DIR = the same temp dir).
    services.ROOT = _TMP
    store = Store()
    premium = services.load_example("premium-pricing-study", store=store)
    positioning = services.load_example("positioning-council", store=store)
    council = sorted(services.list_councils(store=store), key=lambda c: c["id"])[0]
    synthesis = sorted(services.list_syntheses(store=store), key=lambda s: s["id"])[0]
    persona = sorted(store.list_personas(), key=lambda p: p["id"])[0]
    # Assets (UX U8): one evidence input + one generated deliverable on the positioning project,
    # so the asset detail page + the project files lens are in the regression net. created_at is
    # pinned (attach stamps load time, which would drift the row dates across days).
    pid = positioning["project_id"]
    services.attach_asset(pid, path=str(ROOT / "docs" / "assets" / "sonaloop-council.png"),
                          title="Stakeholder sketch", source="mcp: shared by the user",
                          notes="Reference screen from the kickoff", store=store)
    services.attach_asset(pid, content_base64="UEsDBA==", filename="positioning-report.pptx",
                          title="Positioning report (PPTX)", direction="out",
                          source=f'synthesis:{synthesis["id"]}', store=store)
    proj = store.get_research_project(pid)
    for i, a in enumerate(proj["assets"]):
        a["created_at"] = f"2026-06-{10 + i:02d}T09:00:00+00:00"
    store.upsert_research_project(proj)
    evidence = next(a for a in proj["assets"] if a.get("direction") != "out")
    return {
        "project_premium": premium["project_id"],
        "project_positioning": positioning["project_id"],
        "council": council["id"],
        "synthesis": synthesis["id"],
        # the positioning project's own synthesis — the ?d= SSR screen opens it over its project
        "synthesis_positioning": sorted(proj.get("study_ids") or [])[0],
        "persona": persona["id"],
        "asset": evidence["id"],
    }


def screens(ids: dict[str, str]) -> list[tuple]:
    """The ~12 canonical screens (name, path[, click-selector]) — shot in light AND dark.
    An optional third element is clicked after load (waiting for the slide-over), so the
    set covers the row → slide-over interaction (§8.1), not just plain pages."""
    return [
        ("projects", "/projects"),
        ("project-premium", f'/projects/{ids["project_premium"]}'),
        ("project-positioning", f'/projects/{ids["project_positioning"]}'),
        # the Linear-grade FilterBar (UX U10): active chips + the server-filtered outline
        ("project-filtered", f'/projects/{ids["project_positioning"]}?kind=decision,hypothesis'),
        # the Notion-style slide-over open over the outline (UX U6/U11): full detail page
        # in the wide drawer, list visible behind, the CONTEXT URL (?d=) pushed
        ("project-slideover", f'/projects/{ids["project_positioning"]}',
         '[data-drawer^="/syntheses/"]'),
        # the same anatomy reached by ADDRESS (UX U11): direct load of the ?d= context URL
        # SSR-renders background + open panel — reload keeps the list context
        ("project-slideover-ssr",
         f'/projects/{ids["project_positioning"]}?d=%2Fsyntheses%2F{ids["synthesis_positioning"]}'),
        ("personas", "/personas"),
        ("persona", f'/personas/{ids["persona"]}'),
        ("councils", "/councils"),
        ("council", f'/councils/{ids["council"]}'),
        ("synthesis", f'/syntheses/{ids["synthesis"]}'),
        ("decisions", "/decisions"),
        ("hypotheses", "/hypotheses"),
        # assets as a first-class surface (UX U8): the detail page (preview + provenance) and
        # the project files lens (chronological in/out provenance timeline)
        ("asset", f'/assets/{ids["asset"]}'),
        ("project-files", f'/projects/{ids["project_positioning"]}?view=files'),
        ("activity", "/activity"),
        ("documentation", "/documentation"),
        # the ⌘K palette v2 (UX V6) open on the project: Recent (the visits this context
        # accumulated over the screens above — deterministic) · Navigate (Library as ONE
        # expandable entry) · Actions. 4th element = the explicit wait selector.
        ("palette", f'/projects/{ids["project_positioning"]}',
         "[data-cmdk-open]", "#cmdk:not([hidden]) .sl-cmdk-item"),
    ]


# ---------------------------------------------------------------- server


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def boot(port: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "sonaloop.web:create_app", "--factory",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=os.environ.copy())
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/projects", timeout=1)
            return proc
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError("app process died during boot")
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("app did not come up on " + base)


# ---------------------------------------------------------------- shoot + compare


def shoot(base: str, shots: list[tuple], out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme in ("light", "dark"):
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
            # HEAD_JS applies localStorage.theme as [data-theme] before first paint.
            ctx.add_init_script(f"try{{localStorage.setItem('theme','{theme}')}}catch(e){{}}")
            page = ctx.new_page()
            for name, path, *click in shots:
                page.goto(base + path, wait_until="load")  # SSE forbids networkidle
                page.add_style_tag(content="*{animation:none!important;transition:none!important;"
                                           "caret-color:transparent!important}")
                page.wait_for_timeout(SETTLE_MS)
                if click:                                  # interaction screens (slide-over, ⌘K)
                    page.click(click[0] + " >> nth=0")
                    page.wait_for_selector(click[1] if len(click) > 1
                                           else "#drawer.is-open .sl-slide")
                    page.wait_for_timeout(SETTLE_MS)
                # Pin volatile SEED-TIME stamps (activity feed, project updated_at — minute
                # precision, different every run) to a fixed same-width string so the diff
                # only sees real layout/style drift, not the clock.
                page.evaluate(
                    """() => { const re = /\\b\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}\\b/g;
                       const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                       for (let n = walk.nextNode(); n; n = walk.nextNode())
                         if (re.test(n.nodeValue)) n.nodeValue = n.nodeValue.replace(re, '2026-01-01 00:00'); }""")
                target = out_dir / f"{name}--{theme}.png"
                page.screenshot(path=str(target))
                paths.append(target)
            ctx.close()
        browser.close()
    return paths


def compare(current: Path, golden: Path) -> float:
    """Fraction of pixels that differ beyond PIXEL_TOLERANCE (0.0 = identical enough)."""
    from PIL import Image, ImageChops

    with Image.open(golden) as g, Image.open(current) as c:
        g, c = g.convert("RGB"), c.convert("RGB")
        if g.size != c.size:
            return 1.0
        diff = ImageChops.difference(g, c).convert("L").point(
            lambda v: 255 if v > PIXEL_TOLERANCE else 0)
        hist = diff.histogram()
        return hist[255] / (diff.width * diff.height)


def write_diff(current: Path, golden: Path, name: str) -> None:
    from PIL import Image, ImageChops

    DIFF_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(golden) as g, Image.open(current) as c:
        g, c = g.convert("RGB"), c.convert("RGB")
        shutil.copy(golden, DIFF_DIR / f"{name}--golden.png")
        shutil.copy(current, DIFF_DIR / f"{name}--current.png")
        if g.size == c.size:
            mask = ImageChops.difference(g, c).convert("L").point(
                lambda v: 255 if v > PIXEL_TOLERANCE else 0)
            heat = c.copy()
            heat.paste((255, 0, 80), mask=mask)
            heat.save(DIFF_DIR / f"{name}--diff.png")


# ---------------------------------------------------------------- main


def main() -> int:
    update = "--update" in sys.argv[1:]
    ids = seed()
    port = free_port()
    proc = boot(port)
    try:
        shot_dir = GOLDEN_DIR if update else Path(tempfile.mkdtemp(prefix="sonaloop-ux-shots-"))
        paths = shoot(f"http://127.0.0.1:{port}", screens(ids), shot_dir)
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        shutil.rmtree(_TMP, ignore_errors=True)

    if update:
        print(f"wrote {len(paths)} goldens to {GOLDEN_DIR}/ — review + commit them")
        return 0

    if DIFF_DIR.exists():
        shutil.rmtree(DIFF_DIR)
    failures = []
    for current in paths:
        golden = GOLDEN_DIR / current.name
        if not golden.exists():
            failures.append((current.name, "no golden — run `make ux UPDATE=1`"))
            continue
        ratio = compare(current, golden)
        if ratio > DIFF_RATIO:
            write_diff(current, golden, current.stem)
            failures.append((current.name, f"{ratio:.2%} of pixels moved (limit {DIFF_RATIO:.2%})"))
        else:
            print(f"  ok   {current.name}  ({ratio:.3%})")
    if failures:
        print(f"\n✗ {len(failures)}/{len(paths)} screens drifted — diffs in {DIFF_DIR}/")
        for name, why in failures:
            print(f"  FAIL {name}: {why}")
        return 1
    print(f"✓ all {len(paths)} screens match the goldens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
