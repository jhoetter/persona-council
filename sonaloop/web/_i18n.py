from __future__ import annotations

import contextvars

from ..config import ui_language, SUPPORTED_LANGUAGES


# ===================================================================== #
# i18n: the inspector chrome is bilingual (de/en). The active UI language #
# is resolved per request (?lang= -> cookie -> persisted setting) and    #
# held in a contextvar so the module-level render helpers can read it     #
# without threading it through every function. Generated CONTENT keeps    #
# its own content_language; this only switches the surrounding UI.        #
#                                                                         #
# Contract (enforced by tests/test_i18n.py):                              #
#   - STRINGS covers exactly SUPPORTED_LANGUAGES.                          #
#   - every language defines the SAME key set with the SAME {placeholders}.#
#   - every t("literal") used in the codebase resolves to a defined key.   #
# Add a string by adding the key to EVERY language table, never inline.    #
# ===================================================================== #

# Ultimate fallback when a key is missing in the active language (should not
# happen — the parity test guards it — but keeps render robust in prod).
FALLBACK_LANGUAGE = "en"

_UI_LANG: contextvars.ContextVar[str | None] = contextvars.ContextVar("ui_lang", default=None)

STRINGS: dict[str, dict[str, str]] = {
    "de": {
        "personas": "Personas", "councils": "Councils",
        "syntheses": "Synthesen", "favorites": "Favoriten",
        "sidebar": "Sidebar", "breadcrumb_aria": "Seitenposition",
        "settings": "Einstellungen", "documentation": "Dokumentation", "theme": "Erscheinungsbild", "language": "Sprache",
        "theme_light": "Hell", "theme_dark": "Dunkel", "theme_system": "System",
        "personas_lead": "Synthetische Kundenprofile.",
        "councils_lead": "Memory-geerdete Persona-Debatten.",
        "syntheses_lead": "Studien-Bögen über Council-Ketten — die Reports.",
        "projects": "Projekte",
        "projects_lead": "Forschungsprojekte: Councils, Synthesen, Prototypen und Notizen als ein verknüpfter Graph.",
        "meta_report": "Meta-Report", "meta_reports": "Meta-Reports", "meta_reports_lead": "Studienübergreifende Projekt-Reports — je ein Hand-off-Dokument.", "n_sections": "{n} Abschnitte", "toc": "Inhalt", "citations": "Belege", "meta_report_unavailable": "Noch kein Meta-Report — entsteht, wenn die Studie reif ist.", "open_questions_h": "Offene Fragen", "prototypes_h": "Prototypen",
        "no_projects": "Noch keine Projekte. Lege eines an oder backfille deine Synthesen (CLI: research-backfill).",
        "themes_h": "Themen", "build_order_h": "Aufbau-Reihenfolge",
        "type_h": "Typ", "tags_h": "Tags", "clear_filter": "zurücksetzen", "legend": "Legende", "groups_toggle": "Gruppen ein/aus (Themen & Phasen-Hüllen)", "round_n": "Runde {n}", "relations": "Beziehungen", "rel_based_on": "Basiert auf", "rel_feeds_into": "Fließt ein in",
        "no_councils": "Noch keine Councils.", "no_synthesis": "Noch keine Synthese.",
        "prototypes_lead": "Lauffähige Artefakte — von Personas getestet.", "no_prototypes": "Noch keine Artefakte.",
        "notes": "Notizen", "notes_lead": "Rohe Beobachtungen aus der Forschung.", "no_notes": "Noch keine Notizen.", "library_h": "Bibliothek",
        # graph canvas controls
        "graph_hint": "Ziehen · Hintergrund schieben · Pinch / ⌘+Scroll = Zoom · F = einpassen",
        "graph_fit": "Einpassen (F)", "graph_reset": "Layout zurücksetzen (R)",
        "graph_zoom_in": "Zoom in (+)", "graph_zoom_out": "Zoom out (−)",
        # sections / prototype detail
        "section": "Abschnitt", "no_members": "Keine Mitglieder.", "n_nodes": "{n} Knoten",
        "pulse": "Pulse", "gaps": "Gaps", "saturation": "Sättigung",
        "sessions": "Sessions", "no_sessions": "keine Sessions",
        "grounded_yes": "grounded", "grounded_no": "unbestätigt",
        "open_in_new_tab": "In neuem Tab öffnen",
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
        "favorite": "Favorit", "mark_as_favorite": "Als Favorit markieren", "unstar": "Stern entfernen",
        # recommendations / effort-impact
        "effort_value": "Aufwand {a}/5 · Nutzen {n}/5",
        "ei_high_leverage": "hoher Hebel", "ei_worthwhile": "lohnend",
        "ei_neutral": "neutral", "ei_critical": "kritisch prüfen",
        "ei_quick_wins": "Quick Wins", "ei_big_bets": "Big Bets",
        "ei_fill_ins": "Lückenfüller", "ei_time_sinks": "Zeitfresser",
        "ei_effort_axis": "Aufwand →", "ei_value_axis": "Nutzen →",
        "no_data": "Keine Daten.",
        # council framing
        "council_motion": "Untersuchte These",
        "council_motion_help": "{n} Personas reagieren aus ihrer GELEBTEN ERFAHRUNG: bestätigt die These (dafür), teils (bedingt) oder widerlegt sie (dagegen). Es ist keine Abstimmung über eine Entscheidung — es ist, was sie tatsächlich erleben. Die Erkenntnis steht darunter.",
        "council_finding": "Erkenntnis aus diesem Council",
        "council_questions_help": "Eine offene Discovery-Runde — wir HÖREN ZU, was {n} Personas tatsächlich erleben. Keine These, keine Abstimmung; die Antworten unten sind die Forschungsdaten.",
        "council_eval_help": "{n} Personas reagieren aus ihrer gelebten Erfahrung darauf — was es auslöst, was fehlt.",
        "council_kicker_discovery": "Discovery · {n} Stimmen · offene Nutzerforschung",
        "council_kicker_evaluation": "Konzept-Resonanz · {n} Stimmen",
        "council_kicker_decision": "Entscheidung · {n} Stimmen",
        "council_mode_discovery": "Discovery", "council_mode_evaluation": "Konzept-Resonanz", "council_mode_decision": "Entscheidung",
        "council_input_given": "Gegebener Input (Prompt + Kontext)",
        "council_drew_on": "Stützte sich auf",
        "further_answers": "Weitere Antworten", "cited_by": "Zitiert von",
        # vote labels
        "vote_support": "Befürwortend", "vote_maybe": "Bedingt",
        "vote_abstain": "Enthaltung", "vote_oppose": "Ablehnend",
        # stance buckets
        "stance_positive": "Positiv / begeistert", "stance_skeptical": "Skeptisch / ablehnend",
        "stance_support": "Befürwortend", "stance_oppose": "Ablehnend",
        "stance_neutral": "Neutral", "stance_conditional": "Bedingt / teils",
        "stance_other": "Sonstige",
        # sentiment section
        "sentiment_block": "Stimmungsbild",
        "sentiment_scope_chain": "die Council-Kette", "sentiment_scope_session": "diese Sitzung",
        "sentiment_intro": "Stimmen über {scope} — wer befürwortet, wer ist skeptisch.",
        "per_council": "Pro Council",
        "personas_by_sentiment": "Personas nach Stimmung — Begeisterungs-Score (Befürwortung − Ablehnung)",
        "stance_of_contributions": "Haltung der Wortbeiträge",











        "voices_in_analyses": "Stimmen in Analysen",
        # synthesis report
        "answer_exec_summary": "Executive Summary",
        "question": "Frage",
        "councils_overview": "Referenzierte Councils (Belege)",
        "evidence_decoupled_note": "Diese Synthese ist eigenständig. Councils sind zitierte Evidenz — kein Bestandteil der Synthese (entkoppelt).",
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
        "completed": "Abgeschlossen", "running": "läuft",
        "iterations": "Iterationen",
        "voices_meta": "Stimmen: {s}",
        # council detail
        "sentiment_this_council": "Stimmungsbild dieses Councils",
        "proposal_short_summary": "Proposal &amp; Kurz-Summary",
        "proposal": "Proposal", "summary": "Summary",
        "vote": "Abstimmung", "created": "Erzeugt", "status": "Status", "project": "Projekt", "fidelity": "Fidelity", "done": "done",
        # persona detail
        "current_state": "Aktueller Zustand",
        "goals": "Ziele", "pain_points": "Pain Points", "relationships": "Beziehungen",
        "calendar": "Kalender", "no_days_yet": "Noch keine Tage.",
        "properties": "Eigenschaften", "role": "Rolle", "industry": "Branche",
        "size": "Größe", "tools": "Tools", "memory": "Memory", "open": "öffnen",
        "n_projects": "{n} Projekte", "n_projects_one": "{n} Projekt", "n_nodes_one": "{n} Knoten", "n_open": "{n} offen",
        # activity detail
        "what_happened": "Was geschah", "thought": "Gedanke",
        "conversation": "Konversation", "none_f": "Keine.",
        "actions": "Aktionen", "artifacts": "Artefakte", "open_loops": "Offene Loops",
        "persona": "Persona", "tool": "Tool", "mood": "Mood",
        "participants": "Beteiligte", "alone": "allein", "decision": "Entscheidung",
        # calendar
        "tab_week": "Woche", "tab_month": "Monat", "tab_year": "Jahr",
        "n_more": "+{n} mehr", "less": "weniger", "more": "mehr",
        "n_events": "{n} Events",
        # memory
        "memory_title": "Memory — {name}",
        "memory_sub": "Projekt-Timelines, Time-Travel und Recall.",
        "show_state": "Stand zeigen", "recall": "Recall", "today": "Heute",
        "cmdk_placeholder": "Suchen oder springen… (Projekte, Personas, Councils, …)", "cmdk_empty": "Keine Treffer",
        "cmdk_jump": "Springen", "cmdk_nav": "navigieren", "cmdk_open": "öffnen", "cmdk_close": "schließen", "notes_h": "Notizen",
        "recall_placeholder": "z.B. Brandschutz",
        "active_projects": "Projekte", "open_threads": "Offene Fäden",
        "knowledge": "Wissen", "mem_people": "Personen", "mem_topics": "Themen", "mem_tools": "Tools",
        "none": "keine", "nothing": "nichts",
        "state_at": "Stand am {date}", "nothing_valid": "nichts gültig",
        "open_threads_count": "Offene Fäden: {n}",
        "outdated": "überholt", "since": "seit",
    },
    "en": {
        "personas": "Personas", "councils": "Councils",
        "syntheses": "Syntheses", "favorites": "Favorites",
        "sidebar": "Sidebar", "breadcrumb_aria": "Page position",
        "settings": "Settings", "documentation": "Documentation", "theme": "Appearance", "language": "Language",
        "theme_light": "Light", "theme_dark": "Dark", "theme_system": "System",
        "personas_lead": "Synthetic customer profiles.",
        "councils_lead": "Memory-grounded persona debates.",
        "syntheses_lead": "Study arcs across council chains — the reports.",
        "projects": "Projects",
        "projects_lead": "Research projects: councils, syntheses, prototypes and notes as one linked graph.",
        "meta_report": "Meta-Report", "meta_reports": "Meta-Reports", "meta_reports_lead": "Cross-study project reports — each a hand-off document.", "n_sections": "{n} sections", "toc": "Contents", "citations": "Citations", "meta_report_unavailable": "No meta-report yet — generated once the study matures.", "open_questions_h": "Open questions", "prototypes_h": "Prototypes",
        "no_projects": "No projects yet. Create one or backfill your syntheses (CLI: research-backfill).",
        "themes_h": "Themes", "build_order_h": "Build order",
        "type_h": "Type", "tags_h": "Tags", "clear_filter": "clear", "legend": "Legend", "groups_toggle": "Toggle groups (theme & phase hulls)", "round_n": "Round {n}", "relations": "Relations", "rel_based_on": "Based on", "rel_feeds_into": "Feeds into",
        "no_councils": "No councils yet.", "no_synthesis": "No synthesis yet.",
        "prototypes_lead": "Runnable artifacts — tested by personas.", "no_prototypes": "No artifacts yet.",
        "notes": "Notes", "notes_lead": "Raw observations from the research.", "no_notes": "No notes yet.", "library_h": "Library",
        # graph canvas controls
        "graph_hint": "drag · pan background · pinch / ⌘+scroll to zoom · F to fit",
        "graph_fit": "Fit to view (F)", "graph_reset": "Reset layout (R)",
        "graph_zoom_in": "Zoom in (+)", "graph_zoom_out": "Zoom out (−)",
        # sections / prototype detail
        "section": "Section", "no_members": "No members.", "n_nodes": "{n} nodes",
        "pulse": "Pulse", "gaps": "Gaps", "saturation": "Saturation",
        "sessions": "Sessions", "no_sessions": "no sessions",
        "grounded_yes": "grounded", "grounded_no": "unconfirmed",
        "open_in_new_tab": "Open in new tab",
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
        "favorite": "Favorite", "mark_as_favorite": "Mark as favorite", "unstar": "Unstar",
        # recommendations / effort-impact
        "effort_value": "Effort {a}/5 · Value {n}/5",
        "ei_high_leverage": "high leverage", "ei_worthwhile": "worthwhile",
        "ei_neutral": "neutral", "ei_critical": "review critically",
        "ei_quick_wins": "Quick Wins", "ei_big_bets": "Big Bets",
        "ei_fill_ins": "Fill-ins", "ei_time_sinks": "Time sinks",
        "ei_effort_axis": "Effort →", "ei_value_axis": "Value →",
        "no_data": "No data.",
        # council framing
        "council_motion": "The hypothesis investigated",
        "council_motion_help": "{n} personas react from their LIVED EXPERIENCE: confirms the hypothesis (for), partly (conditional), or refutes it (against). This is not a decision vote — it is what they actually experience. The insight is below.",
        "council_finding": "What this council found",
        "council_questions_help": "An open discovery round — we LISTEN to what {n} personas actually experience. No hypothesis, no vote; the answers below are the research data.",
        "council_eval_help": "{n} personas react to it from their lived experience — what it triggers, what's missing.",
        "council_kicker_discovery": "Discovery · {n} voices · open user research",
        "council_kicker_evaluation": "Concept reaction · {n} voices",
        "council_kicker_decision": "Decision · {n} voices",
        "council_mode_discovery": "Discovery", "council_mode_evaluation": "Concept reaction", "council_mode_decision": "Decision",
        "council_input_given": "Input given (prompt + context)",
        "council_drew_on": "Drew on",
        "further_answers": "Further answers", "cited_by": "Cited by",
        # vote labels
        "vote_support": "For", "vote_maybe": "Conditional",
        "vote_abstain": "Abstain", "vote_oppose": "Against",
        # stance buckets
        "stance_positive": "Positive / enthusiastic", "stance_skeptical": "Skeptical / opposed",
        "stance_support": "Support", "stance_oppose": "Oppose",
        "stance_neutral": "Neutral", "stance_conditional": "Conditional / partly",
        "stance_other": "Other",
        # sentiment section
        "sentiment_block": "Sentiment",
        "sentiment_scope_chain": "the council chain", "sentiment_scope_session": "this session",
        "sentiment_intro": "Voices across {scope} — who supports, who is skeptical.",
        "per_council": "Per council",
        "personas_by_sentiment": "Personas by sentiment — enthusiasm score (support − opposition)",
        "stance_of_contributions": "Stance of the contributions",











        "voices_in_analyses": "Voices in analyses",
        # synthesis report
        "answer_exec_summary": "Executive Summary",
        "question": "Question",
        "councils_overview": "Referenced councils (evidence)",
        "evidence_decoupled_note": "This synthesis stands alone. Councils are cited evidence — not part of the synthesis (decoupled).",
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
        "completed": "Completed", "running": "running",
        "iterations": "Iterations",
        "voices_meta": "Voices: {s}",
        # council detail
        "sentiment_this_council": "Sentiment of this council",
        "proposal_short_summary": "Proposal &amp; brief summary",
        "proposal": "Proposal", "summary": "Summary",
        "vote": "Vote", "created": "Created", "status": "Status", "project": "Project", "fidelity": "Fidelity", "done": "done",
        # persona detail
        "current_state": "Current state",
        "goals": "Goals", "pain_points": "Pain points", "relationships": "Relationships",
        "calendar": "Calendar", "no_days_yet": "No days yet.",
        "properties": "Properties", "role": "Role", "industry": "Industry",
        "size": "Size", "tools": "Tools", "memory": "Memory", "open": "open",
        "n_projects": "{n} projects", "n_projects_one": "{n} project", "n_nodes_one": "{n} node", "n_open": "{n} open",
        # activity detail
        "what_happened": "What happened", "thought": "Thought",
        "conversation": "Conversation", "none_f": "None.",
        "actions": "Actions", "artifacts": "Artifacts", "open_loops": "Open loops",
        "persona": "Persona", "tool": "Tool", "mood": "Mood",
        "participants": "Participants", "alone": "alone", "decision": "Decision",
        # calendar
        "tab_week": "Week", "tab_month": "Month", "tab_year": "Year",
        "n_more": "+{n} more", "less": "less", "more": "more",
        "n_events": "{n} events",
        # memory
        "memory_title": "Memory — {name}",
        "memory_sub": "Project timelines, time travel and recall.",
        "show_state": "Show state", "recall": "Recall", "today": "Today",
        "cmdk_placeholder": "Search or jump to… (projects, personas, councils, …)", "cmdk_empty": "No results",
        "cmdk_jump": "Jump to", "cmdk_nav": "navigate", "cmdk_open": "open", "cmdk_close": "close", "notes_h": "Notes",
        "recall_placeholder": "e.g. fire safety",
        "active_projects": "Projects", "open_threads": "Open threads",
        "knowledge": "Knowledge", "mem_people": "People", "mem_topics": "Topics", "mem_tools": "Tools",
        "none": "none", "nothing": "nothing",
        "state_at": "State at {date}", "nothing_valid": "nothing valid",
        "open_threads_count": "Open threads: {n}",
        "outdated": "outdated", "since": "since",
    },
}


def _lang() -> str:
    """The active UI language: per-request contextvar, else the persisted setting."""
    return _UI_LANG.get() or ui_language()


def t(key: str, **kw: object) -> str:
    """Translate `key` into the active UI language, formatting any `{placeholder}`s.

    Falls back to FALLBACK_LANGUAGE, then to the raw key — so a missing string
    degrades visibly rather than raising. The parity test keeps this from ever
    firing in practice."""
    table = STRINGS.get(_lang(), STRINGS[FALLBACK_LANGUAGE])
    # Singular form: when count is 1 and a "<key>_one" variant exists, prefer it ("1 Projekt", "1 node").
    if kw.get("n") == 1 and (key + "_one") in table:
        key = key + "_one"
    value = table.get(key)
    if value is None:
        value = STRINGS[FALLBACK_LANGUAGE].get(key, key)
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
