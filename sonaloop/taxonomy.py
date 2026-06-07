from __future__ import annotations

import re
import unicodedata
from typing import Literal

ToolId = str

EventType = Literal["meeting", "focus", "interruption", "admin", "decision", "site_visit"]
CollaborationMode = Literal["meeting", "working alone", "interruption with another stakeholder", "site visit"]

GENERIC_TOOLS: list[tuple[ToolId, str]] = [
    ("email", "E-Mail"),
    ("calendar", "Kalender"),
    ("documents", "Dokumente"),
    ("notes", "Notizen"),
]

GENERIC_LABELS: dict[str, str] = dict(GENERIC_TOOLS)


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", normalized.lower()).strip("_")
    return slug or "tool"


def _clean_tool_label(value: str) -> str:
    label = value.strip(" .;:()[]{}\"'")
    label = re.sub(r"\s+", " ", label)
    return label


def _split_tool_phrase(value: str) -> list[str]:
    normalized = re.sub(r"\s+(und|and|oder|or)\s+", ",", value, flags=re.IGNORECASE)
    return [_clean_tool_label(part) for part in normalized.split(",") if _clean_tool_label(part)]


def explicit_tools(description: str) -> list[tuple[ToolId, str]]:
    patterns = [
        r"(?:nutzt|verwenden|verwendet|arbeitet mit|arbeitet in|uses|use|works with)\s+(.+?)(?:[.;]|$)",
        r"(?:tooling|tools|stack|software)\s*[:=]\s*(.+?)(?:[.;]|$)",
    ]
    pairs: list[tuple[ToolId, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, description, flags=re.IGNORECASE):
            for label in _split_tool_phrase(match.group(1)):
                tool_id = _slug(label)
                if tool_id not in [existing_id for existing_id, _ in pairs]:
                    pairs.append((tool_id, label))
    return pairs


def normalized_tools(description: str) -> tuple[list[ToolId], list[str]]:
    pairs = explicit_tools(description) or GENERIC_TOOLS
    return [tool_id for tool_id, _ in pairs], [label for _, label in pairs]


def normalized_tool_ids(description: str) -> list[ToolId]:
    return normalized_tools(description)[0]


def tool_label(tool_id: str) -> str:
    return GENERIC_LABELS.get(tool_id, tool_id.replace("_", " ").title())


def tool_labels(tool_ids: list[str]) -> list[str]:
    return [tool_label(tool_id) for tool_id in tool_ids]
