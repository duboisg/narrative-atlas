from narrative_atlas.client import ResilientExtractor


class ScriptedClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def complete(self, system_prompt, user_prompt):
        self.prompts.append(user_prompt)
        return next(self.responses)


def test_requests_continuation_and_deduplicates_items():
    client = ScriptedClient(
        [
            '[{"name":"Mara"}, {"name":"Ilya"}',
            '[{"name":"Ilya"}, {"name":"Saye"}]',
        ]
    )
    extractor = ResilientExtractor(client, request_delay=0)
    items = extractor.extract("system", "source", continuation_rounds=2)
    assert [item["name"] for item in items] == ["Mara", "Ilya", "Saye"]
    assert "Continue with a fresh JSON array" in client.prompts[1]
