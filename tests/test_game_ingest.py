from src.game_ingest import GameDocument, chunks, delete_collection, ingest_documents


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.api_key = "test"

    def post(self, path, payload):
        self.calls.append((path, payload))
        return {"created": True}

    def delete(self, path, payload):
        self.calls.append((path, payload))
        return {"deleted": True}


def test_chunking_preserves_moderation_context(monkeypatch):
    class Embedding:
        data = [type("Item", (), {"embedding": [0.1, 0.2]})()]

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.embeddings = type("Emb", (), {"create": lambda *_args, **_kwargs: Embedding()})()

    monkeypatch.setattr("src.game_ingest.OpenAI", FakeOpenAI)
    http = FakeHttp()
    count = ingest_documents([GameDocument("a", "moderation_queue", "one two three", "p1", "queued")], "games", http)
    assert count == 1
    path, payload = http.calls[-1]
    assert path == "/v1/vector/upsert"
    assert payload["vectors"][0]["metadata"]["moderation_state"] == "queued"


def test_chunks_are_deterministic():
    assert chunks("alpha beta gamma", size=2) == ["alpha beta", "gamma"]


def test_delete_collection_uses_named_collection():
    http = FakeHttp()
    assert delete_collection("game-documents", http) == {"deleted": True}
    assert http.calls == [
        ("/v1/vector/collection/delete", {"collection": "game-documents"})
    ]
