# Video Script – Universal Data Connector Demo

---

## Minutes 0–2: Data Flow Diagram

**What to draw on Excalidraw or a whiteboard while you talk:**

Draw 3 columns:
1. **Left** → "LLM / Voice Assistant" (a box with a microphone icon)
2. **Middle** → "Universal Data Connector (FastAPI)" (a box)
3. **Right** → 3 stacked boxes: "CRM", "Support Tickets", "Analytics"

Draw arrows:

```
LLM  →→  GET /llm/functions  →→  Connector
     ←←  JSON schemas         ←←

LLM  →→  POST /llm/call       →→  Connector.fetch()
         {function_name,            ↓
          arguments}           Business Rules Engine
                                    ↓
     ←←  DataResponse         ←←  voice_summary + data
```

**What to say (word for word):**

> "Hi, I'm going to walk you through the Universal Data Connector — a FastAPI service that lets an LLM query different data sources through function calling.

> The flow has two phases. In phase one — discovery — the LLM calls `GET /llm/functions`. The connector returns three OpenAI-compatible JSON schemas, one for each data source: CRM customers, support tickets, and analytics metrics. The LLM now knows exactly what tools it has and what parameters each one accepts.

> In phase two — execution — the user says something like 'any urgent support tickets?' The LLM maps that to `get_support_tickets` with `priority: high, status: open`, and sends a `POST /llm/call` to our connector.

> The request hits the Support connector, which reads the data, applies our business rules — open tickets go first, high priority goes first — then our voice optimizer generates a single spoken sentence: 'Showing the 5 most recent high-priority open tickets out of 10 total.' That sentence goes straight back to the LLM, which reads it out to the user.

> Every response uses the same envelope — `data`, plus a `metadata` block with the voice summary, data freshness, and pagination — so the LLM always knows how to interpret the response regardless of which data source it came from."

---

## Minutes 2–4: Live Code Demo

**Step 1 — Show the server is running**

Open a terminal, run:
```bash
python -m uvicorn app.main:app --reload
```
Point to the log line: `Starting Universal Data Connector v1.0.0 | max_results=10`

> "The server starts, finds the data files, and is ready to go."

**Step 2 — Open /docs**

Go to `http://localhost:8000/docs` in the browser.

> "FastAPI auto-generates this Swagger UI from our Pydantic models. You can see three data source endpoints and the two LLM function-calling endpoints."

**Step 3 — Demo 1: Discover function schemas**

In a new terminal:
```bash
curl http://localhost:8000/llm/functions
```
Scroll to the `parameters` section of one schema.

> "This is exactly what you'd pass as the `functions` argument to OpenAI's chat API. The LLM reads these descriptions and knows what to ask for."

**Step 4 — Demo 2: CRM filter**

```bash
curl "http://localhost:8000/data/crm?status=active&plan=pro&limit=3"
```

> "Three active pro-plan customers. Notice the metadata: voice summary says 'Showing 3 of X...', and we have a data freshness label."

**Step 5 — Demo 3: Support tickets — urgent first**

```bash
curl "http://localhost:8000/data/support?status=open&priority=high&voice_mode=true"
```

> "Voice mode caps this at 5 results. Open high-priority tickets are sorted to the top by the business rules engine. The voice summary is ready to speak verbatim."

**Step 6 — Demo 4: LLM function call**

```bash
curl -X POST http://localhost:8000/llm/call \
  -H "Content-Type: application/json" \
  -d '{"function_name":"get_analytics_metrics","arguments":{"metric":"daily_active_users","aggregate":true}}'
```

> "This is what the LLM actually sends. It gets back a single aggregated record — average, min, max — instead of 30 raw rows. Perfect for a voice response."

**Step 7 — Run tests**

```bash
python -m pytest tests/ -v
```

> "63 tests, all passing. We test connector filtering, business rules, and every HTTP endpoint."

---

## Minutes 4–6: Scalability Discussion

**What to say:**

> "Let's be honest about scalability. Right now the connector reads from static JSON files on disk. That's fine for a prototype, but it would not handle 10,000 concurrent users.

> Here are the **three specific bottlenecks** and what I'd change:

> **Bottleneck 1 — Disk I/O.** Every API call opens and reads a JSON file from disk. With 10,000 users simultaneously, we'd hit file descriptor limits and terrible latency. The fix: replace JSON files with a proper database — PostgreSQL for CRM and tickets, a time-series DB like TimescaleDB or InfluxDB for analytics. Use async database drivers like `asyncpg` so FastAPI can serve requests while waiting for DB results.

> **Bottleneck 2 — No caching.** If 500 users all ask 'what are the current open tickets?' in the same second, we hit the DB 500 times for identical results. The fix: add Redis caching in front of the connectors. Set a TTL of, say, 30 seconds for support tickets and 5 minutes for analytics aggregations. This alone would cut DB load by 90% for popular queries.

> **Bottleneck 3 — Single process.** Right now we run one uvicorn process. The fix: run multiple uvicorn workers behind a load balancer like Nginx, or containerize with Docker and deploy to Kubernetes. Because our connectors are stateless — they don't hold any in-memory state between requests — horizontally scaling is straightforward.

> **What stays the same:** The LLM integration layer, the `DataResponse` envelope, and the business rules engine. Those are CPU-light and scale just fine. The connector abstraction also means we could swap the data layer to a distributed database without changing a single line of the router or LLM code.

> So in summary: same architecture, swap JSON → async DB, add Redis, run multiple workers. That would comfortably get us to 10,000 users."

---

## Tips

- **Keep terminal font large** so the JSON response is readable on screen
- **Pre-run the server** before recording so there's no startup fumbling
- **Highlight the `voice_summary` field** in every response — that's the most impressive part
- Excalidraw link to draw the diagram live: https://excalidraw.com
