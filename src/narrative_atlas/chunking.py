"""Structure-aware chunking for long documents."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    title: str
    start_character: int
    end_character: int

    @property
    def estimated_tokens(self) -> int:
        return max(1, len(self.text) // 4)


HEADING_PATTERN = re.compile(r"(?m)^(?:#{1,3}\s+.+|(?:CHAPTER|PART)\s+[^\n]+)$", re.IGNORECASE)


def _sections(text: str) -> list[tuple[str, str, int]]:
    matches = list(HEADING_PATTERN.finditer(text))
    if not matches:
        return [("Document", text, 0)]

    sections: list[tuple[str, str, int]] = []
    if matches[0].start() > 0 and text[: matches[0].start()].strip():
        sections.append(("Front matter", text[: matches[0].start()].strip(), 0))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(0).lstrip("# ").strip()
        sections.append((title, text[match.start() : end].strip(), match.start()))
    return sections


def chunk_document(
    text: str,
    *,
    max_characters: int = 24_000,
    overlap_characters: int = 2_000,
) -> list[Chunk]:
    """Split on narrative boundaries, then use overlapping windows for oversized sections."""
    if max_characters <= 0:
        raise ValueError("max_characters must be positive")
    if overlap_characters < 0 or overlap_characters >= max_characters:
        raise ValueError("overlap_characters must be between 0 and max_characters - 1")

    chunks: list[Chunk] = []
    for title, section, section_start in _sections(text):
        cursor = 0
        while cursor < len(section):
            hard_end = min(len(section), cursor + max_characters)
            end = hard_end
            if hard_end < len(section):
                paragraph_break = section.rfind("\n\n", cursor + max_characters // 2, hard_end)
                sentence_break = section.rfind(". ", cursor + max_characters // 2, hard_end)
                end = max(paragraph_break + 2, sentence_break + 2, cursor + max_characters // 2)
            chunk_text = section[cursor:end].strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        index=len(chunks),
                        text=chunk_text,
                        title=title,
                        start_character=section_start + cursor,
                        end_character=section_start + end,
                    )
                )
            if end >= len(section):
                break
            cursor = max(cursor + 1, end - overlap_characters)
    return chunks
