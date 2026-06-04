from __future__ import annotations

import contextvars
import html
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import services
from . import presentation as _pres
from .config import DATA_DIR, load_env, ui_language, set_ui_language, SUPPORTED_LANGUAGES
from .storage import Store


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
        "councils_overview": "Councils im Überblick",
        "jump_into_council": "In den Council springen →",
        "recommendations": "Handlungsempfehlungen",
        "positioning": "Positionierung",
        "voices": "Stimmen",
        "sentiment_over_chain": "Stimmungsbild über die Council-Kette",
        "segments": "Segmente",
        "validated_pain_solvers": "Validierte Pain-Solver",
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
        "councils_overview": "Councils overview",
        "jump_into_council": "Jump into the council →",
        "recommendations": "Recommendations",
        "positioning": "Positioning",
        "voices": "Voices",
        "sentiment_over_chain": "Sentiment across the council chain",
        "segments": "Segments",
        "validated_pain_solvers": "Validated pain solvers",
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


# ===================================================================== #
# Design tokens + theme (G0). Light defaults; dark via prefers-color-     #
# scheme and an explicit [data-theme] override (manual toggle).          #
# ===================================================================== #
from .web_assets import CSS, HEAD_JS, _RGRAPH_JS, _SYN_STYLE, _SYN_SCRIPT  # noqa: F401  (extracted assets)

ICONS = {
    "overview": '<svg class="ic" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/></svg>',
    "personas": '<svg class="ic" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.2"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0"/><path d="M16 5.2a3 3 0 0 1 0 5.6"/><path d="M17.5 19a5.5 5.5 0 0 0-3-4.9"/></svg>',
    "councils": '<svg class="ic" viewBox="0 0 24 24"><path d="M21 11.5a8.5 8.5 0 0 1-12.5 7.5L4 20l1-4.5A8.5 8.5 0 1 1 21 11.5z"/></svg>',
    "syntheses": '<svg class="ic" viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/></svg>',
    "projects": '<svg class="ic" viewBox="0 0 24 24"><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M8 7l8 0M7 8l4 8M17 8l-4 8"/></svg>',
    "memory": '<svg class="ic" viewBox="0 0 24 24"><path d="M12 3a4 4 0 0 0-4 4 3.5 3.5 0 0 0-1 6.8V17a3 3 0 0 0 5 2 3 3 0 0 0 5-2v-3.2A3.5 3.5 0 0 0 16 7a4 4 0 0 0-4-4z"/></svg>',
    "panel": '<svg class="ic" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>',
    "sun": '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/></svg>',
    "back": '<svg class="ic" viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>',
    "analytics": '<svg class="ic" viewBox="0 0 24 24"><path d="M3 21h18"/><rect x="5" y="11" width="3.4" height="7" rx="1"/><rect x="10.3" y="6" width="3.4" height="12" rx="1"/><rect x="15.6" y="13" width="3.4" height="5" rx="1"/></svg>',
    "star": '<svg class="ic star" viewBox="0 0 24 24"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 17.9 6.8 20.6l1-5.8L3.5 9.7l5.9-.9z"/></svg>',
    "bulb": '<svg class="ic" viewBox="0 0 24 24"><path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.8 10.6c.5.5.8 1 .8 1.6V16h6v-.8c0-.6.3-1.1.8-1.6A6 6 0 0 0 12 3z"/></svg>',
    "target": '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/></svg>',
    "compass": '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M15.6 8.4l-2 5.2-5.2 2 2-5.2z"/></svg>',
    "search": '<svg class="ic" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
}


def _esc(value: object) -> str:
    return html.escape(str(value))


def _icon(name: str) -> str:
    return ICONS.get(name, "")


_AV_COLORS = ["#3d7b5f", "#2f6f9f", "#a66b1f", "#7a5ea6", "#b3493f", "#4a7d7d", "#5a6b8a"]


def _avatar(p: dict, size: int = 36) -> str:
    if (p.get("avatar") or {}).get("path"):
        return f'<img class="av" style="width:{size}px;height:{size}px" src="/{_esc(p["avatar"]["path"])}" alt="">'
    name = p.get("display_name", "?")
    ini = "".join(w[0] for w in name.split()[:2]).upper() or "?"
    c = _AV_COLORS[sum(map(ord, p.get("id", "x"))) % len(_AV_COLORS)]
    fs = max(10, size // 3)
    return f'<span class="av" style="width:{size}px;height:{size}px;background:{c};font-size:{fs}px">{_esc(ini)}</span>'


def _stance_color(s: str) -> str:
    s = (s or "").lower()
    if any(k in s for k in ["positiv", "befürwort", "support", "abgeschloss", "done", "grün", "green", "stark"]):
        return "var(--green)"
    if any(k in s for k in ["skept", "oppose", "nein", "negativ", "rot", "verloren", "abgelehnt", "blocked"]):
        return "var(--red)"
    if any(k in s for k in ["bedingt", "maybe", "neutral", "läuft", "prog", "warn", "teilweise"]):
        return "var(--amber)"
    if any(k in s for k in ["indiff", "abstain", "kaum", "egal"]):
        return "var(--muted)"
    return "var(--accent)"


def _label(text: str, color: str | None = None, variant: str = "soft", dot: bool = True) -> str:
    d = f'<span class="ld" style="background:{color or "var(--muted)"}"></span>' if dot else ""
    return f'<span class="lbl lbl-{variant}">{d}{_esc(text)}</span>'


def _crumbs_html(crumbs: list) -> str:
    parts = []
    for i, (label, href) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        if href and not last:
            parts.append(f'<a class="bc-link" href="{_esc(href)}" title="{_esc(label)}">{_esc(label)}</a>')
        else:
            parts.append(f'<span class="bc-cur" title="{_esc(label)}">{_esc(label)}</span>')
        if not last:
            parts.append('<span class="bc-sep" aria-hidden="true">›</span>')
    return '<nav class="breadcrumb" aria-label="Seitenposition">' + "".join(parts) + "</nav>"



APP_JS = """
<script>
(function(){
  var MIN=180,MAX=480,HIDE=32;
  var app=document.getElementById('app'),rz=document.getElementById('rz'),tb=document.getElementById('sbt'),th=document.getElementById('thm');
  try{ if(localStorage.getItem('sidebar-open')==='false') app.classList.add('collapsed');
       var w=localStorage.getItem('sidebar-width'); if(w) app.style.setProperty('--sidebar-w',w+'px'); }catch(e){}
  function toggle(){ app.classList.toggle('collapsed');
    try{localStorage.setItem('sidebar-open',String(!app.classList.contains('collapsed')));}catch(e){} }
  if(tb) tb.addEventListener('click',toggle);
  if(th) th.addEventListener('click',function(){
    var cur=document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
    var nx=cur==='dark'?'light':'dark'; document.documentElement.dataset.theme=nx;
    try{localStorage.setItem('theme',nx);}catch(e){} });
  var gmode=false,gt;
  document.addEventListener('keydown',function(e){
    var tag=(e.target.tagName||'').toLowerCase(); if(tag==='input'||tag==='textarea'||tag==='select') return;
    if(e.key==='['){ toggle(); return; }
    if(e.key==='g'){ gmode=true; clearTimeout(gt); gt=setTimeout(function(){gmode=false;},800); return; }
    if(gmode){ var m={o:'/projects',p:'/personas',r:'/projects'}; if(m[e.key]) location.href=m[e.key]; gmode=false; }
  });
  if(rz){
    var sx=0,sw=248,resizing=false,last=248;
    rz.addEventListener('pointerdown',function(e){ e.preventDefault(); resizing=true; sx=e.clientX;
      sw=parseInt(getComputedStyle(app).getPropertyValue('--sidebar-w'))||248;
      document.body.style.cursor='col-resize'; document.body.style.userSelect='none'; rz.setPointerCapture(e.pointerId); });
    rz.addEventListener('pointermove',function(e){ if(!resizing) return; var next=sw+(e.clientX-sx);
      if(next<=HIDE){ app.classList.add('collapsed'); try{localStorage.setItem('sidebar-open','false');}catch(e){} }
      else { var c=Math.max(MIN,Math.min(MAX,next)); last=c; app.style.setProperty('--sidebar-w',c+'px');
             app.classList.remove('collapsed'); try{localStorage.setItem('sidebar-open','true');}catch(e){} } });
    rz.addEventListener('pointerup',function(e){ if(!resizing) return; resizing=false;
      document.body.style.cursor=''; document.body.style.userSelect='';
      try{localStorage.setItem('sidebar-width',String(last));}catch(e){} });
  }
  var sc=document.querySelector('section'); var tocLinks=[].slice.call(document.querySelectorAll('.toc a'));
  if(sc && tocLinks.length){
    var map={}; tocLinks.forEach(function(a){ map[a.getAttribute('href').slice(1)]=a; });
    var obs=new IntersectionObserver(function(es){ es.forEach(function(en){ if(en.isIntersecting){
      tocLinks.forEach(function(l){l.classList.remove('active');}); if(map[en.target.id]) map[en.target.id].classList.add('active'); } }); },
      {root:sc,rootMargin:'0px 0px -78% 0px',threshold:0});
    document.querySelectorAll('.doc-main [id]').forEach(function(s){ obs.observe(s); });
  }
  // ---- favorites / stars (client-side, localStorage) ----
  var SK='pc-stars', ICN=__FAV_ICONS__;
  function readStars(){ try{return JSON.parse(localStorage.getItem(SK)||'{}');}catch(e){return {};} }
  function writeStars(m){ try{localStorage.setItem(SK,JSON.stringify(m));}catch(e){} }
  function renderStars(){
    var m=readStars();
    document.querySelectorAll('[data-star]').forEach(function(b){ b.classList.toggle('on', !!m[b.getAttribute('data-star')]); });
    var favs=document.getElementById('favs'); if(!favs) return;
    var keys=Object.keys(m);
    favs.innerHTML='';
    if(!keys.length){ var e=document.createElement('span'); e.className='muted small'; e.style.cssText='padding:5px 9px;display:block'; e.textContent='Mit Stern markieren'; favs.appendChild(e); return; }
    keys.forEach(function(k){ var f=m[k];
      var row=document.createElement('div'); row.className='favrow';
      var a=document.createElement('a'); a.href=f.href||'#'; a.title=f.label||'';
      var ic=document.createElement('span'); ic.className='favic'; ic.innerHTML=ICN[f.type]||''; a.appendChild(ic);
      a.appendChild(document.createTextNode(' '+(f.label||k)));
      var x=document.createElement('button'); x.className='favx'; x.setAttribute('data-unstar',k); x.setAttribute('aria-label','Unstar'); x.title='Unstar'; x.textContent='\\u00d7';
      row.appendChild(a); row.appendChild(x); favs.appendChild(row); });
  }
  document.addEventListener('click',function(e){
    var ux=e.target.closest && e.target.closest('[data-unstar]');
    if(ux){ e.preventDefault(); e.stopPropagation(); var mm=readStars(); delete mm[ux.getAttribute('data-unstar')]; writeStars(mm); renderStars(); return; }
    var b=e.target.closest && e.target.closest('[data-star]'); if(!b) return;
    e.preventDefault(); e.stopPropagation();
    var m=readStars(), k=b.getAttribute('data-star');
    if(m[k]) delete m[k]; else m[k]={href:b.getAttribute('data-href'),label:b.getAttribute('data-label'),type:b.getAttribute('data-type')};
    writeStars(m); renderStars();
  });
  renderStars();
})();
</script>
"""


def _nav(active: str, store: Store) -> str:
    items = [("/projects", "projects", t("projects")), ("/personas", "personas", t("personas"))]
    nav = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{_icon(key)}<span>{label}</span></a>'
        for href, key, label in items
    )
    # Favorites are stored client-side (localStorage); this container is filled by JS.
    favs = (f'<div class="navhead">{t("favorites")}</div>'
            f'<div class="sb-quick" id="favs"><span class="muted small" style="padding:5px 9px;display:block">{t("mark_with_star")}</span></div>')
    return f'<nav class="nav">{nav}</nav>{favs}'


def _star(kind: str, ident: str, label: str, href: str) -> str:
    return (f'<button class="starbtn" data-star="{_esc(kind)}:{_esc(ident)}" data-href="{_esc(href)}" '
            f'data-label="{_esc(label)}" data-type="{_esc(kind)}" title="{_esc(t("favorite"))}" aria-label="{_esc(t("mark_as_favorite"))}">'
            f'{_icon("star")}</button>')


_FAV_ICONS_JSON = json.dumps({"persona": ICONS["personas"], "council": ICONS["councils"], "synthesis": ICONS["syntheses"]})


def _layout(title: str, body: str, store: Store, crumbs: list | None = None,
            active: str = "", actions: str = "") -> str:
    crumbs = crumbs or [(title, None)]
    theme_btn = f'<button class="iconbtn" id="thm" title="{t("theme_toggle")}" aria-label="Theme">' + _icon("sun") + "</button>"
    other = "en" if _lang() == "de" else "de"
    lang_btn = (f'<a class="iconbtn" id="lang" href="?lang={other}" title="{_esc(t("lang_toggle"))}" '
                f'aria-label="Language" style="font-size:11px;font-weight:600;text-decoration:none">{t("lang_short")}</a>')
    app_js = APP_JS.replace("__FAV_ICONS__", _FAV_ICONS_JSON)
    return f"""<!doctype html>
<html lang="{_lang()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · Persona Council</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
{HEAD_JS}<style>{CSS}</style></head>
<body><div class="app" id="app">
  <aside class="sidebar">
    <div class="brand"><span class="mark"></span><a href="/">Persona&nbsp;Council</a></div>
    <div class="sb-scroll">{_nav(active, store)}</div>
    <div class="sb-foot"><a href="/projects">{t("projects")}</a> · <a href="https://github.com/jhoetter/persona-council">{t("repo")}</a></div>
  </aside>
  <div class="resize" id="rz" role="separator" aria-orientation="vertical" aria-label="Sidebar resize"></div>
  <div class="main">
    <header class="topbar"><button class="iconbtn" id="sbt" title="{t("sidebar")} ([)" aria-label="Sidebar">{_icon("panel")}</button>
      {_crumbs_html(crumbs)}<span class="spacer"></span><span class="tb-actions">{actions}{lang_btn}{theme_btn}</span></header>
    <section>{body}</section>
  </div>
</div>{app_js}</body></html>"""


def _empty_state(title: str, message: str) -> str:
    return f'<div class="page"><div class="card"><h2>{_esc(title)}</h2><p class="muted">{_esc(message)}</p><p><a class="btn" href="/projects">{_icon("back")} {t("projects")}</a></p></div></div>'


def _projects_page() -> str:
    """The Projects list — the app's home (project-centric IA)."""
    store = Store()
    rows = []
    for p in services.list_research_projects(store=store):
        rows.append(f'<a class="row" href="/projects/{_esc(p["id"])}">{_icon("projects")}'
                    f'<span class="title">{_esc(p["title"])}</span>'
                    f'<span class="right"><span>{p["studies"]} {t("syntheses")}</span>'
                    f'<span>{p["edges"]} {t("build_order_h")}</span>'
                    f'<span>{len(p.get("themes", []))} {t("themes_h")}</span></span></a>')
    rows_html = "".join(rows) or f'<div class="row muted">{t("no_projects")}</div>'
    body = f'<div class="page"><h1 class="h1">{t("projects")}</h1><p class="lead">{t("projects_lead")}</p><div class="rows">{rows_html}</div></div>'
    return _layout(t("projects"), body, store, crumbs=[(t("projects"), None)], active="projects")


_EDGE_COLORS = {"spawned_from": "#6b7cff", "refines": "#34a853", "contrasts": "#ea4335",
                "depends_on": "#a142f4", "duplicates": "#9aa0a6", "answers": "#f29900"}
_THEME_PALETTE = ["#6b7cff", "#34a853", "#f29900", "#a142f4", "#ea4335", "#00897b", "#5f6368", "#d81b60"]


def _theme_color(theme: str, vocab: list[str]) -> str:
    try:
        return _THEME_PALETTE[vocab.index(theme) % len(_THEME_PALETTE)]
    except ValueError:
        return "#9aa0a6"




def _graph_layout(graph: dict) -> dict:
    """Deterministic initial layout: x by longest-path depth, y stacked within depth."""
    nodes = graph["nodes"]
    idx = {n["study_id"]: i for i, n in enumerate(nodes)}
    incoming = {n["study_id"]: [] for n in nodes}
    for e in graph["edges"]:
        if e["from_study"] in incoming and e["to_study"] in incoming:
            incoming[e["to_study"]].append(e["from_study"])
    depth: dict[str, int] = {}

    def d(sid, seen=()):
        if sid in depth:
            return depth[sid]
        if sid in seen or not incoming[sid]:
            depth[sid] = 0
            return 0
        depth[sid] = 1 + max(d(p, seen + (sid,)) for p in incoming[sid])
        return depth[sid]

    for n in nodes:
        d(n["study_id"])
    per_depth: dict[int, int] = {}
    pos = {}
    for n in sorted(nodes, key=lambda x: (depth[x["study_id"]], x["created_at"])):
        de = depth[n["study_id"]]
        row = per_depth.get(de, 0)
        per_depth[de] = row + 1
        pos[n["study_id"]] = (40 + de * 300, 30 + row * 104)
    return pos


# node box dimensions (must match _RGRAPH_JS NW/NH)
_NW, _NH = 250, 58
# Saved drag-layouts in localStorage are keyed by this; bump on any layout-algorithm change.
_LAYOUT_VERSION = 4


def _proto_tags(pr: dict) -> set:
    """An artifact's open tags, mirroring methodology._artifact_tags (type tag + discriminators).
    Read from the record's data; no artifact value assumed."""
    tags = {pr.get("type") or _pres.DEFAULT_ARTIFACT_TYPE}
    if pr.get("fidelity"):
        tags.add(pr["fidelity"])
    for tg in (pr.get("tags") or []):
        tags.add(tg)
    return tags


def _artifact_present(pr: dict) -> dict:
    """Resolve an artifact's display fields purely from data: the type tag's presentation hint +
    the first discriminator tag's short label. Generic fallbacks when no hint exists."""
    type_tag = pr.get("type") or _pres.DEFAULT_ARTIFACT_TYPE
    tp = _pres.present(type_tag, pr.get("presentation"))
    disc = ""
    for tg in ([pr.get("fidelity")] + list(pr.get("tags") or [])):
        if tg:
            disc = _pres.present(tg)["short"]
            break
    return {"label": tp["label"], "color": tp["color"], "glyph": tp["glyph"], "icon": tp["icon"], "disc": disc}


def _convex_hull(points: list[tuple]) -> list[tuple]:
    """Andrew's monotone chain — the convex hull of a point set (CCW), no shape assumed."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _expand_hull(hull: list[tuple], margin: float) -> list[list]:
    """Push each hull vertex outward from the centroid by `margin` (a faint surrounding envelope)."""
    import math
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)
    out = []
    for x, y in hull:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1.0
        out.append([x + dx / d * margin, y + dy / d * margin])
    return out


def _methodology_layout(graph: dict) -> dict | None:
    """Generic DAG layout (spec/methodology-constellations.md §5): x = longest-path depth over
    `consumes`; a step's nodes fan vertically when it has >1 (diverge), sit on the axis when 1
    (a waist) → diamonds emerge for any fan→waist. Artifacts are placed in their PRODUCING step's
    column and routed to the first downstream step that consumes their tag — all read from the
    graph + tags, no phase-key literals. Returns {pos, diamonds, proto_*} or None (no methodology)."""
    ms = graph.get("methodology_state") or {}
    steps = ms.get("steps") or ms.get("phases") or []
    if not steps:
        return None
    by_id = {s["key"]: s for s in steps}
    # longest-path depth over the consumes DAG
    depth: dict[str, int] = {}

    def dep(sid: str) -> int:
        if sid in depth:
            return depth[sid]
        depth[sid] = 0  # guard
        cs = by_id.get(sid, {}).get("consumes", [])
        depth[sid] = (max((dep(c) for c in cs), default=-1) + 1)
        return depth[sid]

    for s in steps:
        dep(s["key"])
    COLW, ROWH, X0, AXIS = 520, 118, 40, 340
    by_step: dict[str, list] = {}
    for n in graph["nodes"]:
        by_step.setdefault(n.get("phase", ""), []).append(n)
    col_x = {s["key"]: X0 + depth[s["key"]] * COLW for s in steps}
    pos: dict[str, tuple] = {}
    fan_half: dict[str, float] = {}
    is_fan: dict[str, bool] = {}
    for s in steps:
        sk = s["key"]
        ns = sorted(by_step.get(sk, []), key=lambda n: n.get("created_at", ""))
        k = len(ns)
        # a diamond emerges only once a fan actually HAS nodes (no empty silhouettes)
        is_fan[sk] = k > 1 or (s.get("is_fan") and k >= 1)
        for i, n in enumerate(ns):
            pos[n["study_id"]] = (col_x[sk], AXIS + (i - (k - 1) / 2.0) * ROWH)
        fan_half[sk] = (((k - 1) / 2.0) * ROWH + 64) if k else 64
    maxdepth = max(depth.values(), default=0)
    extra_x, j = X0 + (maxdepth + 1) * COLW, 0
    for n in graph["nodes"]:
        if n["study_id"] not in pos:
            pos[n["study_id"]] = (extra_x, AXIS + j * ROWH); j += 1
    # Faint silhouette per fan step = the CONVEX HULL of the fan's own nodes plus its bracketing
    # waist nodes (the single-node steps it consumes / that consume it). This is purely structural:
    # it becomes a diamond when a fan sits between two waists, a wedge for a root/terminal fan, and a
    # correct polygon for branches — it never fabricates a "diamond" where the DAG isn't diamond-shaped.
    consumers: dict[str, list[str]] = {s["key"]: [] for s in steps}
    for s in steps:
        for c in s.get("consumes", []):
            consumers.setdefault(c, []).append(s["key"])
    diamonds = []
    for s in steps:
        sk = s["key"]
        if not is_fan.get(sk):
            continue
        node_ids = [n["study_id"] for n in by_step.get(sk, [])]
        if not node_ids:
            continue
        anchors: list[str] = []
        for c in s.get("consumes", []):                       # bracket: upstream WAIST steps
            if not is_fan.get(c):
                anchors += [n["study_id"] for n in by_step.get(c, [])]
        for o in consumers.get(sk, []):                       # bracket: downstream WAIST steps
            if not is_fan.get(o):
                anchors += [n["study_id"] for n in by_step.get(o, [])]
        pts = []
        for sid in node_ids + anchors:
            x, y = pos[sid]
            pts += [(x, y), (x + _NW, y), (x, y + _NH), (x + _NW, y + _NH)]
        hull = _convex_hull(pts)
        if len(hull) >= 3:
            diamonds.append(_expand_hull(hull, 18))

    def _match(name: str, step_key: str):
        cands = by_step.get(step_key, [])
        nw = set(re.findall(r"\w+", name.lower())) - {"lo", "fi", "mid", "der", "die", "das", "idee", "·"}
        best, score = None, 0
        for n in cands:
            sc = len(nw & set(re.findall(r"\w+", n.get("title", "").lower())))
            if sc > score:
                best, score = n, sc
        return best or (cands[0] if cands else None)

    # build steps (declare produces.artifact_type) and the steps that consume each artifact tag
    build_steps = [s for s in steps if (s.get("produces") or {}).get("artifact_type")]
    PW = 200
    proto_pos, proto_edges, used_y = {}, [], {}
    for pr in (graph.get("prototypes") or []):
        ptags = _proto_tags(pr)
        # the producing step: artifact_type matches, disambiguated by a shared discriminator tag
        bs = None
        for s in build_steps:
            prod = s["produces"]
            if prod.get("artifact_type") in ptags:
                disc = set(prod.get("more_tags") or [])
                if not disc or (disc & ptags):
                    bs = s; break
        if bs is None and build_steps:
            bs = build_steps[0]
        if bs is None:
            continue
        bk = bs["key"]
        outs = consumers.get(bk, [])
        nxt = outs[0] if outs else bk
        src = _match(pr.get("name", ""), bk)
        cx = (col_x[bk] + _NW + col_x[nxt]) / 2 - PW / 2
        cy2 = pos[src["study_id"]][1] if src else AXIS
        while round(cy2) in used_y.get(round(cx), set()):
            cy2 += 70
        used_y.setdefault(round(cx), set()).add(round(cy2))
        proto_pos[pr["id"]] = (cx, cy2)
        if src:
            proto_edges.append((src["study_id"], pr["id"], False))   # idea → artifact (solid)
        # tested-at: the nearest downstream decide step requiring a session of one of this artifact's tags
        test_step = None
        for s in sorted(steps, key=lambda s: depth[s["key"]]):
            if depth[s["key"]] <= depth[bk]:
                continue
            req = s.get("requires") or {}
            need = set(req.get("session_of_tags") or []) | set(req.get("artifact_tags") or [])
            if need & ptags and s.get("convergence_node"):
                test_step = s; break
        if test_step:
            proto_edges.append((pr["id"], test_step["convergence_node"], True))  # artifact → tested-at (dashed)
    return {"pos": pos, "diamonds": diamonds, "proto_pos": proto_pos, "proto_edges": proto_edges, "proto_w": PW}


def _graph_interactive(graph: dict) -> str:
    """Interactive, drag-and-drop graph (vanilla JS/SVG, no deps): drag nodes, pan the
    background, scroll to zoom; click a node to open its synthesis."""
    nodes = graph["nodes"]
    if not nodes:
        return f'<p class="muted">{_esc(t("no_synthesis"))}</p>'
    vocab = graph["project"].get("themes", [])
    ml = _methodology_layout(graph)
    pos = ml["pos"] if ml else _graph_layout(graph)
    diamonds = ml["diamonds"] if ml else []
    # If an idea has a prototype that feeds the convergence, route THROUGH the prototype:
    # suppress the idea's direct edge to that convergence so there's one clear path.
    suppress = set()
    if ml:
        src_of, conv_of = {}, {}
        for a, b, dashed in ml.get("proto_edges", []):
            (conv_of if dashed else src_of).__setitem__(a, b)  # dashed: proto→conv; solid: idea→proto
        for proto, conv in conv_of.items():
            idea = next((s for s, pr in src_of.items() if pr == proto), None)
            if idea:
                suppress.add((idea, conv))
    jnodes = []
    for n in nodes:
        tags = n.get("theme_tags", [])
        x, y = pos[n["study_id"]]
        sent = max(n.get("sentiment", {}).items(), key=lambda kv: kv[1])[0] if n.get("sentiment") else "—"
        if n.get("kind"):                         # heterogeneous evidence node (plan graph)
            sub = f'{n.get("kind_label", "")} · ' + (", ".join(t for t in tags if t != n["kind"])[:48] or "—")
            color = n.get("color") or "#9aa0a6"
            href = n.get("href") or ""
        else:                                     # legacy synthesis node
            sub = f'{n.get("council_count", 0)} {t("councils")} · {sent} · ' + (", ".join(tags[:3]) or "—")
            color = _theme_color(tags[0], vocab) if tags else "#9aa0a6"
            href = f'/syntheses/{n["study_id"]}'
        jnodes.append({"id": n["study_id"], "x": x, "y": y, "tags": tags,
                       "label": n["title"][:38] + ("…" if len(n["title"]) > 38 else ""),
                       "sub": sub, "color": color, "href": href})
    _colorlist = list(_EDGE_COLORS.values())
    jedges = []
    for e in graph["edges"]:
        if (e["from_study"], e["to_study"]) in suppress:
            continue  # routed through the prototype instead
        if e["from_study"] in pos and e["to_study"] in pos:
            col = _EDGE_COLORS.get(e["type"], "#9aa0a6")
            jedges.append({"from": e["from_study"], "to": e["to_study"], "color": col, "type": e["type"],
                           "mid": _colorlist.index(col) if col in _colorlist else 0})
    # Artifact nodes (placed in their build step) + dashed "tested-at" edges. Every label, glyph
    # and color is resolved from DATA (the artifact's type/tags + presentation hints) — nothing
    # methodology-specific is hardcoded here.
    if ml:
        ppos = ml.get("proto_pos", {})
        pw = ml.get("proto_w", 200)
        acolor: dict[str, str] = {}
        for pr in (graph.get("prototypes") or []):
            if pr["id"] not in ppos:
                continue
            x, y = ppos[pr["id"]]
            ap = _artifact_present(pr)
            acolor[pr["id"]] = ap["color"]
            prefix = (ap["glyph"] + " ") if ap["glyph"] else ""
            sub = f'{ap["disc"]} · {ap["label"]} ↗' if ap["disc"] else f'{ap["label"]} ↗'
            jnodes.append({"id": pr["id"], "x": x, "y": y, "tags": [], "w": pw, "h": 46,
                           "label": (prefix + pr["name"])[:30] + ("…" if len(pr["name"]) > 28 else ""),
                           "sub": sub, "color": ap["color"],
                           "href": f'/prototypes/{pr["slug"]}', "proto": True})
        for a, b, dashed in ml.get("proto_edges", []):
            col = acolor.get(a) or acolor.get(b) or "#9aa0a6"
            jedges.append({"from": a, "to": b, "color": col, "type": "artifact", "mid": 0, "dashed": bool(dashed)})
    # Bump _LAYOUT_VERSION whenever the layout algorithm changes → stale saved drags are dropped.
    data = json.dumps({"nodes": jnodes, "edges": jedges, "diamonds": diamonds,
                       "key": graph["project"].get("id", "x"), "lv": _LAYOUT_VERSION}, ensure_ascii=False)
    de = _lang() == "de"
    hint = ("Ziehen · Hintergrund schieben · Pinch / ⌘+Scroll = Zoom · F = einpassen"
            if de else "drag · pan background · pinch / ⌘+scroll to zoom · F to fit")
    fit_t = "Einpassen (F)" if de else "Fit to view (F)"
    reset_t = "Layout zurücksetzen (R)" if de else "Reset layout (R)"
    zin_t = "Zoom in (+)"
    zout_t = "Zoom out (−)"
    # The canvas fills its container (CSS height:100%); this fallback only matters
    # if rendered outside the full-bleed project layout.
    maxy = max((y for _x, y in pos.values()), default=0)
    height = max(360, int(maxy) + 64 + 48)
    return (
        '<div class="rgwrap">'
        f'<svg id="rg" width="100%" height="{height}"><defs>'
        + "".join(f'<marker id="rgah-{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                  f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
                  for i, c in enumerate(_EDGE_COLORS.values()))
        + '<pattern id="rggrid" width="26" height="26" patternUnits="userSpaceOnUse">'
          '<circle cx="1.2" cy="1.2" r="1.1" fill="var(--line-2)"/></pattern>'
        + '</defs>'
        + '<rect id="rgbg" x="0" y="0" width="100%" height="100%" fill="url(#rggrid)"/>'
        + '<g id="rgroot"><g id="rgdia"></g><g id="rgedges"></g><g id="rgnodes"></g></g></svg>'
        + f'<div class="rghint">{hint}</div>'
        + '<div class="rgctrls">'
          f'<div class="rgzl" id="rgzl">100%</div>'
          f'<button class="rgbtn" data-act="zin" title="{zin_t}">+</button>'
          f'<button class="rgbtn" data-act="zout" title="{zout_t}">−</button>'
          f'<button class="rgbtn" data-act="fit" title="{fit_t}">⤢</button>'
          f'<button class="rgbtn" data-act="reset" title="{reset_t}">↺</button>'
          '</div>'
        + '<svg class="rgmini" id="rgmini" viewBox="0 0 172 118" preserveAspectRatio="none">'
          '<g id="rgmnodes"></g><rect id="rgmvp"></rect></svg>'
        + '</div>'
        f'<script type="application/json" id="rgdata">{data}</script>{_RGRAPH_JS}')


def _graph_svg(graph: dict) -> str:
    """Read-only SVG of the project graph: study nodes laid out in build order
    (top→bottom), typed edges as colored right-side arcs. Nodes link to the synthesis."""
    nodes = graph["nodes"]
    if not nodes:
        return f'<p class="muted">{_esc(t("no_synthesis"))}</p>'
    vocab = graph["project"].get("themes", [])
    idx = {n["study_id"]: i for i, n in enumerate(nodes)}
    NW, NH, X0, ROW = 380, 60, 24, 92
    XR = X0 + NW
    H = 24 + len(nodes) * ROW
    W = XR + 120
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" '
             f'xmlns="http://www.w3.org/2000/svg" font-family="inherit">',
             '<defs>']
    for typ, col in _EDGE_COLORS.items():
        parts.append(f'<marker id="ah-{typ}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                     f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{col}"/></marker>')
    parts.append('</defs>')
    # edges (drawn first, behind nodes)
    for e in graph["edges"]:
        if e["from_study"] not in idx or e["to_study"] not in idx:
            continue
        fi, ti = idx[e["from_study"]], idx[e["to_study"]]
        col = _EDGE_COLORS.get(e["type"], "#9aa0a6")
        y1 = 24 + fi * ROW + NH / 2
        y2 = 24 + ti * ROW + NH / 2
        bulge = XR + 24 + 10 * abs(ti - fi)
        parts.append(f'<path d="M{XR} {y1:.0f} C {bulge:.0f} {y1:.0f}, {bulge:.0f} {y2:.0f}, {XR} {y2:.0f}" '
                     f'fill="none" stroke="{col}" stroke-width="1.6" marker-end="url(#ah-{e["type"]})" opacity="0.85"/>')
    # nodes
    for i, n in enumerate(nodes):
        y = 24 + i * ROW
        tags = n.get("theme_tags", [])
        bar = _theme_color(tags[0], vocab) if tags else "#c9cdd6"
        sent = max(n.get("sentiment", {}).items(), key=lambda kv: kv[1])[0] if n.get("sentiment") else "—"
        title = _esc(n["title"][:46] + ("…" if len(n["title"]) > 46 else ""))
        sub = _esc(f'{n.get("council_count", 0)} councils · {sent} · ' + (", ".join(tags[:3]) or "—"))
        parts.append(
            f'<a href="/syntheses/{_esc(n["study_id"])}">'
            f'<rect x="{X0}" y="{y}" width="{NW}" height="{NH}" rx="9" fill="var(--panel)" stroke="var(--line)"/>'
            f'<rect x="{X0}" y="{y}" width="5" height="{NH}" rx="2.5" fill="{bar}"/>'
            f'<text x="{X0 + 16}" y="{y + 24}" font-size="13.5" font-weight="600" fill="var(--ink)">{title}</text>'
            f'<text x="{X0 + 16}" y="{y + 43}" font-size="11.5" fill="var(--muted)">{sub}</text>'
            f'</a>')
    parts.append('</svg>')
    return "".join(parts)


def _pills(items: list[str]) -> str:
    return "".join(f'<span class="pill">{_esc(item)}</span>' for item in items)


def _md(text: str) -> str:
    if not text:
        return ""

    def fmt(s: str) -> str:
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _esc(s))

    def _cells(row: str) -> list[str]:
        r = row.strip()
        if r.startswith("|"): r = r[1:]
        if r.endswith("|"): r = r[:-1]
        return [c.strip() for c in r.split("|")]

    lines = text.split("\n")
    n = len(lines)
    out: list[str] = []
    in_ul = False
    i = 0
    while i < n:
        raw = lines[i]
        line = raw.rstrip(); stripped = line.lstrip()
        # GitHub-style pipe table: header row, then a |---|---| separator row
        if stripped.startswith("|") and i + 1 < n:
            sep = lines[i + 1].strip()
            if sep.startswith("|") and "-" in sep and not set(sep) - set("|:- "):
                if in_ul:
                    out.append("</ul>"); in_ul = False
                header = _cells(stripped)
                j = i + 2
                rows = []
                while j < n and lines[j].strip().startswith("|"):
                    rows.append(_cells(lines[j])); j += 1
                th = "".join(f"<th>{fmt(c)}</th>" for c in header)
                trs = "".join("<tr>" + "".join(f"<td>{fmt(c)}</td>" for c in r) + "</tr>" for r in rows)
                out.append(f'<table class="mdtable"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>')
                i = j; continue
        if not stripped:
            if in_ul:
                out.append("</ul>"); in_ul = False
            i += 1; continue
        if stripped.startswith(("- ", "* ")):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{fmt(stripped[2:])}</li>"); i += 1; continue
        if in_ul:
            out.append("</ul>"); in_ul = False
        if line.startswith("### "):
            out.append(f"<h4>{fmt(line[4:])}</h4>")
        elif line.startswith("## "):
            out.append(f"<h3>{fmt(line[3:])}</h3>")
        elif line.startswith("# "):
            out.append(f"<h3>{fmt(line[2:])}</h3>")
        else:
            out.append(f"<p>{fmt(line)}</p>")
        i += 1
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def _srcchips(s: str) -> str:
    return re.sub(r"\[(C\d[^\]]*)\]", r'<span class="srcchip">\1</span>', s)


def _rec_row(text: str) -> str:
    m = re.match(r"\s*\[?PRIO\s*(\d+)\]?\s*[—:\-]\s*(.*)", text, re.S)
    if m:
        n = int(m.group(1)); body = m.group(2)
        badge = f'<span class="prio prio-{min(n, 5)}">PRIO {n}</span>'
    else:
        body = text; badge = '<span class="prio prio-5">•</span>'
    return f'<div class="rec">{badge}<div>{_srcchips(_esc(body))}</div></div>'


def _rec_item(x) -> tuple:
    if isinstance(x, dict):
        return str(x.get("text", "")), x.get("aufwand"), x.get("nutzen")
    return str(x), None, None


def _rec_row_n(i: int, text: str, a, n) -> str:
    ax = f'<span class="axchip">{t("effort_value", a=a, n=n)}</span>' if (a and n) else ""
    return f'<div class="rec" id="rec-{i}"><span class="recnum">{i}</span><div>{_srcchips(_esc(text))}{ax}</div></div>'


_EI_LEV = {"g": ("var(--green)", "ei_high_leverage"), "a": ("var(--accent)", "ei_worthwhile"),
           "m": ("var(--amber)", "ei_neutral"), "r": ("var(--red)", "ei_critical")}
_EI_OFFSETS = {
    1: [(0, 0)], 2: [(-17, 0), (17, 0)], 3: [(0, -18), (-17, 13), (17, 13)],
    4: [(-16, -16), (16, -16), (-16, 16), (16, 16)],
    5: [(0, -20), (-19, -5), (19, -5), (-12, 18), (12, 18)],
    6: [(0, -21), (18, -11), (18, 11), (0, 21), (-18, 11), (-18, -11)],
}


def _effort_impact(recs: list) -> str:
    """recs: [(text, aufwand, nutzen)] (1-based order = label). HTML Aufwand×Nutzen matrix
    with hover popovers — no list needed. Returns '' when nothing is scored."""
    scored = [(i, txt, a, n) for i, (txt, a, n) in enumerate(recs, 1) if a and n]
    if not scored:
        return ""
    W, H = 560, 420
    padL, padR, padT, padB = 50, 24, 22, 46
    def X(a): return padL + (a - 1) / 4 * (W - padL - padR)
    def Y(n): return (H - padB) - (n - 1) / 4 * (H - padT - padB)
    def lev(a, n):
        d = n - a
        return "g" if d >= 2 else "a" if d >= 1 else "r" if d <= -1 else "m"
    mx, my = X(3), Y(3)
    q = 'font-size="11" fill="var(--muted)" opacity="0.85"'
    bg = [
        f'<rect x="{padL}" y="{padT}" width="{mx-padL:.0f}" height="{my-padT:.0f}" fill="var(--green)" opacity="0.06"/>',
        f'<line x1="{mx:.0f}" y1="{padT}" x2="{mx:.0f}" y2="{H-padB}" stroke="var(--line)" stroke-dasharray="3 4"/>',
        f'<line x1="{padL}" y1="{my:.0f}" x2="{W-padR}" y2="{my:.0f}" stroke="var(--line)" stroke-dasharray="3 4"/>',
        f'<line x1="{padL}" y1="{padT}" x2="{padL}" y2="{H-padB}" stroke="var(--line)"/>',
        f'<line x1="{padL}" y1="{H-padB}" x2="{W-padR}" y2="{H-padB}" stroke="var(--line)"/>',
        f'<text x="{padL+8}" y="{padT+15}" {q}>{t("ei_quick_wins")}</text>',
        f'<text x="{W-padR-6}" y="{padT+15}" text-anchor="end" {q}>{t("ei_big_bets")}</text>',
        f'<text x="{padL+8}" y="{H-padB-9}" {q}>{t("ei_fill_ins")}</text>',
        f'<text x="{W-padR-6}" y="{H-padB-9}" text-anchor="end" {q}>{t("ei_time_sinks")}</text>',
        f'<text x="{(padL+W-padR)/2:.0f}" y="{H-9}" text-anchor="middle" font-size="12" fill="var(--ink)">{t("ei_effort_axis")}</text>',
        f'<text transform="translate(15,{(padT+H-padB)/2:.0f}) rotate(-90)" text-anchor="middle" font-size="12" fill="var(--ink)">{t("ei_value_axis")}</text>',
    ]
    svg = f'<svg class="ei-bg" viewBox="0 0 {W} {H}" aria-hidden="true">{"".join(bg)}</svg>'
    groups: dict = {}
    for it in scored:
        groups.setdefault((it[2], it[3]), []).append(it)
    dots = []
    for (a, n), items in groups.items():
        offs = _EI_OFFSETS.get(len(items), [(0, 0)] * len(items))
        cx, cy = X(a), Y(n)
        for off, (i, txt, a2, n2) in zip(offs, items):
            color, levkey = _EI_LEV[lev(a2, n2)]
            levlabel = t(levkey)
            lp = (cx + off[0]) / W * 100
            tp = (cy + off[1]) / H * 100
            cls = "ei-dot"
            if tp <= 24:
                cls += " below"
            if lp >= 70:
                cls += " algn-r"
            elif lp <= 24:
                cls += " algn-l"
            pop = (f'<span class="ei-pop"><span class="ei-pop-h" style="color:{color}">#{i} · {levlabel}</span>'
                   f'<span class="ei-pop-t">{_srcchips(_esc(txt))}</span>'
                   f'<span class="ei-pop-m">{t("effort_value", a=a2, n=n2)}</span></span>')
            dots.append(f'<span class="{cls}" tabindex="0" style="left:{lp:.2f}%;top:{tp:.2f}%;--c:{color}">'
                        f'<span class="ei-num">{i}</span>{pop}</span>')
    leg = ('<div class="ei-leg">'
           f'<span><i style="background:var(--green)"></i>{t("ei_high_leverage")}</span>'
           f'<span><i style="background:var(--accent)"></i>{t("ei_worthwhile")}</span>'
           f'<span><i style="background:var(--amber)"></i>{t("ei_neutral")}</span>'
           f'<span><i style="background:var(--red)"></i>{t("ei_critical")}</span></div>')
    return f'<div class="ei-wrap"><div class="ei-plot">{svg}{"".join(dots)}</div>{leg}</div>'


def _doc(main: str, toc: str = "", rail: str = "") -> str:
    cls = "d3" if (toc and rail) else ("d2" if rail else "d1")
    toc_html = f'<div class="toc">{toc}</div>' if toc else ""
    rail_html = f'<aside class="rail">{rail}</aside>' if rail else ""
    return f'<div class="page"><div class="doc {cls}">{toc_html}<div class="doc-main">{main}</div>{rail_html}</div></div>'


# ----------------------------- chart primitives ----------------------------- #
# Vanilla inline charts (CSS/conic-gradient/SVG) — no build step, dark-mode safe.
_VOTE_ORDER = ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]
_VOTE_COLOR = {"SUPPORT": "var(--green)", "MAYBE": "var(--amber)", "ABSTAIN": "var(--muted)", "OPPOSE": "var(--red)"}


def _vote_label(k: str) -> str:
    return t("vote_" + k.lower())


def _stacked(parts: list[tuple], thin: bool = False) -> str:
    """parts: [(value, color, label)]. Renders a single horizontal stacked bar."""
    total = sum(v for v, _, _ in parts) or 1
    segs = "".join(f'<i style="width:{v / total * 100:.3f}%;background:{c}" title="{_esc(lbl)}: {v}"></i>'
                   for v, c, lbl in parts if v)
    return f'<div class="stacked{" thin" if thin else ""}">{segs}</div>'


def _legend(parts: list[tuple]) -> str:
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{c}"></i>{_esc(lbl)} {v}</span>' for v, c, lbl in parts) + "</div>"


def _donut(parts: list[tuple], size: int = 118) -> str:
    total = sum(v for v, _, _ in parts) or 1
    stops, acc = [], 0.0
    for v, c, _ in parts:
        if not v:
            continue
        start = acc / total * 100; acc += v; end = acc / total * 100
        stops.append(f"{c} {start:.3f}% {end:.3f}%")
    grad = "conic-gradient(" + ",".join(stops or ["var(--line-2) 0 100%"]) + ")"
    return f'<div class="donut" style="--g:{grad};width:{size}px;height:{size}px"></div>'


def _hbars(rows: list[tuple], maxv: int | None = None) -> str:
    """rows: [(label, value, color)]. Horizontal bar chart."""
    mx = maxv or max((v for _, v, _ in rows), default=0) or 1
    return "".join(
        f'<div class="brow"><span class="blab" title="{_esc(lbl)}">{_esc(lbl)}</span>'
        f'<span class="btrack"><i style="width:{v / mx * 100:.2f}%;background:{c}"></i></span>'
        f'<span class="bval">{v}</span></div>' for lbl, v, c in rows)


def _area(points: list[tuple], w: int = 560, h: int = 140) -> str:
    """points: [(label, value)]. Area + line chart (SVG, viewBox-scaled)."""
    if not points:
        return f'<p class="muted small">{t("no_data")}</p>'
    n = len(points); mx = max(v for _, v in points) or 1
    pad = 6
    def x(i): return pad + (i * (w - 2 * pad) / (n - 1 if n > 1 else 1))
    def y(v): return h - pad - (v / mx * (h - 2 * pad))
    pts = [(x(i), y(v)) for i, (_, v) in enumerate(points)]
    line = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    fill = f"M{pts[0][0]:.1f},{h - pad} L" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + f" L{pts[-1][0]:.1f},{h - pad} Z"
    dots = "".join(f'<circle class="dot" cx="{px:.1f}" cy="{py:.1f}" r="2"></circle>' for px, py in pts)
    first, last = points[0][0], points[-1][0]
    return (f'<div class="area"><svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<path class="fl" d="{fill}"></path><path class="ln" d="{line}"></path>{dots}</svg></div>'
            f'<div class="axis"><span>{_esc(first)}</span><span>{_esc(last)}</span></div>')


def _stance_bucket(s: str) -> tuple[str, str]:
    """Classify a free-text stance into (label, color) for distribution charts."""
    s = (s or "").lower()
    if any(k in s for k in ["begeist", "positiv", "stark", "support", "befürwort"]):
        return (t("stance_positive"), "var(--green)")
    if any(k in s for k in ["skept", "ableh", "oppose", "negativ", "kaum", "gar nicht"]):
        return (t("stance_skeptical"), "var(--red)")
    if any(k in s for k in ["neutral", "abstain", "enthalt"]):
        return (t("stance_neutral"), "var(--muted)")
    if any(k in s for k in ["bedingt", "maybe", "teilweise", "passt", "tangiert", "hebel"]):
        return (t("stance_conditional"), "var(--amber)")
    return (t("stance_other"), "var(--accent)")


# --------------------- contextual analytics (council / synthesis) --------------------- #
# Charts live ON the council and the synthesis, computed from that scope's sessions.
def _vote_parts(sessions: list[dict]) -> tuple[Counter, list[tuple]]:
    tot: Counter = Counter()
    for s in sessions:
        for v in s.get("votes", []):
            tot[v.get("vote")] += 1
    return tot, [(tot.get(k, 0), _VOTE_COLOR[k], _vote_label(k)) for k in _VOTE_ORDER]


def _overview_html(parts: list[tuple]) -> str:
    return (f'<div class="dnrow">{_donut(parts)}<div style="flex:1">'
            f'{_stacked(parts)}{_legend(parts)}</div></div>')


def _per_council_html(sessions: list[dict]) -> str:
    rows = []
    for s in sorted(sessions, key=lambda x: x.get("created_at", "")):
        _, parts = _vote_parts([s])
        n = len(s.get("persona_ids", []))
        rows.append(
            f'<a class="crow" href="/councils/{_esc(s["id"])}"><span class="ct" title="{_esc(s["prompt"])}">{_esc(s["prompt"])}</span>'
            f'{_stacked(parts, thin=True)}<span class="cn">{n} P · {_esc(s.get("created_at", "")[:10])}</span></a>'
        )
    return "".join(rows)


def _personas_by_sentiment_html(store: Store, sessions: list[dict]) -> str:
    pv: dict = defaultdict(Counter)
    for s in sessions:
        for v in s.get("votes", []):
            pv[v.get("persona_id")][v.get("vote")] += 1
    if not pv:
        return ""
    personas = {p["id"]: p for p in services.list_personas(store=store)}
    data = []
    for pid, cnt in pv.items():
        n = sum(cnt.values()) or 1
        score = (cnt.get("SUPPORT", 0) - cnt.get("OPPOSE", 0) + 0.4 * cnt.get("MAYBE", 0)) / n
        data.append((pid, cnt, score))
    data.sort(key=lambda x: x[2], reverse=True)
    rows = []
    for pid, cnt, score in data:
        p = personas.get(pid)
        name = p["display_name"] if p else pid
        av = _avatar(p, 22) if p else ""
        _, parts = (None, [(cnt.get(k, 0), _VOTE_COLOR[k], _vote_label(k)) for k in _VOTE_ORDER])
        pct = round(score * 100)
        col = _stance_color("positiv" if pct >= 33 else "skept" if pct < 0 else "bedingt")
        rows.append(
            f'<div class="prow"><a class="pn" href="/personas/{_esc(pid)}">{av}<span>{_esc(name)}</span></a>'
            f'{_stacked(parts, thin=True)}<span class="ps" style="color:{col}">{pct:+d}</span></div>'
        )
    return "".join(rows)


def _stance_dist_html(sessions: list[dict]) -> str:
    sb: Counter = Counter(); colors: dict = {}
    for s in sessions:
        for t in s.get("turns", []):
            lbl, col = _stance_bucket(t.get("stance"))
            sb[lbl] += 1; colors[lbl] = col
    rows = [(lbl, v, colors[lbl]) for lbl, v in sb.most_common()]
    return _hbars(rows) if rows else ""


def _sentiment_section(store: Store, sessions: list[dict], sid: str = "sentiment",
                       title: str | None = None, per_council: bool = False) -> str | None:
    """Reusable sentiment analytics block, embedded ON a council or synthesis."""
    if title is None:
        title = t("sentiment_block")
    sessions = [s for s in sessions if s]
    tot, parts = _vote_parts(sessions)
    nvotes = sum(v for v, _, _ in parts)
    has_turns = any(s.get("turns") for s in sessions)
    if not nvotes and not has_turns:
        return None
    scope = t("sentiment_scope_chain") if per_council else t("sentiment_scope_session")
    blocks = [f'<p class="ihint">{t("sentiment_intro", scope=scope)}</p>']
    if nvotes:
        blocks.append(_overview_html(parts))
    if per_council and len(sessions) > 1:
        pc = _per_council_html(sessions)
        if pc:
            blocks.append(f'<p class="ihint" style="margin-top:18px">{t("per_council")}</p>' + pc)
    pbs = _personas_by_sentiment_html(store, sessions)
    if pbs:
        blocks.append(f'<p class="ihint" style="margin-top:18px">{t("personas_by_sentiment")}</p>' + pbs)
    sd = _stance_dist_html(sessions)
    if sd:
        blocks.append(f'<p class="ihint" style="margin-top:18px">{t("stance_of_contributions")}</p>' + sd)
    return f'<div class="sec" id="{_esc(sid)}"><h2>{_esc(title)}</h2>' + "".join(blocks) + "</div>"


# --------------------------- voices / Stimmen panel --------------------------- #
_SENT_COLOR = {"positiv": "var(--green)", "bedingt": "var(--amber)", "neutral": "var(--muted)",
               "skeptisch": "var(--skep)", "ablehnend": "var(--red)"}
_SENT_ORDER = ["positiv", "bedingt", "neutral", "skeptisch", "ablehnend"]
_REL_ORDER = ["stark", "teilweise", "kaum", "irrelevant"]
_REL_LEVEL = {"stark": 4, "teilweise": 2, "kaum": 1, "irrelevant": 0}


def _sent_color(s: str) -> str:
    return _SENT_COLOR.get(s, "var(--muted)")


def _relbar(rel: str) -> str:
    lvl = _REL_LEVEL.get(rel, 2)
    ticks = "".join(f'<i class="{"on" if i < lvl else ""}"></i>' for i in range(4))
    return f'<span class="relbar" title="{_esc(t("relevance_tooltip", rel=rel))}">{ticks}</span>'


VOICES_JS = """
<script>
(function(){
  var root=document.getElementById('voices'); if(!root) return;
  var rows=[].slice.call(root.querySelectorAll('.vrow'));
  var chips=[].slice.call(root.querySelectorAll('.vchip'));
  var search=root.querySelector('.vsearch'), sortSel=root.querySelector('.vsort');
  var dist=root.querySelector('.vdist'), count=root.querySelector('.vcount'), box=root.querySelector('.vrows');
  var SENT=['positiv','bedingt','neutral','skeptisch','ablehnend'], REL=['stark','teilweise','kaum','irrelevant'];
  var SC={positiv:'var(--green)',bedingt:'var(--amber)',neutral:'var(--muted)',skeptisch:'var(--skep)',ablehnend:'var(--red)'};
  var RC={stark:'var(--accent)',teilweise:'var(--accent)',kaum:'var(--muted)',irrelevant:'var(--line)'};
  function active(f){ return chips.filter(function(c){return c.dataset.facet===f && c.classList.contains('on');}).map(function(c){return c.dataset.val;}); }
  function ok(r){ var fs=['sentiment','relevance','segment'];
    for(var i=0;i<fs.length;i++){ var a=active(fs[i]); if(a.length && a.indexOf(r.dataset[fs[i]])<0) return false; }
    var q=(search.value||'').trim().toLowerCase(); if(q && (r.dataset.text||'').indexOf(q)<0) return false; return true; }
  function bar(keys,colors,counts,tot){ return '<span class="stacked thin">'+keys.map(function(k){var v=counts[k]||0; return v?('<i title="'+k+': '+v+'" style="width:'+(v/tot*100)+'%;background:'+colors[k]+'"></i>'):''; }).join('')+'</span>'; }
  function render(){
    var vis=[]; rows.forEach(function(r){var v=ok(r); r.classList.toggle('hide',!v); if(v)vis.push(r);});
    var cs={},cr={}; vis.forEach(function(r){cs[r.dataset.sentiment]=(cs[r.dataset.sentiment]||0)+1; cr[r.dataset.relevance]=(cr[r.dataset.relevance]||0)+1;});
    var tot=vis.length||1;
    dist.innerHTML='<span class="dk">__SENT_LABEL__</span>'+bar(SENT,SC,cs,tot)+'<span class="dk">__REL_LABEL__</span>'+bar(REL,RC,cr,tot);
    count.textContent='__NOFM__'.replace('{n}',vis.length).replace('{m}',rows.length);
    var key=sortSel.value, so={positiv:0,bedingt:1,neutral:2,skeptisch:3,ablehnend:4}, ro={stark:0,teilweise:1,kaum:2,irrelevant:3};
    vis.sort(function(a,b){
      if(key==='name') return (a.dataset.name||'').localeCompare(b.dataset.name||'');
      if(key==='relevance') return (ro[a.dataset.relevance]-ro[b.dataset.relevance])||(a.dataset.name||'').localeCompare(b.dataset.name||'');
      if(key==='shift') return (b.dataset.shift-a.dataset.shift)||(so[a.dataset.sentiment]-so[b.dataset.sentiment]);
      return (so[a.dataset.sentiment]-so[b.dataset.sentiment])||(a.dataset.name||'').localeCompare(b.dataset.name||''); });
    vis.forEach(function(r){box.appendChild(r);});
  }
  chips.forEach(function(c){ c.addEventListener('click',function(){c.classList.toggle('on'); render();}); });
  search.addEventListener('input',render); sortSel.addEventListener('change',render);
  rows.forEach(function(r){ var m=r.querySelector('.vrow-main'); if(!m) return;
    m.addEventListener('click',function(e){ if(e.target.closest('[data-star]'))return; r.classList.toggle('open'); var ex=r.querySelector('.vexp'); if(ex) ex.hidden=!r.classList.contains('open'); }); });
  render();
})();
</script>
"""


def _voices_panel(store: Store, syn: dict) -> str | None:
    voices = syn.get("voices", [])
    if not voices:
        return None
    personas = {p["id"]: p for p in services.list_personas(store=store)}
    segments = sorted({v.get("segment", "") for v in voices if v.get("segment")})

    def chip(facet: str, val: str, color: str | None = None) -> str:
        dot = f'<i style="background:{color}"></i>' if color else ""
        return f'<button class="vchip" data-facet="{facet}" data-val="{_esc(val)}">{_esc(val)}{dot}</button>'

    filt = (f'<div class="fgroup"><span class="flabel">{t("sentiment_label")}</span>'
            + "".join(chip("sentiment", s, _sent_color(s)) for s in _SENT_ORDER) + "</div>"
            + f'<div class="fgroup"><span class="flabel">{t("relevance_label")}</span>'
            + "".join(chip("relevance", r) for r in _REL_ORDER) + "</div>")
    if segments:
        filt += (f'<div class="fgroup"><span class="flabel">{t("segment")}</span>'
                 + "".join(chip("segment", s) for s in segments) + "</div>")
    ph_search = _esc(t("search_arg_name"))
    tools = (f'<div class="vtools"><div class="vfilters">{filt}</div>'
             f'<div class="vtools-right"><input class="vsearch" type="text" placeholder="{ph_search}">'
             f'<select class="vsort"><option value="sentiment">{t("sort_by_sentiment")}</option>'
             f'<option value="relevance">{t("sort_relevance")}</option><option value="name">{t("name_label")}</option>'
             f'<option value="shift">{t("sort_shift_first")}</option></select></div></div>')

    rows = []
    for v in voices:
        pid = v.get("persona_id", "")
        name = v.get("persona_name") or (personas.get(pid, {}) or {}).get("display_name") or pid
        p = personas.get(pid) or {"id": pid, "display_name": name}
        sent = v.get("sentiment", "neutral"); rel = v.get("relevance", "teilweise"); seg = v.get("segment", "")
        sh = v.get("shift")
        has_shift = bool(sh and (sh.get("trigger") or sh.get("to")))
        shbadge = (f'<span class="shiftbadge">{_esc(sh.get("from",""))} → {_esc(sh.get("to",""))}</span>'
                   if has_shift else "")
        segchip = f'<span class="segchip" title="{_esc(seg)}">{_esc(seg)}</span>' if seg else ""
        exp = []
        if has_shift:
            cid = sh.get("council_id", "")
            link = f' <a href="/councils/{_esc(cid)}">{t("to_council")}</a>' if cid else ""
            shift_lbl = _esc(t("shift_label", a=sh.get("from", ""), b=sh.get("to", "")))
            exp.append(f'<div class="vshift"><strong>{shift_lbl}</strong> {_esc(sh.get("trigger",""))}{link}</div>')
        for e in v.get("evidence", []):
            cid = e.get("council_id", "")
            link = f' <a href="/councils/{_esc(cid)}">{t("to_council")}</a>' if cid else ""
            exp.append(f'<div class="vev">„{_esc(e.get("quote",""))}“{link}</div>')
        exp_html = f'<div class="vexp" hidden>{"".join(exp)}</div>' if exp else ""
        text = f'{name} {v.get("key_argument","")} {seg}'.lower()
        rows.append(
            f'<div class="vrow" data-sentiment="{_esc(sent)}" data-relevance="{_esc(rel)}" data-segment="{_esc(seg)}" '
            f'data-name="{_esc(name)}" data-shift="{1 if has_shift else 0}" data-text="{_esc(text)}">'
            f'<div class="vrow-main"><span class="vav">{_avatar(p, 30)}</span>'
            f'<div class="vmeta"><div class="vline1"><b>{_esc(name)}</b>{_label(sent, _sent_color(sent))}{_relbar(rel)}{shbadge}</div>'
            f'<div class="varg">{_esc(v.get("key_argument",""))}</div></div>'
            f'<div class="vright">{segchip}{_star("persona", pid, name, f"/personas/{pid}")}<span class="vchev">▸</span></div>'
            f'</div>{exp_html}</div>'
        )
    js = (VOICES_JS.replace("__SENT_LABEL__", t("sentiment_label"))
          .replace("__REL_LABEL__", t("relevance_label"))
          .replace("__NOFM__", t("voices_n_of_m", n="{n}", m="{m}")))
    return (f'<div class="sec" id="stimmen"><h2>{t("voices_count", n=len(voices))}</h2>'
            f'<p class="ihint">{t("voices_intro")}</p>'
            f'<div class="voices" id="voices">{tools}<div class="vdist"></div><div class="vcount"></div>'
            f'<div class="vrows">{"".join(rows)}</div></div></div>') + js


def _persona_voices_html(store: Store, pid: str) -> str:
    out = []
    for syn in store.list_syntheses():
        for v in syn.get("voices", []):
            if v.get("persona_id") != pid:
                continue
            sent = v.get("sentiment", "neutral")
            sh = v.get("shift")
            shb = (f'<span class="shiftbadge">{_esc(sh.get("from",""))} → {_esc(sh.get("to",""))}</span>'
                   if (sh and (sh.get("trigger") or sh.get("to"))) else "")
            out.append(
                '<div class="vrow"><div class="vrow-main" style="cursor:default"><span></span>'
                f'<div class="vmeta"><div class="vline1"><a href="/syntheses/{_esc(syn["id"])}"><b>{_esc(syn["title"])}</b></a>'
                f'{_label(sent, _sent_color(sent))}{_relbar(v.get("relevance","teilweise"))}{shb}</div>'
                f'<div class="varg" style="white-space:normal">{_esc(v.get("key_argument",""))}</div></div>'
                '<div class="vright"></div></div></div>'
            )
            break
    if not out:
        return ""
    return f'<div class="sec" id="stimmen"><h2>{t("voices_in_analyses")}</h2><div class="vrows">{"".join(out)}</div></div>'


# --------------------------- synthesis report --------------------------- #



def _synthesis_html(store: Store, syn: dict) -> str:
    done = syn.get("status", "done") == "done"
    sec = []  # (id, short_label, html)
    # 1) Executive Summary — large prose, no box
    if syn.get("gesamtbild"):
        question = _esc(syn.get("goal") or syn.get("start_input", ""))
        sec.append(("exec", t("summary"),
            f'<div class="es" id="exec"><p class="qa-q" data-label="{_esc(t("question"))}">{question}</p>'
            f'<div class="eyebrow">{t("answer_exec_summary")}</div>'
            f'<div class="es-prose">{_md(syn["gesamtbild"])}</div></div>'))
    # 2) Councils im Überblick — card per council: tally, takeaway, expand, jump
    cards = []
    for i, cid in enumerate(syn.get("council_ids", []), 1):
        c = store.get_council_session(cid)
        if not c:
            continue
        tally = Counter(v.get("vote") for v in (c.get("votes") or []) if isinstance(v, dict))
        parts = [(tally.get(k, 0), _VOTE_COLOR[k], k) for k in _VOTE_ORDER]
        chips = "".join(_label(f"{tally[k]} {k}", _VOTE_COLOR[k]) for k in _VOTE_ORDER if tally.get(k))
        prompt = c.get("prompt") or cid
        summ = c.get("summary") or ""
        take = _esc(summ[:165] + ("…" if len(summ) > 165 else ""))
        es = c.get("exec_summary") or summ or c.get("proposal") or ""
        cards.append(
            f'<article class="ccard">'
            f'<div class="cc-top"><span class="cc-n">C{i}</span><div class="cc-bar">{_stacked(parts, thin=True)}</div></div>'
            f'<h3 class="cc-title"><a href="/councils/{_esc(cid)}">{_esc(prompt[:74])}</a></h3>'
            f'<p class="cc-take">{take}</p>'
            f'<div class="cc-chips">{chips}</div>'
            f'<details class="cc-more"><summary></summary><div class="cc-es">{_md(es)}</div></details>'
            f'<a class="cc-jump" href="/councils/{_esc(cid)}">{t("jump_into_council")}</a>'
            f'</article>')
    if cards:
        sec.append(("councils", t("councils"),
            f'<div class="block" id="councils"><h2 class="bh">{t("councils_overview")} <span class="cnt">{len(cards)}</span></h2>'
            f'<div class="cgrid">{"".join(cards)}</div></div>'))
    rec_items = [_rec_item(x) for x in syn.get("handlungsempfehlungen", [])]
    chart = _effort_impact(rec_items)
    if chart:
        body = chart  # hover popovers replace the list
    else:
        rows = "".join(_rec_row_n(i, t, a, n) for i, (t, a, n) in enumerate(rec_items, 1)) or '<p class="muted">—</p>'
        body = f'<div class="reclist">{rows}</div>'
    sec.append(("empfehlungen", t("recommendations"),
                f'<div class="block" id="empfehlungen"><h2 class="bh">{t("recommendations")}</h2>{body}</div>'))
    if syn.get("positionierung"):
        sec.append(("positionierung", t("positioning"),
                    f'<div class="block" id="positionierung"><h2 class="bh">{t("positioning")}</h2><div class="es-prose sm">{_md(syn["positionierung"])}</div></div>'))
    # voices — who thinks what & why (filter/sort/shift/evidence)
    panel = _voices_panel(store, syn)
    if panel:
        sec.append(("stimmen", t("voices"), f'<div class="block" id="stimmen">{panel}</div>'))
    else:
        syn_sessions = [store.get_council_session(cid) for cid in syn.get("council_ids", [])]
        sent = _sentiment_section(store, syn_sessions, title=t("sentiment_over_chain"), per_council=True)
        if sent:
            sec.append(("stimmen", t("voices"), f'<div class="block" id="stimmen">{sent}</div>'))
    # supporting analysis
    segs = "".join(
        f'<div class="segrow"><div><strong>{_esc(s.get("segment",""))}</strong><br><span class="muted">{_esc(s.get("why",""))}</span></div>'
        f'{_label(s.get("stance",""), _stance_color(s.get("stance","")))}</div>' for s in syn.get("segmente", [])
    ) or '<p class="muted">—</p>'
    sec.append(("segmente", t("segments"), f'<div class="block" id="segmente"><h2 class="bh">{t("segments")}</h2>{segs}</div>'))
    ps = "".join(f'<div class="psolve">{_srcchips(_esc(x))}</div>' for x in syn.get("pain_solvers", [])) or '<p class="muted">—</p>'
    sec.append(("painsolver", "Pain-Solver", f'<div class="block" id="painsolver"><h2 class="bh">{t("validated_pain_solvers")}</h2>{ps}</div>'))
    if syn.get("offene_fragen"):
        of = "".join(f'<div class="psolve">{_esc(x)}</div>' for x in syn["offene_fragen"])
        sec.append(("offene", t("open_questions"), f'<div class="block" id="offene"><h2 class="bh">{t("open_questions_next_study")}</h2>{of}</div>'))
    # arc (collapsed)
    sec.append(("bogen", t("course"),
                f'<details class="block" id="bogen"><summary class="bh" style="cursor:pointer">{t("arc_course")}</summary><div class="es-prose sm">{_md(_srcchips(syn.get("arc_narrative","")))}</div></details>'))

    # ---- slim meta strip (replaces the old Eigenschaften rail) ----
    cs = Counter(v.get("sentiment", "neutral") for v in syn.get("voices", []))
    smeta = " · ".join(f"{cs[k]} {k}" for k in _SENT_ORDER if cs.get(k))
    mchips = [_label(t("completed") if done else t("running"), "var(--green)" if done else "var(--amber)")]
    mchips.append(f'<span class="mchip">{len(syn.get("council_ids", []))} {t("councils")}</span>')
    if syn.get("iterations"):
        mchips.append(f'<span class="mchip">{syn["iterations"]} {t("iterations")}</span>')
    if smeta:
        mchips.append(f'<span class="mchip">{t("voices_meta", s=_esc(smeta))}</span>')
    mchips.append(f'<span class="mchip">{_esc(syn["created_at"][:10])}</span>')
    head = (f'<header class="syn-head"><h1>{_esc(syn["title"])}</h1>'
            f'<div class="syn-meta">{"".join(mchips)}</div></header>')

    ticks = "".join(f'<a class="tick" href="#{sid}"><span class="tk-label">{_esc(lbl)}</span><span class="tk-bar"></span></a>'
                    for sid, lbl, _ in sec)
    rail = f'<nav class="syn-rail" aria-label="{_esc(t("sections"))}">{ticks}</nav>'
    main = head + "".join(h for _, _, h in sec)
    return _SYN_STYLE + f'<div class="syn-wrap"><div class="syn-main">{main}</div>{rail}</div>' + _SYN_SCRIPT


def create_app():
    load_env()
    try:
        from fastapi import FastAPI, Query
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError("Install web dependencies first: uv sync") from exc

    DATA_DIR.mkdir(exist_ok=True)
    app = FastAPI(title="Persona Council")
    app.mount("/data", StaticFiles(directory="data"), name="data")
    # Serve prototype apps so they can be viewed directly in the inspector (read-only).
    from .config import prototypes_dir as _proto_dir
    _pd = _proto_dir()
    _pd.mkdir(parents=True, exist_ok=True)
    app.mount("/proto-files", StaticFiles(directory=str(_pd), html=True), name="proto-files")

    @app.middleware("http")
    async def _ui_language_middleware(request, call_next):
        """Resolve the UI language per request (?lang= -> cookie -> setting), expose
        it to the render helpers via the contextvar, and persist an explicit choice."""
        lang, persist = _resolve_request_language(
            request.query_params.get("lang"), request.cookies.get("ui_lang"))
        token = _UI_LANG.set(lang)
        try:
            response = await call_next(request)
        finally:
            _UI_LANG.reset(token)
        if persist:
            response.set_cookie("ui_lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
            set_ui_language(lang)
        return response

    # ---------- helpers that need the store ----------
    def _persona_card(p: dict, store: Store) -> str:
        pid = p["id"]
        try:
            proj = services.list_active_projects(pid, store=store)
        except Exception:
            proj = []
        loops = len(store.list_threads(pid, "open"))
        st = services.get_current_state(pid, store=store)
        cur = st.get("current_activity") if st.get("current_activity") != "not simulated yet" else t("not_simulated_yet")
        meta = []
        if proj:
            meta.append(_label(t("n_projects", n=len(proj)), "var(--accent)"))
        if loops:
            meta.append(_label(t("n_open", n=loops), "var(--amber)"))
        return (
            f'<a class="pcard" href="/personas/{_esc(pid)}">'
            f'{_star("persona", pid, p["display_name"], f"/personas/{pid}")}'
            f'<div class="top">{_avatar(p, 40)}<div style="min-width:0"><div class="nm">{_esc(p["display_name"])}</div>'
            f'<div class="ro">{_esc(p["role"]["title"])} · {_esc(p["company_context"]["industry"])}</div></div></div>'
            f'<div class="st">{_esc(cur)}</div><div class="meta">{"".join(meta)}</div></a>'
        )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        # Home is the Projects list (project-centric IA; Overview removed).
        return _projects_page()

    @app.get("/personas", response_class=HTMLResponse)
    def personas_list() -> str:
        store = Store()
        personas = services.list_personas(store=store)
        cards = "".join(_persona_card(p, store) for p in personas) or f'<p class="muted">{t("no_personas")}</p>'
        body = f'<div class="page"><h1 class="h1">{t("personas")}</h1><p class="lead">{t("personas_lead", n=len(personas))}</p><div class="pgrid">{cards}</div></div>'
        return _layout(t("personas"), body, store, crumbs=[(t("personas"), None)], active="personas")

    @app.get("/personas/{persona_id}", response_class=HTMLResponse)
    def persona_detail(persona_id: str, date_value: str | None = Query(default=None, alias="date"), view: str = Query(default="day")) -> str:
        store = Store()
        try:
            data = services.get_persona(persona_id, store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("profile_not_found"), t("persona_runtime_cleared")), store, active="personas")
        p = data["persona"]
        state = services.get_current_state(p["id"], store=store)
        selected_date = date_value or (data["daily_summaries"][-1]["date"] if data["daily_summaries"] else date.today().isoformat())
        view = view if view in {"day", "week", "month", "year"} else "day"
        period = services.get_calendar_period(p["id"], selected_date, view, store)
        avatar = f'<img class="avatar" src="/{_esc(p["avatar"]["path"])}" alt="">' if p.get("avatar") else f'<div>{_avatar(p, 120)}</div>'
        date_links = "".join(
            f'<a class="pill" href="/personas/{_esc(p["id"])}?date={_esc(s["date"])}&view={_esc(view)}">{_esc(s["date"])}</a>'
            for s in data["daily_summaries"][-10:])
        daycount = Counter()
        for e in store.list_experience_events(p["id"]):
            ts = e.get("timestamp") or ""
            if len(ts) >= 10:
                daycount[ts[:10]] += 1
        act_pts = [(d[5:], daycount[d]) for d in sorted(daycount)]
        activity = (f'<div class="sec" id="aktivitaet"><h2>{t("activity_over_time")}</h2>'
                    f'<p class="ihint">{t("activities_per_day", n=sum(daycount.values()))}</p>{_area(act_pts)}</div>'
                    if act_pts else "")
        voices = _persona_voices_html(store, p["id"])
        main = f"""
        <div class="hero"><h1>{_esc(p["display_name"])}</h1><p class="sub">{_esc(p["role"]["title"])} · {_esc(p["company_context"]["industry"])}</p></div>
        <div class="identity"><div>{avatar}</div><div>
          <div class="card"><h3>{t("current_state")}</h3><p><strong>{_esc(state["current_activity"])}</strong></p><p class="muted">{_esc(state["collaboration_mode"])}</p><p class="thought">{_esc(state["current_thought"])}</p></div>
        </div></div>
        {voices}
        {activity}
        <div class="sec" id="ziele"><h2>{t("goals")}</h2>{_pills(p["goals"])}</div>
        <div class="sec" id="pains"><h2>{t("pain_points")}</h2>{_pills([x["issue"] for x in data["pain_points"]] or p["pain_points"])}</div>
        <div class="sec" id="bez"><h2>{t("relationships")}</h2>{''.join(f'<p><strong>{_esc(r["name"])}</strong> <span class="muted">— {_esc(r["type"])}: {_esc(r["friction"])}</span></p>' for r in p["relationships"])}</div>
        <div class="sec" id="cal"><h2>{t("calendar")}</h2><p class="muted">{date_links or t("no_days_yet")}</p>
        {_calendar_tabs(p["id"], selected_date, view)}{_period_calendar_html(p["id"], selected_date, view, period)}</div>
        """
        rail = (f'<h4>{t("properties")}</h4>'
                f'<div class="prop"><span class="k">{t("role")}</span><span class="v">{_esc(p["role"]["title"])}</span></div>'
                f'<div class="prop"><span class="k">{t("industry")}</span><span class="v">{_esc(p["company_context"]["industry"])}</span></div>'
                f'<div class="prop"><span class="k">{t("size")}</span><span class="v">{_esc(p["company_context"].get("size",""))}</span></div>'
                f'<div class="prop"><span class="k">{t("tools")}</span><span class="v">{_pills(p["tools"])}</span></div>'
                f'<div class="prop"><span class="k">{t("memory")}</span><span class="v"><a class="bc-link" href="/personas/{_esc(p["id"])}/memory">{_icon("memory")} {t("open")}</a></span></div>')
        return _layout(p["display_name"], _doc(main, rail=rail), store,
                       crumbs=[(t("personas"), "/personas"), (p["display_name"], None)], active="personas",
                       actions=_star("persona", p["id"], p["display_name"], f'/personas/{p["id"]}'))

    @app.get("/personas/{persona_id}/memory", response_class=HTMLResponse)
    def persona_memory(persona_id: str, as_of: str | None = Query(default=None), q: str | None = Query(default=None)) -> str:
        store = Store()
        pm = store.get_persona(persona_id)
        cr = [(t("personas"), "/personas"), (pm["display_name"] if pm else persona_id, f"/personas/{persona_id}"), (t("memory"), None)]
        return _layout(t("memory"), _memory_html(store, persona_id, as_of, q), store, crumbs=cr, active="personas")

    @app.get("/activities/{activity_id}", response_class=HTMLResponse)
    def activity_detail(activity_id: str) -> str:
        store = Store()
        try:
            data = services.get_activity(activity_id, store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("activity_not_found"), t("runtime_maybe_cleared")), store, active="personas")
        p = data["persona"]; a = data["activity"]
        alone_label = t("alone")
        main = f"""
        <div class="hero"><h1>{_esc(a["task"])}</h1><p class="sub">{_esc(a["timestamp"])} · {_esc(a["event_type"])} · {_esc(a.get("collaboration_mode","unknown"))}</p></div>
        <div class="grid two">
          <div class="card"><h3>{t("what_happened")}</h3><p>{_esc(a.get("what_happened", a["summary"]))}</p></div>
          <div class="card"><h3>{t("thought")}</h3><p class="thought">{_esc(a.get("persona_thought","—"))}</p></div></div>
        <div class="sec"><h2>{t("conversation")}</h2>{''.join(f'<div class="quote"><strong>{_esc(c.get("speaker",""))}</strong><br>{_esc(c.get("text",""))}</div>' for c in a.get("conversation", [])) or f'<p class="muted">{t("none_f")}</p>'}</div>
        <div class="grid"><div class="card"><h3>{t("actions")}</h3>{_pills(a.get("actions_done", [])) or '—'}</div>
          <div class="card"><h3>{t("artifacts")}</h3>{_pills(a.get("artifacts_touched", [])) or '—'}</div>
          <div class="card"><h3>{t("open_loops")}</h3>{_pills(a.get("open_loops", [])) or '—'}</div></div>
        """
        rail = (f'<h4>{t("properties")}</h4>'
                f'<div class="prop"><span class="k">{t("persona")}</span><span class="v"><a class="bc-link" href="/personas/{_esc(p["id"])}">{_esc(p["display_name"])}</a></span></div>'
                f'<div class="prop"><span class="k">{t("tool")}</span><span class="v">{_esc(a["tool"])}</span></div>'
                f'<div class="prop"><span class="k">{t("mood")}</span><span class="v">{_esc(a["impact"]["mood"])}</span></div>'
                f'<div class="prop"><span class="k">{t("participants")}</span><span class="v">{_pills(a.get("participants", []) or [alone_label])}</span></div>'
                f'<div class="prop"><span class="k">{t("decision")}</span><span class="v muted">{_esc(a.get("decision") or "—")}</span></div>')
        return _layout(a["task"], _doc(main, rail=rail), store,
                       crumbs=[(t("personas"), "/personas"), (p["display_name"], f'/personas/{p["id"]}'), (a["task"][:46], None)], active="personas")

    @app.get("/councils", response_class=HTMLResponse)
    def councils() -> str:
        store = Store()
        rows = []
        for c in services.list_councils(store=store):
            v = c["votes"]; tot = max(1, sum(v.values()))
            bar = (f'<span class="votebar" title="SUPPORT {v["SUPPORT"]} · MAYBE {v["MAYBE"]} · OPPOSE {v["OPPOSE"]}">'
                   f'<i style="width:{v["SUPPORT"]/tot*100}%;background:var(--green)"></i>'
                   f'<i style="width:{v["MAYBE"]/tot*100}%;background:var(--amber)"></i>'
                   f'<i style="width:{(v["OPPOSE"]+v["ABSTAIN"])/tot*100}%;background:var(--muted)"></i></span>')
            rows.append(f'<a class="row" href="/councils/{_esc(c["id"])}">{_icon("councils")}'
                        f'<span class="title">{_esc(c["prompt"])}</span>'
                        f'<span class="right">{bar}<span>{c["personas"]} {t("personas")}</span><span>{_esc(c["created_at"][:10])}</span>'
                        f'{_star("council", c["id"], c["prompt"][:60], f"/councils/{c['id']}")}</span></a>')
        rows_html = "".join(rows) or f'<div class="row muted">{t("no_councils")}</div>'
        body = f'<div class="page"><h1 class="h1">{t("councils")}</h1><p class="lead">{t("councils_lead")}</p><div class="rows">{rows_html}</div></div>'
        return _layout(t("councils"), body, store, crumbs=[(t("projects"), "/projects"), (t("councils"), None)], active="projects")

    @app.get("/councils/{session_id}", response_class=HTMLResponse)
    def council_detail(session_id: str) -> str:
        store = Store()
        session = store.get_council_session(session_id)
        if not session:
            return _layout(t("not_found"), _empty_state(t("council_not_found"), t("runtime_maybe_cleared")), store, active="councils")
        voices_detail_h = t("voices_in_detail", n=len(session["turns"]))
        proposal_short_h = t("proposal_short_summary")
        proposal_h = t("proposal"); summary_h = t("summary")
        sentiment_title = t("sentiment_this_council")
        vote_h = t("vote"); personas_h = t("personas"); created_h = t("created")
        councils_crumb = t("councils"); council_title = t("councils")
        turns = []
        for tn in session["turns"]:
            mod = " mod" if (tn.get("speaker") == "Moderator" or tn.get("stance") == "moderation") else ""
            stance = _label(tn["stance"], _stance_color(tn.get("stance", ""))) if tn.get("stance") else ""
            concerns = "".join(f'<p class="muted small">• {_esc(q)}</p>' for q in tn.get("questions_or_pushback", [])[:4])
            mem = "".join(f'<p class="muted small">{_icon("search")} {_esc(m)}</p>' for m in tn.get("memory_used", [])[:3])
            turns.append(f'<div class="turn{mod}"><div class="hd"><b>{_esc(tn["speaker"])}</b> {stance}</div><p>{_esc(tn["content"])}</p>{concerns}{mem}</div>')
        turns_html = '<div style="display:grid;gap:12px">' + "".join(turns) + "</div>"
        exec_html = _md(session.get("exec_summary", "")) or f'<p>{_esc(session["summary"])}</p>'
        sentiment = _sentiment_section(store, [session], title=sentiment_title) or ""
        main = (f'<div class="hero"><h1>{_esc(session["prompt"])}</h1><p class="sub">{_esc(session["selection_reason"])}</p></div>'
                f'<div class="callout"><span class="emj">{_icon("compass")}</span><div>{exec_html}</div></div>'
                f'{sentiment}'
                f'<div class="sec" id="stimmen"><h2>{voices_detail_h}</h2>{turns_html}</div>'
                f'<details class="sec"><summary>{proposal_short_h}</summary><div class="card"><strong>{proposal_h}</strong><p>{_esc(session["proposal"])}</p><strong>{summary_h}</strong><p>{_esc(session["summary"])}</p></div></details>')
        vc = {v: sum(1 for x in session["votes"] if x.get("vote") == v) for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]}
        rail = (f'<h4>{vote_h}</h4>'
                + "".join(f'<div class="prop"><span class="k">{_vote_label(k)}</span><span class="v">{vc[k]}</span></div>' for k in vc)
                + f'<div class="prop"><span class="k">{personas_h}</span><span class="v">{len(session.get("persona_ids", []))}</span></div>'
                + f'<div class="prop"><span class="k">{created_h}</span><span class="v">{_esc(session["created_at"][:10])}</span></div>')
        crumbs = [(t("projects"), "/projects")]
        parent_syn = services.parent_study_of_council(session_id, store)
        if parent_syn:
            proj = services.parent_project_of_study(parent_syn["id"], store)
            if proj:
                crumbs.append((proj["title"], f"/projects/{proj['id']}"))
            crumbs.append((parent_syn["title"], f"/syntheses/{parent_syn['id']}"))
        crumbs.append((session["prompt"][:50], None))
        return _layout(council_title, _doc(main, rail=rail), store,
                       crumbs=crumbs, active="projects",
                       actions=_star("council", session_id, session["prompt"][:60], f"/councils/{session_id}"))

    @app.get("/syntheses", response_class=HTMLResponse)
    def syntheses() -> str:
        store = Store()
        rows = []
        for s in store.list_syntheses():
            done = s.get("status", "done") == "done"
            rows.append(f'<a class="row" href="/syntheses/{_esc(s["id"])}">{_icon("syntheses")}'
                        f'<span class="title">{_esc(s["title"])}</span>'
                        f'<span class="right">{_label(t("done") if done else t("running"), "var(--green)" if done else "var(--amber)")}'
                        f'<span>{len(s.get("council_ids", []))} {t("councils")}</span><span>{_esc(s["created_at"][:10])}</span>'
                        f'{_star("synthesis", s["id"], s["title"], f"/syntheses/{s['id']}")}</span></a>')
        rows_html = "".join(rows) or f'<div class="row muted">{t("no_synthesis")}</div>'
        body = f'<div class="page"><h1 class="h1">{t("syntheses")}</h1><p class="lead">{t("syntheses_lead")}</p><div class="rows">{rows_html}</div></div>'
        return _layout(t("syntheses"), body, store, crumbs=[(t("projects"), "/projects"), (t("syntheses"), None)], active="projects")

    @app.get("/syntheses/{synthesis_id}", response_class=HTMLResponse)
    def synthesis_detail(synthesis_id: str) -> str:
        store = Store()
        syn = store.get_synthesis(synthesis_id)
        if not syn:
            return _layout(t("not_found"), _empty_state(t("synthesis_not_found"), t("runtime_maybe_cleared")), store, active="syntheses")
        actions = (_star("synthesis", synthesis_id, syn["title"], f"/syntheses/{synthesis_id}")
                   + f'<button class="btn" onclick="window.print()">{t("export_pdf")}</button>')
        crumbs = [(t("projects"), "/projects")]
        proj = services.parent_project_of_study(synthesis_id, store)
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((syn["title"], None))
        return _layout(syn["title"], _synthesis_html(store, syn), store,
                       crumbs=crumbs, active="projects", actions=actions)

    @app.get("/projects", response_class=HTMLResponse)
    def projects() -> str:
        return _projects_page()

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(project_id: str) -> str:
        store = Store()
        try:
            graph = services.get_project_graph(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("not_found"), t("runtime_maybe_cleared")), store, active="projects")
        proj = graph["project"]
        # edge legend (shown in the floating open-questions panel)
        used_types = sorted({e["type"] for e in graph["edges"]})
        edge_leg = "".join(
            f'<span class="pill" style="border-color:{_EDGE_COLORS.get(ty, "#9aa0a6")}">{_esc(ty)}</span>'
            for ty in used_types) or f'<span class="muted small">—</span>'
        oqs = [o for o in graph["open_questions"] if o.get("status") == "open"]
        oq_html = "".join(f'<li>{_esc(o["text"])}</li>' for o in oqs[:30]) or f'<li class="muted">—</li>'
        reports = store.list_meta_reports(proj["id"])
        meta_btn = (f'<a class="btn" href="/projects/{_esc(proj["id"])}/meta">{_icon("syntheses")} {t("meta_report")}</a>'
                    if reports else "")
        if services.get_plan(proj["id"], store=store):    # the analyze/act/verify plan view
            meta_btn = f'<a class="btn" href="/projects/{_esc(proj["id"])}/plan">{_icon("projects")} Plan</a>' + meta_btn
        # Linear-style filter: EVERY tag present on a node is a toggleable chip — incl. the
        # methodology's open step tags (capability/role), not just LLM theme tags. No fixed vocab.
        node_tags = []
        for n in graph["nodes"]:
            for tgx in n.get("theme_tags", []):
                if tgx not in node_tags:
                    node_tags.append(tgx)
        vocab_all = list(dict.fromkeys((proj.get("themes") or []) + node_tags))
        chips = "".join(
            f'<button class="rgchip" data-theme="{_esc(th)}" style="--c:{_theme_color(th, vocab_all)}">{_esc(th)}</button>'
            for th in vocab_all)
        left = (f'<span class="ptlabel">{_icon("search")}{t("filter")}</span>{chips}'
                f'<a class="rgclear" style="display:none">{t("clear_filter")}</a>') if chips else ""
        oqbtn = f'<button class="btn" id="oqbtn">{t("legend")} · {t("open_questions_h")} ({len(oqs)})</button>'
        # (No bespoke methodology strip: the graph itself — columns, emergent silhouettes, and the
        # tag filter — conveys the constellation. A linear step strip would mis-imply a sequence.)
        toolbar = f'<div class="ptoolbar">{left}<span class="spacer"></span>{oqbtn}{meta_btn}</div>'
        # Artifact viewer: artifacts + recorded persona sessions (read-only).
        protos = graph.get("prototypes") or []
        proto_html = ""
        if protos:
            rows = []
            for p in protos:
                sess = store.list_prototype_sessions(prototype_id=p["id"])
                run_badge = ('<span class="pill" style="border-color:#3d7b5f">running</span>'
                             + f' <a href="{_esc(p["url"])}" target="_blank">open ↗</a>' if p.get("running") and p.get("url") else "")
                sl = []
                for s in sess[:6]:
                    r = s.get("reaction", {})
                    gv = "✓" if s.get("grounded_verified") else "○"
                    sl.append(f'<li>{_esc(s.get("persona_id",""))}: {_esc(str(r.get("verdict") or r.get("summary","")))[:80]} '
                              f'<span class="muted small">{gv} grounded</span></li>')
                sl_html = ("<ul style='margin:4px 0 0 18px'>" + "".join(sl) + "</ul>") if sl else '<div class="muted small">— keine Sessions —</div>'
                ap = _artifact_present(p)
                pill = ap["disc"] or ap["label"]
                rows.append(f'<div class="strow"><a href="/prototypes/{_esc(p["slug"])}">{_icon("projects")}<b>{_esc(p["name"])}</b></a> '
                            f'<span class="pill">{_esc(pill)}</span> <span class="muted small">{_esc(p.get("version",""))}</span> '
                            f'<a class="btn" style="padding:2px 8px" href="/prototypes/{_esc(p["slug"])}">ansehen ↗</a>{sl_html}</div>')
            proto_html = (f'<div class="oqp-h" style="margin-top:14px">{t("prototypes_h")} ({len(protos)})</div>'
                          + "".join(rows))
        # Open questions + legend + prototypes live in a floating panel so the graph keeps the canvas.
        panel = (
            f'<div class="oqpanel" id="oqpanel" hidden>'
            f'<div class="oqp-h">{t("build_order_h")} (edges)</div>'
            f'<div class="pills" style="margin:6px 0 14px">{edge_leg}</div>'
            f'<div class="oqp-h">{t("open_questions_h")}</div>'
            f'<ul style="margin:6px 0 0 18px">{oq_html}</ul>'
            f'{proto_html}</div>')
        oq_js = ("<script>(function(){var b=document.getElementById('oqbtn'),"
                 "p=document.getElementById('oqpanel');if(!b||!p)return;"
                 "b.addEventListener('click',function(e){e.stopPropagation();p.hidden=!p.hidden;});"
                 "document.addEventListener('click',function(e){"
                 "if(!p.hidden&&!p.contains(e.target)&&e.target!==b)p.hidden=true;});})();</script>")
        body = (
            f'<div class="proj">'
            f'<div class="proj-head"><h1 class="h1">{_esc(proj["title"])}</h1>'
            f'<p class="lead">{_esc(proj.get("goal", ""))}</p>'
            f'{toolbar}</div>'
            f'<div class="graphcard proj-graph">{_graph_interactive(graph)}</div>'
            f'{panel}{oq_js}'
            f'</div>')
        return _layout(proj["title"], body, store, crumbs=[(t("projects"), "/projects"), (proj["title"], None)], active="projects")

    @app.get("/projects/{project_id}/meta", response_class=HTMLResponse)
    def project_meta(project_id: str) -> str:
        store = Store()
        try:
            md = services.export_meta_report(project_id, format="md", store=store)
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("meta_report"), t("runtime_maybe_cleared")), store, active="projects")
        body = f'<div class="page"><div class="doc">{_md(md)}</div></div>'
        actions = f'<button class="btn" onclick="window.print()">{t("export_pdf")}</button>'
        return _layout(proj["title"] + " — " + t("meta_report"), body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f"/projects/{project_id}"), (t("meta_report"), None)],
                       active="projects", actions=actions)

    def _plan_html(plan: dict, store) -> str:
        tasks = plan.get("tasks", [])
        done = sum(1 for t in tasks if t["status"] == "done")
        complete = bool(tasks) and done == len(tasks)
        by_title = {t["id"]: t.get("title", t["id"]) for t in tasks}
        STATUS = {"done": ("✓", "var(--green)"), "active": ("◐", "var(--accent)"),
                  "todo": ("○", "var(--muted)"), "blocked": ("!", "var(--red)")}
        # Resolve evidence links by IDENTITY (which collection the ref lives in), not by a kind
        # literal — the kind LABEL comes from data via present(); storage membership is legitimate.
        _syn_ids = {s["id"] for s in store.list_syntheses()}
        _protos = {p["id"]: p for p in store.list_prototypes(plan["project_id"])}

        def ev_chip(r: dict) -> str:
            rid, kind = r.get("id", ""), r.get("kind", "")
            label = _pres.present(kind)["short"] if kind else rid
            href = None
            if rid in _protos:
                p = _protos[rid]
                href, label = f"/prototypes/{p['slug']}", f"{label} · {p.get('name', p['slug'])}"
            elif rid in _syn_ids:
                href = f"/syntheses/{rid}"
            elif store.get_council_session(rid):
                href = f"/councils/{rid}"
            if href:
                return f'<a class="ev" href="{href}">{_esc(label)} ↗</a>'
            return f'<span class="ev">{_esc(label)}</span>'

        def row(t: dict) -> str:
            mark, clr = STATUS.get(t["status"], ("○", "var(--muted)"))
            cons = " · ".join(by_title.get(c, c) for c in t.get("consumes", []))
            cons_html = f'<div class="small muted" style="margin-top:4px">⊂ {_esc(cons)}</div>' if cons else ""
            req = t.get("requires", {}) or {}
            gates = []
            if req.get("min_inputs") is not None:
                gates.append(f"min. {req['min_inputs']} Inputs")
            if req.get("gate_tag"):
                gates.append(_pres.present(req["gate_tag"])["short"])
            for tg in (req.get("session_of_tags") or []):
                gates.append(f"Session: {_pres.present(tg)['short']}")
            for tg in (req.get("artifact_tags") or []):
                gates.append(f"Artefakt: {_pres.present(tg)['short']}")
            gates_html = "".join(f'<span class="gate">{_esc(x)}</span>' for x in gates)
            cap = t.get("capability", "")
            cap_html = f'<span class="pcap">{_esc(cap)}</span>' if cap else ""
            # skip the frame self-reference (a frame task produces a ref to itself); link the rest
            evs = "".join(ev_chip(r) for r in t.get("produces", []) if r.get("id") != t["id"])
            ev_html = f'<div class="evs">{evs}</div>' if evs else ""
            return (f'<div class="ptask"><div class="pmark" style="color:{clr}">{mark}</div>'
                    f'<div class="pbody"><div class="prow1"><span class="ptitle">{_esc(t.get("title", t["id"]))}</span>'
                    f'{cap_html}{gates_html}</div>{cons_html}{ev_html}</div></div>')

        secs = []
        for b, label in [("analyze", "Analyze · verstehen"), ("act", "Act · Councils, Prototypen, Tests"),
                         ("verify", "Verify · verdichten & entscheiden")]:
            rows = "".join(row(t) for t in tasks if t["bucket"] == b)
            if rows:
                secs.append(f'<div class="psec"><div class="psec-h">{label}</div>{rows}</div>')
        pill = ('<span class="pill" style="color:var(--green)">● Plan komplett</span>' if complete
                else f'<span class="pill">{len(tasks) - done} offen</span>')
        head = (f'<div class="card plan-head"><div class="ph-goal">{_esc(plan.get("goal", ""))}</div>'
                f'<div class="small muted" style="margin-top:6px">Methodik: '
                f'<b>{_esc(plan.get("methodology") or "freiform")}</b> · {len(tasks)} Tasks · {done} erledigt &nbsp;{pill}</div></div>')
        css = ("<style>.plan-head{margin-bottom:20px}.ph-goal{font-weight:650;font-size:16px;line-height:1.4}"
               ".psec{margin:0 0 24px}.psec-h{font-size:12px;text-transform:uppercase;letter-spacing:.05em;"
               "color:var(--muted);font-weight:600;margin:0 0 10px}"
               ".ptask{display:flex;gap:12px;padding:11px 13px;border:1px solid var(--line);border-radius:var(--radius);"
               "background:var(--panel);margin-bottom:8px}.pmark{font-weight:700;width:16px;text-align:center;flex:none}"
               ".pbody{flex:1;min-width:0}.prow1{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.ptitle{font-weight:550}"
               ".pcap{font-size:11px;color:var(--accent);background:var(--accent-weak);padding:1px 8px;border-radius:999px}"
               ".gate{font-size:11px;color:var(--muted);background:var(--hover);padding:1px 8px;border-radius:999px}"
               ".evs{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.ev{font-size:11px;color:var(--muted);"
               "background:var(--panel-2);border:1px solid var(--line);padding:2px 8px;border-radius:6px;text-decoration:none}"
               "a.ev:hover{color:var(--accent);border-color:var(--accent)}</style>")
        return f'{css}<div class="page">{head}{"".join(secs)}</div>'

    @app.get("/projects/{project_id}/plan", response_class=HTMLResponse)
    def project_plan(project_id: str) -> str:
        store = Store()
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state("Plan", t("runtime_maybe_cleared")), store, active="projects")
        plan = services.get_plan(project_id, store=store)
        if not plan:
            body = f'<div class="page">{_empty_state("Plan", "Dieses Projekt hat noch keinen Plan (Freiform/Legacy).")}</div>'
        else:
            body = _plan_html(plan, store)
        return _layout(proj["title"] + " — Plan", body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f"/projects/{project_id}"), ("Plan", None)],
                       active="projects")

    @app.get("/prototypes/{slug}", response_class=HTMLResponse)
    def prototype_view(slug: str) -> str:
        store = Store()
        try:
            p = services.get_prototype_artifact(slug, store=store)
        except Exception:
            return _layout(t("not_found"), _empty_state(t("prototypes_h"), t("runtime_maybe_cleared")), store, active="projects")
        crumbs = [(t("projects"), "/projects")]
        proj = store.get_research_project(p["project_id"]) if p.get("project_id") else None
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((p["name"], None))
        _ap = _artifact_present(p)
        fid = f'<span class="pill">{_esc(_ap["disc"] or _ap["label"])}</span>'
        src = f'/proto-files/{_esc(slug)}/{_esc(p.get("entry", "index.html"))}'
        sessions = store.list_prototype_sessions(prototype_id=p["id"])
        sl = []
        for s in sessions:
            r = s.get("reaction", {})
            gv = "✓ grounded" if s.get("grounded_verified") else "○ unbestätigt"
            liked = "".join(f"<li>👍 {_esc(x)}</li>" for x in (r.get("liked") or [])[:3])
            fric = "".join(f"<li>⚠ {_esc(x)}</li>" for x in (r.get("friction") or [])[:3])
            sl.append(f'<div class="strow"><b>{_esc(s.get("persona_id",""))}</b> '
                      f'<span class="muted small">{gv}</span><div class="small" style="margin-top:3px">'
                      f'{_esc(str(r.get("verdict","")))}</div><ul class="small" style="margin:4px 0 0 16px">{liked}{fric}</ul></div>')
        sessions_html = ("".join(sl)) or f'<div class="muted small">— {t("prototypes_h")}: keine Sessions —</div>'
        body = (
            f'<div class="page"><h1 class="h1">{_esc(p["name"])} {fid} '
            f'<span class="muted small">{_esc(p.get("version",""))} · {_esc(slug)}</span></h1>'
            f'<p class="lead"><a class="btn" href="{src}" target="_blank">{_icon("projects")} In neuem Tab öffnen ↗</a></p>'
            f'<div class="protoframe"><iframe src="{src}" title="{_esc(p["name"])}" loading="lazy"></iframe></div>'
            f'<div class="card" style="margin-top:16px"><b>{t("prototypes_h")} · Sessions ({len(sessions)})</b>'
            f'<div style="margin-top:8px">{sessions_html}</div></div></div>')
        return _layout(p["name"], body, store, crumbs=crumbs, active="projects")

    # ---------------- JSON API (unchanged surface) ----------------
    @app.get("/api/personas")
    def api_personas():
        return JSONResponse(services.list_personas())

    @app.get("/api/personas/{persona_id}")
    def api_persona(persona_id: str):
        try:
            return JSONResponse(services.get_persona(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/calendar")
    def api_calendar(persona_id: str, date_value: str | None = Query(default=None, alias="date")):
        try:
            return JSONResponse(services.get_calendar(persona_id, date_value))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/calendar-period")
    def api_calendar_period(persona_id: str, date_value: str | None = Query(default=None, alias="date"), view: str = "day"):
        try:
            return JSONResponse(services.get_calendar_period(persona_id, date_value, view))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/memory")
    def api_memory(persona_id: str):
        try:
            return JSONResponse(services.get_persona_memory(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/projects")
    def api_projects(persona_id: str):
        try:
            return JSONResponse(services.list_active_projects(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/state-at")
    def api_state_at(persona_id: str, as_of: str = Query(...)):
        try:
            return JSONResponse(services.get_state_at(persona_id, as_of))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/recall")
    def api_recall(persona_id: str, q: str = Query(...), as_of: str | None = Query(default=None), k: int = 8):
        try:
            return JSONResponse(services.recall_memory(persona_id, q, as_of, k))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/evaluate")
    def api_evaluate(persona_id: str):
        try:
            return JSONResponse(services.evaluate_simulation_full(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/activities/{activity_id}")
    def api_activity(activity_id: str):
        try:
            return JSONResponse(services.get_activity(activity_id))
        except KeyError:
            return JSONResponse({"error": "activity_not_found"}, status_code=404)

    @app.get("/api/councils")
    def api_councils():
        return JSONResponse(services.list_councils())

    @app.get("/api/syntheses")
    def api_syntheses():
        return JSONResponse(services.list_syntheses())

    @app.get("/api/syntheses/{synthesis_id}")
    def api_synthesis(synthesis_id: str):
        try:
            return JSONResponse(services.get_synthesis(synthesis_id))
        except KeyError:
            return JSONResponse({"error": "synthesis_not_found"}, status_code=404)

    return app


# ----------------------------- calendar helpers ----------------------------- #
def _calendar_html(persona_id: str, day: str, blocks: list[dict]) -> str:
    by_hour: dict[int, list[dict]] = {h: [] for h in range(7, 20)}
    for block in blocks:
        hour = int(block["calendar_event"]["start"][11:13])
        by_hour.setdefault(hour, []).append(block)
    rows = []
    for hour in range(7, 20):
        rows.append(f'<div class="hour">{hour:02d}:00</div><div class="slot">')
        for block in by_hour.get(hour, []):
            cal = block["calendar_event"]; activity = block.get("activity") or {}
            kind = activity.get("event_type", "focus")
            rows.append(
                f'<a class="block {kind}" href="/activities/{_esc(activity.get("id",""))}">'
                f'<strong>{_esc(cal["start"][11:16])}-{_esc(cal["end"][11:16])} · {_esc(cal["title"])}</strong>'
                f'<span class="meta">{_esc(block.get("collaboration_mode") or "")} · {_esc(cal["location_or_tool"])}</span><br>'
                f'{_esc(block.get("persona_thought") or cal["outcome"])}</a>')
        rows.append("</div>")
    return f'<div class="calendar">{"".join(rows)}</div>'


def _calendar_tabs(persona_id: str, selected_date: str, view: str) -> str:
    labels = {"day": t("tab_day"), "week": t("tab_week"), "month": t("tab_month"), "year": t("tab_year")}
    return '<div class="tabs">' + "".join(
        f'<a class="{"active" if view == tab else ""}" href="/personas/{_esc(persona_id)}?date={_esc(selected_date)}&view={tab}">{labels[tab]}</a>'
        for tab in ["day", "week", "month", "year"]) + "</div>"


def _event_chip(event: dict) -> str:
    return (f'<a class="block {event.get("event_type","focus")}" href="/activities/{_esc(event["id"])}">'
            f'<strong>{_esc(event["timestamp"][11:16])} · {_esc(event["task"])}</strong>'
            f'<span class="meta">{_esc(event.get("tool",""))}</span></a>')


def _period_calendar_html(persona_id: str, selected_date: str, view: str, period: dict) -> str:
    if view == "day":
        return _calendar_html(persona_id, selected_date, services.get_calendar(persona_id, selected_date)["blocks"])
    start = date.fromisoformat(period["period_start"]); end = date.fromisoformat(period["period_end"]); days = period["days"]
    if view == "week":
        cells = []; current = start
        while current <= end:
            dk = current.isoformat(); chips = "".join(_event_chip(e) for e in days.get(dk, [])[:4])
            cells.append(f'<div class="daycell"><h4>{_esc(dk)}</h4>{chips or "<p class=\"muted small\">—</p>"}</div>'); current += timedelta(days=1)
        return f'<div class="calendar-grid week">{"".join(cells)}</div>'
    if view == "month":
        cells = []; current = start
        while current <= end:
            dk = current.isoformat(); evs = days.get(dk, []); chips = "".join(_event_chip(e) for e in evs[:3])
            cells.append(f'<div class="daycell monthcell"><h4>{current.day}</h4><div class="count">{t("n_events", n=len(evs))}</div>{chips}</div>'); current += timedelta(days=1)
        return f'<div class="calendar-grid month">{"".join(cells)}</div>'
    cells = []
    for m in range(1, 13):
        me = [e for dk, evs in days.items() if date.fromisoformat(dk).month == m for e in evs]
        cells.append(f'<div class="daycell"><h4>{start.year}-{m:02d}</h4><div class="count">{t("n_events", n=len(me))}</div>{"".join(_event_chip(e) for e in me[:2])}</div>')
    return f'<div class="calendar-grid year">{"".join(cells)}</div>'


def _memory_html(store: Store, persona_id: str, as_of: str | None, q: str | None) -> str:
    p = store.get_persona(persona_id)
    if not p:
        return _empty_state(t("profile_not_found"), t("runtime_maybe_cleared"))
    pid = p["id"]
    outdated_label = _label(t("outdated"), "var(--muted)", "outline", False)
    since_label = t("since")
    none_html = f'<p class="muted">{t("none")}</p>'
    proj_cards = []
    for proj in services.list_active_projects(pid, store=store):
        tl = services.get_project(pid, proj["entity_id"], store=store)["facts"]
        rows = "".join(
            f'<p class="{"muted" if not f["valid"] else ""}">{_esc(f["t_valid"][:10])} · <strong>{_esc(f.get("status") or "—")}</strong> · {_esc(f["fact"])}'
            f'{" " + outdated_label if not f["valid"] else ""}</p>' for f in tl[-8:])
        proj_cards.append(f'<div class="card"><h3>{_esc(proj["name"])} · <span class="muted">{_esc(proj.get("status") or "?")}</span></h3>{rows}</div>')
    loops = "".join(f'<p>• {_esc(t["text"])} <span class="muted small">{since_label} {_esc((t.get("opened_on") or "")[:10])}</span></p>' for t in store.list_threads(pid, "open")[:20])
    digests = "".join(f'<div class="card"><h3>{_esc(d["scope"])} · {_esc(d["period_start"][:10])}–{_esc(d["period_end"][:10])}</h3><p>{_esc(d.get("text",""))}</p></div>' for d in store.list_digests(pid)[-6:])
    struct = services.evaluate_simulation(pid, store=store, persist=False)
    crit = services.latest_critic_report(pid, store=store)
    struct_rows = "".join(_label(f'{c["name"]}: {c["status"]}', _stance_color(c["status"])) for c in struct["checks"])
    crit_rows = ("".join(_label(f"{k}: {v}/5", "var(--green)" if v >= 4 else "var(--amber)") for k, v in crit["dimensions"].items()) if crit else f'<span class="muted">{t("no_critic_run")}</span>')
    tt = ""
    if as_of:
        st = services.get_state_at(pid, as_of, store=store)
        ent_rows = "".join(f'<p><strong>{_esc(e["name"])}</strong> <span class="muted">({_esc(e["kind"])})</span> → {_esc(e.get("status_at") or "—")}</p>' for e in st["entities"] if e.get("status_at"))
        nothing_valid_html = f'<p class="muted">{t("nothing_valid")}</p>'
        tt = (f'<div class="card"><h3>{t("state_at", date=_esc(as_of))}</h3>{ent_rows or nothing_valid_html}'
              f'<p class="muted small">{t("open_threads_count", n=len(st.get("open_threads", [])))}</p></div>')
    rc = ""
    if q:
        hits = services.recall_memory(pid, q, store=store, k=8)["hits"]
        nothing_html = f'<p class="muted">{t("nothing")}</p>'
        rc = f'<div class="card"><h3>{t("recall")}</h3>' + ("".join(f'<p class="quote">[{_esc(h["obj_type"])}] {_esc(h.get("when") or "")} · score {_esc(h["score"])}<br>{_esc(h["text"])}</p>' for h in hits) or nothing_html) + "</div>"
    mem_title = t("memory_title", name=_esc(p["display_name"]))
    recall_ph = _esc(t("recall_placeholder"))
    main = f"""
    <div class="hero"><h1 style="display:flex;align-items:center;gap:9px">{_icon("memory")} {mem_title}</h1><p class="sub">{t("memory_sub")}</p></div>
    <div class="card"><h3>{t("quality")}</h3><p><strong>{t("structure")}:</strong> {_esc(struct["verdict"])} · {struct_rows}</p><p><strong>{t("critic")}:</strong> {crit_rows}</p></div>
    <div class="grid two">
      <form method="get" class="card"><h3>{t("time_travel")}</h3><input type="date" name="as_of" value="{_esc(as_of or '')}"> <button class="btn">{t("show_state")}</button></form>
      <form method="get" class="card"><h3>{t("recall")}</h3><input type="text" name="q" value="{_esc(q or '')}" placeholder="{recall_ph}" style="width:58%"> <button class="btn">{t("search")}</button></form>
    </div>{tt}{rc}
    <div class="sec"><h2>{t("active_projects")}</h2><div class="grid two">{''.join(proj_cards) or none_html}</div></div>
    <div class="sec"><h2>{t("open_threads")}</h2><div class="card">{loops or none_html}</div></div>
    <div class="sec"><h2>{t("digests")}</h2>{digests or none_html}</div>
    """
    return _doc(main)


def main() -> None:
    import os
    import uvicorn

    host = os.getenv("PERSONA_COUNCIL_WEB_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("PERSONA_COUNCIL_WEB_PORT", "8787"))
    except ValueError:
        port = 8787
    url = f"http://{host}:{port}"
    print(
        "\n" + "─" * 56 + "\n"
        "  Persona Council inspector is ready.\n"
        f"  → Open {url} in your browser.\n"
        + "─" * 56 + "\n",
        flush=True,
    )
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()

