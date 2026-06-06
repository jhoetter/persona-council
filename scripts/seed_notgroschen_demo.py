"""Seed a Markdown-first demo design-thinking project (spec/markdown-authoring-harness.md §5).

Builds "Notgroschen für junge Erwachsene" across all Double-Diamond phases — observation notes,
a Discovery council, a Define synthesis, a concept, an Evaluation council, a prototype + sessions,
and a Deliver spec — with all analysis prose authored as Markdown (the target authoring style).
Reuses the global personas; idempotent (aborts if the project already exists).
Run: uv run python scripts/seed_notgroschen_demo.py
"""
from persona_council import services as S
from persona_council.storage import Store
st = Store()

TITLE = "Notgroschen für junge Erwachsene"
if any(p["title"] == TITLE for p in S.list_research_projects(store=st)):
    print("project already exists — aborting to avoid duplicates"); raise SystemExit

A="persona_35fe1b951710951f"  # Aylin (Studentin, knapp, skeptisch)
J="persona_d07673697d25d43e"  # Jonas (Student, Nebenjob, knapp)
SO="persona_81387c20f1bff051" # Sophie (Studium/Berufseinstieg)
T="persona_6ce737e8370f3150"  # Tobias (erstes hohes Gehalt)
L="persona_1d4f399b41aeb950"  # Leon (Azubi, erstes Auto)
NAME={A:"Aylin Yıldız",J:"Jonas Reinhardt",SO:"Sophie Bachmann",T:"Tobias Wegener",L:"Leon Brandt"}

proj = S.create_research_project(
    TITLE,
    goal="Jungen Erwachsenen mit knappem Budget helfen, einen verlässlichen Notgroschen aufzubauen — "
         "ohne Frust, ohne Verkaufsdruck, in machbaren Mini-Schritten.",
    store=st)
PID = proj["id"]
S.set_project_methodology(PID, "double_diamond", store=st)
print("project:", PID)

# ---------------- DISCOVER: observation notes ----------------
S.create_note(PID, kind="note", title="Beobachtung: „Notgroschen“ ist abstrakt",
    text=("Im Erstgespräch nennt **niemand** spontan „Notgroschen“ als Ziel. Konkret wird es erst bei einem "
          "_Vorfall_:\n\n- kaputtes Handy\n- Autoreparatur\n- Strom-Nachzahlung\n\nDer Bedarf ist real, das **Wort** "
          "weckt nichts."), store=st)
S.create_note(PID, kind="note", title="Beobachtung: Der erste Schritt ist die Hürde",
    text=("Sparen scheitert selten am _Wollen_, sondern am **Anfangen**: "
          "„Wie viel? Wohin? Was, wenn ich es doch brauche?“ Offene Fragen → Aufschub."), store=st)

# ---------------- DISCOVER: discovery council ----------------
QS = [
    "Was machst du, wenn plötzlich eine größere unerwartete Ausgabe kommt (kaputtes Handy, Reparatur, Nachzahlung)?",
    "Legst du gerade Geld für Notfälle zur Seite — und warum (nicht)?",
    "Was würde dir wirklich helfen, einen Puffer aufzubauen?",
]
ANS = {
 A:["Ehrlich? Ich schiebe es auf die nächste BAföG-Zahlung oder frage zur Not meine Eltern. Ein echter Puffer ist nicht da.",
    "Nein. Am Monatsende ist nichts übrig, das ich „weglegen“ könnte — und ich trau diesen Spar-Apps nicht.",
    "Wenn es so klein wäre, dass ich es nicht merke. 5 € die Woche klingt machbar, 50 € im Monat nicht."],
 J:["Ich verschiebe andere Sachen und lebe ein, zwei Wochen sehr knapp. Kreditkarte vermeide ich bewusst.",
    "Mini, auf einem zweiten Konto. Aber ohne System — mal 20 €, mal gar nichts.",
    "Ein fester, automatischer Mini-Betrag, den ich selbst stoppen kann, wenn es eng wird."],
 SO:["Ich hab ein kleines Polster, aber es ist gleichzeitig mein „Urlaubsgeld“ — es vermischt sich alles.",
    "Halb. Ich will, komme aber über den ersten Schritt nicht hinaus, weil ich nicht weiß, wie viel „genug“ ist.",
    "Eine klare, ehrliche Orientierung: was ist ein realistisches erstes Ziel — und dann in Ruhe."],
 T:["Ich kann es aus dem Gehalt auffangen, merke es aber. Reserve ist eher Zufall als Plan.",
    "Ja, aber unstrukturiert. Es liegt auf dem Giro und wird heimlich wieder ausgegeben.",
    "Trennung vom Alltagskonto — sichtbar, aber nicht weggesperrt. Und Zahlen, die ich selbst nachprüfen kann."],
}
turns=[]
for pid,answers in ANS.items():
    for qi,ans in enumerate(answers):
        turns.append({"persona_id":pid,"content":ans,"question_index":qi})
disc = S.record_council(PID,
    prompt="Discovery: Wie gehen junge Erwachsene mit unerwarteten Ausgaben um — und was hält sie vom Notgroschen ab?",
    persona_ids=list(ANS), turns=turns, questions=QS,
    selection_reason="Vier junge Erwachsene mit knappem bis mittlerem Budget, von Studium bis erstem Gehalt — die Bandbreite, für die der Notgroschen am meisten zählt.",
    summary=("Der Notgroschen ist **gewollt, aber nicht gestartet**. Die Hürde ist der _erste Schritt_, nicht die "
             "Disziplin: unklar _wie viel_, _wohin_, und die Angst, nicht mehr ranzukommen."),
    exec_summary=(
        "Vier offene Gespräche zeigen ein klares, wiederkehrendes Muster.\n\n"
        "**Was alle teilen**\n\n"
        "- Ohne Puffer wird ein Vorfall _aufgeschoben_ oder über Eltern/knappes Leben abgefedert.\n"
        "- Der Wunsch nach einem Puffer ist da — der **Start** fehlt.\n\n"
        "**Drei Blocker**\n\n"
        "1. **Unklarheit** — „Wie viel ist genug?“ lähmt (Sophie, Tobias).\n"
        "2. **Größe** — 50 €/Monat schreckt ab, _5 €/Woche_ wirkt machbar (Aylin).\n"
        "3. **Zugriff-Angst** — weggesperrtes Geld ist ein Nein; es muss erreichbar bleiben (Jonas).\n\n"
        "**Vertrauen** entsteht über _Selbstkontrolle_ und Transparenz — nicht über Zwang."),
    key=f"{PID}-disc", store=st)
DISC_ID = disc["id"] if isinstance(disc,dict) and disc.get("id") else disc.get("session",{}).get("id") if isinstance(disc,dict) else None
DISC_ID = disc.get("id") or (disc.get("session") or {}).get("id")
print("discovery council:", DISC_ID)

# ---------------- DEFINE: synthesis ----------------
define = S.record_synthesis(
    title="Define: Der Notgroschen scheitert am ersten Schritt, nicht am Willen",
    start_input="Wie gehen junge Erwachsene mit unerwarteten Ausgaben um — und was hält sie vom Notgroschen ab?",
    goal="Das Discovery-Bild zu einer scharfen Problem-Definition verdichten.",
    council_ids=[DISC_ID] if DISC_ID else [],
    payload={
      "gesamtbild":(
        "Der Notgroschen ist ein **Wunsch ohne Einstieg**. Junge Erwachsene wollen einen Puffer, aber drei "
        "Reibungen verhindern den Start:\n\n"
        "1. **„Wie viel ist genug?“** — fehlende Orientierung lähmt.\n"
        "2. **Zu große erste Rate** — Monatsbeträge schrecken ab; _wöchentliche Mini-Beträge_ wirken machbar.\n"
        "3. **Angst vor Wegsperren** — der Puffer muss _erreichbar_ bleiben, sonst wird gar nicht erst angefangen.\n\n"
        "> „Wenn es so klein wäre, dass ich es nicht merke.“ — Aylin\n\n"
        "Der Hebel ist also **nicht** mehr Disziplin oder ein besseres Produkt, sondern ein **reibungsarmer erster "
        "Schritt** mit Selbstkontrolle und ehrlicher Orientierung."),
      "key_problems":[
        "Keine Orientierung, was ein realistisches erstes Ziel ist [C1]",
        "Monatsbeträge schrecken ab — der Einstieg muss in Wochen-Mini-Schritten denkbar sein",
        "Weggesperrtes Geld = sofortiges Nein; Erreichbarkeit ist Bedingung",
      ],
      "pain_solvers":[
        "Ein **winziger, automatischer** Startbetrag, den man selbst stoppen kann",
        "Eine ehrliche, unverkäuferische Orientierung („ein erstes Ziel: 1 Monatsmiete“)",
      ],
      "offene_fragen":[
        "Welcher Wochenbetrag fühlt sich „unmerklich“ an, ohne bedeutungslos zu sein?",
        "Reicht Sichtbarkeit (eigenes Töpfchen) ohne echtes Wegsperren?",
      ],
      "voices":[
        {"persona_id":A,"persona_name":"Aylin Yıldız","sentiment":"bedingt","relevance":"stark",
         "key_argument":"Nur _unmerklich kleine_ Beträge sind realistisch.","segment":"Studium/knapp"},
        {"persona_id":J,"persona_name":"Jonas Reinhardt","sentiment":"positiv","relevance":"stark",
         "key_argument":"Automatisch ja — aber **selbst stoppbar**.","segment":"Studium/Nebenjob"},
        {"persona_id":SO,"persona_name":"Sophie Bachmann","sentiment":"bedingt","relevance":"stark",
         "key_argument":"Braucht eine klare Antwort auf „wie viel ist genug“.","segment":"Berufseinstieg"},
        {"persona_id":T,"persona_name":"Tobias Wegener","sentiment":"positiv","relevance":"teilweise",
         "key_argument":"Sichtbar trennen, nicht wegsperren; Zahlen nachprüfbar.","segment":"erstes Gehalt"},
      ],
      "positionierung":"Ein **Starthelfer**, kein Sparprodukt: macht den ersten Schritt unmerklich klein, "
                       "sichtbar und jederzeit umkehrbar.",
    },
    key=f"{PID}-define", store=st)
DEFINE_ID = define.get("id") or (define.get("synthesis") or {}).get("id")
print("define synthesis:", DEFINE_ID)

# ---------------- DEVELOP: concept note ----------------
concept = S.create_note(PID, kind="concept", title="Konzept: Notgroschen-Starter (Wochen-Mini + Aufrundung)",
    text=("**Idee:** Ein _Starthelfer_, der den ersten Schritt unmerklich klein macht.\n\n"
          "- **Wochen-Mini:** ein selbst gewählter Mini-Betrag (Default _5 €/Woche_), jederzeit pausierbar.\n"
          "- **Aufrundung:** Zahlungen werden auf den nächsten Euro aufgerundet, der Rest wandert ins Töpfchen.\n"
          "- **Sichtbar, nicht weggesperrt:** das Geld bleibt erreichbar — kein Strafgefühl.\n"
          "- **Ehrliche Orientierung:** „erstes Ziel = 1 Monatsmiete“, offen begründet, **kein** Verkauf.\n\n"
          "> Anti-Ziel: kein neues Konto, kein Vertrieb, keine Gebühr."), store=st)
print("concept:", concept.get("id") or (concept.get("note") or {}).get("id"))

# ---------------- DEVELOP: evaluation council ----------------
EV = {
 A:("bedingt","Das mit den 5 € die Woche nehm ich — solange ich es mit einem Klick stoppen kann und keiner anruft."),
 J:("support","Genau so: automatisch, aber ich behalte den Stopp-Knopf. Aufrundung merke ich eh nicht."),
 SO:("bedingt","Gut, aber sag mir das erste Ziel konkret. 'Eine Monatsmiete' wäre eine Ansage, an der ich mich festhalten kann."),
 T:("support","Sichtbar trennen statt wegsperren trifft es. Wenn die Aufrundung transparent abrechnet, bin ich dabei."),
}
ev_turns=[{"persona_id":pid,"content":c,"stance":stance} for pid,(stance,c) in EV.items()]
evalc = S.record_council(PID,
    prompt="Evaluation: Trägt der „Notgroschen-Starter“ (Wochen-Mini + Aufrundung, jederzeit stoppbar)?",
    persona_ids=list(EV), turns=ev_turns,
    proposal=("**Notgroschen-Starter:** unmerklich kleiner Wochen-Mini (Default 5 €) + Aufrundung beim Bezahlen, "
              "_sichtbar statt weggesperrt_, jederzeit per Klick stoppbar, mit ehrlichem ersten Ziel (1 Monatsmiete)."),
    selection_reason="Dieselben vier Stimmen aus Discovery — sie können first-hand sagen, ob das Konzept ihren echten Blocker trifft.",
    summary=("Breit getragen — **kein Gegenwind**. Bedingung: der _Stopp-Knopf_ und ein **konkretes erstes Ziel** "
             "müssen sichtbar sein."),
    exec_summary=(
        "Vier Reaktionen, **zwei klare Ja** (Jonas, Tobias), **zwei bedingte Ja** (Aylin, Sophie), kein Nein.\n\n"
        "**Was trägt**\n\n"
        "- Die _Selbstkontrolle_ (Stopp-Knopf) ist der Vertrauensanker — sie nimmt Aylin und Jonas die Angst.\n"
        "- _Sichtbar statt weggesperrt_ trifft Tobias' Bedürfnis nach Erreichbarkeit + Nachprüfbarkeit.\n\n"
        "**Auflage aus dem Council**\n\n"
        "1. Das **erste Ziel konkret benennen** („1 Monatsmiete“) — sonst bleibt Sophie hängen.\n"
        "2. Aufrundung **transparent abrechnen**, sonst kippt das Vertrauen."),
    key=f"{PID}-eval", store=st)
EVAL_ID = evalc.get("id") or (evalc.get("session") or {}).get("id")
print("eval council:", EVAL_ID)

# ---------------- DEVELOP: prototype + sessions ----------------
S.register_prototype("notgroschen-starter-v01", "Notgroschen-Starter v0.1",
    "prototypes/notgroschen-starter-v01", entry="index.html", run="static",
    version="v0.1", project_id=PID, fidelity="lo-fi",
    notes="Statischer Klick-Dummy des Wochen-Mini + Aufrundungs-Rechners mit ehrlichem 'wir verdienen nichts'-Hinweis.",
    store=st)
proto = next(p for p in st.list_prototypes() if p["slug"]=="notgroschen-starter-v01")
PROTO_ID = proto["id"]
for i,(pid,verdict,grounded) in enumerate([
    (A,"„5 €, ein Klick, kein Anruf“ — das nimmt mir die Hürde. Den Stopp-Knopf hab ich sofort gesucht und gefunden.",True),
    (SO,"Der Rechner ist klar, aber das **erste Ziel** ('1 Monatsmiete') fehlt mir hier noch sichtbar.",True),
    (T,"Der ehrliche Hinweis 'wir verdienen nichts' wirkt — und die Aufrundung ist nachvollziehbar.",True),
]):
    S.record_prototype_session(pid, PROTO_ID, f"{PID}-ps{i}", "2026-06-06",
        reaction={"persona":NAME[pid],"fidelity":"lo-fi","version":"v0.1",
                  "observed_state_refs":["5 €/Woche (Default-Wochen-Mini)",
                                          "An diesem Rechner verdienen wir nichts. Dein Geld bleibt auf deinem Konto."],
                  "focus":"Senkt der Starter die Einstiegshürde — und bleibt das Vertrauen?",
                  "verdict":verdict,
                  "grounded_verified":grounded},
        key=f"{PID}-ps{i}", store=st)
print("prototype + 3 sessions recorded")

# ---------------- DELIVER: final synthesis ----------------
deliver = S.record_synthesis(
    title="Deliver: Notgroschen-Starter — die dev-fertige Spec",
    start_input="Wie bringen wir junge Erwachsene zum ersten Schritt beim Notgroschen?",
    goal="Discovery → Define → Develop zu einer umsetzbaren Spec mit Empfehlungen und offenen Risiken verdichten.",
    council_ids=[c for c in [DISC_ID,EVAL_ID] if c],
    payload={
      "gesamtbild":(
        "Über Discovery, Define und einen Develop-Test trägt **ein** Befund stabil: der Notgroschen scheitert am "
        "_ersten Schritt_, und ein **unmerklich kleiner, selbst stoppbarer** Starter löst genau das.\n\n"
        "Der Klick-Dummy bestätigt: die **Selbstkontrolle** (Stopp-Knopf) und der ehrliche "
        "„wir verdienen nichts“-Hinweis erzeugen Vertrauen; die offene Lücke ist das **sichtbare erste Ziel**.\n\n"
        "Empfehlung: bauen — schlank, mit den zwei Council-Auflagen als Pflicht."),
      "handlungsempfehlungen":[
        {"text":"**Stopp-Knopf** prominent und ein-Klick — der Vertrauensanker, ohne ihn kein Start.","aufwand":2,"nutzen":5},
        {"text":"**Erstes Ziel sichtbar** machen („1 Monatsmiete“, offen begründet) statt nur Beträge.","aufwand":2,"nutzen":4},
        {"text":"**Aufrundung transparent** abrechnen (jeder Cent nachvollziehbar).","aufwand":3,"nutzen":4},
        {"text":"Kein neues Konto, kein Vertrieb, keine Gebühr — als Produktprinzip festschreiben.","aufwand":1,"nutzen":5},
      ],
      "offene_fragen":[
        "Welcher Default-Wochenbetrag maximiert Start-Rate ohne Bedeutungslosigkeit (A/B: 3/5/7 €)?",
        "Reicht „sichtbar getrennt“ dauerhaft, oder braucht es eine optionale leichte Hürde gegen Impuls-Zugriff?",
      ],
      "positionierung":"**Starthelfer statt Sparprodukt** — unmerklich klein, sichtbar, jederzeit umkehrbar, ehrlich.",
      "voices":[
        {"persona_id":J,"persona_name":"Jonas Reinhardt","sentiment":"positiv","relevance":"stark",
         "key_argument":"Automatisch mit Stopp-Knopf = endlich machbar.","segment":"Studium"},
        {"persona_id":SO,"persona_name":"Sophie Bachmann","sentiment":"bedingt","relevance":"stark",
         "key_argument":"Erst mit sichtbarem erstem Ziel komme ich ins Tun.","segment":"Berufseinstieg",
         "shift":{"from":"bedingt","to":"positiv","trigger":"klarer Stopp-Knopf im Dummy","council_id":EVAL_ID or ""}},
      ],
    },
    key=f"{PID}-deliver", store=st)
print("deliver synthesis:", deliver.get("id") or (deliver.get("synthesis") or {}).get("id"))

DELIVER_ID = deliver.get("id") or (deliver.get("synthesis") or {}).get("id")

# ---- DEVELOP: hi-fi prototype (iterates on the eval-council's two requirements) ----
S.register_prototype("notgroschen-starter-v02","Notgroschen-Starter v0.2","prototypes/notgroschen-starter-v02",
  entry="index.html",run="static",version="v0.2",project_id=PID,fidelity="hi-fi",
  notes="Hi-fi-Iteration: sichtbares erstes Ziel (1 Monatsmiete, Fortschrittsring), prominenter Stopp-Knopf, "
        "transparente Aufrundung — setzt die zwei Auflagen aus dem Evaluation-Council um.",store=st)
PROTO2=next(x["id"] for x in st.list_prototypes() if x["slug"]=="notgroschen-starter-v02")
for i,(pid,nm,verdict) in enumerate([
 (SO,"Sophie Bachmann","Jetzt sehe ich das **erste Ziel** (1 Monatsmiete) sofort — _das_ bringt mich ins Tun."),
 (J,"Jonas Reinhardt","Der Pausieren-Knopf ist jetzt direkt sichtbar. Genau so vertraue ich dem."),
]):
    S.record_prototype_session(pid,PROTO2,f"{PID}-ps2-{i}","2026-06-06",
      reaction={"persona":nm,"fidelity":"hi-fi","version":"v0.2",
                "focus":"Lösen die zwei Council-Auflagen den Rest-Zweifel?","verdict":verdict,
                "observed_state_refs":["Erstes Ziel: 1 Monatsmiete (520 €), Fortschrittsring 32%","Pausieren (Stopp-Knopf)"]},
      key=f"{PID}-ps2-{i}",store=st)

# ---- wire evidence into the plan's diamond (so the project graph shows it) ----
# Evidence belongs on ACT tasks that consume a frame (diverge); syntheses sit on the verify tasks.
from persona_council.services import _plan as PL
PL.add_task(PID,"act","explore","Explore · Discover",consumes=["frame__discover"],task_id="act__discover",store=st)
PL.add_task(PID,"act","explore","Evaluate · Develop",consumes=["frame__develop"],task_id="act__eval",store=st)
PL.add_task(PID,"act","build","Build · Develop",consumes=["frame__develop"],task_id="act__build",store=st)
for task,ref in [("act__discover",{"kind":"council","id":DISC_ID}),
                 ("verify__define",{"kind":"synthesis","id":DEFINE_ID}),
                 ("act__eval",{"kind":"council","id":EVAL_ID}),
                 ("act__build",{"kind":"artifact","id":PROTO_ID}),
                 ("act__build",{"kind":"artifact","id":PROTO2}),
                 ("verify__deliver",{"kind":"synthesis","id":DELIVER_ID})]:
    S.link_evidence(PID,task,ref,store=st)

S.record_open_questions(PID, [
    "Default-Wochenbetrag: 3, 5 oder 7 € — was maximiert die Start-Rate?",
    "Reicht sichtbare Trennung, oder braucht es eine sanfte Zugriff-Hürde?",
], store=st)
print("DONE — project built:", PID)
