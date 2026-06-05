from __future__ import annotations

import contextvars

from ..config import ui_language, SUPPORTED_LANGUAGES


# ===================================================================== #
# i18n: the inspector chrome is bilingual (de/en). The active UI language #
# is resolved per request (?lang= -> cookie -> persisted setting) and    #
# held in a contextvar so the module-level render helpers can read it     #
# without threading it through every function. Generated CONTENT keeps    #
# its own content_language; this only switches the surrounding UI.        #
# ===================================================================== #

_UI_LANG: contextvars.ContextVar[str | None] = contextvars.ContextVar("ui_lang", default=None)

STRINGS: dict[str, dict[str, str]] = {
    "de": {
        "overview": "Übersicht", "personas": "Personas", "councils": "Councils",
        "syntheses": "Synthesen", "favorites": "Favoriten", "mark_with_star": "Mit Stern markieren",
        "theme_toggle": "Theme wechseln", "sidebar": "Sidebar", "repo": "Repo",
        "lang_toggle": "Sprache: Deutsch (zu English wechseln)", "lang_short": "EN",
        "back_to_overview": "Zur Übersicht",
        "overview_lead": "Synthetische Kundenpersonas, ihre simulierten Arbeitstage, Councils und Synthese-Reports.",
        "personas_lead": "{n} synthetische Kundenprofile.",
        "councils_lead": "Memory-geerdete Persona-Debatten.",
        "syntheses_lead": "Studien-Bögen über Council-Ketten — die Reports.",
        "projects": "Projekte",
        "projects_lead": "Forschungs-Graphen: Studien (Synthesen) als Knoten, getaggt und verkettet.",
        "graph": "Graph", "meta_report": "Meta-Report", "open_questions_h": "Offene Fragen", "prototypes_h": "Artefakte",
        "no_projects": "Noch keine Projekte. Lege eines an oder backfille deine Synthesen (CLI: research-backfill).",
        "source_studies": "Quell-Studien", "themes_h": "Themen", "build_order_h": "Aufbau-Reihenfolge",
        "filter": "Filter", "clear_filter": "zurücksetzen", "legend": "Legende",
        "no_councils": "Noch keine Councils.", "no_synthesis": "Noch keine Synthese.",
        "export_pdf": "Export PDF",
        # generic / not-found
        "not_found": "Nicht gefunden",
        "no_personas": "Noch keine Personas.",
        "runtime_maybe_cleared": "Runtime-Daten evtl. geleert.",
        "profile_not_found": "Profil nicht gefunden",
        "persona_runtime_cleared": "Die Runtime-Daten wurden evtl. geleert.",
        "council_not_found": "Council nicht gefunden",
        "synthesis_not_found": "Synthese nicht gefunden",
        "activity_not_found": "Aktivität nicht gefunden",
        # star
        "favorite": "Favorit", "mark_as_favorite": "Als Favorit markieren",
        # recommendations / effort-impact
        "effort_value": "Aufwand {a}/5 · Nutzen {n}/5",
        "ei_high_leverage": "hoher Hebel", "ei_worthwhile": "lohnend",
        "ei_neutral": "neutral", "ei_critical": "kritisch prüfen",
        "ei_quick_wins": "Quick Wins", "ei_big_bets": "Big Bets",
        "ei_fill_ins": "Lückenfüller", "ei_time_sinks": "Zeitfresser",
        "ei_effort_axis": "Aufwand →", "ei_value_axis": "Nutzen →",
        "no_data": "Keine Daten.",
        # project overview ("story")
        "ov_question": "Die Frage", "ov_path": "Der Weg", "ov_answer": "Die Antwort",
        "ov_full_solution": "Vollständige Lösung", "ov_view_proto": "Prototyp ansehen",
        "ov_concepts": "Konzepte", "ov_prototypes": "Prototypen", "ov_grounded": "Grounded Sessions",
        "ov_open": "Offene Fragen", "ov_no_answer": "Noch keine abschließende Antwort — Lauf nicht beendet.",
        # council framing
        "council_motion": "Zur Debatte gestellte These",
        "council_motion_help": "Jede Stimme reagiert auf diese These — Zustimmung, bedingt oder Ablehnung.",
        "council_finding": "Was dieser Council ergab",
        # vote labels
        "vote_support": "Befürwortend", "vote_maybe": "Bedingt",
        "vote_abstain": "Enthaltung", "vote_oppose": "Ablehnend",
        # stance buckets
        "stance_positive": "Positiv / begeistert", "stance_skeptical": "Skeptisch / ablehnend",
        "stance_neutral": "Neutral", "stance_conditional": "Bedingt / teils",
        "stance_other": "Sonstige",
        # sentiment section
        "sentiment_block": "Stimmungsbild",
        "sentiment_scope_chain": "die Council-Kette", "sentiment_scope_session": "diese Sitzung",
        "sentiment_intro": "Stimmen über {scope} — wer befürwortet, wer ist skeptisch.",
        "per_council": "Pro Council",
        "personas_by_sentiment": "Personas nach Stimmung — Begeisterungs-Score (Befürwortung − Ablehnung)",
        "stance_of_contributions": "Haltung der Wortbeiträge",
        "sentiment_label": "Sentiment", "relevance_label": "Relevanz",
        "name_label": "Name",
        "relevance_tooltip": "Relevanz / tangiert: {rel}",
        "voices_count": "Stimmen ({n})",
        "voices_intro": "Pro Persona: Sentiment, Relevanz (tangiert), Schlüssel-Argument und Wandel — "
                        "filtern, sortieren, aufklappen für Belege.",
        "search_arg_name": "Suche Argument / Name…",
        "sort_by_sentiment": "Sortieren: Sentiment", "sort_relevance": "Relevanz",
        "sort_shift_first": "Wandel zuerst",
        "segment": "Segment",
        "to_council": "→ Council",
        "shift_label": "Wandel {a} → {b}:",
        "voices_n_of_m": "{n} von {m} Stimmen",
        "voices_in_analyses": "Stimmen in Analysen",
        # synthesis report
        "answer_exec_summary": "Antwort · Executive Summary",
        "question": "Frage",
        "councils_overview": "Referenzierte Councils (Belege)",
        "evidence_decoupled_note": "Diese Synthese ist eigenständig. Councils sind zitierte Evidenz — kein Bestandteil der Synthese (entkoppelt).",
        "jump_into_council": "In den Council springen →",
        "recommendations": "Handlungsempfehlungen",
        "positioning": "Positionierung",
        "voices": "Stimmen",
        "sentiment_over_chain": "Stimmungsbild über die Council-Kette",
        "segments": "Segmente",
        "validated_pain_solvers": "Validierte Pain-Solver",
        "key_problems": "Kernprobleme", "affinity_clusters": "Affinity-Cluster",
        "ranking": "Ranking", "shortlist": "Shortlist",
        "open_questions": "Offene Fragen",
        "open_questions_next_study": "Offene Fragen / Nächste Studie",
        "course": "Verlauf", "arc_course": "Bogen / Verlauf",
        "sections": "Abschnitte",
        "exec_summary_marker": "Exec-Summary",
        "completed": "Abgeschlossen", "running": "läuft",
        "iterations": "Iterationen",
        "voices_meta": "Stimmen: {s}",
        # council detail
        "sentiment_this_council": "Stimmungsbild dieses Councils",
        "voices_in_detail": "Stimmen im Detail ({n})",
        "proposal_short_summary": "Proposal &amp; Kurz-Summary",
        "proposal": "Proposal", "summary": "Summary",
        "vote": "Abstimmung", "created": "Erzeugt", "done": "done",
        # persona detail
        "activity_over_time": "Aktivität über Zeit",
        "activities_per_day": "Simulierte Aktivitäten pro Tag ({n} gesamt).",
        "current_state": "Aktueller Zustand",
        "goals": "Ziele", "pain_points": "Pain Points", "relationships": "Beziehungen",
        "calendar": "Kalender", "no_days_yet": "Noch keine Tage.",
        "properties": "Eigenschaften", "role": "Rolle", "industry": "Branche",
        "size": "Größe", "tools": "Tools", "memory": "Memory", "open": "öffnen",
        "n_projects": "{n} Projekte", "n_open": "{n} offen",
        "not_simulated_yet": "noch nicht simuliert",
        "simulated_activities": "simulierte Aktivitäten",
        "latest_synthesis": "Neueste Synthese · {n} Councils",
        # activity detail
        "what_happened": "Was geschah", "thought": "Gedanke",
        "conversation": "Konversation", "none_f": "Keine.",
        "actions": "Aktionen", "artifacts": "Artefakte", "open_loops": "Offene Loops",
        "persona": "Persona", "tool": "Tool", "mood": "Mood",
        "participants": "Beteiligte", "alone": "allein", "decision": "Entscheidung",
        # calendar
        "tab_day": "Tag", "tab_week": "Woche", "tab_month": "Monat", "tab_year": "Jahr",
        "n_events": "{n} Events",
        # memory
        "memory_title": "Memory — {name}",
        "memory_sub": "Projekt-Timelines, Time-Travel und Recall.",
        "quality": "Qualität", "structure": "Struktur", "critic": "Kritiker",
        "time_travel": "Time-Travel", "show_state": "Stand zeigen",
        "recall": "Recall", "search": "Suchen",
        "recall_placeholder": "z.B. Brandschutz",
        "active_projects": "Aktive Projekte", "open_threads": "Offene Fäden",
        "digests": "Digests", "none": "keine", "nothing": "nichts",
        "state_at": "Stand am {date}", "nothing_valid": "nichts gültig",
        "open_threads_count": "Offene Fäden: {n}",
        "no_critic_run": "noch kein Kritiker-Lauf",
        "outdated": "überholt", "since": "seit",
    },
    "en": {
        "overview": "Overview", "personas": "Personas", "councils": "Councils",
        "syntheses": "Syntheses", "favorites": "Favorites", "mark_with_star": "Mark with a star",
        "theme_toggle": "Toggle theme", "sidebar": "Sidebar", "repo": "Repo",
        "lang_toggle": "Language: English (switch to German)", "lang_short": "DE",
        "back_to_overview": "Back to overview",
        "overview_lead": "Synthetic customer personas, their simulated workdays, councils and synthesis reports.",
        "personas_lead": "{n} synthetic customer profiles.",
        "councils_lead": "Memory-grounded persona debates.",
        "syntheses_lead": "Study arcs across council chains — the reports.",
        "projects": "Projects",
        "projects_lead": "Research graphs: studies (syntheses) as nodes, tagged and linked.",
        "graph": "Graph", "meta_report": "Meta-Report", "open_questions_h": "Open questions", "prototypes_h": "Artifacts",
        "no_projects": "No projects yet. Create one or backfill your syntheses (CLI: research-backfill).",
        "source_studies": "Source studies", "themes_h": "Themes", "build_order_h": "Build order",
        "filter": "Filter", "clear_filter": "clear", "legend": "Legend",
        "no_councils": "No councils yet.", "no_synthesis": "No synthesis yet.",
        "export_pdf": "Export PDF",
        # generic / not-found
        "not_found": "Not found",
        "no_personas": "No personas yet.",
        "runtime_maybe_cleared": "Runtime data may have been cleared.",
        "profile_not_found": "Profile not found",
        "persona_runtime_cleared": "The runtime data may have been cleared.",
        "council_not_found": "Council not found",
        "synthesis_not_found": "Synthesis not found",
        "activity_not_found": "Activity not found",
        # star
        "favorite": "Favorite", "mark_as_favorite": "Mark as favorite",
        # recommendations / effort-impact
        "effort_value": "Effort {a}/5 · Value {n}/5",
        "ei_high_leverage": "high leverage", "ei_worthwhile": "worthwhile",
        "ei_neutral": "neutral", "ei_critical": "review critically",
        "ei_quick_wins": "Quick Wins", "ei_big_bets": "Big Bets",
        "ei_fill_ins": "Fill-ins", "ei_time_sinks": "Time sinks",
        "ei_effort_axis": "Effort →", "ei_value_axis": "Value →",
        "no_data": "No data.",
        # project overview ("story")
        "ov_question": "The question", "ov_path": "The path", "ov_answer": "The answer",
        "ov_full_solution": "Full solution", "ov_view_proto": "View prototype",
        "ov_concepts": "Concepts", "ov_prototypes": "Prototypes", "ov_grounded": "Grounded sessions",
        "ov_open": "Open questions", "ov_no_answer": "No conclusion yet — run not finished.",
        # council framing
        "council_motion": "The motion put to the council",
        "council_motion_help": "Each voice responds to this motion — for, conditional, or against.",
        "council_finding": "What this council found",
        # vote labels
        "vote_support": "For", "vote_maybe": "Conditional",
        "vote_abstain": "Abstain", "vote_oppose": "Against",
        # stance buckets
        "stance_positive": "Positive / enthusiastic", "stance_skeptical": "Skeptical / opposed",
        "stance_neutral": "Neutral", "stance_conditional": "Conditional / partly",
        "stance_other": "Other",
        # sentiment section
        "sentiment_block": "Sentiment",
        "sentiment_scope_chain": "the council chain", "sentiment_scope_session": "this session",
        "sentiment_intro": "Voices across {scope} — who supports, who is skeptical.",
        "per_council": "Per council",
        "personas_by_sentiment": "Personas by sentiment — enthusiasm score (support − opposition)",
        "stance_of_contributions": "Stance of the contributions",
        "sentiment_label": "Sentiment", "relevance_label": "Relevance",
        "name_label": "Name",
        "relevance_tooltip": "Relevance / affected: {rel}",
        "voices_count": "Voices ({n})",
        "voices_intro": "Per persona: sentiment, relevance (affected), key argument and shift — "
                        "filter, sort, expand for evidence.",
        "search_arg_name": "Search argument / name…",
        "sort_by_sentiment": "Sort: sentiment", "sort_relevance": "Relevance",
        "sort_shift_first": "Shift first",
        "segment": "Segment",
        "to_council": "→ Council",
        "shift_label": "Shift {a} → {b}:",
        "voices_n_of_m": "{n} of {m} voices",
        "voices_in_analyses": "Voices in analyses",
        # synthesis report
        "answer_exec_summary": "Answer · Executive Summary",
        "question": "Question",
        "councils_overview": "Referenced councils (evidence)",
        "evidence_decoupled_note": "This synthesis stands alone. Councils are cited evidence — not part of the synthesis (decoupled).",
        "jump_into_council": "Jump into the council →",
        "recommendations": "Recommendations",
        "positioning": "Positioning",
        "voices": "Voices",
        "sentiment_over_chain": "Sentiment across the council chain",
        "segments": "Segments",
        "validated_pain_solvers": "Validated pain solvers",
        "key_problems": "Key problems", "affinity_clusters": "Affinity clusters",
        "ranking": "Ranking", "shortlist": "Shortlist",
        "open_questions": "Open questions",
        "open_questions_next_study": "Open questions / Next study",
        "course": "Course", "arc_course": "Arc / Course",
        "sections": "Sections",
        "exec_summary_marker": "Exec summary",
        "completed": "Completed", "running": "running",
        "iterations": "Iterations",
        "voices_meta": "Voices: {s}",
        # council detail
        "sentiment_this_council": "Sentiment of this council",
        "voices_in_detail": "Voices in detail ({n})",
        "proposal_short_summary": "Proposal &amp; brief summary",
        "proposal": "Proposal", "summary": "Summary",
        "vote": "Vote", "created": "Created", "done": "done",
        # persona detail
        "activity_over_time": "Activity over time",
        "activities_per_day": "Simulated activities per day ({n} total).",
        "current_state": "Current state",
        "goals": "Goals", "pain_points": "Pain points", "relationships": "Relationships",
        "calendar": "Calendar", "no_days_yet": "No days yet.",
        "properties": "Properties", "role": "Role", "industry": "Industry",
        "size": "Size", "tools": "Tools", "memory": "Memory", "open": "open",
        "n_projects": "{n} projects", "n_open": "{n} open",
        "not_simulated_yet": "not simulated yet",
        "simulated_activities": "simulated activities",
        "latest_synthesis": "Latest synthesis · {n} councils",
        # activity detail
        "what_happened": "What happened", "thought": "Thought",
        "conversation": "Conversation", "none_f": "None.",
        "actions": "Actions", "artifacts": "Artifacts", "open_loops": "Open loops",
        "persona": "Persona", "tool": "Tool", "mood": "Mood",
        "participants": "Participants", "alone": "alone", "decision": "Decision",
        # calendar
        "tab_day": "Day", "tab_week": "Week", "tab_month": "Month", "tab_year": "Year",
        "n_events": "{n} events",
        # memory
        "memory_title": "Memory — {name}",
        "memory_sub": "Project timelines, time travel and recall.",
        "quality": "Quality", "structure": "Structure", "critic": "Critic",
        "time_travel": "Time travel", "show_state": "Show state",
        "recall": "Recall", "search": "Search",
        "recall_placeholder": "e.g. fire safety",
        "active_projects": "Active projects", "open_threads": "Open threads",
        "digests": "Digests", "none": "none", "nothing": "nothing",
        "state_at": "State at {date}", "nothing_valid": "nothing valid",
        "open_threads_count": "Open threads: {n}",
        "no_critic_run": "no critic run yet",
        "outdated": "outdated", "since": "since",
    },
}


def _lang() -> str:
    return _UI_LANG.get() or ui_language()


def t(key: str, **kw: object) -> str:
    lang = _lang() if _lang() in STRINGS else "en"
    value = STRINGS[lang].get(key) or STRINGS["en"].get(key, key)
    return value.format(**kw) if kw else value


def _resolve_request_language(query_lang: str | None, cookie_lang: str | None) -> tuple[str, bool]:
    """Resolve the UI language for a request and whether it should be persisted.
    Precedence: explicit ?lang= (persist) -> cookie -> stored setting."""
    q = (query_lang or "").strip().lower()[:2]
    if q in SUPPORTED_LANGUAGES:
        return q, True
    c = (cookie_lang or "").strip().lower()[:2]
    if c in SUPPORTED_LANGUAGES:
        return c, False
    return ui_language(), False
