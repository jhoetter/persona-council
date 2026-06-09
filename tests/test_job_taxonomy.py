"""Job/Framework/Format taxonomy (docs/job-framework-format.md).

The canonical taxonomy.json must load, be internally consistent, and reference Frameworks that
are REAL methodology keys plus the implemented/planned Format ids. Follow-on tickets (website
IA, sharpen-question-helper presets, methodology surface) consume these stable ids.
"""
from __future__ import annotations

from sonaloop import job_taxonomy as T
from sonaloop import methodology as M


def test_layers_are_the_three_axes():
    layers = T.layers()
    assert set(layers) == {"job", "framework", "format"}
    for layer in layers.values():
        assert layer["name"] and layer["definition"] and layer["doctor_analogy"]


def test_framework_ids_are_real_methodology_keys(store):
    registry = {m["key"] for m in M.list_methodologies(store=store)}
    assert T.framework_keys() <= registry


def test_seed_jobs_present_and_resolve():
    jobs = {j["id"] for j in T.jobs()}
    assert {
        "positioning", "pricing", "jtbd_demand",
        "ideation_hmw", "continuous_discovery", "churn_reasons",
    } <= jobs

    known_formats = T.format_ids()
    known_frameworks = T.framework_keys()
    for job in T.jobs():
        assert job["frameworks"], job["id"]
        assert job["default_framework"] in job["frameworks"], job["id"]
        assert set(job["frameworks"]) <= known_frameworks, job["id"]
        assert set(job["formats"]) <= known_formats, job["id"]
        cov = job["coverage"]
        assert cov["min_personas"] >= 1 and cov["persona_axes"], job["id"]


def test_planned_formats_referenced_by_stable_id():
    by_id = {f["id"]: f for f in T.formats()}
    assert {"council", "prototype_test", "head_to_head", "red_team"} <= set(by_id)
    assert by_id["head_to_head"]["status"] == "planned"
    assert by_id["red_team"]["status"] == "planned"


def test_get_job_round_trips():
    assert T.get_job("positioning")["default_framework"] == "double_diamond"


def test_framework_descriptions_are_structured_and_complete(store):
    """The website 'how it works' page + the job presets consume ONE clean shape:
    {id, name, what, when, stages:[{id, name, what}]} — every Framework must fill all fields."""
    descs = T.framework_descriptions(store=store)
    ids = [d["id"] for d in descs]
    # every taxonomy Framework with a real methodology spec is described, in taxonomy order
    assert ids == [fw["id"] for fw in T.frameworks() if fw["methodology_key"] in {m["key"] for m in M.list_methodologies(store=store)}]
    assert {"double_diamond", "double_diamond_deep", "dschool_micro", "lean_jtbd"} <= set(ids)
    for d in descs:
        assert d["id"] and d["name"] and d["what"] and d["when"], d["id"]
        assert d["stages"], d["id"]
        for st in d["stages"]:
            assert st["id"] and st["name"] and st["what"], (d["id"], st)


def test_get_framework_description_round_trips(store):
    dd = T.get_framework_description("double_diamond", store=store)
    assert dd["name"] == "Double Diamond"
    assert [s["id"] for s in dd["stages"]] == ["discover", "define", "develop", "deliver"]


def test_get_framework_description_unknown_raises(store):
    import pytest
    with pytest.raises(KeyError):
        T.get_framework_description("nope", store=store)
