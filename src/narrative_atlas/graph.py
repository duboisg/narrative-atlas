"""Cross-link scenes and arcs, then prepare visualization-ready timeline data."""

from __future__ import annotations

from typing import Any


def _normalized(values: list[Any]) -> set[str]:
    return {" ".join(str(value).casefold().split()) for value in values}


def match_score(scene: dict[str, Any], arc: dict[str, Any]) -> int:
    score = 0
    pairs = (
        ("characters_present", "characters_involved"),
        ("themes", "themes"),
        ("conflicts", "conflicts"),
    )
    for scene_key, arc_key in pairs:
        if _normalized(scene.get(scene_key, [])) & _normalized(arc.get(arc_key, [])):
            score += 1
    scene_location = " ".join(str(scene.get("location", "")).casefold().split())
    arc_locations = _normalized(arc.get("locations_involved", []))
    if scene_location and any(
        scene_location in location or location in scene_location for location in arc_locations
    ):
        score += 1
    return score


def link_scenes_to_arcs(
    scenes: list[dict[str, Any]],
    arcs: list[dict[str, Any]],
    *,
    minimum_score: int = 2,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    arc_lookup = {arc["id"]: arc for arc in arcs}
    for arc in arcs:
        arc["scenes"] = []
    for scene in scenes:
        scene["arcs"] = []
        for arc in arcs:
            if match_score(scene, arc) >= minimum_score:
                scene["arcs"].append(arc["id"])
                arc_lookup[arc["id"]]["scenes"].append(scene["id"])
    return scenes, arcs


def _position(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    labels = {"beginning": 0.0, "middle": 0.5, "end": 1.0}
    try:
        return float(value)
    except (TypeError, ValueError):
        return labels.get(str(value).casefold(), 0.5)


def timeline(scenes: list[dict[str, Any]], arcs: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(
        scenes,
        key=lambda scene: (scene.get("chunk_index", 0), _position(scene.get("position", 0.5))),
    )
    characters = sorted(
        {character for scene in ordered for character in scene.get("characters_present", [])}
    )
    return {
        "metadata": {
            "total_scenes": len(ordered),
            "total_arcs": len(arcs),
            "total_characters": len(characters),
        },
        "scenes": ordered,
        "arcs": arcs,
        "characters": {
            "list": characters,
            "presence": {
                character: [
                    scene["id"]
                    for scene in ordered
                    if character in scene.get("characters_present", [])
                ]
                for character in characters
            },
        },
    }
