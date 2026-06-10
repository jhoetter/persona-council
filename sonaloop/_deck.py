"""sonaloop._deck — VENDORED COPY of the sonaloop-design deck master template.

Do not edit by hand. Single source of truth: ../sonaloop-design/deck.data.mjs ->
scripts/gen-deck.mjs. Refresh with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency."""

# Colour roles, bare RRGGBB (python-pptx convention). PALETTE["series"] is the chart order.
PALETTE: dict = {
  "bg": "FAF8F3",
  "panel": "FFFFFF",
  "surface2": "F1EFE8",
  "line": "E9E5DB",
  "ink": "1A1815",
  "muted": "635E56",
  "faint": "8C857A",
  "accent": "5E6AD2",
  "accentInk": "FFFFFF",
  "accentWeak": "ECEBF8",
  "green": "3D9B6B",
  "amber": "B87A25",
  "red": "CF4D5F",
  "violet": "7A5ED1",
  "blue": "3D7FC4",
  "skep": "C2683F",
  "series": [
    "5E6AD2",
    "7A5ED1",
    "3D7FC4",
    "3D9B6B",
    "B87A25",
    "CF4D5F",
    "C2683F"
  ]
}

# Slide geometry (inches) + the shared frame coordinates every layout hangs off.
FRAME: dict = {
  "width": 13.333,
  "height": 7.5,
  "margin": 0.7,
  "headerTop": 0.5,
  "headerH": 0.9,
  "ruleY": 1.34,
  "ruleW": 0.85,
  "contentTop": 1.65,
  "footerH": 0.42
}

# Role-based type scale (pt). "mono" selects the Geist Mono face in PPTX.
TYPE: dict = {
  "eyebrow": {
    "size": 12,
    "bold": True,
    "mono": True,
    "color": "accent"
  },
  "display": {
    "size": 40,
    "bold": True,
    "mono": False,
    "color": "ink"
  },
  "title": {
    "size": 24,
    "bold": True,
    "mono": False,
    "color": "ink"
  },
  "subtitle": {
    "size": 14,
    "bold": False,
    "mono": False,
    "color": "muted"
  },
  "lead": {
    "size": 17,
    "bold": False,
    "mono": False,
    "color": "ink"
  },
  "statement": {
    "size": 26,
    "bold": True,
    "mono": False,
    "color": "ink"
  },
  "body": {
    "size": 13,
    "bold": False,
    "mono": False,
    "color": "ink"
  },
  "quote": {
    "size": 22,
    "bold": False,
    "mono": False,
    "color": "ink"
  },
  "attribution": {
    "size": 12,
    "bold": True,
    "mono": False,
    "color": "ink"
  },
  "caption": {
    "size": 10,
    "bold": False,
    "mono": False,
    "color": "faint"
  },
  "num": {
    "size": 16,
    "bold": True,
    "mono": True,
    "color": "faint"
  },
  "bignum": {
    "size": 110,
    "bold": True,
    "mono": True,
    "color": "accentWeak"
  },
  "kpi": {
    "size": 30,
    "bold": True,
    "mono": False,
    "color": "ink"
  },
  "kpiLabel": {
    "size": 10,
    "bold": False,
    "mono": False,
    "color": "muted"
  }
}

# Insight-family tones (mirrors the report's callout cards).
TONES: dict = {
  "insight": {
    "color": "accent",
    "label": "Insight"
  },
  "recommendation": {
    "color": "green",
    "label": "Recommendation"
  },
  "risk": {
    "color": "amber",
    "label": "Risk"
  }
}

# The layout catalogue — every slide kind the master template defines, in deck order.
LAYOUTS: list = [
  {
    "key": "cover",
    "title": "Cover",
    "desc": "The brand moment — logo, study title, scope line and date, with an optional painterly canvas band on the right. Every customer deck opens here."
  },
  {
    "key": "agenda",
    "title": "Agenda",
    "desc": "Numbered contents derived from the report sections — the reader’s map of the deck."
  },
  {
    "key": "section",
    "title": "Section divider",
    "desc": "A breathing-room slide between chapters: oversized numeral, chapter title, one-line framing."
  },
  {
    "key": "canvas-section",
    "title": "Canvas section",
    "desc": "The cinematic divider: a full-bleed brand canvas with the chapter card floating bottom-left — section art instead of whitespace."
  },
  {
    "key": "summary",
    "title": "Executive summary",
    "desc": "The three or four takeaways a sponsor reads if they read nothing else — each a claim plus one supporting line."
  },
  {
    "key": "insight",
    "title": "Insight",
    "desc": "One finding stated as a headline, evidence bullets beneath it, an optional supporting chart on the right."
  },
  {
    "key": "recommendation",
    "title": "Recommendation",
    "desc": "The green-toned action slide: what to do, why it works, and the effort·impact meta line."
  },
  {
    "key": "risk",
    "title": "Risk",
    "desc": "The amber-toned counterpart: what could break the recommendation, and the early signal to watch."
  },
  {
    "key": "quote",
    "title": "Quote",
    "desc": "One persona voice, large and attributed — the emotional anchor of a chapter."
  },
  {
    "key": "voices",
    "title": "Voices",
    "desc": "The report’s Stimmen panel as a slide: where each persona stands, with sentiment and their key argument."
  },
  {
    "key": "stats",
    "title": "Stats",
    "desc": "A KPI row — the study (or a finding) in four big numbers with quiet sublines."
  },
  {
    "key": "pillars",
    "title": "Pillars",
    "desc": "Three or four capability columns, each led by a hi-fi icon chip — the “how this study worked” slide, and the natural home of the icon library in a deck."
  },
  {
    "key": "chart",
    "title": "Chart",
    "desc": "A full-width native chart led by its takeaway as the headline — the chart is evidence, the headline is the point."
  },
  {
    "key": "comparison",
    "title": "Comparison",
    "desc": "Two columns, status quo against the proposal — the cleanest way to show what actually changes."
  },
  {
    "key": "timeline",
    "title": "Timeline",
    "desc": "Next steps as a horizontal sequence — horizon label, step title, one line of substance each."
  },
  {
    "key": "closing",
    "title": "Closing",
    "desc": "Methodology footnote, where the full evidence lives, and the contact line — the deck’s quiet sign-off."
  },
  {
    "key": "content",
    "title": "Content (fallback)",
    "desc": "The general-purpose slide: heading, typed blocks (paragraphs, bullets, quotes, inline callouts), optional chart or image on the right."
  },
  {
    "key": "image",
    "title": "Image (fallback)",
    "desc": "A fitted, centred image with caption — prototype screenshots, attached assets, persona avatars."
  }
]

# Placeholder content for every layout — the fictitious "Healthy eating without effort" study. Each entry is
# the exact slide dict sonaloop/_pptx.render() accepts; together they are the demo deck.
DECK_TITLE: str = "Healthy eating without effort"
SAMPLE_SLIDES: list = [
  {
    "kind": "cover",
    "logo": True,
    "canvas": "dawn",
    "eyebrow": "Research Report",
    "title": "Healthy eating without effort",
    "subtitle": "What keeps busy people from eating well — and what would actually change it",
    "meta": "German eating panel · 4 personas · 6 councils · 124 simulated days",
    "date": "June 2026"
  },
  {
    "kind": "agenda",
    "heading": "Contents",
    "items": [
      "Executive summary",
      "Decision fatigue, not knowledge",
      "What the panel already tried",
      "Three product directions",
      "Risks & open questions",
      "Next steps"
    ]
  },
  {
    "kind": "section",
    "num": "02",
    "title": "Decision fatigue, not knowledge",
    "subtitle": "Why the 6 pm question defeats every meal plan the panel has tried"
  },
  {
    "kind": "canvas-section",
    "canvas": "meadow",
    "num": "04",
    "title": "Three product directions",
    "subtitle": "What the panel would actually adopt — ranked by leverage"
  },
  {
    "kind": "summary",
    "heading": "Executive summary",
    "items": [
      {
        "title": "The blocker is the 6 pm decision",
        "text": "Every persona knows what healthy means. Plans fail at the moment of deciding tonight’s dinner, when energy is lowest."
      },
      {
        "title": "Plans collapse against real evenings",
        "text": "Meal prep survives Monday and Tuesday, then erodes. By Thursday the panel is improvising — and improvising defaults to takeaway."
      },
      {
        "title": "Low-friction defaults win",
        "text": "A pre-decided weekly menu with a one-tap shopping basket out-performed every willpower-based approach the panel discussed."
      },
      {
        "title": "Budget is the adoption ceiling",
        "text": "Mehmet and Sabine cap any solution near €60/week — defaults that creep past it get abandoned within two weeks."
      }
    ]
  },
  {
    "kind": "insight",
    "tone": "insight",
    "num": "01",
    "statement": "The real bottleneck is deciding at 6 pm — not cooking skill, not nutrition knowledge.",
    "support": [
      "All four personas could name a healthy dinner they like; none could say what they’d eat tonight.",
      "In 124 simulated days, the panel skipped cooking on 71% of evenings that started without a plan.",
      "When a plan existed before 4 pm, home cooking held up even on stressful days."
    ],
    "chart": {
      "type": "bar",
      "categories": [
        "Decision fatigue",
        "Time to cook",
        "Budget pressure",
        "Knowledge gap"
      ],
      "values": [
        9,
        6,
        4,
        2
      ]
    },
    "footnote": "Mentions across 6 councils, weighted by vote support."
  },
  {
    "kind": "recommendation",
    "tone": "recommendation",
    "num": "02",
    "statement": "Ship a Sunday default menu: five pre-decided dinners with a one-tap shopping basket.",
    "support": [
      "Removes the 6 pm decision entirely — the highest-leverage friction point the study found.",
      "Lena and Tom would pay for it today; Mehmet adopts if the basket stays under €60/week.",
      "Swappable single dinners keep autonomy without reopening the whole decision."
    ],
    "meta": "Effort 2/5 · Value 5/5 · Quick win"
  },
  {
    "kind": "risk",
    "tone": "risk",
    "num": "03",
    "statement": "Budget-constrained personas churn quietly if the default basket creeps past €60 a week.",
    "support": [
      "Mehmet treats €60/week as a hard ceiling — one overage and the service is “not for people like me”.",
      "Price creep is invisible in usage metrics until the second skipped week.",
      "Watch-signal: basket edits that only remove items two weeks in a row."
    ],
    "meta": "Likelihood medium · Impact high"
  },
  {
    "kind": "quote",
    "text": "I don’t fail at cooking, I fail at deciding. By the time I know what I want to eat, the kebab is faster.",
    "attribution": "Mehmet",
    "role": "Student · budget-constrained · eats out 5×/week"
  },
  {
    "kind": "voices",
    "heading": "Where the panel stands on the default menu",
    "items": [
      {
        "name": "Lena",
        "role": "Marketing manager, 34",
        "sentiment": "support",
        "text": "Would pay from day one — “deciding is the only part of cooking I hate”."
      },
      {
        "name": "Mehmet",
        "role": "Student, 23",
        "sentiment": "conditional",
        "text": "In, if the weekly basket stays under €60 and lunch leftovers count."
      },
      {
        "name": "Sabine",
        "role": "Working mom, 41",
        "sentiment": "support",
        "text": "Needs kid-safe swaps per dinner; otherwise the default fails on Wednesdays."
      },
      {
        "name": "Tom",
        "role": "Developer, 29",
        "sentiment": "opposed",
        "text": "Rejects subscriptions on principle — would only use a free, exportable menu."
      }
    ]
  },
  {
    "kind": "stats",
    "heading": "The study in numbers",
    "items": [
      {
        "label": "Personas",
        "value": 4,
        "sub": "German eating panel"
      },
      {
        "label": "Councils",
        "value": 6,
        "sub": "incl. 2 red-team rounds"
      },
      {
        "label": "Simulated days",
        "value": 124,
        "sub": "Jan–May 2026"
      },
      {
        "label": "Evenings unplanned",
        "value": "71%",
        "sub": "ended in takeaway or skipping"
      }
    ]
  },
  {
    "kind": "pillars",
    "heading": "How this study worked",
    "items": [
      {
        "icon": "personas",
        "title": "Grounded personas",
        "text": "Four panel members with durable identities, memories and provenance — not improvised characters."
      },
      {
        "icon": "calendar",
        "title": "Simulated days",
        "text": "124 lived evenings: commutes, fridge stares, takeaway temptations — friction observed, not asked about."
      },
      {
        "icon": "councils",
        "title": "Structured councils",
        "text": "Six moderated debates with votes on the record, including two red-team rounds against our own thesis."
      },
      {
        "icon": "syntheses",
        "title": "Inspectable evidence",
        "text": "Every claim in this deck links back to a session you can open and read end-to-end."
      }
    ]
  },
  {
    "kind": "chart",
    "num": "02",
    "heading": "Weeknight cooking collapses after Tuesday",
    "chart": {
      "type": "line",
      "series": [
        {
          "label": "Home-cooked dinners",
          "points": [
            86,
            74,
            61,
            48,
            42,
            55,
            63
          ]
        },
        {
          "label": "With Sunday default (pilot)",
          "points": [
            88,
            84,
            79,
            76,
            71,
            74,
            77
          ]
        }
      ],
      "labels": [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun"
      ]
    },
    "footnote": "Share of panel evenings cooked at home, % — 124 simulated days vs. 14-day pilot."
  },
  {
    "kind": "comparison",
    "heading": "Tonight, unaided vs. with a Sunday default",
    "left": {
      "title": "Status quo",
      "items": [
        "6 pm: open fridge, no plan, low energy",
        "20 minutes of app-scrolling for recipes",
        "Missing one ingredient kills the dish",
        "Default outcome: delivery or skipping"
      ]
    },
    "right": {
      "title": "With the default menu",
      "items": [
        "Dinner was decided on Sunday",
        "Basket arrived Tuesday — everything’s there",
        "One-tap swap if the day went sideways",
        "Default outcome: the planned meal"
      ]
    }
  },
  {
    "kind": "timeline",
    "heading": "Next steps",
    "steps": [
      {
        "label": "Week 1",
        "title": "Prototype the default menu",
        "text": "Clickable Sunday-planning flow; five dinners, one-tap basket."
      },
      {
        "label": "Weeks 2–3",
        "title": "Panel walkthrough",
        "text": "All four personas drive the prototype; measure drop-off per step."
      },
      {
        "label": "Week 4",
        "title": "Price the basket",
        "text": "Test the €60 ceiling with Mehmet and Sabine head-to-head."
      },
      {
        "label": "Q3",
        "title": "Live pilot",
        "text": "20 households, two weeks, against the cooked-dinner baseline."
      }
    ]
  },
  {
    "kind": "closing",
    "logo": True,
    "title": "Thank you",
    "text": "Built with the Sonaloop research engine: grounded personas, simulated days, structured councils — every statement in this deck traces back to an inspectable session.",
    "meta": "Full report, persona sessions and evidence: Sonaloop workspace · Healthy eating without effort",
    "contact": "research@sonaloop.dev"
  },
  {
    "kind": "content",
    "num": "03",
    "heading": "What the panel already tried",
    "blocks": [
      {
        "type": "p",
        "text": "Every persona has a failed system in the drawer — the pattern is identical: high setup energy, no resilience to one bad day."
      },
      {
        "type": "li",
        "text": "Lena: Sunday meal prep — abandoned after three weeks (“Sunday became a chore”)."
      },
      {
        "type": "li",
        "text": "Sabine: family meal plan on the fridge — collapses whenever a kid vetoes a dinner."
      },
      {
        "type": "li",
        "text": "Tom: macro-tracking app — precise, joyless, deleted after a month."
      },
      {
        "type": "callout",
        "kind": "accent",
        "label": "Insight",
        "text": "Systems that demand daily willpower decay; systems that remove decisions persist."
      }
    ],
    "chart": {
      "type": "gauge",
      "items": [
        {
          "label": "Systems still in use after 8 weeks",
          "value": 1,
          "max": 7
        }
      ]
    },
    "footnote": "Sources: councils 01–04, day simulations Jan–Mar."
  },
  {
    "kind": "image",
    "num": "04",
    "heading": "Prototype — Sunday planning flow",
    "image": None,
    "caption": "Default menu screen: five dinners, one-tap basket, swap affordance per row."
  }
]
