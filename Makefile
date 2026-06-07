WEB_PORT ?= 8787
FORWARDED_WEB_PORT ?= 18787

UV ?= uv

.PHONY: install dev dev-forwarded mcp snapshot restore skills test test-smoke kill-ports playwright

# Symlink version-controlled skills into .claude/skills/ so Claude Code discovers
# them (.claude/skills is gitignored). Run once after clone.
skills:
	@mkdir -p .claude/skills
	@for d in claude-skills/*/; do n=$$(basename $$d); ln -sfn ../../$$d .claude/skills/$$n; echo "linked $$n"; done

# Write the portable, local-only snapshot of all generated state to data/export/.
snapshot:
	$(UV) run sonaloop export-snapshot

# Rebuild the runtime DB from data/export/ (use after `git clone` to reproduce
# the exact local state without regenerating).
restore:
	$(UV) run sonaloop import-snapshot

install:
	$(UV) sync
	$(UV) run playwright install chromium   # headless browser for prototype screenshots + meta-report PDF
	@echo "installed - run 'make dev' for :$(WEB_PORT) or 'make dev-forwarded' for :$(FORWARDED_WEB_PORT)"

# --reload is scoped to the Python source: without --reload-dir the stat-poller
# walks the whole tree every 250ms (.venv/, data/ with its constantly-changing
# SQLite WAL, prototypes/) and pegs a CPU, which can wedge the server over time.
dev: kill-ports
	@echo "→ Web   http://127.0.0.1:$(WEB_PORT)"
	$(UV) run python -m uvicorn 'sonaloop.web:create_app' --factory --reload \
	  --reload-dir sonaloop --reload-exclude '*/data/*' \
	  --host 127.0.0.1 --port $(WEB_PORT)

# Forwarded dev profile for viewing this machine through an SSH tunnel.
#   ssh -L $(FORWARDED_WEB_PORT):127.0.0.1:$(FORWARDED_WEB_PORT) <host>
dev-forwarded:
	$(MAKE) dev WEB_PORT=$(FORWARDED_WEB_PORT)

mcp:
	$(UV) run sonaloop-mcp

# Full test suite (pytest, dev dependency-group). Hermetic: temp DB, no network.
test:
	$(UV) run --group dev pytest -q

test-smoke:
	$(UV) run python -m compileall sonaloop
	$(UV) run sonaloop persona-list >/dev/null
	$(UV) run python -c "from sonaloop.web import create_app; app=create_app(); print(app.title)"

# Re-fetch just the chromium binary (the playwright package is a hard dependency via `uv sync`).
# Needed for prototype screenshots + the meta-report PDF export.
playwright:
	$(UV) run playwright install chromium

kill-ports:
	@for p in $(WEB_PORT); do \
	  pids=$$(lsof -ti :$$p 2>/dev/null); \
	  [ -n "$$pids" ] && kill -9 $$pids 2>/dev/null || true; \
	done; true
