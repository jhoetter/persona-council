# Persona Council — Memory & Simulation Architecture

> **Status:** Proposal / living tracker. Started 2026-06-02.
> **Scope:** Wie Personas ein über Zeit wachsendes, abrufbares Gedächtnis
> bekommen und wie die Tagessimulation als **agentic MCP-Harness** läuft.
> **Leitsatz:** Nichts hardcodieren. Der Server stellt *Fähigkeiten* bereit; der
> steuernde LLM-Agent entscheidet, *wann* er sie nutzt. Outcomes (Projekt
> gewonnen/verloren, Baustelle, Abschluss, Dauer) werden **simuliert, nie
> verregelt**.

Grundprompts der Personas: [`persona-source-prompts.md`](persona-source-prompts.md)
(lokal, git-ignored) — niemals löschen. Alle generierten Daten dürfen jederzeit
neu erzeugt werden. Offene Arbeit wird im einzigen Tracker geführt:
[`../SPEC_TRACKER.md`](../SPEC_TRACKER.md). Hinweis: eine **geteilte Welt**
(personenübergreifendes Gedächtnis) wurde bewusst verworfen — kaum Vorteile bei
hoher Komplexität; Multi-Perspektive entsteht über Councils.

---

## 0. Warum überhaupt (Problem)

Heute fließt Erinnerung nur per **Recency** in die Simulation ein
(`render_soul` / `simulate_day` ziehen „die letzten 8–12 Events"). Daraus folgen
vier harte Grenzen:

1. **Kein Projekt-/Entitäts-Begriff.** „Café Lindgrün", „Anbau Reuter",
   „Familie Vogt", „Denkmalbehörde" leben nur als Freitext *in* Events. Kein
   Objekt sammelt über Zeit Zustand → man kann nicht fragen „wie geht Carla *ein
   Projekt* durch".
2. **Keine zeitliche Schichtung.** Nach ~12 Events fällt alles aus dem Kontext;
   ein Jahr Simulation sprengt den Kontext und verliert den Bogen.
3. **Keine Relevanz-Retrieval.** Man kann nicht „alles zu Projekt X" oder „was
   letzten Monat hier war" ziehen — nur „zuletzt".
4. **Hardcodierte `reflection`** (Template-Text, feste Themen) verstößt bereits
   gegen „nichts hardcodieren" und gegen SPEC „must not fall back to
   deterministic placeholder text".

---

## 1. Prinzipien (von bim-agent / bim-database übernommen)

1. **MCP = Fähigkeiten, nicht Implementierung.** Der Agent interessiert sich nicht
   für SQLite vs. Graph; er ruft `recall_memory(...)`. Die Technik dahinter darf
   sich ändern, ohne dass Prompts brechen.
2. **Context-Gatherer + Author-Split** (bim-agents Kernmuster — und schon heute
   das Modell von Persona Council): Ein MCP-Tool **sammelt Kontext** und
   **schreibt strukturiertes Ergebnis zurück**; das **Verfassen/Urteilen macht
   der Harness-LLM** (Claude Code / Codex), kein serverseitiger Text-API-Call.
3. **Erst grob, dann Detail** (bim-database): Kompaktheits-Hierarchie
   `list_* → *_status → *_summary → *_state`. Nie das volle Gedächtnis dumpen.
4. **Agent zieht on demand.** „Jetzt schaue ich, ob in der Historie was Passendes
   ist" ist ein *Tool-Call* des Agenten (`recall_memory`), kein Auto-Inject.
   Personas erzählen nicht ständig aus Erinnerungen — sie greifen *bei Bedarf*
   darauf zu.
5. **Plan vor Aktion** (bim-agents Scene-Plan): Vor der Tagessimulation wird ein
   **Tages-Plan** erzeugt, der erst analysiert, *was* heute dran/spannend ist.
6. **Envelope-Standard:** jedes Tool antwortet `{ ok, data, next_recommended_tool?,
   _meta }`. `next_recommended_tool` bildet einen impliziten Entscheidungs-DAG.
7. **Model-agnostisch.** Methodik in Specs, Harness-Glue (Skills/Loop) als Adapter.
8. **Nichts hardcodieren.** Dauer, Ausgang, Fortschritt von Projekten entstehen
   im LLM. Der Store *protokolliert* nur, was der Agent entschieden hat.

---

## 2. Instruktions-Hierarchie (Ziel-Struktur)

```
AGENTS.md                                  Repo-Einstieg (existiert)
└─ spec/memory-and-simulation-architecture.md   DIESE Datei: Architektur + Methodik
   ├─ spec/persona-source-prompts.md       kanonische Grundprompts (lokal, nie löschen)
   ├─ spec/mcp-tool-contract.md            exakte Tool-Signaturen + Envelope
   ├─ spec/simulation-loop-contract.md     der Driver-Loop, model-neutral
   └─ claude-skills/*/SKILL.md             dünne Harness-Adapter
```

---

## 3. Das Gedächtnis-Modell — drei Schichten + Projektion

Deckt sich mit dem Stand der Agenten-Memory-Forschung (CoALA-Schichten; Zep/
Graphiti = *temporaler* Wissensgraph; „Konsolidierung statt mehr speichern").

```
Schicht 1  EPISODISCH        experience_events (roh, zeitgestempelt)        ✔ existiert
Schicht 2  SEMANTISCH /       Entitäten (project|person|org|building|authority)
           TEMPORAL-GRAPH     + bi-temporale Fakten (t_valid / t_invalid)    ← neu
Schicht 3  KONSOLIDIERT       LLM-Digests Woche/Monat/Jahr + Projekt-Ledger  ← neu
                              (ersetzt die hardcodierte reflection)
PROJEKTION  MEMORY.md         pro Persona aus Schicht 2/3 gerendert          ← neu
            (LLM- & menschenlesbare Oberfläche, neben SOUL.md)
RETRIEVAL   recall_memory     HYBRID: Keyword/Entität + semantisch (Embeddings),
                              gewichtet mit Recency + Wichtigkeit, on demand
```

**Jede Persona hat ein abgeschlossenes Gedächtnis** (entschieden 2026-06-02):
Personas kennen einander *nicht*; Entitäten/Fakten werden **nicht**
personenübergreifend geteilt. (Eine geteilte Welt ist explizit nicht nötig.)

### 3.1 Warum „Struktur-Wahrheit + Markdown-Projektion"
- **Struktur (SQLite, bi-temporal)** ist die abfragbare Wahrheit → „Projekt-
  Timeline", „Zustand am Datum X" (time-travel), saubere Relationen. Emuliert
  einen temporalen Graphen *ohne* neue Infrastruktur (kein Neo4j).
- **MEMORY.md** ist die LLM-freundliche Projektion (wie SOUL.md): „Aktive
  Projekte (Mini-Timeline) · Schlüsselpersonen · zuletzt geschlossen · Archiv".
  Sie wird *gerendert*, nicht von Hand gepflegt.
- **Time-Travel** = `t_valid/t_invalid` + datierte Digests. Alte Stände werden
  **invalidiert, nie gelöscht** (Graphitis bi-temporales Modell) → jeder
  historische Zustand bleibt rekonstruierbar.

### 3.2 Entitäten & Fakten (Beispiel Carla / Café Lindgrün)
`entity(project "Café Lindgrün")` bekommt eine Fakten-Kette, die **Tag für Tag
vom LLM fortgeschrieben** wird:
```
Erstkontakt (Mai) → Aufmaß (2.6.) → Brandschutz-Auflage offen
 → Entwurf v1 präsentiert → Kunde will Änderung → … → Bauantrag
 → Umbau läuft → Eröffnung
```
Frage „wie geht Carla ein Café-Projekt durch?" → Antwort fällt aus dem Graphen,
nicht aus einer Annahme. **Ob/wann** Phasen kippen, entscheidet das LLM.

---

## 4. Der agentic Simulations-Loop (Plan → Simulate → Consolidate)

Jeder simulierte Tag durchläuft vier Phasen. Jede generative Phase ist ein
**Gather-Tool (Kontext) → Host-LLM verfasst → Write-Tool (persistiert)**.

```
PHASE A — ORIENT & PLAN  (vor der Simulation)
  brief_day(persona, date)            → MCP gathert: aktive Projekte, fällige/
                                         überfällige open_loops, letzte Digests,
                                         relevante Erinnerungen (recall), Saison/
                                         Wochentag. KEIN fertiger Plan.
  → Host-LLM verfasst day_plan.md      Analyse "was ist heute spannend / dran?":
                                         welche Threads heute plausibel bewegt
                                         werden, welche Spannungen offen sind.
  put_day_plan(persona, date, plan)    persistiert Plan (Sidecar, versioniert).

PHASE B — SIMULATE  (heute schon vorhanden, plan-aware gemacht)
  simulate_day(persona, date)          nutzt day_plan als Steuerung; Host-LLM
                                         authored Blöcke + Aktivitäten (wie jetzt),
                                         jede Aktivität referenziert Entitäten.

PHASE C — CONSOLIDATE  (neu — der eigentliche Memory-Aufbau)
  brief_consolidation(persona, date)   → MCP gathert: die Aktivitäten des Tages +
                                         aktuelle Zustände der berührten Entitäten.
  → Host-LLM verfasst memory_deltas:    welche Entitäten kamen vor; pro Entität
                                         neue Fakten / Statuswechsel / ENTSCHIEDENE
                                         Ausgänge (gewonnen/verloren/verzögert/
                                         abgeschlossen); welche open_loops sich
                                         öffneten/schlossen; Wichtigkeit.
  record_memory_deltas(persona, date)  schreibt bi-temporale Fakten; alter Status
                                         bekommt t_invalid (nicht gelöscht).

PHASE D — ROLLUP  (periodisch, ersetzt hardcodierte reflection)
  brief_digest(persona, scope, period) → MCP gathert Tage/Wochen des Zeitraums.
  → Host-LLM verfasst Digest            Woche/Monat/Jahr-Zusammenfassung + Bögen.
  put_digest(persona, scope, period)    Konsolidierung → hält ein Jahr tragbar.
```

**Mode-Disziplin** (bim-agent): A/B/C/D sind getrennt; Fehler in C führt zurück
zu „analysieren", nicht zu blindem Schreiben.

**Mehrtägige Läufe:** `continue_simulation` iteriert A→D; offene Loops & aktive
Projekte aus Phase C tragen über `brief_day` in den nächsten Tag.

---

## 4A. Multi-Resolution & Sampled Timeline (Trends ohne jeden Tag)

Ziel (Johannes 2026-06-02): **Trends über Wochen/Monate/Jahre abbilden, ohne
jeden einzelnen Tag zu simulieren** — „stichprobenartig simulieren, aber dennoch
Trends erkennen". Lösung: die Zeit in **mehreren Auflösungen** modellieren. Grobe
Ebenen tragen den Bogen; nur wenige repräsentative Tage werden *konkret*
simuliert und verankern den Bogen mit gelebten Belegen.

```
JAHR/QUARTAL   period_plan (grob)   LLM-Bogen: welche Projekte starten/laufen/
                                    enden, Auslastungs-/Stimmungs-Trend, Saison,
                                    Markt. KEINE Tagesdetails.
   └─ MONAT    period_plan          verfeinert den Quartalsbogen; nennt Meilen-
                                    steine + welche Tage sich zu simulieren lohnen.
        └─ WOCHE  period_plan       optional; nur wenn der Monat dicht ist.
             └─ TAG  sampled days   N repräsentative Tage (z.B. Aufmaß-Tag,
                                    zäher Tag, Meilenstein-Tag) — voller Loop A→D.
```

**Sampling statt Vollabdeckung.** Statt 30 Tage simuliert man z.B. 3–5
charakteristische Tage pro Monat. Der `period_plan` legt fest, *welche* Tage
interessant sind (`brief_period` schlägt Kandidaten vor: Meilensteine, Konflikte,
typische Routine). Dazwischen liefert der grobe Plan die Progression „sinngemäß".

**Wie der Trend in den Graphen kommt (rein LLM, nichts hardcodiert):**
- Der `period_plan` wird vom Host-LLM verfasst und als **Entitäts-Fakten mit
  Intervall-Gültigkeit** konsolidiert: „Café Lindgrün: Status *Bau*, gültig
  2026-09-01…2026-12-15" — ein Fakt deckt einen Zeitraum ab, auch ohne dass jeder
  Tag simuliert wurde. Genau dafür sind die `t_valid/t_invalid`-Intervalle da.
- Die wenigen `sampled days` erzeugen konkrete Episoden, die in diese Intervalle
  fallen und sie belegen/verfeinern (oder dem Plan widersprechen → der nächste
  `period_plan` korrigiert).
- **Trend-Fakten** (z.B. „Auslastung Q3 sinkend", „Akquise zäh") sind eigene
  Entitäts-Fakten/Digests mit Zeitraum → später per `recall_memory`/`get_timeline`
  als Trend abfragbar.

**Konsistenz Grob↔Fein.** Vor jedem `sampled day` injiziert `brief_day` den
gültigen `period_plan` → der Tag bleibt im Bogen. Nach einer Stichprobe rollt ein
`brief_digest` Sample-Tage + Plan zu einem Perioden-Digest zusammen; weicht die
Realität der Samples vom Plan ab, schreibt der nächste `period_plan` den Bogen
fort (emergent, nicht erzwungen).

So entsteht ein durchgehender Jahresbogen aus *wenigen* konkreten Tagen + groben,
LLM-verfassten Perioden — abfragbar als „wie lief Projekt X über Q3" oder „wie
entwickelte sich Sabines Auslastung übers Jahr".

---

## 5. MCP-Tool-Oberfläche (nach Kategorien)

Namenskonvention wie bim-database: `list_*` Überblick · `get_*` Detail ·
`*_status`/`*_summary` kompakt · `recall_*`/`*_next` Routing · `brief_*` Gather
für eine Author-Phase · `record_*`/`put_*` Write-Back · `verify_*` Post-Write.
Alle liefern den Envelope `{ ok, data, next_recommended_tool?, _meta }`.

### 5.1 Persona / Identität  (existiert, bleibt)
`create_persona`, `bulk_create_personas`, `update_persona`, `get_persona`,
`list_personas`, `get_persona_soul`, `prepare_persona_agent_context`,
`generate_avatar`.

### 5.2 Memory-Retrieval  ← NEU (das „in die Historie schauen")
- `recall_memory(persona, query, as_of?, k?)` — **hybrides, scored** Retrieval
  über Episoden + Fakten + Digests: **Keyword/Entitäts-Overlap + semantische
  Suche (Embeddings)**, kombiniert mit Recency-Decay × Wichtigkeit. Das Tool für
  „gibt es etwas Passendes in der Vergangenheit?". Liefert kompakte Treffer.
  Embeddings: OpenAI (Key liegt bereits in `.env`, heute für Avatare). Wichtig:
  Das verstößt **nicht** gegen „Server generiert keinen Text" — Embeddings sind
  Retrieval, keine Text-Erzeugung; das Verfassen bleibt beim Host-LLM.
- `list_active_projects(persona)` — kompakt: Projekt · Status · last_touched ·
  #open_loops.
- `get_project(persona, project_id, as_of?)` — volle Fakten-/Status-Timeline
  eines Projekts (time-travel via `as_of`).
- `get_timeline(persona, start, end, entity?)` — Events/Fakten in einem Fenster.
- `get_state_at(persona, as_of)` — Snapshot: welche Projekte/Fakten waren am
  Datum X gültig (time-travel).
- `search_entities(persona, kind?, name?)` — Personen/Gebäude/Ämter/Projekte
  finden.
- `get_open_loops(persona, status?)` — offene Fäden (jetzt mit Identität).

### 5.3 Planung  ← NEU (Plan vor Aktion, mehrere Auflösungen)
- `brief_day(persona, date)` — Gather für die Tagesplanung (Phase A); injiziert
  den gültigen Perioden-Plan.
- `put_day_plan(persona, date, plan_md)` / `get_day_plan(persona, date)`.
- `brief_period(persona, scope, period)` — Gather für Jahr/Quartal/Monat/Woche:
  liefert bisherige Bögen, aktive Projekte, letzte Digests; schlägt **Sample-Tage**
  vor (siehe §4A).
- `put_period_plan(persona, scope, period, plan_md)` /
  `get_period_plan(persona, scope, period)` / `list_period_plans(persona)`.

### 5.4 Simulation  (existiert, erweitert)
- `simulate_day` (plan-aware), `simulate_range`, `continue_simulation`,
  `clear_simulations`, `purge_runtime_data`.
- `brief_consolidation(persona, date)` ← NEU · `record_memory_deltas(...)` ← NEU.

### 5.5 Konsolidierung / Digests  ← NEU
- `brief_digest(persona, scope, period)` · `put_digest(...)` ·
  `list_digests(persona)`.

### 5.6 Inspektion / Zustand  (existiert)
`get_current_state`, `get_calendar`, `get_calendar_period`, `get_activity`,
`summarize_persona_period`, `extract_pain_points`.
- `get_persona_memory(persona)` ← NEU: rendert/liefert MEMORY.md.

### 5.7 Council / Antworten  (existiert)
`select_council`, `run_council`, `ask_persona`, `compare_personas`.
→ Profitiert automatisch: `ask_persona` kann jetzt `recall_memory` nutzen, statt
nur „letzte Events" zu sehen.

### 5.8 Evidence / Export  (existiert)
`attach_evidence`, `export_persona`, `export_logs`, `export_council_session`.

### 5.9 MCP Resources / Prompts  ← NEU (wie bim-database)
- Resource `persona-council://schema/memory` — Schema der Memory-Objekte.
- Prompt `simulate-persona-day(persona, date)` — Adapter-Playbook, das den Loop
  A→D als Anleitung an den Harness gibt.

---

## 6. Context-Engineering (gegen Über-Narration & Token-Bloat)

1. **Selektives Retrieval:** In `brief_day`/Aktivitäts-Frames wird **nur** das
   für heute Relevante injiziert (Entitäts-Überlappung + recall-Score), nicht die
   ganze Historie.
2. **Kompaktheits-Hierarchie:** Default kompakt (`*_status`/`*_summary`); volle
   Objekte (`get_project`/`*_state`) nur, wenn der Agent gezielt nachfragt.
3. **MEMORY.md als Projektion:** ein knapper, gerenderter Stand statt roher
   Event-Dump.
4. **Anti-Narrations-Norm (Prompt):** „Erinnerung ist Hintergrund. Beziehe dich
   nur darauf, wenn dieser Moment es echt verlangt." (passt zur bestehenden
   Anti-Steering-Haltung in SOUL.)
5. **Handoff-Summaries:** jeder Tag/Phase gibt eine kompakte Übergabe zurück;
   der nächste Tag startet mit sauberem Kontext.

---

## 7. Datenmodell (SQLite, additiv — bestehende Tabellen bleiben)

```sql
-- Schicht 2: Entitäten
CREATE TABLE entities (
  id TEXT PRIMARY KEY, persona_id TEXT NOT NULL,
  kind TEXT NOT NULL,             -- project|person|org|building|authority|tool_topic
  name TEXT NOT NULL,
  status TEXT,                    -- frei, LLM-vergeben (z.B. akquise|beauftragt|bau|abgeschlossen|verloren)
  first_seen TEXT, last_seen TEXT, created_at TEXT, updated_at TEXT
);

-- Schicht 2: bi-temporale Fakten (time-travel)
CREATE TABLE entity_facts (
  id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, entity_id TEXT NOT NULL,
  fact TEXT NOT NULL,
  t_valid TEXT NOT NULL,          -- ab wann galt es (Simulationszeit)
  t_invalid TEXT,                 -- NULL = noch gültig; sonst abgelöst (nicht gelöscht)
  importance INTEGER,             -- LLM-vergeben (Retrieval-Gewicht)
  source_event_id TEXT,           -- Beleg-Episode
  created_at TEXT
);

-- Verknüpfung Episode ↔ Entität
CREATE TABLE event_entities (
  event_id TEXT NOT NULL, entity_id TEXT NOT NULL, role TEXT,
  PRIMARY KEY (event_id, entity_id)
);

-- open_loops mit Identität (statt anonyme Strings)
CREATE TABLE threads (
  id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, entity_id TEXT,
  text TEXT NOT NULL, status TEXT,         -- open|resolved|abandoned
  opened_on TEXT, closed_on TEXT, created_at TEXT
);

-- Planung (alle Auflösungen: day|week|month|quarter|year)
CREATE TABLE plans (
  id TEXT PRIMARY KEY, persona_id TEXT NOT NULL,
  scope TEXT NOT NULL,            -- day|week|month|quarter|year
  period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  briefing TEXT, plan_md TEXT,
  sample_days TEXT,               -- JSON: vorgeschlagene/simulierte Sample-Tage
  created_at TEXT, UNIQUE(persona_id, scope, period_start)
);

-- Schicht 3: Digests (rückblickend; Plan = vorausschauend)
CREATE TABLE memory_digests (
  id TEXT PRIMARY KEY, persona_id TEXT NOT NULL,
  scope TEXT NOT NULL,            -- week|month|quarter|year
  period_start TEXT, period_end TEXT, text TEXT, created_at TEXT
);

-- Embeddings für semantische Suche (hybrid mit Keyword/Entität)
CREATE TABLE embeddings (
  obj_type TEXT NOT NULL,         -- event|fact|digest|plan
  obj_id TEXT NOT NULL,
  persona_id TEXT NOT NULL,
  model TEXT NOT NULL,            -- z.B. text-embedding-3-small
  vector BLOB NOT NULL,           -- float32-Array
  created_at TEXT,
  PRIMARY KEY (obj_type, obj_id)
);
```

Episodische `experience_events` bleiben unverändert die Roh-Schicht; sie bekommen
über `event_entities` nur Verknüpfungen.

**Retrieval-Scoring (hybrid, Generative-Agents-Muster):**
`score = w1·semantische_Ähnlichkeit + w2·Keyword/Entitäts-Overlap +
w3·Recency-Decay + w4·Importance`. Semantik via OpenAI-Embeddings
(`text-embedding-3-small`, Key aus `.env`); Kosinus-Ähnlichkeit in Python
(bei dieser Datenmenge Brute-Force ausreichend, keine Vektor-DB nötig).
`as_of`-Filter respektiert `t_valid/t_invalid` für time-travel.

---

## 8. „Nichts hardcodieren" — konkrete Garantien

- **Projekt-Dauer/-Ausgang:** Kein `projekt = 3 Monate`. In Phase C bekommt das
  LLM die *verstrichene Zeit* als Kontext („diese Sanierung läuft seit 14
  Monaten, denkmalnah") und beurteilt Plausibilität selbst: gewonnen, verloren,
  verzögert, Baustopp, abgenommen. Der Store schreibt nur mit.
- **Reflection → LLM-Digest:** Die heutige hardcodierte `reflection` (Template +
  feste Themen in `services.py`) wird durch `brief_digest`/`put_digest` ersetzt.
- **Council-/Tagesinhalt** bleibt LLM-authored (wie bisher).
- **Status-Vokabular ist frei:** `entity.status`/`threads.status` werden vom LLM
  vergeben, nicht aus einer festen Enum erzwungen (nur leichte Normalisierung).

---

## 9. Migration & Daten-Reset

Reset ist ausdrücklich erlaubt. Empfohlener Neuaufbau:
1. `purge_runtime_data` (Personas + Memory weg) **oder** `clear_simulations`
   (nur Sim/Memory weg, Personas bleiben).
2. Personas aus [`persona-source-prompts.md`](persona-source-prompts.md) neu
   erzeugen (Host-Authoring-Pfad / `persona-bulk`).
3. Tage simulieren — jetzt mit Loop A→D, sodass Memory mitwächst.
Die Grundprompts sind die einzige nicht-regenerierbare Quelle und liegen sicher
in `spec/`.

---

## 10. Roadmap (dünn anfangen, messbar)

> **STATUS 2026-06-02: P0–P10 IMPLEMENTIERT.** Code: `storage.py` (Tabellen +
> Schema-Version), `memory.py` (Embeddings/Recall/Resolution/Projektion/Time-
> Travel), `llm_simulation.py` (Builder + Validatoren), `services.py`
> (brief_*/record_*/put_* Orchestrierung, effective_persona, forgetting),
> `evaluation.py` (Qualitäts-Harness), `mcp_server.py` (58 Tools + Envelope +
> next_recommended_tool + Resource + Prompt), `cli.py` (Memory-Kommandos).
> Verifiziert end-to-end: semantische Recall (OpenAI live), bi-temporales
> Time-Travel, Multi-Resolution-Bogen über Monate.
>
> **Abnahme-Lauf (Deep Vertical, 2026-06-02):** Carla, Bernd, Andreas über
> Juni–August 2026, je 3 Sample-Tage/Monat durch die volle Schleife
> (brief_period → sample_days → brief_day/simulate → consolidate → digest).
> Ergebnis: **`evaluate_simulation` 7/7 grün, 0 warn, 0 rot je Persona.**
> Projekt-Lebenszyklen emergent & LLM-entschieden (z. B. Areal Lindenhof:
> bedingtes Go → Kaufverhandlung → angekauft; Gewerbehof Sülz → verloren;
> Anbau Krämer → abgeschlossen & übergeben), per Time-Travel pro Monatsende
> korrekt abrufbar — mit nur 9 simulierten Tagen je Persona statt 90. Damit ist
> die „Definition top" (§10) für das Vertical erfüllt.

**Empfohlene Ausführungsreihenfolge (Eval-Harness früh):**
`P0 → P1 → P2 → P7 → P3 → P4 → P4A → P5 → P6 → P8 → P9 → P10`.
Begründung: Sobald P1 (Entitäten) + P2 (Recall) stehen, wird **P7 (Eval-Harness)
vorgezogen**, damit jede weitere Säule gegen eine messbare Latte gebaut wird statt
blind. P6 (Konsistenz) folgt direkt nach den ersten Mehrtages-/Sampling-Läufen,
sobald genug Daten Widersprüche/Dubletten provozieren.

- [x] **P0 — Fundament:** Tabellen aus §7 + Envelope-Helper + `_meta`.
- [x] **P1 — Entitäts-Extraktion (Phase C):** `brief_consolidation` +
      `record_memory_deltas`; rückwirkend auf die vorhandenen Tage anwenden.
      *Akzeptanz:* `list_active_projects(carla-sommer)` zeigt „Café Lindgrün" mit
      Fakten-Timeline.
- [x] **P2 — Retrieval + MEMORY.md:** `recall_memory` (hybrid: Keyword/Entität +
      **OpenAI-Embeddings**), `embeddings`-Tabelle + Backfill, `get_project`,
      `get_state_at`, `get_persona_memory`. *Akzeptanz:* semantische Anfrage
      („alles rund um Brandschutz") findet relevante Episoden; time-travel-Query
      „Stand am Datum X" funktioniert.
- [x] **P3 — Plan vor Aktion (Tag):** `brief_day` + `put_day_plan`; `simulate_day`
      plan-aware. *Akzeptanz:* day_plan.md analysiert sichtbar „was ist heute
      dran" aus dem Gedächtnis.
- [x] **P4 — Konsolidierung:** `brief_digest`/`put_digest`; hardcodierte
      reflection entfernen.
- [x] **P4A — Multi-Resolution & Sampling (§4A):** `brief_period`/
      `put_period_plan` für Woche/Monat/Quartal/Jahr; stichprobenartige
      Tagessimulation; Intervall-Fakten + Trend-Digests. *Akzeptanz:* „wie lief
      Projekt X über Q3" und „Sabines Auslastung übers Jahr" beantwortbar, ohne
      jeden Tag simuliert zu haben.
- [x] **P5 — Harness-Politur:** MCP Resource/Prompt, `next_recommended_tool`
      überall, Skill-Adapter, `spec/mcp-tool-contract.md` +
      `spec/simulation-loop-contract.md`.

### Langzeit-Qualitäts-Phasen (§12 — nötig für „top über lange Zeit")
- [x] **P6 — Konsistenz:** Entity Resolution + Widerspruchs-/Anomalie-Erkennung
      (§12.1). *Akzeptanz:* kein Projekt existiert doppelt; widersprüchliche
      Stände werden geflaggt/invalidiert.
- [x] **P7 — Evaluations-Harness:** `evaluate_simulation` mit Uniformitäts-,
      Über-Narrations-, Kontinuitäts-, Anti-Steering-, Konsistenz-Checks (§12.5,
      §12.7). *Akzeptanz:* Report über einen Jahreslauf, betroffene Tage
      regenerierbar.
- [x] **P8 — Welt-Schicht:** `world_context` + relevante Injektion (§12.3).
- [x] **P9 — Persona-Evolution & Beziehungen:** `persona_revisions` (belegter,
      träger Wandel) + Beziehungs-Entitäten (§12.2, §12.4).
- [x] **P10 — Skalierung:** Vergessen/Salienz/Pruning + Seeds + Schema-Versionen
      (§12.6, §12.8).

### Definition „top" (Done-Kriterium für Langzeit)
Ein simulierter **Jahreslauf** gilt als top, wenn `evaluate_simulation` grün ist:
keine Uniformität/Wiederholungsmuster, keine Über-Narration, Projekte bewegen
sich realistisch und schließen teils ab, open_loops werden teils gelöst, keine
Widersprüche/Dubletten, kein unbelegter Anti-Steering-Drift — und „wie lief
Projekt X / Trend Y über Zeit" ist kohärent beantwortbar.

---

## 11. Entscheidungen (Johannes, 2026-06-02 — entschieden)

1. **Retrieval-Tiefe:** ✅ **Hybrid** — Keyword/Entität **+ semantische Suche via
   OpenAI-Embeddings** (Key liegt in `.env`). Siehe §5.2 / §7.
2. **Geteilte Welt:** ✅ **Nein** — Personas kennen einander nicht; jedes
   Gedächtnis ist abgeschlossen, keine personenübergreifenden Entitäten.
3. **Zeitbasis:** ✅ **Gültigkeitszeit als Intervall** (`t_valid/t_invalid` in
   Simulationszeit) + simpler `created_at`-Stempel. Kein volles akademisches
   Bi-Temporal. Intervalle tragen auch das Sampling (§4A).
4. **Plan-Granularität:** ✅ **Mehrere Auflösungen** — Tages-Plan **plus**
   Wochen-/Monats-/Quartals-Pläne, mit **stichprobenartiger** Tagessimulation und
   Trend-Abbildung über Intervalle/Digests. Siehe §4A.

### Noch offen
- Gewichte `w1..w4` im Retrieval-Score (empirisch tunen).
- Default-Sample-Dichte pro Monat (Vorschlag: 3–5 Tage; vom `period_plan`
  fallweise bestimmt, nicht fix).

---

## 12. Langzeit-Qualität — Säulen für „top über lange Zeit"

Die §§1–11 sind die Wirbelsäule. Damit Läufe über Monate/Jahre **kohärent,
lebendig und nachweislich gut** bleiben, kommen folgende Säulen hinzu. Ohne sie
ist die Architektur tragfähig, aber nicht „top".

### 12.1 Entitäts-Auflösung & Konsistenz (Pflicht für Kohärenz)
Über lange Zeit driften Bezeichnungen und Stände auseinander.
- **Entity Resolution beim Schreiben:** `record_memory_deltas` matcht neue
  Erwähnungen gegen bestehende Entitäten (Name-Normalisierung + Embedding-
  Ähnlichkeit + Kontext) und **merged statt dupliziert** („Café Lindgrün" =
  „das Café in der Bergstraße"). Tool: `resolve_entity(persona, mention)` →
  bestehende id oder neu.
- **Widerspruchserkennung:** beim Setzen eines Fakts prüft das System gegen
  aktuell gültige Fakten derselben Entität; Konflikt → alter Fakt wird
  invalidiert (t_invalid) **oder** als `anomaly` markiert (nicht-blockierend,
  sichtbar — bim-database-Muster). Tool: `list_memory_anomalies(persona)`.
- **Status-Übergangs-Plausibilität (weich):** das LLM bekommt bei
  Status­wechseln den bisherigen Verlauf und begründet Sprünge; harte Enums
  bleiben verboten, aber „verloren → im Bau" ohne Begründung wird als Anomalie
  geflaggt.

### 12.2 Persona-Evolution / Charakterbögen
SOUL ist heute statisch (nur aus `source_description`). Für Langzeit-Realismus
darf sich die Identität **langsam, LLM-getrieben** wandeln.
- Neue Schicht **`persona_revisions`**: periodisch (z.B. via `brief_period`)
  schlägt das LLM behutsame Änderungen an Traits/Goals/Pains/Tools vor, **belegt
  durch konsolidierte Fakten** (nicht aus dem Nichts). Versioniert, mit
  Provenienz; der **Quell-Grundprompt bleibt unverändert** (Trennung
  „Kern-Identität" vs. „gewachsene Identität").
- `render_soul` zeigt aktuelle + Quell-Identität; Diff sichtbar.
- Guard: Wandel ist die Ausnahme, nicht der Default — Trägheit ist realistisch
  (Bernd ändert sich kaum; Tobias schneller).

### 12.3 Welt-/Kontext-Schicht (exogen, kein geteiltes Personen-Wissen)
Ein „Backdrop", der allen Personas denselben äußeren Rahmen gibt, ohne dass sie
einander kennen.
- **`world_context`** (datierte, LLM-/kuratiert gepflegte Fakten): Saison/Wetter,
  Feiertage/Ferien, Recht & Förderung (GEG-Novellen, KfW-Programme), Bau-/
  Immobilienmarkt, Zins. `brief_day`/`brief_period` injizieren den **für die
  Persona relevanten** Ausschnitt (Frank ↔ Förderung, Bernd ↔ Wetter, Andreas ↔
  Zins/Markt).
- Persönliche exogene Ereignisse (Urlaub, Krankheit, Auftragsflaute) entstehen im
  Plan/Consolidate — LLM-simuliert, nicht verregelt.
- Anti-Steering bleibt: Welt-Fakten sind neutral, kein Produkt-Push.

### 12.4 Beziehungs-Evolution
`relationships` aus dem Profil werden auf **Personen-Entitäten** abgebildet und
entwickeln sich: aus „Bauherr Familie Vogt" wird Stammkunde; die freie
Bauzeichnerin fällt mal aus; ein Bauamt-Sachbearbeiter wird zum wiederkehrenden
Reibungspunkt. Beziehungs-Fakten laufen über denselben bi-temporalen Mechanismus.

> **Aufteilung deterministisch vs. LLM (gelernt 2026-06-02):** Die deterministische
> Harness deckt **nur strukturelle Integrität** ab (Uniformität, Wiederholung,
> Block-Muster, Kontinuität, Projekt-Bewegung, Konsistenz). **Anti-Steering /
> Glaubwürdigkeit ist semantisch** und lässt sich NICHT gleichzeitig generisch
> (branchenunabhängig, ohne hartcodierte Markerliste) UND zuverlässig per Keyword/
> Lexik prüfen — lexikalische Versuche fluten mit normalem Arbeitsvokabular. Daher
> ist Anti-Steering Aufgabe des **LLM-Kritikers** (Feature #2), nicht der
> deterministischen Checks. Keine hartcodierten, branchenspezifischen Wortlisten.

### 12.5 Simulationsqualität & Evaluation — woran wir „top" messen
Ohne Messung kein „top". Eine **Kritiker-Schicht** (LLM-Subagenten + billige
Heuristiken), die nach Läufen prüft und Befunde zurückschreibt:
- **Uniformitäts-Detektor:** gleiche Start-/Endzeiten, gleiche Blockmuster,
  wiederholte Formulierungen über Personas/Tage (genau die bisherigen
  Beschwerden — jetzt automatisch erkannt).
- **Über-Narrations-Check:** erzählt die Persona ständig aus Erinnerungen statt zu
  arbeiten?
- **Kontinuitäts-Check:** werden open_loops je geschlossen? bewegen sich Projekte,
  oder hängen sie ewig? schließt überhaupt mal eins ab?
- **Anti-Steering-Audit:** driftet jemand ohne Beleg Richtung BIM/KI/Tool-Adoption?
  (siehe 12.7)
- **Konsistenz-Audit:** Widersprüche/Dubletten (aus 12.1).
- **Plausibilitäts-/Diversitäts-Score** pro Persona-Zeitraum.
Tools: `evaluate_simulation(persona?, period?)` → strukturierter Report +
Anomalien; speist die nächste Generierung (Regenerieren betroffener Tage).
*Akzeptanz von „top" = diese Checks grün über einen simulierten Jahreslauf.*

### 12.6 Vergessen & Salienz (Skalierung)
Damit ein Jahr tragbar bleibt: Episoden altern in den Digests auf; alte,
unwichtige Rohdetails werden **archiviert/gepruned** (nicht im aktiven Retrieval),
während konsolidierte Fakten/Bögen erhalten bleiben. Wichtigkeit + Recency-Decay
steuern, was „erinnert" bleibt („smarter durch Konsolidieren, nicht durch mehr
Speichern").

### 12.7 Anti-Steering auf Trend-Ebene
Die bestehende Anti-Steering-Regel muss in **Perioden-Plänen und Konsolidierung**
reassertiert werden: über Monate darf nicht *schleichend* die ganze Kohorte zu
Tool-/Methoden-Fans werden. Skeptiker bleiben skeptisch, außer Fakten zwingen
plausibel zum Wandel (dann via 12.2, mit Beleg).

### 12.8 Determinismus, Seeds & Schema-Versionierung
- Seed-Strategie über alle Auflösungen (Jahr→Tag) für reproduzierbare Läufe;
  Embeddings/Sampling deterministisch gemacht, wo möglich.
- `schema_version` auf Memory-Objekten + Migrationspfad (bim-Muster), damit lange
  laufende Datenbestände nicht brechen.

---

## Quellen (Recherche)
- Zep — Temporal KG for Agent Memory: https://arxiv.org/abs/2501.13956
- Graphiti / Neo4j (bi-temporal): https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/
- Memory for Autonomous LLM Agents (Survey 2026): https://arxiv.org/html/2603.07670v1
- AI Agent Memory Types (CoALA): https://atlan.com/know/types-of-ai-agent-memory/
- Interne Muster: `~/repos/bim-agent` (Context-Gatherer+Author, Scene-Plan,
  Driver-Loop) und `~/repos/bim-database` (Tool-Kategorien, Kompaktheits-
  Hierarchie, Envelope + `next_recommended_tool`).
```
