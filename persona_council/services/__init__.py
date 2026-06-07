"""Service layer (split out of the former monolithic persona_council/services.py).

Behavior-preserving package split: every previously-public name on
`persona_council.services` is still importable as `services.<name>` and via
`from persona_council.services import <name>`. The original file's bare-name
cross-calls are preserved verbatim in the submodules; this __init__ binds the
needed cross-module names into each submodule's globals after all submodules are
imported, so those LOAD_GLOBAL lookups resolve exactly as before — without
introducing import cycles.

The host-authored simulation globals cluster (simulate_day / record_day /
record_month_bundle + the generate_day_plan_with_llm / generate_activity
monkeypatch targets) all live together in ._simulation, so the
globals()[...] = ... swap-and-restore keeps working unchanged.
"""

from __future__ import annotations

# --- Re-export the non-function module surface (constants, models, helpers that
#     the original services.py exposed as module attributes) -------------------
from ..config import (
    ROOT, utc_now_iso, content_language, ensure_content_language, language_instruction,
    critic_threshold, critic_sample_k,
)
from ..models import (
    CalendarEvent,
    CouncilSession,
    DailySummary,
    Evidence,
    ExperienceEvent,
    MetaReport,
    OpenQuestion,
    PainPointObservation,
    Persona,
    PrototypeSession,
    Reflection,
    ResearchProject,
    SimulationResult,
    Synthesis,
)
from ..storage import Store
from ..taxonomy import GENERIC_TOOLS, normalized_tool_ids, normalized_tools
from .. import memory as memory_mod
from .. import evaluation as evaluation_mod
from ..llm_simulation import (
    build_cohort_critic_prompt,
    build_consolidation_prompt,
    build_meta_outline_prompt,
    build_meta_section_prompt,
    validate_meta_outline_payload,
    validate_meta_section_payload,
    build_digest_prompt,
    build_eval_critic_prompt,
    build_evidence_check_prompt,
    build_persona_revision_prompt,
    build_plan_prompt,
    build_profile_prompt,
    build_synthesis_prompt,
    generate_activity,
    generate_day_plan_with_llm,
    validate_activity_payload,
    validate_cohort_critic_payload,
    validate_digest_payload,
    validate_eval_critic_payload,
    validate_evidence_check_payload,
    validate_memory_deltas_payload,
    validate_persona_revision_payload,
    validate_plan_payload,
    validate_profile_payload,
    validate_synthesis_payload,
)

# --- Submodules (order matters only for *binding*, not for import-time safety:
#     no submodule references another submodule at import time) ----------------
from . import _common
from . import _personas
from . import _simulation
from . import _consolidation
from . import _memory
from . import _evaluation
from . import _snapshots
from . import _councils
from . import _synthesis
from . import _research
from . import _engines
from . import _sections

_SUBMODULES = (
    _common, _personas, _simulation, _consolidation, _memory, _evaluation,
    _snapshots, _councils, _synthesis, _research, _engines, _sections,
)


def _collect_public_symbols() -> dict[str, object]:
    """Build the registry of every symbol defined in a submodule.

    A name is owned by the submodule that *defines* it (its __module__ ends with
    that submodule). For plain constants (no __module__) the first submodule that
    declares it wins; engines' redefined brief_next/record_judgment win because we
    take the value as bound on the submodule that lists it in its own __all__-like
    body — handled by preferring the engines copy explicitly below.
    """
    registry: dict[str, object] = {}
    for mod in _SUBMODULES:
        mod_name = mod.__name__.rsplit(".", 1)[-1]
        for name, value in vars(mod).items():
            if name.startswith("__"):
                continue
            owner = getattr(value, "__module__", None)
            if owner is not None:
                # Only register functions/classes physically defined in THIS submodule.
                if owner.endswith("." + mod_name):
                    registry[name] = value
            else:
                # constants / non-introspectable: register once (first definer)
                registry.setdefault(name, value)
    return registry


_REGISTRY = _collect_public_symbols()

# brief_next / record_judgment: the dispatching versions defined in _engines are
# the public ones (they shadow the methodology-engine imports). Ensure those win.
_REGISTRY["brief_next"] = _engines.brief_next
_REGISTRY["record_judgment"] = _engines.record_judgment

# The methodology-registry / suggestions / plan-engine / prototype seam names were module
# globals of the original services.py. Submodules reference some of them by bare name, so they
# must be part of the bound registry too. The constellation runtime was retired (HX3): a
# methodology only SEEDS the plan (set_project_methodology re-seeds an existing project; HX3).
for _eng_name in (
    "MethodologyError", "list_methodologies", "get_methodology", "register_methodology",
    "set_project_methodology",
    "suggest_capabilities", "suggest_roles", "suggest_artifact_types", "suggest_section_kinds", "suggest_methodologies",
    "PlanError", "new_plan", "validate_plan", "seed_plan_from_methodology", "ready_tasks",
    "is_complete", "render_plan_md",
    "_plan", "_proto", "_browser",
):
    _REGISTRY[_eng_name] = getattr(_engines, _eng_name)
del _eng_name

# --- Bind cross-module references into each submodule's globals so the verbatim
#     bare-name calls resolve exactly like the original single-module file. We do
#     NOT overwrite a name a submodule already defines locally (protects the
#     engines dispatch redefinitions and any local shadowing). ------------------
for _mod in _SUBMODULES:
    _mdict = vars(_mod)
    for _name, _value in _REGISTRY.items():
        if _name not in _mdict:
            _mdict[_name] = _value

# --- Promote everything to the package namespace (services.<name>) -------------
for _name, _value in _REGISTRY.items():
    globals()[_name] = _value

# Re-export the methodology-registry / suggestions / plan-engine / prototype seam names
# that the original services.py exposed (they live on _engines after its imports).
for _name in (
    "MethodologyError", "list_methodologies", "get_methodology", "register_methodology",
    "set_project_methodology",
    "suggest_capabilities", "suggest_roles", "suggest_artifact_types", "suggest_section_kinds", "suggest_methodologies",
    "PlanError", "new_plan", "validate_plan", "seed_plan_from_methodology", "ready_tasks",
    "is_complete", "render_plan_md",
    "_plan", "_proto", "_browser",
):
    globals()[_name] = getattr(_engines, _name)

# Stdlib / typing names the original module exposed as attributes (some callers do
# services.Path / services.datetime etc.). Re-export to preserve the surface.
from typing import Any  # noqa: E402,F401
from pathlib import Path  # noqa: E402,F401
from datetime import date, datetime, time, timedelta  # noqa: E402,F401

del _name, _value, _mod, _mdict
del _REGISTRY, _collect_public_symbols

# --- Single-module patch semantics --------------------------------------------
# The original services.py was ONE module: setattr(services, "X", v) (e.g. tests
# monkeypatching generate_day_plan_with_llm / generate_activity / ROOT, or the
# record_day/record_month_bundle globals() swap reading those names) all hit the
# same namespace that every function read its globals from. After the package
# split a name like ROOT lives in each submodule's own __dict__, so a plain
# setattr on the package would not reach the functions. We restore the original
# behavior with a forwarding module: assigning services.X also writes X into every
# submodule that already defines X, so existing globals lookups see the new value.
import sys as _sys
import types as _types


class _ServicesModule(_types.ModuleType):
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        subs = self.__dict__.get("_SUBMODULES")
        if subs and not name.startswith("__"):
            for _m in subs:
                if name in _m.__dict__:
                    _m.__dict__[name] = value


_self = _sys.modules[__name__]
_self.__class__ = _ServicesModule
# _SUBMODULES stays as a module attribute so the forwarder can reach the submodules.
