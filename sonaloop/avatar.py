from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from .config import ROOT, load_env, utc_now_iso
from .services import stable_id
from .storage import Store


def _post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def build_avatar_prompt(persona: dict[str, Any], style: str | None = None) -> str:
    role = persona["role"]["title"]
    company = persona["company_context"]["industry"]
    working_style = persona["personality"]["working_style"]
    traits = persona.get("identity_traits", {})
    gender = traits.get("gender_presentation", "unspecified")
    age_range = traits.get("age_range", "unspecified")
    _constraints = traits.get("avatar_constraints", [])
    constraints = "; ".join(_constraints) if isinstance(_constraints, list) else str(_constraints)
    avatar_profile = traits.get("avatar_profile", {})
    if isinstance(avatar_profile, dict):
        visual_profile = (
            f"Distinct visual profile: {avatar_profile.get('hair', 'distinct professional hairstyle')}; "
            f"{avatar_profile.get('glasses', 'individual eyewear choice')}; "
            f"{avatar_profile.get('expression', 'individual professional expression')}; "
            f"{avatar_profile.get('clothing', 'distinct professional clothing')}; "
            f"{avatar_profile.get('role_cue', 'role-appropriate office background')}."
        )
    else:
        # avatar_profile authored as free text (or empty) — use it directly.
        profile_text = str(avatar_profile).strip() or "distinct professional appearance for this role"
        notes = traits.get("appearance_notes")
        visual_profile = f"Distinct visual profile: {profile_text}." + (f" {notes}." if notes else "")
    identity_clause = f" named {persona['display_name']}"
    if gender != "unspecified":
        identity_clause += f", with {gender} gender presentation"
    if age_range != "unspecified":
        identity_clause += f", age range {age_range}"
    return (
        f"Create a professional editorial avatar portrait of a fictional person{identity_clause}, "
        f"working in the role of {role} in {company}. "
        f"The person should feel {working_style}. Neutral studio background, natural expression, "
        f"clean modern business look, no text, no logos, no photorealistic claim of a real person. "
        f"{visual_profile} "
        f"Hard constraints: {constraints or 'do not contradict the display name, role, or provided identity traits'}. "
        f"Style: {style or 'polished semi-realistic professional avatar'}. "
        f"Same overall illustration language as the other personas, but a clearly different face, hair, clothing, and silhouette."
    )


def generate_persona_avatar(persona_id: str, style: str | None = None, store: Store | None = None) -> dict[str, Any]:
    load_env()
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    out_dir = Path(os.getenv("AVATAR_OUTPUT_DIR", "data/avatars"))
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_avatar_prompt(persona, style)
    result = _post_json(
        "https://api.openai.com/v1/images/generations",
        {"model": model, "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "medium"},
        api_key,
    )
    data = result["data"][0]
    if data.get("b64_json"):
        img_bytes = base64.b64decode(data["b64_json"])
    elif data.get("url"):
        with urllib.request.urlopen(data["url"], timeout=180) as resp:
            img_bytes = resp.read()
    else:
        raise RuntimeError("No image payload returned by OpenAI image generation.")
    filename = f"{persona['slug']}-{stable_id('avatar', persona['id'], prompt).split('_')[1]}.png"
    out_path = out_dir / filename
    out_path.write_bytes(img_bytes)
    avatar = {
        "path": str(out_path.relative_to(ROOT)),
        "prompt": prompt,
        "model": model,
        "validated_against": ["display_name", "role", "identity_traits"],
        "known_risks": [],
        "generated_at": utc_now_iso(),
    }
    persona["avatar"] = avatar
    persona["updated_at"] = utc_now_iso()
    store.upsert_persona(persona, reason="generate_persona_avatar")
    return avatar
