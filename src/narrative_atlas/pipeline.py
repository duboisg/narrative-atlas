"""End-to-end orchestration with checkpointed outputs."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .chunking import Chunk, chunk_document
from .client import ResilientExtractor
from .extractors import SPECS
from .graph import link_scenes_to_arcs, timeline
from .merge import merge_items


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return result or "item"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def _render_markdown(title: str, items: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", "", f"{len(items)} structured records.", ""]
    for item in items:
        lines.extend([f"## {item.get('name', 'Unnamed')}", ""])
        for key, value in item.items():
            if key in {"name", "id"} or key.startswith("_"):
                continue
            label = key.replace("_", " ").title()
            if isinstance(value, list):
                rendered = ", ".join(str(entry) for entry in value)
            elif isinstance(value, dict):
                rendered = f"`{json.dumps(value, ensure_ascii=False)}`"
            else:
                rendered = str(value)
            if rendered:
                lines.extend([f"**{label}:** {rendered}", ""])
    return "\n".join(lines).rstrip() + "\n"


class NarrativePipeline:
    def __init__(self, extractor: ResilientExtractor, output_dir: Path):
        self.extractor = extractor
        self.output_dir = output_dir
        self.checkpoint_dir = output_dir / "checkpoints"

    def _extract_chunk(self, kind: str, chunk: Chunk, *, resume: bool) -> list[dict[str, Any]]:
        checkpoint = self.checkpoint_dir / kind / f"chunk-{chunk.index:04d}.json"
        if resume and checkpoint.exists():
            return json.loads(checkpoint.read_text(encoding="utf-8"))
        spec = SPECS[kind]
        items = self.extractor.extract(
            spec.system_prompt,
            spec.prompt(chunk.text, chunk.title, chunk.index),
            identity_key=spec.identity_key,
        )
        for position, item in enumerate(items):
            item["chunk_index"] = chunk.index
            item["chunk_title"] = chunk.title
            item.setdefault("id", f"{kind[:-1]}-{chunk.index:04d}-{position + 1:03d}")
        _write_json(checkpoint, items)
        time.sleep(self.extractor.request_delay)
        return items

    def run(
        self,
        text: str,
        *,
        kinds: Iterable[str] = ("characters", "locations", "scenes", "arcs"),
        max_characters: int = 24_000,
        overlap_characters: int = 2_000,
        resume: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        selected = list(dict.fromkeys(kinds))
        unknown = sorted(set(selected) - set(SPECS))
        if unknown:
            raise ValueError(f"Unknown extraction types: {', '.join(unknown)}")

        chunks = chunk_document(
            text,
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            self.output_dir / "manifest.json",
            {
                "chunk_count": len(chunks),
                "source_characters": len(text),
                "estimated_source_tokens": max(1, len(text) // 4),
                "extraction_types": selected,
                "chunks": [
                    {
                        "index": chunk.index,
                        "title": chunk.title,
                        "characters": len(chunk.text),
                        "estimated_tokens": chunk.estimated_tokens,
                        "start_character": chunk.start_character,
                        "end_character": chunk.end_character,
                    }
                    for chunk in chunks
                ],
            },
        )

        results: dict[str, list[dict[str, Any]]] = {}
        for kind in selected:
            extracted = [
                item
                for chunk in chunks
                for item in self._extract_chunk(kind, chunk, resume=resume)
            ]
            final = (
                extracted
                if kind == "scenes"
                else merge_items(extracted, SPECS[kind].identity_key)
            )
            for index, item in enumerate(final):
                item["id"] = f"{kind[:-1]}-{index + 1:04d}-{_slug(item.get('name', 'item'))[:48]}"
            results[kind] = final
            _write_json(self.output_dir / f"{kind}.json", final)
            (self.output_dir / f"{kind}.md").write_text(
                _render_markdown(kind.title(), final), encoding="utf-8"
            )

        if "scenes" in results and "arcs" in results:
            scenes, arcs = link_scenes_to_arcs(results["scenes"], results["arcs"])
            results["scenes"], results["arcs"] = scenes, arcs
            _write_json(self.output_dir / "scenes.json", scenes)
            _write_json(self.output_dir / "arcs.json", arcs)
            _write_json(self.output_dir / "timeline.json", timeline(scenes, arcs))
        return results
