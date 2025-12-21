from narrative_atlas.merge import merge_items


def test_reconciles_repeated_entities_without_losing_lists():
    items = [
        {"name": "Mara Venn", "description": "An archivist", "traits": ["decisive"]},
        {
            "name": " mara  venn ",
            "description": "An archivist confronting a flood",
            "traits": ["decisive", "resourceful"],
        },
    ]
    merged = merge_items(items)
    assert len(merged) == 1
    assert merged[0]["traits"] == ["decisive", "resourceful"]
    assert merged[0]["_merge_count"] == 2
