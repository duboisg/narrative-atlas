"""Reusable narrative extraction specifications."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionSpec:
    name: str
    identity_key: str
    system_prompt: str
    instructions: str

    def prompt(self, text: str, title: str, index: int) -> str:
        return f"""Analyze segment {index + 1}, titled \"{title}\".

{self.instructions}

Return only a valid JSON array. Use [] when nothing qualifies. Do not invent facts that are
not supported by the excerpt. Keep source-grounding fields short enough to avoid reproducing
large passages.

SOURCE EXCERPT
{text}
"""


COMMON_SYSTEM = (
    "You are a meticulous narrative analyst. Extract structured facts from the supplied "
    "excerpt, preserve uncertainty, and return only valid JSON."
)


SPECS = {
    "characters": ExtractionSpec(
        name="characters",
        identity_key="name",
        system_prompt=COMMON_SYSTEM,
        instructions="""Extract narratively significant characters. For each item include:
- name
- description: role, motivations, and development evidenced here
- aliases: array
- relationships: array of concise statements
- traits: array
- significance: low, medium, or high
- first_mentioned: a short source locator or phrase, never a long quotation""",
    ),
    "locations": ExtractionSpec(
        name="locations",
        identity_key="name",
        system_prompt=COMMON_SYSTEM,
        instructions="""Extract locations that host events or materially shape the narrative.
For each item include name, type, description, events, atmosphere, significance, and a short
first_mentioned locator. Exclude places that are only incidental references.""",
    ),
    "scenes": ExtractionSpec(
        name="scenes",
        identity_key="name",
        system_prompt=COMMON_SYSTEM,
        instructions="""Extract complete dramatic scenes with meaningful action, dialogue,
revelation, conflict, or character development. Include name, summary, position (0.0-1.0),
characters_present, location, dramatic_purpose, tension_level (0.0-1.0), themes, and conflicts.
Exclude transitions and pure exposition.""",
    ),
    "arcs": ExtractionSpec(
        name="arcs",
        identity_key="name",
        system_prompt=COMMON_SYSTEM,
        instructions="""Extract significant narrative threads that extend beyond one isolated
event. Include name, type, description, current_stage, key_events, characters_involved,
locations_involved, conflicts, themes, first_mentioned, and last_mentioned.""",
    ),
}
