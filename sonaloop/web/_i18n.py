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
        "syntheses": "Reports", "favorites": "Favoriten",
        "sidebar": "Sidebar", "breadcrumb_aria": "Seitenposition",
        "settings": "Einstellungen", "documentation": "Dokumentation", "theme": "Erscheinungsbild", "language": "Sprache",
        "theme_light": "Hell", "theme_dark": "Dunkel", "theme_system": "System",
        "personas_lead": "Synthetische Kundenprofile.",
        "councils_lead": "Memory-geerdete Persona-Debatten.",
        "syntheses_lead": "Strukturierte Reports über die Forschung — exportierbar.",
        "projects": "Projekte",
        "projects_lead": "Forschungsprojekte: Councils, Reports, Prototypen und Notizen als ein verknüpfter Graph.",
        "synthesis_kind": "Report", "n_sections": "{n} Abschnitte", "toc": "Inhalt", "citations": "Belege", "report_unavailable": "Noch kein Report — entsteht, wenn die Studie reif ist.", "open_questions_h": "Offene Fragen", "prototypes_h": "Prototypen",
        "artifacts_h": "Artefakte", "artifact_captured": "erfasst", "artifact_capture_failed": "nicht erfasst — nur Referenz", "artifact_kind_url": "Website", "artifact_kind_prototype": "Prototyp-Link", "artifact_kind_variant": "Variante",
        "assets_h": "Evidenz-Assets", "asset_kind_image": "Bild", "asset_kind_screenshot": "Screenshot", "asset_kind_document": "Dokument", "asset_kind_file": "Datei",
        "no_projects": "Noch keine Projekte. Lege eines an oder backfille deine Reports (CLI: research-backfill).",
        "themes_h": "Themen", "build_order_h": "Aufbau-Reihenfolge",
        "type_h": "Typ", "tags_h": "Tags", "clear_filter": "zurücksetzen", "legend": "Legende", "groups_toggle": "Gruppen ein/aus (Themen & Phasen-Hüllen)", "round_n": "Runde {n}", "relations": "Beziehungen", "rel_based_on": "Basiert auf", "rel_feeds_into": "Fließt ein in",
        "no_councils": "Noch keine Councils.", "no_synthesis": "Noch keine Reports.",
        "prototypes_lead": "Lauffähige Artefakte — von Personas getestet.", "no_prototypes": "Noch keine Artefakte.",
        "notes": "Notizen", "notes_lead": "Rohe Beobachtungen aus der Forschung.", "no_notes": "Noch keine Notizen.", "library_h": "Bibliothek",
        # graph canvas controls
        "graph_hint": "Ziehen · Hintergrund schieben · Pinch / ⌘+Scroll = Zoom · F = einpassen",
        "graph_fit": "Einpassen (F)", "graph_reset": "Layout zurücksetzen (R)",
        "graph_zoom_in": "Zoom in (+)", "graph_zoom_out": "Zoom out (−)",
        # sections / prototype detail
        "section": "Abschnitt", "no_members": "Keine Mitglieder.", "n_nodes": "{n} Knoten",
        "pulse": "Pulse", "gaps": "Gaps", "saturation": "Sättigung", "stalled": "stockt",
        "coverage_h": "Abdeckung", "coverage_panel": "Panel",
        "coverage_level_thin": "dünn", "coverage_level_ok": "ok", "coverage_level_strong": "stark",
        "coverage_recommend": "Empfehlung",
        "sessions": "Sessions", "no_sessions": "keine Sessions",
        "grounded_yes": "grounded", "grounded_no": "unbestätigt",
        "open_in_new_tab": "In neuem Tab öffnen",
        # surveys (the outbound instrument)
        "surveys_h": "Umfragen",
        "surveys_lead": "Versandfertige Instrumente — echte Antworten fließen als Evidenz zurück.",
        "no_surveys": "Noch keine Umfragen.",
        "n_questions": "{n} Fragen", "n_responses": "{n} Antworten",
        "survey_status_draft": "Entwurf", "survey_status_open": "Offen", "survey_status_closed": "Geschlossen",
        "survey_stance_mapped": "Stance-gemappt",
        "survey_predicted": "Council-Prognose", "survey_actual": "Echte Antworten",
        "no_survey_responses": "Noch keine echten Antworten importiert (import_survey_responses).",
        # hypotheses (falsifiable predictions scored against reality)
        "hypotheses_h": "Hypothesen",
        "hypotheses_lead": "Falsifizierbare Wetten über alle Projekte — von der Realität bewertet.",
        "no_hypotheses": "Noch keine Hypothesen.",
        "hyp_open_bets": "Offene Wetten", "hyp_resolved": "Aufgelöst",
        "hyp_hit_rate": "Trefferquote",
        "hyp_no_resolved": "Noch keine aufgelöst — die Trefferquote erscheint, sobald reale Ergebnisse erfasst sind.",
        "hyp_no_decisive": "noch kein eindeutiges Urteil",
        "hyp_predicted": "Vorhergesagt", "hyp_observed": "Beobachtet", "hyp_confidence": "Konfidenz",
        "hyp_status_open": "Offen", "hyp_status_validated": "Bestätigt",
        "hyp_status_refuted": "Widerlegt", "hyp_status_inconclusive": "Unentschieden",
        "hyp_status_dropped": "Verworfen",
        "hyp_dir_increase": "steigt", "hyp_dir_decrease": "fällt",
        # decisions (what we decided, on which evidence, rejecting what)
        "decisions_h": "Entscheidungen",
        "decisions_lead": "Was entschieden wurde, auf welcher Evidenz — und was verworfen wurde.",
        "no_decisions": "Noch keine Entscheidungen.",
        "dec_status_proposed": "Vorgeschlagen", "dec_status_adopted": "Beschlossen",
        "dec_status_superseded": "Abgelöst",
        "dec_rejected": "Verworfen", "dec_superseded_by": "Abgelöst durch",
        "dec_supersedes": "Löst ab",
        "dec_informed_h": "Floss in Entscheidungen ein",
        # generic / not-found
        "not_found": "Nicht gefunden",
        "no_personas": "Noch keine Personas.",
        "runtime_maybe_cleared": "Runtime-Daten evtl. geleert.",
        "profile_not_found": "Profil nicht gefunden",
        "persona_runtime_cleared": "Die Runtime-Daten wurden evtl. geleert.",
        "council_not_found": "Council nicht gefunden",
        "synthesis_not_found": "Report nicht gefunden",
        "activity_not_found": "Aktivität nicht gefunden",
        # star
        "favorite": "Favorit", "mark_as_favorite": "Als Favorit markieren", "unstar": "Stern entfernen",
        # recommendations / effort-impact
        "effort_value": "Aufwand {a}/5 · Nutzen {n}/5",
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
        "h2h_title": "Kopf-an-Kopf-Vergleich",
        "h2h_kicker": "Kopf-an-Kopf · {n} Stimmen",
        "h2h_lead": "Direkter Vergleich der Optionen — eine begründete, segmentierte Präferenz statt zwei getrennter Ja/Nein-Runden.",
        "h2h_preference": "Präferenz",
        "h2h_margin": "Vorsprung",
        "h2h_no_pref": "Keine klare Präferenz (Gleichstand)",
        "h2h_options": "Optionen",
        "h2h_votes": "Stimmen",
        "h2h_segments": "Wer bevorzugt was (nach Segment)",
        "h2h_segment": "Segment",
        "h2h_voters": "Stimmen",
        "h2h_prefers": "Bevorzugt",
        "h2h_tie": "Gleichstand",
        "h2h_decisive_tie": "Gleichstand", "h2h_decisive_narrow": "knapp",
        "h2h_decisive_clear": "klar", "h2h_decisive_decisive": "eindeutig",
        "rt_title": "Red-Team (Gegenprobe)",
        "rt_kicker": "Red-Team · {n} Stimmen",
        "rt_lead": "Bewusst die Gegenseite — warum dieses Segment NICHT adoptiert/zahlt oder abwandert. Stresstest statt Bestätigung.",
        "rt_case_against": "Argumente dagegen",
        "rt_case_for": "Argumente dafür",
        "rt_blockers": "Blocker-Themen",
        "rt_blocker": "Blocker",
        "rt_pull": "Zugkraft",
        "rt_personas": "Personas",
        "rt_voices": "Stimmen",
        "rt_top_blocker": "Größter Blocker",
        "rt_severity": "Schweregrad",
        "rt_no_objections": "Keine substanziellen Einwände",
        "rt_sev_low": "gering", "rt_sev_medium": "mittel",
        "rt_sev_high": "hoch", "rt_sev_critical": "kritisch",
        "council_input_given": "Gegebener Input (Prompt + Kontext)",
        "council_drew_on": "Stützte sich auf",
        "further_answers": "Weitere Antworten", "cited_by": "Zitiert von",
        # stance scale labels (the five canonical buckets — stance_scale.json label_keys; votes
        # are stances too, so the vote charts/legends resolve these same keys)
        "stance_support": "Befürwortend", "stance_conditional": "Bedingt / teils",
        "stance_neutral": "Neutral", "stance_skeptical": "Skeptisch / ablehnend",
        "stance_oppose": "Ablehnend",
        # friction levels (usability-session steps — friction_levels.json label_keys)
        "likelihood_rare": "Selten", "likelihood_unlikely": "Unwahrscheinlich", "likelihood_possible": "Möglich", "likelihood_likely": "Wahrscheinlich", "likelihood_certain": "Nahezu sicher",
        "friction_none": "Reibungslos", "friction_hesitation": "Zögern",
        "friction_confusion": "Verwirrung", "friction_blocked": "Blockiert",
        # session replay inspector (usability sessions — list / funnel / dual timeline)
        "sessions_lead": "Replaybare Usability-Sessions — die Dual-Timeline pro Persona, Schritt für Schritt.",
        "session_not_found": "Session nicht gefunden.",
        # ("Klick-Prototyp", not the bare word: the presentation-from-data grep gate bans the
        # hardcoded artifact literal — and the fidelity rung is the clickable walk, not the artifact)
        "fidelity_artifact": "Artefakt", "fidelity_prototype": "Klick-Prototyp", "fidelity_live": "Live",
        "outcome_dropped": "Abgesprungen bei Schritt {n}",
        "friction_n": "{n}× Reibung",
        "funnel_h": "Funnel",
        "funnel_hint": "{n} Sessions zu diesem Gegenstand — pro Schritt: erreicht, weiter, abgesprungen.",
        "funnel_entered": "erreicht", "funnel_continued": "weiter", "funnel_dropped": "abgesprungen",
        "step_n": "Schritt {n}", "steps_h": "Schritte", "subject_h": "Gegenstand",
        "friction_rail_h": "Reibungspunkte", "replay_h": "Replay",
        "verdict_continue": "würde weitermachen", "verdict_drop": "würde abbrechen",
        "action_look": "Ansehen", "action_click": "Klick", "action_type": "Eingabe",
        "action_select": "Auswahl", "action_scroll": "Scrollen", "action_key": "Taste",
        "action_navigate": "Navigieren", "action_back": "Zurück", "action_wait": "Warten",
        "action_give_up": "Aufgegeben",
        # capability profile (rungs + tech comfort — tech_comfort.json label_keys)
        "capabilities_h": "Fähigkeiten",
        "cap_rung_see": "Ansehen", "cap_rung_walk": "Durchklicken",
        "cap_rung_drive": "Selbst bedienen", "cap_rung_login": "Login",
        "cap_tech_comfort": "Tech-Komfort", "cap_devices": "Geräte",
        "cap_accessibility": "Barrierefreiheit",
        "cap_derived": "abgeleitet", "cap_authored": "deklariert", "cap_evidence": "evidenzbasiert",
        "tech_comfort_novice": "Neuling", "tech_comfort_cautious": "Vorsichtig",
        "tech_comfort_comfortable": "Sicher", "tech_comfort_fluent": "Versiert",
        "tech_comfort_expert": "Experte",
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
        "evidence_decoupled_note": "Dieser Report ist eigenständig. Councils sind zitierte Evidenz — kein Bestandteil des Reports (entkoppelt).",
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
        "vote": "Abstimmung", "created": "Erzeugt", "project": "Projekt", "fidelity": "Fidelity", "done": "done",
        # persona detail
        "current_state": "Aktueller Zustand",
        "goals": "Ziele", "pain_points": "Pain Points", "relationships": "Beziehungen",
        "calendar": "Kalender", "no_days_yet": "Noch keine Tage.",
        "properties": "Eigenschaften", "role": "Rolle", "industry": "Branche",
        "size": "Größe", "tools": "Tools", "memory": "Memory", "open": "öffnen",
        "n_projects": "{n} Projekte", "n_projects_one": "{n} Projekt", "n_nodes_one": "{n} Knoten", "n_sections_one": "{n} Abschnitt", "n_open": "{n} offen",
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
        "search": "Suchen",
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
        "syntheses": "Reports", "favorites": "Favorites",
        "sidebar": "Sidebar", "breadcrumb_aria": "Page position",
        "settings": "Settings", "documentation": "Documentation", "theme": "Appearance", "language": "Language",
        "theme_light": "Light", "theme_dark": "Dark", "theme_system": "System",
        "personas_lead": "Synthetic customer profiles.",
        "councils_lead": "Memory-grounded persona debates.",
        "syntheses_lead": "Structured reports across the research — exportable.",
        "projects": "Projects",
        "projects_lead": "Research projects: councils, reports, prototypes and notes as one linked graph.",
        "synthesis_kind": "Report", "n_sections": "{n} sections", "toc": "Contents", "citations": "Citations", "report_unavailable": "No report yet — generated once the study matures.", "open_questions_h": "Open questions", "prototypes_h": "Prototypes",
        "artifacts_h": "Artifacts", "artifact_captured": "captured", "artifact_capture_failed": "not captured — reference only", "artifact_kind_url": "Website", "artifact_kind_prototype": "Prototype", "artifact_kind_variant": "Variant",
        "assets_h": "Evidence assets", "asset_kind_image": "Image", "asset_kind_screenshot": "Screenshot", "asset_kind_document": "Document", "asset_kind_file": "File",
        "no_projects": "No projects yet. Create one or backfill your reports (CLI: research-backfill).",
        "themes_h": "Themes", "build_order_h": "Build order",
        "type_h": "Type", "tags_h": "Tags", "clear_filter": "clear", "legend": "Legend", "groups_toggle": "Toggle groups (theme & phase hulls)", "round_n": "Round {n}", "relations": "Relations", "rel_based_on": "Based on", "rel_feeds_into": "Feeds into",
        "no_councils": "No councils yet.", "no_synthesis": "No reports yet.",
        "prototypes_lead": "Runnable artifacts — tested by personas.", "no_prototypes": "No artifacts yet.",
        "notes": "Notes", "notes_lead": "Raw observations from the research.", "no_notes": "No notes yet.", "library_h": "Library",
        # graph canvas controls
        "graph_hint": "drag · pan background · pinch / ⌘+scroll to zoom · F to fit",
        "graph_fit": "Fit to view (F)", "graph_reset": "Reset layout (R)",
        "graph_zoom_in": "Zoom in (+)", "graph_zoom_out": "Zoom out (−)",
        # sections / prototype detail
        "section": "Section", "no_members": "No members.", "n_nodes": "{n} nodes",
        "pulse": "Pulse", "gaps": "Gaps", "saturation": "Saturation", "stalled": "stalled",
        "coverage_h": "Coverage", "coverage_panel": "Panel",
        "coverage_level_thin": "thin", "coverage_level_ok": "ok", "coverage_level_strong": "strong",
        "coverage_recommend": "Recommendation",
        "sessions": "Sessions", "no_sessions": "no sessions",
        "grounded_yes": "grounded", "grounded_no": "unconfirmed",
        "open_in_new_tab": "Open in new tab",
        # surveys (the outbound instrument)
        "surveys_h": "Surveys",
        "surveys_lead": "Sendable instruments — real responses flow back as evidence.",
        "no_surveys": "No surveys yet.",
        "n_questions": "{n} questions", "n_responses": "{n} responses",
        "survey_status_draft": "Draft", "survey_status_open": "Open", "survey_status_closed": "Closed",
        "survey_stance_mapped": "stance-mapped",
        "survey_predicted": "Council prediction", "survey_actual": "Real answers",
        "no_survey_responses": "No real responses imported yet (import_survey_responses).",
        # hypotheses (falsifiable predictions scored against reality)
        "hypotheses_h": "Hypotheses",
        "hypotheses_lead": "Falsifiable bets across all projects — scored by reality.",
        "no_hypotheses": "No hypotheses yet.",
        "hyp_open_bets": "Open bets", "hyp_resolved": "Resolved",
        "hyp_hit_rate": "Hit rate",
        "hyp_no_resolved": "None resolved yet — the hit rate appears once real results are recorded.",
        "hyp_no_decisive": "no decisive verdicts yet",
        "hyp_predicted": "Predicted", "hyp_observed": "Observed", "hyp_confidence": "Confidence",
        "hyp_status_open": "Open", "hyp_status_validated": "Validated",
        "hyp_status_refuted": "Refuted", "hyp_status_inconclusive": "Inconclusive",
        "hyp_status_dropped": "Dropped",
        "hyp_dir_increase": "increases", "hyp_dir_decrease": "decreases",
        # decisions (what we decided, on which evidence, rejecting what)
        "decisions_h": "Decisions",
        "decisions_lead": "What was decided, on which evidence — and what was rejected.",
        "no_decisions": "No decisions yet.",
        "dec_status_proposed": "Proposed", "dec_status_adopted": "Adopted",
        "dec_status_superseded": "Superseded",
        "dec_rejected": "Rejected", "dec_superseded_by": "Superseded by",
        "dec_supersedes": "Supersedes",
        "dec_informed_h": "Informed decisions",
        # generic / not-found
        "not_found": "Not found",
        "no_personas": "No personas yet.",
        "runtime_maybe_cleared": "Runtime data may have been cleared.",
        "profile_not_found": "Profile not found",
        "persona_runtime_cleared": "The runtime data may have been cleared.",
        "council_not_found": "Council not found",
        "synthesis_not_found": "Report not found",
        "activity_not_found": "Activity not found",
        # star
        "favorite": "Favorite", "mark_as_favorite": "Mark as favorite", "unstar": "Unstar",
        # recommendations / effort-impact
        "effort_value": "Effort {a}/5 · Value {n}/5",
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
        "h2h_title": "Head-to-Head comparison",
        "h2h_kicker": "Head-to-Head · {n} voices",
        "h2h_lead": "A direct comparison of the options — one reasoned, segmented preference instead of two separate yes/no rounds.",
        "h2h_preference": "Preference",
        "h2h_margin": "Margin",
        "h2h_no_pref": "No clear preference (tie)",
        "h2h_options": "Options",
        "h2h_votes": "Votes",
        "h2h_segments": "Who prefers what (by segment)",
        "h2h_segment": "Segment",
        "h2h_voters": "Voters",
        "h2h_prefers": "Prefers",
        "h2h_tie": "Tie",
        "h2h_decisive_tie": "tie", "h2h_decisive_narrow": "narrow",
        "h2h_decisive_clear": "clear", "h2h_decisive_decisive": "decisive",
        "rt_title": "Red-Team (case against)",
        "rt_kicker": "Red-Team · {n} voices",
        "rt_lead": "Deliberately the negative case — why this segment would NOT adopt/pay or would churn. A stress-test, not a flattering pass.",
        "rt_case_against": "Case against",
        "rt_case_for": "Case for",
        "rt_blockers": "blocker themes",
        "rt_blocker": "Blocker",
        "rt_pull": "Pull",
        "rt_personas": "Personas",
        "rt_voices": "voices",
        "rt_top_blocker": "Top blocker",
        "rt_severity": "Severity",
        "rt_no_objections": "No substantive objections",
        "rt_sev_low": "low", "rt_sev_medium": "medium",
        "rt_sev_high": "high", "rt_sev_critical": "critical",
        "council_input_given": "Input given (prompt + context)",
        "council_drew_on": "Drew on",
        "further_answers": "Further answers", "cited_by": "Cited by",
        # stance scale labels (the five canonical buckets — stance_scale.json label_keys; votes
        # are stances too, so the vote charts/legends resolve these same keys)
        "stance_support": "Support", "stance_conditional": "Conditional / partly",
        "stance_neutral": "Neutral", "stance_skeptical": "Skeptical / opposed",
        "stance_oppose": "Oppose",
        # friction levels (usability-session steps — friction_levels.json label_keys)
        "likelihood_rare": "Rare", "likelihood_unlikely": "Unlikely", "likelihood_possible": "Possible", "likelihood_likely": "Likely", "likelihood_certain": "Near-certain",
        "friction_none": "None", "friction_hesitation": "Hesitation",
        "friction_confusion": "Confusion", "friction_blocked": "Blocked",
        # session replay inspector (usability sessions — list / funnel / dual timeline)
        "sessions_lead": "Replayable usability sessions — the per-persona dual timeline, step by step.",
        "session_not_found": "Session not found.",
        "fidelity_artifact": "Artifact", "fidelity_prototype": "Prototype", "fidelity_live": "Live",
        "outcome_dropped": "Dropped at step {n}",
        "friction_n": "{n}× friction",
        "funnel_h": "Funnel",
        "funnel_hint": "{n} sessions of this subject — per step: entered, continued, dropped.",
        "funnel_entered": "entered", "funnel_continued": "continued", "funnel_dropped": "dropped",
        "step_n": "Step {n}", "steps_h": "Steps", "subject_h": "Subject",
        "friction_rail_h": "Friction points", "replay_h": "Replay",
        "verdict_continue": "would continue", "verdict_drop": "would drop",
        "action_look": "Look", "action_click": "Click", "action_type": "Type",
        "action_select": "Select", "action_scroll": "Scroll", "action_key": "Key",
        "action_navigate": "Navigate", "action_back": "Back", "action_wait": "Wait",
        "action_give_up": "Give up",
        # capability profile (rungs + tech comfort — tech_comfort.json label_keys)
        "capabilities_h": "Capabilities",
        "cap_rung_see": "See", "cap_rung_walk": "Walk",
        "cap_rung_drive": "Drive", "cap_rung_login": "Login",
        "cap_tech_comfort": "Tech comfort", "cap_devices": "Devices",
        "cap_accessibility": "Accessibility",
        "cap_derived": "derived", "cap_authored": "authored", "cap_evidence": "evidence-backed",
        "tech_comfort_novice": "Novice", "tech_comfort_cautious": "Cautious",
        "tech_comfort_comfortable": "Comfortable", "tech_comfort_fluent": "Fluent",
        "tech_comfort_expert": "Expert",
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
        "evidence_decoupled_note": "This report stands alone. Councils are cited evidence — not part of the report (decoupled).",
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
        "vote": "Vote", "created": "Created", "project": "Project", "fidelity": "Fidelity", "done": "done",
        # persona detail
        "current_state": "Current state",
        "goals": "Goals", "pain_points": "Pain points", "relationships": "Relationships",
        "calendar": "Calendar", "no_days_yet": "No days yet.",
        "properties": "Properties", "role": "Role", "industry": "Industry",
        "size": "Size", "tools": "Tools", "memory": "Memory", "open": "open",
        "n_projects": "{n} projects", "n_projects_one": "{n} project", "n_nodes_one": "{n} node", "n_sections_one": "{n} section", "n_open": "{n} open",
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
        "search": "Search",
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
