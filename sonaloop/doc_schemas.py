"""Documentation data-schema examples (rendered by the web docs hub's Concepts pages).

These are illustrative JSON strings shown to the reader so they can see the exact stored shape of each
artefact + the five content primitives. They live OUTSIDE the `sonaloop.web` package on purpose: the
web-scoped grep gates (spec/research-plan-engine.md R8) forbid hardcoded evidence-kind presentation
literals like `"kind": "council"` inside the UI code — these inert example strings are documentation, not
presentation logic, so they belong here as data. Field names mirror sonaloop/models.py +
spec/unified-artifact-schema.md.
"""
from __future__ import annotations

# The five content primitives as real JSON (spec/unified-artifact-schema.md §2).
PRIM_JSON = {
    "Ref": '{ "kind": "memory|council|synthesis|prototype_state|persona|external",\n'
           '  "id": "council_…",      // when it points at a stored record\n'
           '  "text": "…",            // when it is a free observed-state string\n'
           '  "quote": "…" }          // optional supporting quote',
    "Stance": '{ "value": -2, "label": "oppose" }\n'
              '// −2 oppose · −1 skeptical · 0 neutral · +1 conditional · +2 support',
    "Statement": '{ "persona_id": "persona_…",\n'
                 '  "text": "…markdown, in the persona\'s voice…",\n'
                 '  "stance": { "value": 1, "label": "conditional" },   // optional\n'
                 '  "about":  { "kind": "prompt", "id": "q0" },         // what it responds to\n'
                 '  "refs":   [ { "kind": "memory", "text": "missed a deadline in March" } ] }',
    "Prompt": '{ "text": "…markdown…", "kind": "question|proposal|goal|focus|hypothesis", "id": "q0" }',
    "Finding": '{ "text": "…markdown…",\n'
               '  "kind": "summary|key_problem|recommendation|open_question|risk|cluster|segment",\n'
               '  "score": { "effort": 2, "value": 5 },   // optional\n'
               '  "refs":  [ { "kind": "council", "id": "council_…" } ] }',
}

# Per-artefact example records (trimmed but real-shaped).
EXAMPLES = {
    "persona":
        '{\n  "id": "persona_7f3…", "slug": "lena-vogt",\n  "display_name": "Lena Vogt",\n'
        '  "role": { "title": "Head of Operations", "seniority": "lead" },\n'
        '  "company_context": { "industry": "logistics", "size": "120" },\n'
        '  "segment": { "name": "ops leaders at mid-size firms" },\n'
        '  "goals": ["ship the Q3 rollout"], "constraints": ["no new headcount"],\n'
        '  "pain_points": ["Monday triage eats the morning"],\n'
        '  "soul": { "rendered": "data/personas/lena-vogt/SOUL.md" },\n'
        '  "avatar": { "path": "data/personas/lena-vogt/avatar.png" },\n'
        '  "created_at": "2026-03-02T…", "updated_at": "2026-05-30T…"\n}',
    "project":
        '{\n  "id": "proj_a91…", "slug": "weekly-planning",\n'
        '  "title": "Weekly planning", "goal": "How might we make weekly planning effortless?",\n'
        '  "methodology": "double_diamond", "phase": "develop",\n'
        '  "persona_ids": ["persona_7f3…"],\n'
        '  "study_ids": ["syn_22b…"], "council_ids": ["council_4c1…"],\n'
        '  "notes": [ { "id": "note_8e…", "text": "Monday triage is the worst", "kind": "note" } ],\n'
        '  "sections": [ { "id": "sec_1…", "title": "Problem exploration" } ],\n'
        '  "themes": ["triage", "trust"], "study_tags": { "syn_22b…": ["triage"] },\n'
        '  "status": "active"\n}',
    "council":
        '{\n  "id": "council_4c1…", "project_id": "proj_a91…",\n'
        '  "persona_ids": ["persona_7f3…", "persona_b2…"],\n'
        '  "prompts": [ { "id": "q0", "kind": "question",\n'
        '                 "text": "What makes weekly planning painful?" } ],\n'
        '  "statements": [\n'
        '    { "persona_id": "persona_7f3…", "text": "Every Monday I rebuild the plan from scratch.",\n'
        '      "stance": { "value": -1, "label": "skeptical" },\n'
        '      "about": { "kind": "prompt", "id": "q0" },\n'
        '      "refs": [ { "kind": "memory", "text": "lost an afternoon to triage in March" } ] }\n'
        '  ],\n'
        '  "findings": [ { "kind": "summary", "text": "Triage, not tooling, is the core pain." } ],\n'
        '  "votes": []\n}',
    "synthesis":
        '{\n  "id": "syn_22b…", "title": "Weekly planning — the core problem",\n'
        '  "scope": "convergence", "goal": "Find the single sharpest pain",\n'
        '  "prompts": [ { "kind": "goal", "text": "What is the core problem to solve?" } ],\n'
        '  "findings": [\n'
        '    { "kind": "key_problem", "text": "Monday triage, not tooling.",\n'
        '      "refs": [ { "kind": "council", "id": "council_4c1…" } ] },\n'
        '    { "kind": "recommendation", "text": "Auto-carry unfinished tasks.",\n'
        '      "score": { "effort": 2, "value": 5 } }\n'
        '  ],\n'
        '  "statements": [ { "persona_id": "persona_7f3…", "text": "If it just carried over, I\'d trust it." } ],\n'
        '  "references": [ { "kind": "council", "id": "council_4c1…" } ],\n'
        '  "sections": [ { "id": "s1", "heading": "The problem", "markdown": "…", "figures": [] } ]\n}',
    "prototype":
        '// the prototype artefact\n{\n  "id": "proto_5d…", "slug": "weekly-planner-v2",\n'
        '  "name": "Weekly Planner", "version": "v2", "kind": "web",\n'
        '  "path": "prototypes/weekly-planner-v2/", "entry": "index.html",\n'
        '  "run": "static", "tags": ["midfi"]\n}\n\n'
        '// a proband session = a persona actually using it\n{\n'
        '  "persona_id": "persona_7f3…", "prototype_id": "proto_5d…",\n'
        '  "statements": [\n'
        '    { "persona_id": "persona_7f3…", "text": "I clicked Add task and got a blank screen.",\n'
        '      "stance": { "value": 1, "label": "conditional" },\n'
        '      "refs": [ { "kind": "prototype_state", "text": "after Add task → empty state" } ] }\n'
        '  ]\n}',
    "note":
        '{\n  "id": "note_8e…", "title": "Personas dread Monday triage",\n'
        '  "text": "Idea: auto-carry unfinished tasks into the new week.",\n'
        '  "kind": "note",\n'
        '  "data": { "lens": "solution", "artifact_kind": "prototype", "prototype_ids": ["proto_5d…"] },\n'
        '  "created_at": "2026-04-11T…"\n}',
    "section":
        '{\n  "id": "sec_1…", "project_id": "proj_a91…",\n'
        '  "title": "Problem exploration", "kind": "theme",\n'
        '  "member_ids": ["council_4c1…", "note_8e…", "syn_22b…"],\n'
        '  "order": 1, "parent_id": null\n}',
}
