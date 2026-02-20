# Written Summary – Universal Data Connector

## Challenges Faced and Solutions

**Challenge 1: Making the LLM understand what data is available**
The biggest design challenge was not the data fetching itself — it was the *interface between the connector and the LLM*. An LLM cannot guess what parameters it can send. I solved this by adding a `llm_schema()` method to the base connector class, forcing every connector to self-describe in OpenAI function-calling format. The `/llm/functions` endpoint exposes all schemas at once so the LLM can discover tools at session start without any hard-coding.

**Challenge 2: Voice responses vs. API responses have different needs**
A developer querying the API wants raw, paginated data. A voice assistant needs a short spoken sentence and at most 5 items. I introduced a `voice_mode` flag and a `voice_summary` field in every response. The business rules engine enforces the `MAX_VOICE_RESULTS` ceiling when `voice_mode=true`, and the `build_voice_summary()` service constructs a natural-language sentence tailored to the data source and applied filters (e.g. *"Showing the 5 most recent high-priority open tickets out of 10 total"*).

**Challenge 3: Consistent response format across heterogeneous data**
CRM data is tabular, analytics data is time-series, and aggregated analytics is a single summary record. A naive approach would return different shapes, confusing the LLM. I introduced a `DataResponse` envelope with a `DataMeta` block that includes `data_type`, `data_freshness`, `applied_filters`, pagination, and `voice_summary`. Every endpoint returns the same shape regardless of what's inside.

---

## Design Decisions and Tradeoffs

| Decision | Tradeoff |
|---|---|
| **Static JSON files as data source** | Zero setup friction, but no real-time updates. In production, connectors would call a database or external API |
| **One `llm_schema()` per connector** | Clean separation of concerns, but means updating schema whenever the connector API changes |
| **Voice summary built server-side** | The LLM gets a ready sentence — faster for the user — but reduces the LLM's creative control over phrasing |
| **Priority-based sorting for support tickets** | Urgent tickets always surface first, but this can override the user's explicit sort preference |
| **Aggregation in the connector layer** | Keeps routers thin, but means adding new aggregation types requires touching the connector |

---

## What I Would Improve With More Time

1. **Real database backend** — swap JSON files for PostgreSQL/SQLite using SQLAlchemy, with async queries for better concurrency
2. **Caching layer** — add Redis caching with TTL so repeated LLM calls for the same data don't hit the DB every time
3. **Authentication** — API key middleware so each SaaS customer has their own scoped access
4. **Streaming responses** — for large datasets, use FastAPI's `StreamingResponse` so the LLM starts receiving data immediately
5. **Webhook support** — let data sources push updates rather than polling
6. **Rate limiting** — per-API-key request throttling using a token bucket algorithm
7. **Richer analytics** — week-over-week comparisons, trend detection (rising/falling), anomaly flagging

---

## What I Learned

**LLM function calling is primarily a schema design problem.** Getting the data is the easy part. The hard part is writing clear parameter descriptions so the LLM chooses the right function with the right arguments. A vague description like "filter data" is useless; a precise one like "filter by account status: active | inactive | churned" lets the LLM map a natural-language query to the correct parameter reliably.

**Voice UX constraints drive better API design.** The voice requirement forced me to think about conciseness and relevance from the start. Every endpoint now returns a `voice_summary` that could be spoken verbatim — this discipline would make any API cleaner, not just voice-facing ones.

**Abstraction pays off immediately.** The `BaseConnector` class with `fetch()` and `llm_schema()` took 20 minutes to design. But when I added the third connector, it took under 10 minutes because the pattern was already established. The router stays at 0 lines of data-source-specific code.
