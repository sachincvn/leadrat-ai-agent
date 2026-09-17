# MUSO AI — Leadrat CRM Assistant

Conversational layer over Leadrat CRM: Streamlit UI → FastAPI → LLM with CRM tool
calling → CRM data. Product spec: [`product.md`](product.md).

Two lead tools are wired end-to-end so the whole path already works. Everything
else is a marked place to plug into.

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

Defaults in `.env` run against **mock CRM data** and a **local Ollama model**, so
no Leadrat token is needed to get the project up.

### 1. Pick the model

Three providers, switched by `LLM_PROVIDER` in `.env`. All run open-source weights.

**A — Hugging Face Inference API** (`huggingface`) — nothing to install, no GPU.

```
LLM_PROVIDER=huggingface
HF_API_TOKEN=hf_xxxxxxxx
HF_MODEL=Qwen/Qwen3-8B
```

**B — Ollama** (`ollama`) — local, quantized, offloads to whatever GPU you have.

```bash
ollama pull qwen3:8b     # or qwen3:4b on a small GPU
ollama serve
```

**C — transformers in-process** (`local_hf`) — the raw Hub weights, no Ollama.
Needs ~16 GB VRAM at bf16, ~6 GB with `LOCAL_HF_LOAD_4BIT=true`. Below that it
falls back to CPU and each answer takes minutes. Extra install:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install transformers accelerate bitsandbytes
```

Whichever you choose, the model must support **tool calling** (Qwen3, Qwen2.5-Instruct,
Llama 3.1+, Mistral). Without it the agent can only answer in plain text.

### 2. Start the backend

```bash
python -m uvicorn app.main:app --reload
```

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

## Running against the real Leadrat CRM

Authentication uses the **caller's Leadrat JWT** — not a service API key — so the
CRM enforces that user's own permissions and tenant.

1. Fill in the real endpoints in `app/integrations/crm/leadrat_client.py`
   (paths there are placeholders).
2. Set in `.env`:

   ```
   USE_MOCK_CRM=false
   LEADRAT_BASE_URL=https://api.leadrat.com
   ```

3. Send the token on every request:

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
      base.py  factory.py  ollama_provider.py  huggingface_provider.py
    tools/                   what the LLM is allowed to do
      registry.py              aggregates every module's tool list
      lead/                    one file per CRM API
        get_lead.py  search_leads.py
  integrations/crm/          external systems
    base.py                  CRM contract
    mock_client.py  leadrat_client.py  factory.py
ui/
  app.py                     Streamlit chat screen
  api_client.py              HTTP calls to the backend
  config.py
data/mock/leads.json         synthetic leads
```

Dependencies point one way:
`ui → api → services → agent → tools → integrations → core`.
Nothing lower imports something higher, so any layer can be replaced on its own.

---

## Extending

| Task | Where |
|------|-------|
| Real CRM endpoints | `app/integrations/crm/leadrat_client.py`, then `USE_MOCK_CRM=false` |
| New tools (`get_lead_history`, `get_lead_calls`, `get_lead_tasks`, `apply_lead_filter`) | one new file in `app/agent/tools/lead/`, appended to `LEAD_TOOLS` in that package's `__init__.py` |
| A tool for another CRM module | new package `app/agent/tools/<module>/`, its list added to `tools/registry.py` |
| Another LLM provider | implement `LLMProvider` in `app/agent/llm/`, add it to `factory.PROVIDERS` |
| Conversation memory | `app/services/chat_service.py` — `run_agent()` already accepts `history` |
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
| Health shows ollama but answers fail | `ollama serve` not running, or the model is not pulled |
| `local_hf` is extremely slow | Model does not fit in VRAM — use `huggingface` or `ollama` instead |
| The model never calls a tool | The chosen model does not support tool calling — switch models |
| `401 unauthorized` | Missing or expired JWT — send `Authorization: Bearer <token>` |
| `lead_not_found` on L001 | `USE_MOCK_CRM=false` while the live endpoints are still placeholders |

---

## Conventions

- `data/mock/` is synthetic. **No real customer data in this repo.**
- `.env` is gitignored; only `.env.example` is committed. Never commit a JWT.
- Routes stay thin — logic belongs in `services/`, CRM calls in `integrations/`.
