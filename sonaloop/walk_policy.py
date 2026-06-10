"""WalkPolicy — the safety contract for LIVE SaaS walkthroughs (rung 3; ticket
live-saas-walkthrough; docs/live-walkthrough-safety.md).

The policy is pure data the harness (browser.py) enforces in-session: an explicit origin
allowlist, deny-by-default risk classes from suggestions/walk_denylist.json (payment /
destructive / outbound / account, EN+DE — data-driven like the friction vocabulary), hard
action/duration caps, and the credential redaction layer. Violations never crash the host —
they come back as structured refusals AND land in the session log, so the block itself is
evidence the replay can cite.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit

from .config import suggestions_dir

DEFAULT_MAX_ACTIONS = 60
DEFAULT_MAX_DURATION_S = 900
_POLICY_KEYS = ("allowed_origins", "blocked_categories", "max_actions", "max_duration_s")
_CREDENTIAL_FIELDS = ("username", "password")
_DEFAULT_PORTS = {"http": 80, "https": 443}


def load_denylist() -> dict[str, Any]:
    """The raw denylist vocabulary (suggestions/walk_denylist.json) — categories with EN+DE terms."""
    path = suggestions_dir() / "walk_denylist.json"
    if not path.exists():
        return {"kind": "walk_denylist", "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def denylist_categories() -> list[str]:
    return [i["category"] for i in load_denylist().get("items", [])]


def resolve_denylist(categories: list[str] | None = None) -> dict[str, list[str]]:
    """The ENFORCED term lists per enabled category: EN+DE merged, lowercased, in JSON order.
    `categories=None` enables ALL categories (the deny-by-default stance)."""
    out: dict[str, list[str]] = {}
    for item in load_denylist().get("items", []):
        cat = item["category"]
        if categories is not None and cat not in categories:
            continue
        terms = item.get("terms") or {}
        merged = [t.strip().lower() for lang in ("en", "de") for t in (terms.get(lang) or []) if t.strip()]
        out[cat] = merged
    return out


@lru_cache(maxsize=32)
def _term_pattern(terms: tuple[str, ...]):
    """One compiled WHOLE-WORD alternation per term tuple. \b is Unicode-aware, so DE
    umlaut terms ("löschen") bound correctly; multi-word terms bound at both phrase ends."""
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b")


def match_denylist(text: str, denylist: dict[str, list[str]]) -> dict[str, str] | None:
    """First {category, term} whose term matches the element's accessible name/text on WORD
    BOUNDARIES, case-insensitive — None when the action is allowed. Whole-word, not substring
    (ticket walk-denylist-match-whole-words): "share" must hit "Share with team", never the
    "shared across React" in a benign description. Over-blocking stays the intended failure
    direction — the fix is boundaries, not term removal."""
    low = (text or "").lower()
    if not low:
        return None
    for cat, terms in denylist.items():
        if not terms:
            continue
        m = _term_pattern(tuple(terms)).search(low)
        if m:
            return {"category": cat, "term": m.group(0)}
    return None


def origin_of(url: str) -> str:
    """The normalized origin (scheme://host[:port]; default ports dropped). Rejects anything that
    is not http(s) — javascript:/file:/data: URLs are never a walkthrough subject."""
    parts = urlsplit(str(url or "").strip())
    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https") or not parts.hostname:
        raise ValueError(f"only http(s) URLs are allowed, got {url!r}")
    host = parts.hostname.lower()
    port = parts.port
    if port is not None and port != _DEFAULT_PORTS[scheme]:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def default_policy(url: str | None = None) -> dict[str, Any]:
    """The safe default WalkPolicy: origin-locked to the subject URL (when given), ALL denylist
    categories enabled, the hard caps at their defaults."""
    return {
        "allowed_origins": [origin_of(url)] if url else [],
        "blocked_categories": denylist_categories(),
        "max_actions": DEFAULT_MAX_ACTIONS,
        "max_duration_s": DEFAULT_MAX_DURATION_S,
    }


def normalize_policy(policy: Any, url: str) -> dict[str, Any]:
    """Validate a host-supplied policy patch over the safe defaults into the FULL enforced policy
    (incl. the resolved `denylist` terms, so what is enforced is exactly what is echoed). Unknown
    keys, unknown categories, non-positive caps and an opening URL outside allowed_origins are
    REJECTED — the safety contract never degrades silently."""
    policy = policy if isinstance(policy, dict) else {}
    unknown = sorted(set(policy) - set(_POLICY_KEYS))
    if unknown:
        raise ValueError(f"unknown policy key(s) {unknown} — valid: {list(_POLICY_KEYS)}")
    out = default_policy(url)
    if "allowed_origins" in policy:
        origins = policy["allowed_origins"]
        if not isinstance(origins, list) or not origins:
            raise ValueError("policy.allowed_origins must be a non-empty list of http(s) origins")
        out["allowed_origins"] = [origin_of(o) for o in origins]
    if "blocked_categories" in policy:
        cats = policy["blocked_categories"]
        known = denylist_categories()
        if not isinstance(cats, list):
            raise ValueError(f"policy.blocked_categories must be a list — valid: {known}")
        bad = sorted(set(cats) - set(known))
        if bad:
            raise ValueError(f"unknown denylist categor(ies) {bad} — valid: {known}")
        out["blocked_categories"] = [c for c in known if c in cats]   # JSON order, deduped
    for cap in ("max_actions", "max_duration_s"):
        if cap in policy:
            v = policy[cap]
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise ValueError(f"policy.{cap} must be a positive integer")
            out[cap] = v
    if origin_of(url) not in out["allowed_origins"]:
        raise ValueError(f"the opening URL's origin {origin_of(url)!r} is not in "
                         f"policy.allowed_origins {out['allowed_origins']} — a walkthrough cannot "
                         "start off its own allowlist")
    out["denylist"] = resolve_denylist(out["blocked_categories"])
    return out


def validate_credentials(credentials: Any) -> dict[str, str] | None:
    """Optional test-login credentials, accepted ONLY at open: {username?, password?} with
    non-empty string values. The harness fills them via {type:'fill_credential'} so the secret
    never transits the host loop; the values become the redaction secrets."""
    if credentials is None:
        return None
    if not isinstance(credentials, dict):
        raise ValueError("credentials must be {username?, password?}")
    unknown = sorted(set(credentials) - set(_CREDENTIAL_FIELDS))
    if unknown:
        raise ValueError(f"unknown credentials key(s) {unknown} — valid: {list(_CREDENTIAL_FIELDS)}")
    out = {}
    for k, v in credentials.items():
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"credentials.{k} must be a non-empty string")
        out[k] = v
    return out or None


def redact(obj: Any, secrets: list[str]) -> Any:
    """The redaction layer: every exact credential value in a retained structure (snapshot, log
    entry, action echo) is replaced with '***' before it leaves the harness. Exact-string only —
    pixel content of screenshots and server-side transforms of a secret are NOT covered (see
    docs/live-walkthrough-safety.md)."""
    if not secrets:
        return obj
    if isinstance(obj, str):
        for s in secrets:
            obj = obj.replace(s, "***")
        return obj
    if isinstance(obj, list):
        return [redact(x, secrets) for x in obj]
    if isinstance(obj, dict):
        return {k: redact(v, secrets) for k, v in obj.items()}
    return obj


def policy_defaults() -> dict[str, Any]:
    """The walk_policy_defaults payload: the safe default policy WITH the resolved denylist —
    hosts see exactly what would be enforced before opening anything."""
    raw = load_denylist()
    return {
        "policy": {**default_policy(), "denylist": resolve_denylist()},
        "categories": [{"category": i["category"], "terms": i.get("terms") or {}}
                       for i in raw.get("items", [])],
        "note": ("Defaults applied by walk_open when no policy is passed: allowed_origins locks to "
                 "the opening URL's origin, ALL denylist categories are enabled, and the hard caps "
                 "are max_actions=" + str(DEFAULT_MAX_ACTIONS) + " / max_duration_s="
                 + str(DEFAULT_MAX_DURATION_S) + ". " + str(raw.get("note") or "")),
    }
