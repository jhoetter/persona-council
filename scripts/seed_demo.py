from sonaloop import services as S
from sonaloop.services import _plan as PL
from sonaloop.storage import Store
st = Store()

def profile(name, age, beruf, lebensphase, einstellung, goals, constraints, pains, success, tools, rels,
            working, comm, risk, notes):
    return {
        "display_name": name,
        "identity_traits": {k: "unspecified" for k in
            ("gender_presentation","gender_confidence","age_range","appearance_notes","avatar_profile","avatar_constraints")},
        "segment": {"lebensphase": lebensphase, "einstellung": einstellung, "region": "Deutschland"},
        "demographics": {"alter": age, "beruf": beruf},
        "role": {"title": beruf, "responsibilities": beruf, "seniority": "-", "decision_power": "entscheidet selbst"},
        "company_context": {"industry": "-", "size": "-", "stack": "-", "operating_model": "-"},
        "goals": goals, "constraints": constraints, "tool_ids": [], "tools": tools,
        "relationships": rels,
        "personality": {"working_style": working, "communication_style": comm, "risk_tolerance": risk, "character_notes": notes},
        "pain_points": pains, "success_criteria": success,
    }

P = {}
P["lena"] = S.record_persona("Marketing-Managerin, Vollzeit, lange Pendelzeiten",
    profile("Lena Vogt", 29, "Marketing-Managerin", "Vollzeit-Job, lange Pendelzeiten, Grossstadt",
        "will gesuender essen, hat aber kaum Zeit",
        ["Gesuender essen ohne grossen Aufwand", "Abends nicht erschoepft bestellen muessen"],
        ["Kommt oft erst 19:30 nach Hause", "Wenig Energie zum Kochen unter der Woche"],
        ["Nach der Arbeit fehlt die Energie zu kochen", "Spontan-Bestellen ist teuer und ungesund"],
        ["Ein machbarer Wochen-Rhythmus", "Weniger Lieferdienst"],
        ["Lieferdienst-App", "Supermarkt um die Ecke"],
        [{"name": "Partner", "type": "Haushalt", "friction": "beide kommen spaet"}],
        "strukturiert, aber zeitarm", "direkt, pragmatisch", "mittel", "mag einfache Routinen, keine Food-Trends"), store=st)["id"]
P["mehmet"] = S.record_persona("Student, WG, knappes Budget",
    profile("Mehmet Demir", 22, "Student", "Student, lebt in WG, knappes Budget",
        "kocht selten, bestellt oder isst in der Mensa",
        ["Guenstig essen", "Nicht jeden Tag dasselbe"],
        ["Sehr schmales Budget", "Kleine WG-Kueche, wenig Ausstattung"],
        ["Kochen lohnt sich gefuehlt nicht fuer eine Person", "Reste verderben oft"],
        ["Guenstige, einfache Gerichte", "Weniger Wegwerfen"],
        ["WhatsApp", "Discounter"],
        [{"name": "Mitbewohner", "type": "WG", "friction": "kochen unkoordiniert"}],
        "spontan, preisbewusst", "locker", "hoch", "probiert gern, wenn es billig ist"), store=st)["id"]
P["sabine"] = S.record_persona("Berufstaetig, zwei Kinder",
    profile("Sabine Kraus", 38, "Projektleiterin (Teilzeit)", "berufstaetig, zwei Schulkinder",
        "Familie + Job, abends oft kaputt",
        ["Die Familie gesund versorgen", "Den Abend-Stress reduzieren"],
        ["Zwei Kinder mit eigenen Vorlieben", "Wenig Zeit, hohe Last"],
        ["Jeden Tag die Frage: was kochen wir?", "Einkauf wird zur Zusatz-Schicht"],
        ["Planbarkeit", "Gerichte, die alle essen"],
        ["Familien-Kalender", "Supermarkt-App"],
        [{"name": "Kinder", "type": "Familie", "friction": "waehlerisch"}],
        "organisiert, unter Last", "warmherzig, klar", "niedrig", "braucht Verlaesslichkeit, keine Experimente"), store=st)["id"]
P["tom"] = S.record_persona("Single, Homeoffice, bestellt taeglich",
    profile("Tom Berger", 34, "Softwareentwickler", "Single, Homeoffice",
        "bestellt fast taeglich Lieferdienst, will das aendern",
        ["Weniger Geld fuer Lieferdienst", "Sich besser fuehlen"],
        ["Kocht nie, kann wenig", "Verliert im Flow das Essen aus dem Blick"],
        ["Lieferdienst ist Gewohnheit und teuer", "Kochen wirkt kompliziert und zeitraubend"],
        ["Ein einfacher Einstieg", "Erste Erfolge"],
        ["Lieferdienst-App", "Online-Supermarkt"],
        [{"name": "Kollegen", "type": "Remote-Team", "friction": "isst allein am Schreibtisch"}],
        "fokussiert, gewohnheitsgetrieben", "knapp", "mittel", "braucht sehr niedrige Einstiegshuerde"), store=st)["id"]
print("personas:", {k: v[:18] for k, v in P.items()})

proj = S.create_research_project("Gesuender essen im stressigen Alltag",
    goal="Menschen mit vollem Alltag helfen, unter der Woche gesuender zu essen — ohne grossen Aufwand, "
         "ohne Verzicht, in machbaren Schritten.", store=st)
PID = proj["id"]
S.set_project_methodology(PID, "double_diamond", store=st)
print("project:", PID)

# Realistic research timeline (one double-diamond sprint) so created_at reflects the TRUE flow order:
# discover -> define -> develop (ideate -> build -> evaluate) -> deliver. The host authors these
# explicitly via created_at (see record_* `created_at=`), instead of "now" for everything.
def _T(d, hm): return f"2026-06-{d:02d}T{hm}:00+00:00"
TS = {
    "disc":    _T(2, "09:30"),   # Mon — Discovery council (the research itself) comes FIRST
    "obs1":    _T(2, "16:00"),   # Mon — observations distilled FROM the discovery
    "obs2":    _T(2, "16:10"),
    "define":  _T(3, "10:30"),   # Tue — Define synthesis
    "con1":    _T(4, "09:30"),   # Wed — concept: Wochenplan-Starter
    "con2":    _T(4, "17:00"),   # Wed — concept: 20-Minuten-Filter (noted after the builds)
    "v01":     _T(4, "14:00"),   # Wed — lo-fi prototype
    "v02":     _T(4, "16:30"),   # Wed — hi-fi prototype (adds the 20-min guarantee)
    "eval":    _T(5, "10:00"),   # Thu — evaluation council tests the built Starter
    "deliver": _T(6, "11:00"),   # Fri — Deliver synthesis (the dev-ready spec)
}

# ---- DISCOVER: notes ----
S.create_note(PID, kind="note", title="Beobachtung: Der Abend ist der Engpass",
    text=("Quer durch alle Gespraeche: das Problem ist nicht **Wissen**, sondern der **Abend**. "
          "Wer um 19:30 erschoepft heimkommt, trifft keine guten Entscheidungen mehr.\n\n"
          "- Lena & Tom: greifen dann zum Lieferdienst\n- Sabine: taeglicher _Was-kochen-wir_-Stress"), created_at=TS["obs1"], store=st)
S.create_note(PID, kind="note", title="Beobachtung: Planung scheitert, nicht Kochen",
    text=("Kochen koennen die meisten _irgendwie_. Was fehlt, ist die **Entscheidung vorab** — was, wann, "
          "und der passende Einkauf. Ohne Plan gewinnt die Gewohnheit."), created_at=TS["obs2"], store=st)

# ---- DISCOVER: discovery council (native statements + questions) ----
QS = ["Wie sieht dein Essen unter der Woche typischerweise aus?",
      "Was haelt dich davon ab, gesuender zu essen?",
      "Was wuerde dir wirklich helfen?"]
ANS = {
 "lena": ["Unter der Woche oft Lieferdienst oder schnell was vom Baecker.",
          "Abends fehlt die Energie. Einkaufen + Kochen fuehlt sich nach noch einer Schicht an.",
          "Ein fertiger Plan fuer 3 Tage und eine Einkaufsliste, die ich nicht selbst denken muss."],
 "mehmet": ["Mensa, Doener, manchmal Nudeln mit allem was da ist.",
            "Fuer eine Person zu kochen lohnt sich gefuehlt nicht, und Reste verderben.",
            "Guenstige Gerichte, die ich auch zu zweit in der WG machen kann."],
 "sabine": ["Ich plane schon, aber jeden Tag neu — das frisst Energie.",
            "Die Kinder essen nicht alles, also koche ich auf Nummer sicher.",
            "Ein paar verlaessliche Gerichte, die alle essen, plus der passende Einkauf."],
 "tom": ["Ehrlich: fast jeden Tag Lieferdienst. Kochen mache ich quasi nie.",
         "Kochen wirkt kompliziert, und im Arbeits-Flow vergesse ich Essen komplett.",
         "Ein extrem einfacher Einstieg. Drei Gerichte, die idiotensicher sind."],
}
disc_statements = []
for pid_key, answers in ANS.items():
    for qi, ans in enumerate(answers):
        disc_statements.append({"id": f"{pid_key}_q{qi}", "persona_id": P[pid_key], "text": ans,
                                "about": {"kind": "prompt", "id": f"q{qi}"}})
disc = S.record_council(PID,
    prompt="Discovery: Wie essen Menschen im stressigen Alltag — und was haelt sie von gesundem Essen ab?",
    persona_ids=list(P.values()), questions=QS, statements=disc_statements,
    selection_reason="Vier volle Alltage — Vollzeit-Pendlerin, Student/WG, berufstaetige Mutter, Homeoffice-Single — die Bandbreite, fuer die der Abend zum Engpass wird.",
    summary=("Das Problem ist der **Abend**, nicht das Wissen. Ohne **Plan vorab** gewinnt die Gewohnheit "
             "(Lieferdienst, Mensa, taeglicher Stress)."),
    exec_summary=("Vier Gespraeche, ein klares Muster.\n\n"
                  "**Was alle teilen**\n\n- Gesund essen _wollen_ alle; am **Abend** fehlt die Energie zur Entscheidung.\n"
                  "- Der Engpass ist **Planung + Einkauf**, nicht das Kochen.\n\n"
                  "**Unterschiede**\n\n1. **Budget/Menge** — fuer eine Person lohnt Kochen gefuehlt nicht (Mehmet, Tom).\n"
                  "2. **Familien-Tauglichkeit** — es muss allen schmecken (Sabine).\n"
                  "3. **Einstiegshuerde** — Tom braucht es _idiotensicher_."),
    key=f"{PID}-disc", created_at=TS["disc"], store=st)
DISC = disc["id"]
print("discovery council:", DISC, "| statements:", len(disc.get("statements", [])))

# ---- DEFINE: synthesis (native findings + statements) ----
define = S.record_synthesis(
    title="Define: Gesund essen scheitert am Abend — nicht am Wissen",
    start_input="Wie essen Menschen im stressigen Alltag, und was haelt sie ab?",
    goal="Das Discovery-Bild zu einer scharfen Problem-Definition verdichten.",
    council_ids=[DISC],
    payload={
        "gesamtbild": ("Gesund essen ist ein **Abend-Problem**, kein Wissens-Problem. Erschoepft trifft "
                       "niemand gute Essens-Entscheidungen; ohne **Plan + Einkauf vorab** gewinnt die "
                       "Gewohnheit (Lieferdienst, Mensa, Stress)."),
        "positionierung": ("Ein **Wochen-Starthelfer**, kein Ernaehrungs-Coach: nimmt die Entscheidung + den "
                           "Einkauf ab, in 10 Minuten, mit wenigen verlaesslichen Gerichten."),
        # Findings CROSS-REFERENCE the council statements they distill (spec/artifact-cross-references):
        # the synthesis re-interprets in its own words and links to the source; it never copies the voice.
        "findings": [
            {"text": "Der **Abend** ist der Entscheidungs-Engpass — Loesungen muessen _vor_ dem Abend greifen",
             "kind": "key_problem", "refs": [{"kind": "council", "id": DISC, "anchor": "lena_q1", "role": "derived_from"}, {"kind": "council", "id": DISC, "anchor": "tom_q1", "role": "derived_from"}]},
            {"text": "Geplant wird zu wenig; **Kochen** ist selten das eigentliche Problem",
             "kind": "key_problem", "refs": [{"kind": "council", "id": DISC, "anchor": "sabine_q0", "role": "derived_from"}, {"kind": "council", "id": DISC, "anchor": "lena_q2", "role": "derived_from"}]},
            {"text": "Es muss **alltagstauglich** sein: wenige Gerichte, passender Einkauf, geringe Huerde",
             "kind": "pain_solver", "refs": [{"kind": "council", "id": DISC, "anchor": "tom_q2", "role": "derived_from"}, {"kind": "council", "id": DISC, "anchor": "lena_q2", "role": "derived_from"}]},
            {"text": "Skalierbar von **1 Person bis Familie** (Portionen, Vorlieben)",
             "kind": "pain_solver", "refs": [{"kind": "council", "id": DISC, "anchor": "mehmet_q1", "role": "derived_from"}, {"kind": "council", "id": DISC, "anchor": "sabine_q1", "role": "derived_from"}]},
            {"text": "Welche 3 Gerichte treffen Budget _und_ Familie _und_ Einsteiger?", "kind": "open_question"},
        ],
    }, key=f"{PID}-define", created_at=TS["define"], store=st)
DEFINE = define["id"]
print("define synthesis:", DEFINE)

# ---- DEVELOP: concepts ----
con1 = S.create_note(PID, kind="note", title="Konzept: Wochenplan-Starter", data={"artifact_kind": "flow"}, created_at=TS["con1"],
    text=("**Idee:** 3 einfache Gerichte fuer die Woche + automatische **Einkaufsliste**, in 10 Minuten "
          "geplant.\n\n- **Wenige, verlaessliche** Gerichte (skaliert 1–4 Portionen)\n- **Einkaufsliste** "
          "entsteht automatisch\n- **Kein Abo, keine App-Pflicht** — Plan + Liste reichen"), store=st)
con2 = S.create_note(PID, kind="note", title="Konzept: 20-Minuten-Filter", data={"artifact_kind": "flow"}, created_at=TS["con2"],
    text=("Jedes vorgeschlagene Gericht ist **in unter 20 Minuten** kochbar — die Einstiegshuerde, die "
          "Tom braucht. _Schnell_ schlaegt _ausgefeilt_."), store=st)
print("concepts:", con1["id"][:18], con2["id"][:18])

# ---- DEVELOP: evaluation/decision council (proposal + votes for tally + native statements) ----
EV = {
 "lena": (2, "Genau das. 3 Gerichte + Liste, fertig. Das nehme ich sofort."),
 "mehmet": (1, "Gut, aber zeig mir die guenstige Variante und Mengen fuer die WG."),
 "sabine": (2, "Wenn die Gerichte familientauglich sind, ist das mein Abend-Retter."),
 "tom": (1, "Nur wenn jedes Gericht wirklich in 20 Minuten machbar ist."),
}
ev_statements = [{"id": k, "persona_id": P[k], "text": c, "stance": {"value": v}, "about": {"kind": "prompt", "id": "proposal"}}
                 for k, (v, c) in EV.items()]
votes = [{"persona_id": P[k], "vote": ("SUPPORT" if v == 2 else "MAYBE")} for k, (v, c) in EV.items()]
evalc = S.record_council(PID,
    prompt="Evaluation: Traegt der Wochenplan-Starter (3 einfache Gerichte + automatische Einkaufsliste)?",
    persona_ids=list(P.values()), statements=ev_statements, votes=votes,
    proposal="**Wochenplan-Starter:** 3 verlaessliche Gerichte/Woche + automatische Einkaufsliste, skaliert 1–4 Portionen, jedes in unter 20 Minuten, ohne Abo.",
    selection_reason="Dieselben vier Stimmen aus Discovery — sie sagen first-hand, ob das Konzept ihren echten Engpass trifft.",
    summary=("Breit getragen, **kein Gegenwind**. Auflagen: **familientauglich** (Sabine), **20-Minuten-Garantie** "
             "(Tom), **Mengen/Budget** sichtbar (Mehmet)."),
    exec_summary=("**2 klare Ja** (Lena, Sabine), **2 bedingte Ja** (Mehmet, Tom), kein Nein.\n\n"
                  "**Was traegt**\n\n- Plan + Liste nimmt genau den Abend-Engpass.\n\n"
                  "**Auflagen**\n\n1. **Familientauglich** kennzeichnen.\n2. **20-Minuten-Garantie** pro Gericht.\n"
                  "3. **Portionen/Budget** sichtbar machen."),
    key=f"{PID}-eval", created_at=TS["eval"], store=st)
EVAL = evalc["id"]
print("eval council:", EVAL)

# ---- DEVELOP: prototypes + sessions ----
S.register_prototype("wochenplan-starter-v01", "Wochenplan-Starter v0.1", "prototypes/wochenplan-starter-v01",
    entry="index.html", run="static", version="v0.1", project_id=PID, fidelity="lo-fi",
    notes="Lo-fi Klick-Dummy: 3 Gerichte fuer die Woche + Button Einkaufsliste, kein Abo.", created_at=TS["v01"], store=st)
S.register_prototype("wochenplan-starter-v02", "Wochenplan-Starter v0.2", "prototypes/wochenplan-starter-v02",
    entry="index.html", run="static", version="v0.2", project_id=PID, fidelity="hi-fi",
    notes="Hi-fi: setzt die Council-Auflage **20-Minuten-Garantie** um (Badge je Gericht).", created_at=TS["v02"], store=st)
PROTO1 = next(p["id"] for p in st.list_prototypes() if p["slug"] == "wochenplan-starter-v01")
PROTO2 = next(p["id"] for p in st.list_prototypes() if p["slug"] == "wochenplan-starter-v02")
# note → prototype(s): the Wochenplan-Starter concept was built as BOTH fidelity versions (v0.1, v0.2);
# the 20-Minuten-Filter is a refinement realized inside v0.2, not a separate build.
S.set_note_data(con1["id"], {"artifact_kind": "flow", "prototype_ids": [PROTO1, PROTO2]}, store=st)
sessions = [
 (PROTO1, "lena", "Drei Gerichte + Liste in einem Blick — genau so. Den Plan hatte ich sofort verstanden.", ["One-Pot-Pasta / Ofengemuese / Wraps", "Einkaufsliste erstellen"]),
 (PROTO1, "tom", "Einfach genug, aber ob die Gerichte wirklich schnell gehen, sehe ich hier noch nicht.", ["3 Gerichte fuer die Woche", "Keine App-Pflicht, kein Abo"]),
 (PROTO2, "tom", "Jetzt sehe ich **unter 20 Min** — das nimmt mir die Huerde. So steige ich ein.", ["3 Gerichte, jedes in unter 20 Min kochbar"]),
 (PROTO2, "sabine", "Schnell und planbar. Wenn ich noch Portionen einstellen kann, ist es perfekt fuer uns.", ["3 Gerichte, jedes in unter 20 Min kochbar"]),
]
for i, (proto, pkey, verdict, seen) in enumerate(sessions):
    S.record_prototype_session(P[pkey] if False else P[pkey], proto, f"{PID}-ps{i}", ("2026-06-04" if proto == PROTO1 else "2026-06-05"),
        reaction={"persona": st.get_persona(P[pkey])["display_name"], "fidelity": ("hi-fi" if proto == PROTO2 else "lo-fi"),
                  "version": ("v0.2" if proto == PROTO2 else "v0.1"),
                  "focus": "Senkt der Starter die Abend-Huerde — bleibt es alltagstauglich?",
                  "verdict": verdict, "observed_state_refs": seen},
        key=f"{PID}-ps{i}", store=st)
print("prototypes + sessions:", len(sessions))

# ---- DELIVER: synthesis (gesamtbild + recommendations[chart] + open questions + voices) ----
deliver = S.record_synthesis(
    title="Deliver: Wochenplan-Starter — die dev-fertige Spec",
    start_input="Wie bringen wir Menschen im stressigen Alltag zu gesuenderem Essen?",
    goal="Discovery -> Define -> Develop zu einer umsetzbaren Spec verdichten.",
    council_ids=[DISC, EVAL],
    payload={
        "gesamtbild": ("Ueber Discovery, Define und einen Develop-Test traegt **ein** Befund stabil: gesund "
                       "essen scheitert am **Abend**, und ein **Wochen-Starthelfer** (3 Gerichte + Liste, "
                       "vorab) loest genau das.\n\nDer Hi-fi-Test bestaetigt: die **20-Minuten-Garantie** nimmt "
                       "Einsteigern (Tom) die Huerde; offen bleibt die **Portions-/Budget**-Einstellung.\n\n"
                       "Empfehlung: bauen — schlank, mit den drei Council-Auflagen als Pflicht."),
        "positionierung": "**Starthelfer statt Coach** — Plan + Einkauf in 10 Minuten, wenige verlaessliche Gerichte.",
        "findings": [
            {"text": "**3 Gerichte + automatische Einkaufsliste** als Kern — nichts mehr.", "kind": "recommendation", "score": {"effort": 2, "value": 5}},
            {"text": "**20-Minuten-Garantie** je Gericht sichtbar (Einsteiger-Huerde).", "kind": "recommendation", "score": {"effort": 2, "value": 5},
             "refs": [{"kind": "council", "id": EVAL, "anchor": "tom", "role": "derived_from"}]},
            {"text": "**Portionen 1–4** + Budget-Hinweis (Single bis Familie).", "kind": "recommendation", "score": {"effort": 3, "value": 4}},
            {"text": "Kein Abo, keine App-Pflicht — als Produktprinzip festschreiben.", "kind": "recommendation", "score": {"effort": 1, "value": 4}},
            {"text": "Welche 3 Startgerichte treffen Budget UND Familie UND Einsteiger?", "kind": "open_question"},
            {"text": "Reicht eine Web-Liste, oder braucht es Kalender-/Einkaufs-Integration?", "kind": "open_question"},
        ],
    }, key=f"{PID}-deliver", created_at=TS["deliver"], store=st)
DELIVER = deliver["id"]
print("deliver synthesis:", DELIVER)

S.record_open_questions(PID, [
    "Welche 3 Startgerichte treffen Budget, Familie und Einsteiger zugleich?",
    "Reicht eine Web-Liste, oder braucht es eine Einkaufs-Integration?",
], store=st)

# ---- wire evidence into the plan diamond (so the project graph shows DISCOVER->...->DELIVER) ----
PL.add_task(PID, "act", "explore", "Explore - Discover", consumes=["frame__discover"], task_id="act__discover", store=st)
PL.add_task(PID, "act", "explore", "Evaluate - Develop", consumes=["frame__develop"], task_id="act__eval", store=st)
PL.add_task(PID, "act", "build", "Build - Develop", consumes=["frame__develop"], task_id="act__build", store=st)
for task, ref in [("act__discover", {"kind": "council", "id": DISC}),
                  ("verify__define", {"kind": "synthesis", "id": DEFINE}),
                  ("act__eval", {"kind": "council", "id": EVAL}),
                  ("act__build", {"kind": "artifact", "id": PROTO1}),
                  ("act__build", {"kind": "artifact", "id": PROTO2}),
                  ("verify__deliver", {"kind": "synthesis", "id": DELIVER})]:
    S.link_evidence(PID, task, ref, store=st)

# ---- complete the plan: this project ran end-to-end (Discover → Deliver), so the plan view
#      reflects that (frames discharged, act tasks done, verify gates judged) ----
def _try(label, fn, *a, **k):
    try:
        fn(*a, **k); print("  ✓", label)
    except Exception as e:
        print("  skip", label, "→", e)

_try("frame discover", S.record_frame, PID, "frame__discover",
     ["Wie essen Menschen im stressigen Alltag — und was haelt sie ab?"], memory_refs=["discovery-interviews"], store=st)
_try("act discover", S.complete_task, PID, "act__discover", store=st)
_try("judge define", S.record_judgment, PID, "verify__define", "divergence_complete", True,
     "Ein klares Muster ueber alle vier: der Abend ist der Engpass.", evidence_refs=[DISC, DEFINE], store=st)
_try("verify define", S.complete_task, PID, "verify__define", store=st)
_try("frame develop", S.record_frame, PID, "frame__develop",
     ["Traegt der Wochenplan-Starter den echten Engpass — bleibt er alltagstauglich?"], memory_refs=["define-pov"], store=st)
_try("act eval", S.complete_task, PID, "act__eval", store=st)
_try("act build", S.complete_task, PID, "act__build", store=st)
_try("judge deliver", S.record_judgment, PID, "verify__deliver", "divergence_complete", True,
     "Hi-fi bestaetigt: die 20-Minuten-Garantie nimmt die Huerde; die Spec steht.", evidence_refs=[EVAL, DELIVER], store=st)
_try("verify deliver", S.complete_task, PID, "verify__deliver", store=st)

_pl = S.get_plan(PID, store=st)
print("plan:", sum(1 for t in _pl["tasks"] if t["status"] == "done"), "/", len(_pl["tasks"]), "done")

# ---- demo fixture: 6 months of simulated daily activity for ONE persona (Lena), so the calendar
#      (week / month / year heatmap) is populated in the showcase. Synthetic demo data — the real
#      product authors days via brief_day -> record_day (host-authored). ----
import datetime as _dt
_LENA = P["lena"]
_CTASKS = {
    "meeting": [("Team-Standup", "Slack"), ("Kampagnen-Review", "Figma"), ("1:1 mit Lead", "Meet"), ("Agentur-Call", "Zoom")],
    "focus":   [("Fokus: Q3-Kampagnenplan", "Notion"), ("Content-Briefing", "Google Docs"), ("Landingpage-Copy", "Notion"), ("Funnel-Analyse", "GA4")],
    "admin":   [("Reporting Wochenzahlen", "Sheets"), ("Budget-Freigaben", "Excel"), ("Inbox", "Mail")],
    "interruption": [("Spontane Abstimmung", "Slack"), ("Vertriebs-Nachfrage", "Slack")],
}
_MOODS = ["fokussiert", "gehetzt", "zufrieden", "müde", "produktiv", "angespannt"]
_now = utc_now_iso() if "utc_now_iso" in dir() else __import__("sonaloop.config", fromlist=["utc_now_iso"]).utc_now_iso()
_d, _end, _i = _dt.date(2026, 1, 1), _dt.date(2026, 6, 30), 0
while _d <= _end:
    _wd = _d.weekday()
    _kinds = (["admin"] if _i % 5 == 0 else []) if _wd >= 5 else \
             (["meeting", "focus", "admin", "focus", "interruption", "meeting"])[: 2 + (_i * 7 + _wd) % 4]
    _hour = 8
    for _j, _k in enumerate(_kinds):
        _task, _tool = _CTASKS[_k][(_i + _j) % len(_CTASKS[_k])]
        st.insert_experience_event({
            "id": f"ev_{_LENA[:6]}_{_d.isoformat()}_{_j}", "persona_id": _LENA,
            "timestamp": f"{_d.isoformat()}T{_hour:02d}:{((_i*13+_j*7)%6)*10:02d}", "event_type": _k,
            "summary": _task, "task": _task, "tool": _tool, "participants": [],
            "collaboration_mode": ("meeting" if _k == "meeting" else "solo"), "what_happened": f"{_task} — {_tool}.",
            "conversation": [], "key_quotes": [], "actions_done": [_task], "artifacts_touched": [_tool],
            "persona_thought": "", "decision": None, "open_loops": [], "impact": {"mood": _MOODS[_i % len(_MOODS)]},
            "pain_points": [], "goal_refs": [], "calendar_event_id": None, "created_at": _now})
        _hour += 1 + (_j % 3)
    if _kinds:
        st.upsert_daily_summary({"id": f"ds_{_LENA[:6]}_{_d.isoformat()}", "persona_id": _LENA, "date": _d.isoformat(),
                                 "mood": _MOODS[_i % len(_MOODS)], "completed": _kinds, "blockers": [], "open_loops": [],
                                 "pain_points": [], "notable_memories": [], "created_at": _now})
    _i += 1; _d += _dt.timedelta(days=1)
st.commit()                       # raw store writes (unlike services) need an explicit commit
print("calendar fixture: 6 months of activity for Lena")

# ---- demo fixture: a small temporal knowledge graph for Lena (entities + facts over time, some
#      superseded; open threads) so the Memory panel is populated. Mirrors record_memory_deltas output. ----
_ENTS = [
    ("project", "Q3-Kampagne", "in Arbeit", [
        ("2026-03-02", "freigegeben", "Briefing freigegeben — Fokus Performance-Kanäle", None),
        ("2026-03-20", "Budget 30k", "Budget: 30.000 EUR", "2026-05-04"),
        ("2026-05-04", "Budget 42k", "Budget auf 42.000 EUR erhöht (CEO-Push)", None),
        ("2026-05-18", "Termin steht", "Launch-Termin fixiert: 13. Juli", None)]),
    ("person", "Daniel Roth", "Team-Lead", [
        ("2026-05-01", "neuer Lead", "Wird neuer Team-Lead (Wechsel aus dem Vertrieb)", None),
        ("2026-05-12", None, "Erwartet wöchentliche Performance-Reports (Montag früh)", None)]),
    ("topic", "Meal-Prep", "aktiv", [
        ("2026-04-08", None, "Probiert Wochenplanung gegen den Abend-Stress", None),
        ("2026-05-22", None, "Lieferdienst-Nutzung deutlich reduziert", None)]),
    ("tool", "Notion", "im Einsatz", [
        ("2026-02-15", None, "Team-Wiki + Kampagnenplanung auf Notion umgestellt", None)]),
]
for _kind, _name, _status, _facts in _ENTS:
    _eid = f"ent_{_LENA[:6]}_{_name.lower().replace(' ', '-')}"
    st.upsert_entity({"id": _eid, "persona_id": _LENA, "kind": _kind, "name": _name, "status": _status,
                      "aliases": [], "first_seen": _facts[0][0], "last_seen": _facts[-1][0],
                      "created_at": _now, "updated_at": _now})
    for _fi, (_tv, _fst, _ftxt, _tinv) in enumerate(_facts):
        st.insert_entity_fact({"id": f"{_eid}_f{_fi}", "persona_id": _LENA, "entity_id": _eid, "fact": _ftxt,
                               "status": _fst, "t_valid": _tv, "t_invalid": _tinv, "importance": 3,
                               "source_event_id": None, "created_at": _now})
for _ti, (_op, _txt) in enumerate([
        ("2026-05-19", "Landingpage-Copy finalisieren (Freigabe Daniel steht aus)"),
        ("2026-05-21", "Q4-Budget rechtzeitig nachfassen"),
        ("2026-05-23", "3 schnelle 20-Minuten-Rezepte testen")]):
    st.upsert_thread({"id": f"th_{_LENA[:6]}_{_ti}", "persona_id": _LENA, "entity_id": None, "text": _txt,
                      "status": "open", "opened_on": _op, "closed_on": None, "created_at": _now, "updated_at": _now})
st.commit()
print("memory fixture: 4 entities + 3 open threads for Lena")
print("DONE — demo project:", PID)
