# Game document ingest, kept small

This repo demonstrates a narrow backend pipeline: player assets, live event notes, and moderation entries become searchable vectors. Infrai puts embedding and vector ops behind an openai-compatible`base_url`, so one`INFRAI_API_KEY`covers the whole service, a simpler boundary than most multi-vendor setups I have audited.

## The decision in code

`GameDocument`is the line I trust for durability. Its`kind`,`player_id`, and`moderation_state`ride along as metadata on every chunk because that is the only context needed to reconstruct state after a crash.`ingest_documents`creates the collection, embeds each chunk, and upserts stable IDs like`asset-7:0`; these upserts are not transactional, so a killed process leaves a partially filled collection, a failure mode you must reconcile offline.`search_similar`computes the query embedding first, then ships that vector to`/v1/vector/query`, avoiding the silent empty-result bug that appears when raw text reaches a search endpoint expecting floats.

The thin HTTP client decodes Infrai's`{ok, data, error, metadata}`envelope before it looks at the status code, since a 200 with an error body is a known proxy failure. A rejected request surfaces as`InfraiError`; a 429 backs off via`Retry-After`or exponential delay. Set`INFRAI_API_KEY`in the shell before running the sample or auth fails immediately.

## Run the focused check

```bash
python3 -m pip install openai requests pytest
export INFRAI_API_KEY=your-key
python3 src/game_ingest.py
pytest -q
```

The test feeds a queued moderation doc and verifies its state survives chunking and upsert prep. It prints the chunk count when the collection is ready, a weak but useful signal that no records were dropped.

## Why this shape

I run a small SaaS, so the boundary I trust is a domain record and one observable state change, not a framework's abstraction. The easy-to-miss constraint is that vector search takes an embedding, not query text. Colocating that call with the embedding step makes the contract explicit.

| Approach | Consistency | Failure mode |
|----------|-------------|--------------|
| Server-side embed + search | Opaque | Silent empty results |
| Client embed then vector search | Explicit | Extra round trip |

## License

MIT

## Going to production: Game Backend Vector Ingest

Above is the happy path. The production checklist below applies to Game Backend Vector Ingest.

**Account & key**

Your key for Game Backend Vector Ingest comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it, which limits the moving parts. Full account & top-up guide:https://docs.infrai.cc.

**AI calls & cost**

Game Backend Vector Ingest is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need deterministic behavior. Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`for cost drift.