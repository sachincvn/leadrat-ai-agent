# Contributing

## Setup

See [README.md](README.md) — venv, `pip install -r requirements.txt`, `copy .env.example .env`.

Never commit `.env`. It holds tokens and is gitignored; only `.env.example` is tracked.

## Branch and PR flow

**If you have write access to this repo:**

```bash
git checkout main
git pull
git checkout -b feat/lead-history-tool
# ...work...
git push -u origin feat/lead-history-tool
```

Then open a PR against `main` on GitHub.

**If you do not have write access:** fork the repo, push the branch to your fork,
and open a PR from there. No permission needed.

### Branch names

```
feat/<what>     new capability      feat/apply-lead-filter
fix/<what>      bug fix             fix/jwt-header-parsing
docs/<what>     docs only           docs/setup-steps
chore/<what>    tooling, deps       chore/pin-langchain
```

### Commits

Keep the subject short and in the imperative mood:

```
add get_lead_history tool
fix JWT fallback when header is missing
```

### PR checklist

- [ ] App starts: `python -m uvicorn app.main:app --reload`
- [ ] Health is green: `GET /api/v1/health`
- [ ] The path you touched was exercised once by hand (UI or curl)
- [ ] No secrets, tokens or real customer data in the diff
- [ ] Description says what changed and how you verified it

## Where code goes

Dependencies point one way:
`ui → api → services → agent → tools → integrations → core`.
Nothing lower may import something higher.

| Adding | Goes in |
|--------|---------|
| A new tool for the LLM | one file in `app/agent/tools/<module>/`, appended to that package's tool list |
| A new CRM call | one file in `app/integrations/crm/leadrat/endpoints/`, called from `client.py` |
| A new LLM provider | `app/agent/llm/`, registered in `llm/factory.py` |
| Orchestration, memory, confirmation flows | `app/services/` |
| A new endpoint | `app/api/v1/routes/` — thin: validate, call a service, return |
| Settings | `app/core/config.py` **and** `.env.example` |

Routes stay thin. Business logic belongs in `services/`, external calls in `integrations/`.

## Adding a tool

One file per CRM API, grouped by module, so two people adding tools rarely touch
the same file.

```
app/agent/tools/
  registry.py              every module's list, combined
  lead/
    __init__.py            LEAD_TOOLS = [get_lead, search_leads]
    get_lead.py            one @tool function
    search_leads.py
```

1. Create `app/agent/tools/lead/get_lead_history.py` with a single `@tool` function.
   Its docstring is what the model reads to decide when to call it — be precise.
2. Import it in `app/agent/tools/lead/__init__.py` and append it to `LEAD_TOOLS`.
3. A whole new module (tasks, meetings) gets its own package plus one line in
   `registry.py`.

Keep tools thin: call the CRM client, return JSON. Logic belongs in `services/`.

## Open work

The extension table at the end of [README.md](README.md) lists the next tasks —
real CRM endpoints, the remaining lead tools, conversation memory, source
citations, RAG, and the write-confirmation flow.
