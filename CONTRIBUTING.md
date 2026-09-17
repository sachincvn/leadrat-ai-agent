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
| A new tool for the LLM | `app/agent/tools/lead_tools.py`, registered in `tools/registry.py` |
| A new CRM call | `app/integrations/crm/` — behind the `CRMClient` contract |
| A new LLM provider | `app/agent/llm/`, registered in `llm/factory.py` |
| Orchestration, memory, confirmation flows | `app/services/` |
| A new endpoint | `app/api/v1/routes/` — thin: validate, call a service, return |
| Settings | `app/core/config.py` **and** `.env.example` |

Routes stay thin. Business logic belongs in `services/`, external calls in `integrations/`.

## Open work

The extension table at the end of [README.md](README.md) lists the next tasks —
real CRM endpoints, the remaining lead tools, conversation memory, source
citations, RAG, and the write-confirmation flow.
