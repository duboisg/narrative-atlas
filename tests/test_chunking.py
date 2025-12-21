from narrative_atlas.chunking import chunk_document


def test_chunking_prefers_headings_and_preserves_order():
    text = "# One\n\nAlpha.\n\n# Two\n\nBeta."
    chunks = chunk_document(text, max_characters=100, overlap_characters=10)
    assert [chunk.title for chunk in chunks] == ["One", "Two"]
    assert chunks[0].index == 0
    assert chunks[1].start_character > chunks[0].start_character


def test_oversized_section_uses_overlap():
    text = "# Long\n\n" + ("A sentence. " * 40)
    chunks = chunk_document(text, max_characters=120, overlap_characters=20)
    assert len(chunks) > 1
    assert chunks[1].start_character < chunks[0].end_character
