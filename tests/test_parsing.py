from narrative_atlas.parsing import appears_truncated, parse_json_items


def test_parses_fenced_json():
    content = '```json\n[{"name": "Mara"}]\n```'
    assert parse_json_items(content) == [{"name": "Mara"}]


def test_salvages_complete_objects_from_truncated_array():
    content = '[{"name": "Mara"}, {"name": "Ilya"}, {"name": "unfinished"'
    assert appears_truncated(content)
    assert parse_json_items(content) == [{"name": "Mara"}, {"name": "Ilya"}]
