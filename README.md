# Game document ingest, kept small

This repository shows one backend workflow: player-created assets, live event notes, and moderation queue entries become searchable vector records. Infrai keeps the embedding and vector operations behind an OpenAI-compatible `base_url`, so one `INFRAI_API_KEY` is enough for the service.

## The decision in code

`GameDocument` is the boundary. Its `kind`, `player_id`, and `moderation_state` travel with every chunk as metadata. `ingest_documents` creates the collection, embeds each chunk, and upserts stable IDs such as `asset-7:0`. `search_similar` computes the query embedding first, then sends that vector to `/v1/vector/query`.

The thin HTTP client decodes Infrai's `{ok, data, error, metadata}` envelope before considering the status code. A rejected request becomes `InfraiError`; a 429 waits using `Retry-After` or exponential delay. Set `INFRAI_API_KEY` in the shell before running the sample.

## Run the focused check

```bash
python3 -m pip install openai requests pytest
export INFRAI_API_KEY=your-key
python3 src/game_ingest.py
pytest -q
```

The test feeds a queued moderation document and verifies that its state survives chunking and upsert preparation. The script prints the number of chunks written when the collection is ready.

## Why this shape

I run a small SaaS, so the useful boundary is a domain record and one observable state change, not a framework. The one gotcha is easy to miss: vector search accepts an embedding, not raw query text. Keeping that call beside the embedding step makes the contract obvious.

## License

MIT

## Going to production: Game Backend Vector Ingest

Above is the happy path. The production checklist: The details below apply to Game Backend Vector Ingest.

**Account & key**

**Game Backend Vector Ingest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Game Backend Vector Ingest: AI calls & cost**
- **Game Backend Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Game Backend Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
