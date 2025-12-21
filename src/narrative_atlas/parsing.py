"""Defensive parsing for imperfect or truncated model output."""

from __future__ import annotations

import json
import re
from typing import Any


def strip_code_fence(content: str) -> str:
    value = content.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return "\n".join(lines).strip()
    return value


def appears_truncated(content: str) -> bool:
    value = strip_code_fence(content)
    return value.count("[") > value.count("]") or value.count("{") > value.count("}")


def _close_containers(content: str) -> str:
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", content).rstrip()
    # Closing a top-level array is safe only when every object inside it is complete.
    # Never synthesize a closing brace: that can turn a partial record into plausible data.
    if value.count("{") == value.count("}"):
        value += "]" * max(0, value.count("[") - value.count("]"))
    return value


def _scan_objects(content: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    items: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(content):
        start = content.find("{", cursor)
        if start < 0:
            break
        try:
            value, length = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            cursor = start + 1
            continue
        if isinstance(value, dict):
            items.append(value)
        cursor = start + length
    return items


def parse_json_items(content: str) -> list[dict[str, Any]]:
    """Parse a JSON object/array, repairing simple truncation and salvaging complete objects."""
    value = strip_code_fence(content)
    candidates = (value, _close_containers(value))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    return _scan_objects(value)
