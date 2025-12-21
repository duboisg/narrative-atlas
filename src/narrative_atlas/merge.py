"""Deterministic reconciliation of entities repeated across chunks."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

SIGNIFICANCE = {"low": 1, "medium": 2, "high": 3}


def canonical(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def _merge_strings(left: str, right: str) -> str:
    left, right = left.strip(), right.strip()
    if canonical(left) == canonical(right) or canonical(right) in canonical(left):
        return left
    if canonical(left) in canonical(right):
        return right
    if len(right) > len(left) * 1.5:
        return right
    if len(left) > len(right) * 1.5:
        return left
    separator = " " if left.endswith((".", ";", ":")) else ". "
    return f"{left}{separator}{right}"


def merge_item(existing: dict[str, Any], new: dict[str, Any], key: str = "name") -> dict[str, Any]:
    merged = deepcopy(existing)
    for field, value in new.items():
        if field == key or value in (None, "", []):
            continue
        if field == "first_mentioned" and merged.get(field):
            continue
        if field == "significance" and merged.get(field):
            old_rank = SIGNIFICANCE.get(canonical(merged[field]), 0)
            new_rank = SIGNIFICANCE.get(canonical(value), 0)
            merged[field] = value if new_rank > old_rank else merged[field]
        elif isinstance(value, list) and isinstance(merged.get(field), list):
            seen = {canonical(item) for item in merged[field]}
            merged[field].extend(item for item in value if canonical(item) not in seen)
        elif isinstance(value, str) and isinstance(merged.get(field), str):
            merged[field] = _merge_strings(merged[field], value)
        elif field not in merged:
            merged[field] = deepcopy(value)
        elif isinstance(value, dict) and isinstance(merged[field], dict):
            merged[field] = {**merged[field], **value}
    merged["_merge_count"] = int(existing.get("_merge_count", 1)) + 1
    return merged


def merge_items(items: Iterable[dict[str, Any]], key: str = "name") -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    positions: dict[str, int] = {}
    for item in items:
        identity = canonical(item.get(key, ""))
        if not identity:
            result.append(deepcopy(item))
        elif identity in positions:
            index = positions[identity]
            result[index] = merge_item(result[index], item, key)
        else:
            positions[identity] = len(result)
            result.append(deepcopy(item))
    return result
