
# Universal Data Connector

A production-quality FastAPI service that gives an LLM a **unified interface** to query CRM, support ticket, and analytics data through **OpenAI-compatible function calling**. Responses are voice-optimized — concise, prioritized, and annotated with freshness metadata so an AI assistant can speak them directly.

---

## Features

- **3 Data Connectors** — CRM (customers), Support Tickets, Analytics Metrics
- **LLM Function Calling** — `GET /llm/functions` returns OpenAI-compatible schemas; `POST /llm/call` executes any function
- **Voice-Optimized Responses** — automatic result capping, priority sorting, natural-language `voice_summary` in every response
- **Business Rules Engine** — high-priority open tickets surface first, freshness labels, voice vs API mode limits
- **Auto-generated Docs** — full Swagger UI at `/docs`
- **63 Passing Tests** across connectors, services, and HTTP endpoints
- **Docker Ready** — Dockerfile + docker-compose included

---

## Quick Start

### Option 1 – Local (Python)

```bash
# 1. Clone / open the project folder
cd universal-data-connector

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the env file (defaults work out of the box)
cp .env.example .env

# 4. Start the server
python -m uvicorn app.main:app --reload

# 5. Open interactive docs
open http://localhost:8000/docs
```

### Option 2 – Docker Compose

```bash
docker-compose up --build
```

Then visit: **http://localhost:8000/docs**

---

## Environment Variables

Copy `.env.example` to `.env`. All defaults work without changes.

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | Universal Data Connector | Application name shown in docs |
| `APP_VERSION` | 1.0.0 | Version string |
| `MAX_RESULTS` | 10 | Default result cap for API callers |
| `MAX_VOICE_RESULTS` | 5 | Tighter cap when `voice_mode=true` |
| `DATA_DIR` | data | Directory containing JSON fixture files |

---

## API Reference

### Health

| Endpoint | Description |
|---|---|
| `GET /health/` | Returns `{"status": "ok"}` — use for load balancer checks |
| `GET /health/info` | Returns app version and config |

### Data Endpoints

| Endpoint | Key Query Params | Description |
|---|---|---|
| `GET /data/crm` | `status`, `plan`, `name_search`, `limit`, `voice_mode` | Customer records |
| `GET /data/support` | `status`, `priority`, `customer_id`, `limit`, `voice_mode` | Support tickets (urgent-first) |
| `GET /data/analytics` | `metric`, `date_from`, `date_to`, `aggregate`, `limit` | Daily metrics / aggregated summaries |

### LLM Function Calling

| Endpoint | Description |
|---|---|
| `GET /llm/functions` | Returns all connector schemas in OpenAI function-calling format |
| `POST /llm/call` | Executes a function call by name with arguments dict |

---

## Example Requests

**Query active customers:**
```bash
curl "http://localhost:8000/data/crm?status=active&limit=5"
```

**Urgent open tickets (voice mode):**
```bash
curl "http://localhost:8000/data/support?status=open&priority=high&voice_mode=true"
```

**Analytics aggregated summary:**
```bash
curl "http://localhost:8000/data/analytics?metric=daily_active_users&aggregate=true"
```

**LLM function call (simulates what GPT-4 / Claude would trigger):**
```bash
curl -X POST http://localhost:8000/llm/call \
  -H "Content-Type: application/json" \
  -d '{"function_name": "get_support_tickets", "arguments": {"priority": "high", "status": "open"}}'
```

Response `metadata.voice_summary`:
> *"Showing the 5 most recent high-priority open support tickets out of 10 total."*

---

## OpenAI Integration Example

```python
import openai, requests

# 1. Fetch available tool schemas from the connector
functions = requests.get("http://localhost:8000/llm/functions").json()["functions"]

# 2. Ask GPT-4 a question with those tools available
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Any urgent support tickets right now?"}],
    functions=functions,
)

# 3. Execute whichever function the LLM chose
call = response.choices[0].message.function_call
result = requests.post("http://localhost:8000/llm/call", json={
    "function_name": call.name,
    "arguments": eval(call.arguments),
}).json()

# 4. The voice_summary is ready to speak
print(result["metadata"]["voice_summary"])
```

---

## Running Tests

```bash
python -m pytest tests/ -v
# → 63 passed
```

---

## Project Structure

```
universal-data-connector/
├── app/
│   ├── main.py                 # FastAPI app entry point, CORS, lifespan events
│   ├── config.py               # Pydantic settings from .env
│   ├── models/                 # Pydantic data models
│   ├── connectors/             # CRM, Support, Analytics connectors + base class
│   ├── services/               # Business rules, voice optimizer, data identifier
│   ├── routers/                # health.py, data.py, llm.py
│   └── utils/                  # Logging setup, mock data generator
├── data/                       # JSON fixture files (auto-seeded on first run)
├── tests/                      # 63 unit + integration tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Design Decisions

**Why a separate `/llm/functions` + `/llm/call` pattern?**
Keeps the LLM integration stateless and model-agnostic. Works with OpenAI, Anthropic, or any other provider because the schema format is standard JSON.

**Why named routes (`/data/crm`) instead of one generic `/data/{source}`?**
FastAPI generates cleaner, fully-typed OpenAPI docs. Each endpoint has its own parameter descriptions that the LLM can read.

**Why is `voice_mode` a separate flag?**
Voice and API callers have different needs. A developer calling the API wants all 10 results; a voice assistant should speak no more than 5. The flag enforces this without the caller needing to guess the right limit.
