from narrative_atlas.graph import link_scenes_to_arcs, timeline


def test_links_scenes_to_arcs_and_builds_character_presence():
    scenes = [
        {
            "id": "scene-1",
            "characters_present": ["Mara", "Ilya"],
            "themes": ["public memory"],
            "conflicts": ["preservation vs evacuation"],
            "location": "Glass Archive",
            "chunk_index": 1,
            "position": 0.5,
        }
    ]
    arcs = [
        {
            "id": "arc-1",
            "characters_involved": ["Mara"],
            "themes": ["public memory"],
            "conflicts": [],
            "locations_involved": [],
        }
    ]
    linked_scenes, linked_arcs = link_scenes_to_arcs(scenes, arcs)
    assert linked_scenes[0]["arcs"] == ["arc-1"]
    assert linked_arcs[0]["scenes"] == ["scene-1"]
    data = timeline(linked_scenes, linked_arcs)
    assert data["characters"]["presence"]["Mara"] == ["scene-1"]
