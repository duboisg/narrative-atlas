import json

from narrative_atlas.pipeline import NarrativePipeline


class DeterministicExtractor:
    request_delay = 0

    def extract(self, system_prompt, user_prompt, *, identity_key):
        if "characters_present" in user_prompt:
            return [
                {
                    "name": "Archive rescue",
                    "characters_present": ["Mara"],
                    "themes": ["public memory"],
                    "conflicts": ["preservation vs evacuation"],
                    "location": "Glass Archive",
                    "position": "middle",
                }
            ]
        if "current_stage" in user_prompt:
            return [
                {
                    "name": "Records under water",
                    "characters_involved": ["Mara"],
                    "themes": ["public memory"],
                    "conflicts": ["preservation vs evacuation"],
                    "locations_involved": ["Glass Archive"],
                }
            ]
        return [{"name": "Mara", "description": "An archivist"}]


def test_end_to_end_run_writes_resume_data_and_timeline(tmp_path):
    pipeline = NarrativePipeline(DeterministicExtractor(), tmp_path)
    results = pipeline.run(
        "# Chapter One\n\nMara enters the archive.",
        kinds=["characters", "scenes", "arcs"],
    )
    assert set(results) == {"characters", "scenes", "arcs"}
    assert (tmp_path / "checkpoints" / "scenes" / "chunk-0000.json").exists()
    assert (tmp_path / "timeline.json").exists()
    timeline = json.loads((tmp_path / "timeline.json").read_text(encoding="utf-8"))
    assert timeline["metadata"]["total_scenes"] == 1
    assert timeline["scenes"][0]["arcs"] == [results["arcs"][0]["id"]]
