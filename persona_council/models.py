from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


Json = dict[str, Any]


@dataclass
class Persona:
    id: str
    slug: str
    display_name: str
    source_description: str
    provenance: Json
    identity_traits: Json
    segment: Json
    demographics: Json
    role: Json
    company_context: Json
    goals: list[str]
    constraints: list[str]
    tool_ids: list[str]
    tools: list[str]
    relationships: list[Json]
    personality: Json
    pain_points: list[str]
    success_criteria: list[str]
    avatar: Json | None
    soul: Json | None
    created_at: str
    updated_at: str

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class CalendarEvent:
    id: str
    persona_id: str
    start: str
    end: str
    title: str
    participants: list[str]
    location_or_tool: str
    intent: str
    outcome: str
    created_at: str

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class ExperienceEvent:
    id: str
    persona_id: str
    timestamp: str
    event_type: str
    summary: str
    task: str
    tool: str
    participants: list[str]
    collaboration_mode: str
    what_happened: str
    conversation: list[Json]
    key_quotes: list[str]
    actions_done: list[str]
    artifacts_touched: list[str]
    persona_thought: str
    decision: str | None
    open_loops: list[str]
    impact: Json
    pain_points: list[str]
    goal_refs: list[str]
    calendar_event_id: str | None
    created_at: str

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class DailySummary:
    id: str
    persona_id: str
    date: str
    mood: str
    completed: list[str]
    blockers: list[str]
    open_loops: list[str]
    pain_points: list[str]
    notable_memories: list[str]
    created_at: str

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class Reflection:
    id: str
    persona_id: str
    period_start: str
    period_end: str
    summary: str
    themes: list[str]
    pain_points: list[str]
    created_at: str

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class PainPointObservation:
    id: str
    persona_id: str
    issue: str
    severity: int
    frequency: int
    evidence_event_ids: list[str]
    affected_workflow: str
    opportunity: str
    created_at: str

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class CouncilSession:
    id: str
    prompt: str
    persona_ids: list[str]
    selection_reason: str
    turns: list[Json]
    proposal: str
    votes: list[Json]
    summary: str
    created_at: str
    exec_summary: str = ""  # rich markdown synthesis shown in the UI

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class Synthesis:
    """A study arc: an ordered chain of councils consolidated into cross-council
    learnings (the report is the exported document)."""
    id: str
    title: str
    start_input: str
    council_ids: list[str]
    arc_narrative: str
    gesamtbild: str
    handlungsempfehlungen: list  # [{text, aufwand, nutzen}] — plain strings tolerated (legacy)
    positionierung: str
    pain_solvers: list[str]
    segmente: list[Json]
    offene_fragen: list[str]
    references: list[Json]
    created_at: str
    goal: str = ""                       # what this study arc is trying to learn
    status: str = "done"                 # in_progress | done
    next_council_question: str = ""      # self-contained Q for the next council (if continuing)
    stop_reason: str = ""                # why the loop stopped (goal reached / no follow-up / max)
    iterations: int = 0                  # councils consumed so far
    voices: list[Json] = field(default_factory=list)  # structured per-persona voice records
    citations: list[Json] = field(default_factory=list)  # inline provenance: [{kind, ref, quote}]
    # each voice: {persona_id, persona_name, segment, sentiment, relevance,
    #              key_argument, shift:{from,to,trigger,council_id}|None, evidence:[{council_id,quote}]}

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class Evidence:
    id: str
    persona_id: str
    source_type: str
    content_or_path: str
    notes: str | None
    created_at: str

    def to_dict(self) -> Json:
        return asdict(self)


@dataclass
class SimulationResult:
    persona: Json
    date: str
    calendar_events: list[Json] = field(default_factory=list)
    experience_events: list[Json] = field(default_factory=list)
    daily_summary: Json | None = None
    reflection: Json | None = None

    def to_dict(self) -> Json:
        return asdict(self)
