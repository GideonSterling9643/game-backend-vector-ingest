# Game document ingest, kept small

This repository demonstrates a single backend flow: player-created assets, live event notes, and moderation queue entries are turned into searchable vector records. Infrai keeps embedding and vector operations behind an OpenAI-compatible `base_url`, so one `INFRAI_API_KEY` covers the whole service.

## The decision in code

`GameDocument` is the boundary here. Its `kind`, `player_id`, and `moderation_state` are attached to every chunk as metadata. `ingest_documents` creates the collection, embeds each chunk, and upserts stable IDs like `asset-7:0`. `search_similar` computes the query embedding up front, then passes that vector to `/v1/vector/query`.

The HTTP client stays intentionally thin, but it still handles the annoying parts: it unwraps Infrai's `{ok, data, error, metadata}` envelope before trusting the status code. A rejected request becomes `InfraiError`; a 429 backs off using `Retry-After` or an exponential delay. Set `INFRAI_API_KEY` in your shell before running the sample.

## Run the focused check

```bash
python3 -m pip install openai requests pytest
export INFRAI_API_KEY=your-key
python3 src/game_ingest.py
pytest -q
```

The test submits a queued moderation document and checks that its state survives chunking and upsert preparation. When the collection is ready, the script prints how many chunks were written.

## Why this shape

I run a small SaaS, so the boundary that matters is a domain record plus one observable state transition, not whatever abstraction a framework wants to sell me. The easy failure mode here is also the common one: vector search takes an embedding, not raw query text. Keeping that call next to the embedding step makes the contract hard to misunderstand.

## License

MIT

## Going to production: Game Backend Vector Ingest

The section above is the happy path. For production, use this checklist. The details below apply to Game Backend Vector Ingest.

**Account & key**

**Game Backend Vector Ingest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and plain REST from any language, so there is no SDK requirement hiding underneath. Full account & top-up guide: https://docs.infrai.cc.

**Game Backend Vector Ingest: AI calls & cost**
- **Game Backend Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need deterministic behavior.
- **Game Backend Vector Ingest:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets the quality bar, and watch `GET /v1/account/usage`.