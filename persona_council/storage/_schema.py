from __future__ import annotations


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS personas (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_events (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  start TEXT NOT NULL,
  end TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experience_events (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  event_type TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_summaries (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  date TEXT NOT NULL,
  data TEXT NOT NULL,
  UNIQUE(persona_id, date)
);

CREATE TABLE IF NOT EXISTS reflections (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pain_points (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  issue TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS council_sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS syntheses (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL,
  data TEXT
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Memory layer 2: entities (project|person|org|building|authority|topic)
CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT,
  data TEXT NOT NULL,
  first_seen TEXT,
  last_seen TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_persona ON entities(persona_id, kind);

-- Memory layer 2: bi-temporal facts (valid-time intervals = time-travel)
CREATE TABLE IF NOT EXISTS entity_facts (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  fact TEXT NOT NULL,
  status TEXT,
  t_valid TEXT NOT NULL,
  t_invalid TEXT,
  importance INTEGER DEFAULT 3,
  source_event_id TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_entity ON entity_facts(entity_id);
CREATE INDEX IF NOT EXISTS idx_facts_persona ON entity_facts(persona_id);

-- Episode <-> entity links
CREATE TABLE IF NOT EXISTS event_entities (
  event_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  persona_id TEXT NOT NULL,
  role TEXT,
  PRIMARY KEY (event_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_event_entities_entity ON event_entities(entity_id);

-- Open loops with identity
CREATE TABLE IF NOT EXISTS threads (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  entity_id TEXT,
  text TEXT NOT NULL,
  status TEXT NOT NULL,
  opened_on TEXT,
  closed_on TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_threads_persona ON threads(persona_id, status);

-- Plans across resolutions: day|week|month|quarter|year
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(persona_id, scope, period_start)
);

-- Layer 3: consolidated digests
CREATE TABLE IF NOT EXISTS memory_digests (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(persona_id, scope, period_start)
);

-- Embeddings for hybrid semantic retrieval
CREATE TABLE IF NOT EXISTS embeddings (
  obj_type TEXT NOT NULL,
  obj_id TEXT NOT NULL,
  persona_id TEXT NOT NULL,
  model TEXT NOT NULL,
  dim INTEGER NOT NULL,
  vector BLOB NOT NULL,
  text TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (obj_type, obj_id)
);
CREATE INDEX IF NOT EXISTS idx_embeddings_persona ON embeddings(persona_id, obj_type);

-- Slow, evidence-backed persona identity drift
CREATE TABLE IF NOT EXISTS persona_revisions (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  effective_on TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_revisions_persona ON persona_revisions(persona_id, effective_on);

-- Exogenous world backdrop (not shared persona knowledge)
CREATE TABLE IF NOT EXISTS world_context (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  fact TEXT NOT NULL,
  t_valid TEXT NOT NULL,
  t_invalid TEXT,
  relevance_tags TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Consistency / quality anomalies (non-blocking, visible)
CREATE TABLE IF NOT EXISTS memory_anomalies (
  id TEXT PRIMARY KEY,
  persona_id TEXT,
  kind TEXT NOT NULL,
  severity INTEGER DEFAULT 2,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Evaluation reports (how we measure "top")
CREATE TABLE IF NOT EXISTS eval_reports (
  id TEXT PRIMARY KEY,
  persona_id TEXT,
  period_start TEXT,
  period_end TEXT,
  green INTEGER NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Research graph: a Project groups studies (syntheses) into a themed graph,
-- with typed edges between studies, promotable open questions, and meta-reports.
-- (Distinct from the memory "project" entity, which is a persona's own work project.)
CREATE TABLE IF NOT EXISTS research_projects (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS research_open_questions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  study_id TEXT,
  status TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_roq_project ON research_open_questions(project_id);

CREATE TABLE IF NOT EXISTS meta_reports (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_meta_reports_project ON meta_reports(project_id);

-- ESV: the resumable run object (driver journal). One run drives one project's plan to a
-- self-verified, finished result; `data` holds the step journal + critic rounds (resume = replay it).
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  status TEXT NOT NULL,
  cursor INTEGER NOT NULL DEFAULT 0,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);

-- Methodology engine (spec/methodology-engine-and-prototyping.md): user-defined
-- methodology specs + the LLM-judged gate decisions recorded per phase.
CREATE TABLE IF NOT EXISTS methodologies (
  key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS methodology_judgments (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  phase_key TEXT NOT NULL,
  kind TEXT NOT NULL,
  decided INTEGER NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mjudge_project ON methodology_judgments(project_id);

-- Research plan (spec/research-plan-engine.md): one plan per project — the orchestrator's
-- source of truth (analyze/act/verify task DAG + evidence refs), rendered to plan.md on demand.
CREATE TABLE IF NOT EXISTS research_plans (
  project_id TEXT PRIMARY KEY,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Prototype artifacts (real, minimal, locally-runnable apps) + recorded persona use.
CREATE TABLE IF NOT EXISTS prototypes (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  project_id TEXT,
  version TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prototypes_project ON prototypes(project_id);

CREATE TABLE IF NOT EXISTS prototype_sessions (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  prototype_id TEXT NOT NULL,
  session_id TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_protosess_proto ON prototype_sessions(prototype_id);
"""
