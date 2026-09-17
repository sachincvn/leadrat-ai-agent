# MUSO AI — Leadrat CRM Assistant

Conversational layer over Leadrat CRM: Streamlit UI → FastAPI → LLM with CRM tool
calling → CRM data. Product spec: [`product.md`](product.md).

Two lead tools are wired end-to-end against the live Leadrat API, so the whole
path already works. Everything else is a marked place to plug into.

---

## Quick start

```bash
git clone <repo-url>
cd leadrat-ai-agent

python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt
copy .env.example .env           # cp on macOS / Linux
```

All CRM data comes from the live Leadrat API, so every request needs a Leadrat
JWT — see *Authentication* below.

### 1. Configure the model

Two providers, switched by `LLM_PROVIDER` in `.env`. Both speak the OpenAI
protocol and both are chosen for the same reason: native tool calling, so calls
arrive as structured `tool_calls` rather than text to be parsed out of a
completion.

**A — Mistral La Plateforme** (`mistral`)

```
LLM_PROVIDER=mistral
MISTRAL_API_KEY=...
MISTRAL_MODEL=ministral-8b-latest
```

The free tier serves `ministral-8b-latest`. `mistral-small-latest` and
`mistral-medium-latest` are stronger but need a paid tier — without one they
answer `403 tier_not_allowed`. `LLM_DISABLE_THINKING` does not apply here:
`chat_template_kwargs` is a vLLM/TGI extension the HF router forwards into the
template, and Mistral rejects it.

**B — Hugging Face router** (`huggingface`)

```
LLM_PROVIDER=huggingface
HF_API_TOKEN=hf_xxxxxxxx
HF_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
```

Pick a model the router actually serves **with tool support** — `Qwen/Qwen3-8B`
and `Qwen3-32B` answer but never emit a tool call, which makes the whole agent
useless. Known good: `Qwen/Qwen3-235B-A22B-Instruct-2507`,
`meta-llama/Llama-3.3-70B-Instruct`.

There is deliberately no fallback between the two. A second model answering on
the days the first is unavailable would change tool-calling behaviour without
anyone noticing; instead the turn ends with *"MUSO is temporarily unavailable"*
and the real cause (out of credits, rate limited, rejected key) goes to the
server log.

The model must support **tool calling**. Without it the agent can only answer in
plain text.

Reasoning models spend most of their latency on a `<think>` block nobody reads.
`LLM_DISABLE_THINKING=true` (the default) turns it off at the provider, and any
`<think>` that still slips through is stripped before the answer is returned.

### 2. Start the backend

```bash
python -m uvicorn app.main:app --reload --reload-include .env
```

`--reload-include .env` matters: without it uvicorn watches only `.py` files, so a
changed `.env` is ignored until you restart the process by hand. The `/health`
response always shows which provider and CRM the **running** process actually uses.

Activate the venv in every terminal first. If `uvicorn` alone says
*"is not recognized"*, the venv is not active — either run `.venv\Scriptsctivate`,
or call it as `python -m uvicorn ...` (works regardless of PATH).

- API docs — http://localhost:8000/docs
- Health — http://localhost:8000/api/v1/health

### 3. Start the UI

In a second terminal, with the venv active:

```bash
python -m streamlit run ui/app.py
```

Opens at http://localhost:8501.

### 4. Try it

In the UI, keep the selected lead as `L001` and ask:

- `Give me the details of lead L001`
- `Summarize this lead`
- `Show Facebook leads from Bangalore`

Or straight from the API:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Give me the details of lead L001\",\"lead_id\":\"L001\"}"
```

---

## Authentication

Every request authenticates with the **caller's Leadrat JWT** — not a service API
key — so Leadrat enforces that user's own permissions. The `tenant` header is read
from the token's `custom:tenant_id` claim, so nothing else needs configuring.

Send the token on every request:

   ```
   Authorization: Bearer <leadrat-jwt>
   ```

   ```bash
   curl -X POST http://localhost:8000/api/v1/chat \
     -H "Authorization: Bearer $LEADRAT_JWT" \
     -H "Content-Type: application/json" \
     -d "{\"message\":\"Summarize this lead\",\"lead_id\":\"L001\"}"
   ```

   In the Streamlit UI, paste the token into the **Leadrat JWT** box in the sidebar.

For solo local testing you can put a token in `LEADRAT_JWT` in `.env` and skip the
header. Leave it empty in any shared environment.

How the token flows: `Authorization` header → `app/api/deps.py` → a request-scoped
ContextVar (`app/core/context.py`) → `LeadratClient`. No layer in between has to
pass it around. A 401/403 from Leadrat surfaces as `401 unauthorized`.

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/chat` | Ask MUSO a question |
| GET | `/api/v1/leads/{lead_id}` | One lead |
| GET | `/api/v1/leads/search` | Leads by `source`, `location`, `status` |
| GET | `/api/v1/health` | Active LLM provider, model and CRM mode |

---

## Project structure

```
app/
  main.py                    FastAPI app: middleware, router, lifespan
  core/                      cross-cutting concerns
    config.py                settings from .env  (single source of truth)
    context.py               request-scoped JWT
    logging.py               logging setup
    exceptions.py            domain errors + HTTP mapping
  api/
    deps.py                  shared dependencies (JWT extraction)
    v1/
      router.py              aggregates route modules
      routes/                HTTP layer only — no logic
        chat.py  leads.py  health.py
  schemas/                   Pydantic contracts
    chat.py  lead.py
  services/                  use cases / orchestration
    chat_service.py
  agent/                     the AI layer
    runner.py                agent loop: ask -> tool -> answer
    prompts.py               prompt templates
    llm/                     provider abstraction
      base.py  factory.py  errors.py
      huggingface_provider.py  mistral_provider.py
    tools/                   what the LLM is allowed to do
      registry.py              aggregates every module's tool list
      lead/                    one file per CRM API
        get_lead.py  search_leads.py
  integrations/crm/          external systems
    factory.py               builds the client for the current request
    leadrat/
      http.py                session: JWT + tenant headers, error mapping
      client.py              the CRM methods
      endpoints/             one file per Leadrat API
        get_all_leads.py
ui/
  app.py                     Streamlit chat screen
  api_client.py              HTTP calls to the backend
  config.py
```

Dependencies point one way:
`ui → api → services → agent → tools → integrations → core`.
Nothing lower imports something higher, so any layer can be replaced on its own.

---

## Extending

| Task | Where |
|------|-------|
| A new Leadrat endpoint | one file in `app/integrations/crm/leadrat/endpoints/`, called from `client.py` |
| New tools (`get_lead_history`, `get_lead_calls`, `get_lead_tasks`, `apply_lead_filter`) | one new file in `app/agent/tools/lead/`, appended to `LEAD_TOOLS` in that package's `__init__.py` |
| A tool for another CRM module | new package `app/agent/tools/<module>/`, its list added to `tools/registry.py` |
| Another LLM provider | implement `LLMProvider` in `app/agent/llm/`, add it to `factory.PROVIDERS` |
| Conversation memory | `app/services/chat_history_store.py` — swap the in-process dict for Redis |
| Source citations | `app/agent/runner.py` + `app/schemas/chat.py` |
| RAG over CRM docs | new `app/rag/` package, exposed as one tool |
| Write actions with confirmation | `chat_service.py` — return a pending action, confirm from the UI |
| LangGraph instead of the simple loop | `app/agent/runner.py` only |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uvicorn`/`streamlit` *is not recognized* | venv not active — run `.venv\Scriptsctivate`, or use `python -m uvicorn` / `python -m streamlit` |
| `Backend unreachable` in the UI | Backend not running, or `API_URL` is wrong in `.env` |
| `MUSO is temporarily unavailable` on every turn | Check the server log for the classified cause — `(402)` out of credits, `(429)` rate limited, `(401/403)` a bad key or a model above your tier |
| The model never calls a tool | The chosen model has no tool support on that provider — switch models (see *Configure the model*) |
| Answers are slow (4 s+) | A reasoning model is thinking — set `LLM_DISABLE_THINKING=true`, or use an `-Instruct` model |
| The bot forgets the previous message | Conversation memory is keyed on the caller's JWT — a different/refreshed token starts a new conversation |
| `401 unauthorized` | Missing or expired JWT — send `Authorization: Bearer <token>` |
| `.env` change had no effect | uvicorn was started before the edit — restart it, or run with `--reload-include .env` |
| `401 unauthorized` from every call | No JWT sent, or it expired — paste a fresh one in the UI sidebar |

---

## Conventions

- Never commit CRM responses or tokens — the API returns real customer data.
- `.env` is gitignored; only `.env.example` is committed. Never commit a JWT.
- Routes stay thin — logic belongs in `services/`, CRM calls in `integrations/`.
