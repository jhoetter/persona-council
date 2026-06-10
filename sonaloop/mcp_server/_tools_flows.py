from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_flows(mcp):
    # == Screenshot flows: walkthrough with drop-off, artifact-first (docs/flow-walkthrough.md) ==
    @mcp.tool()
    def define_flow(project_id: str, title: str, steps: list[dict[str, Any]],
                    key: str | None = None) -> dict[str, Any]:
        """Define an ORDERED flow from the project's screenshot assets — each step is
        {asset_id, caption?} (attach the screenshots first via attach_asset /
        attach_prototype_shot). The flow is what personas walk; no live browser anywhere.
        A stable `key` makes re-definition an idempotent upsert."""
        t = time.perf_counter()
        return _env("define_flow", services.define_flow(project_id, title, steps, key), t)

    @mcp.tool()
    def list_flows(project_id: str) -> dict[str, Any]:
        """Every defined flow on a project (id, title, step count)."""
        t = time.perf_counter()
        return _env("list_flows", services.list_flows(project_id), t)

    @mcp.tool()
    def brief_flow_walkthrough(persona_id: str, project_id: str, flow_id: str) -> dict[str, Any]:
        """GATHER one persona's artifact walkthrough: loaded persona context + the ordered
        screens (view_asset each — real pixels) + the authoring contract. YOU walk the flow
        as the persona and record the dual timeline with record_usability_session
        (subject={kind:'flow', id}, fidelity='artifact') — honest friction, the drop-off
        step with its reason, predicted_behaviors with canonical likelihoods."""
        t = time.perf_counter()
        return _env("brief_flow_walkthrough",
                    services.brief_flow_walkthrough(persona_id, project_id, flow_id), t)

    @mcp.tool()
    def flow_funnel(project_id: str, flow_id: str) -> dict[str, Any]:
        """The segment funnel of one flow: per step entered/continued/dropped with the drop
        reasons, the dropping personas and the step captions — where the cohort abandons
        and why, plus the biggest_dropoff headline."""
        t = time.perf_counter()
        return _env("flow_funnel", services.flow_funnel(project_id, flow_id), t)
