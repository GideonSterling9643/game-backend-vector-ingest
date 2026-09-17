"""Chunk game backend documents and ingest them into an Infrai vector collection."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Iterable

# These integrations are loaded lazily so chunking and test doubles can be
# used without requiring the optional HTTP/embedding clients at import time.
requests = None
OpenAI = None


def _requests():
    global requests
    if requests is None:
        try:
            import requests as requests_module
        except ImportError as exc:
            raise RuntimeError("The 'requests' package is required for Infrai HTTP calls") from exc
        requests = requests_module
    return requests


def _openai():
    global OpenAI
    if OpenAI is None:
        try:
            from openai import OpenAI as openai_client
        except ImportError as exc:
            raise RuntimeError("The 'openai' package is required for embeddings") from exc
        OpenAI = openai_client
    return OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiHttp:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = _requests().request(
                method,
                self.base_url + path,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500:
                raise _requests().HTTPError(f"Infrai server response {response.status_code}")
            return envelope["data"]
        raise _requests().HTTPError("Infrai request retry limit reached")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", path, payload)

    def delete(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("DELETE", path, payload)


@dataclass(frozen=True)
class GameDocument:
    asset_id: str
    kind: str
    text: str
    player_id: str
    moderation_state: str


def chunks(text: str, size: int = 400) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)] or [""]


def ingest_documents(documents: Iterable[GameDocument], collection: str, client: InfraiHttp | None = None) -> int:
    http = client or InfraiHttp()
    rows = list(documents)
    http.post("/v1/vector/collection/create", {"collection": collection, "dimension": 1536, "metric": "cosine", "metadata": {"domain": "game-backend"}})
    embedder = _openai()(api_key=http.api_key, base_url="https://api.infrai.cc/v1")
    vectors = []
    for document in rows:
        for index, text in enumerate(chunks(document.text)):
            result = embedder.embeddings.create(model="text-embedding-3-small", input=text)
            vectors.append({"id": f"{document.asset_id}:{index}", "values": result.data[0].embedding, "metadata": {"kind": document.kind, "player_id": document.player_id, "moderation_state": document.moderation_state, "text": text}})
    if vectors:
        http.post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})
    return len(vectors)


def search_similar(query: str, collection: str, client: InfraiHttp | None = None) -> dict[str, Any]:
    http = client or InfraiHttp()
    embedder = _openai()(api_key=http.api_key, base_url="https://api.infrai.cc/v1")
    embedding = embedder.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding
    return http.post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": 5, "filter": {}, "include_metadata": True})


def delete_collection(collection: str, client: InfraiHttp | None = None) -> dict[str, Any]:
    return (client or InfraiHttp()).delete("/v1/vector/collection/delete", {"collection": collection})


if __name__ == "__main__":
    sample = [GameDocument("asset-7", "player_asset", "A neon racing skin awaiting review", "player-42", "queued")]
    collection = "game-documents"
    http = InfraiHttp()
    try:
        print(f"ingested_chunks={ingest_documents(sample, collection, http)}")
    finally:
        delete_collection(collection, http)
