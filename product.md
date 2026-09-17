# MUSO AI — CRM Intelligence & Conversational Assistant

## 1. Overview

MUSO AI is a conversational assistant inside Leadrat CRM. Users ask questions in
plain language instead of navigating screens to find lead information.

It combines conversational AI, CRM tool calling, natural-language filtering and
grounded answers backed by CRM records.

## 2. Problem

Leadrat has no conversational layer over CRM data. Answering simple questions —
what happened with this lead, what was promised, what follow-up is pending, which
leads need attention — means opening several screens and reading records manually.

## 3. Vision

> Make Leadrat conversational.

**User:** "Summarize this lead."
**MUSO:** "Rahul is interested in a 3BHK property. A site visit was completed on
16 September and the customer requested pricing. The latest follow-up is pending."

## 4. Users

- **CRM users** — need faster access to lead information and history.
- **New users** — need guidance while using Leadrat.
- **Admins / product teams** — evaluating CRM intelligence.

## 5. Capabilities

### 5.1 Selected-lead context
The assistant knows which lead is open in the UI. "This lead", "the customer" and
follow-up questions resolve against it.

### 5.2 Lead intelligence
Summarize a lead from its CRM record and activity: status, recent calls, meetings,
tasks, follow-ups, notes, missing information and risk signals.

### 5.3 Grounded answers
Answer only from permitted CRM records. Never invent CRM information. Name the
records that support an important answer.

**User:** "What was promised in the last conversation?"
**MUSO:** "The executive promised to share the 3BHK pricing details."
**Source:** Call — 12 September

### 5.4 Natural-language filtering
> "Show me Facebook leads from Bangalore that haven't been contacted for 3 days."

becomes:

```
Source:       Facebook
Location:     Bangalore
Last contact: more than 3 days ago
```

Show the interpreted filters before applying them. Never guess a filter value —
ask instead.

### 5.5 Follow-up questions
Keep conversation context across turns so "when was the last call?" and "what was
discussed?" stay on the same lead.

## 6. Agent behaviour

For each message the agent decides between: a direct answer, a CRM tool call,
several tool calls, a documentation lookup (RAG), a clarifying question, or a
confirmed write action.

```
User → MUSO agent → ┬→ CRM tools ─┐
                    ├→ RAG        ├→ Answer
                    └→ Clarify   ─┘
```

## 7. Tools

| Tool | Status | Returns |
|------|--------|---------|
| `get_lead` | built | Lead details |
| `search_leads` | built | Leads matching structured conditions |
| `get_lead_history` | planned | Calls, meetings, tasks, notes, status changes |
| `get_lead_calls` | planned | Call records |
| `get_lead_tasks` | planned | Tasks and follow-ups |
| `apply_lead_filter` | planned | Filters applied to the Leads module |

Read tools run automatically when the user is permitted. Write tools require
explicit confirmation.

## 8. Safety & permissions

- The user's Leadrat **JWT** is sent with every request and forwarded to the CRM,
  so the CRM enforces that user's own permissions and tenant.
- Never access another tenant's records; never expose restricted fields.
- Never guess important values — ask for clarification.
- Write actions require explicit confirmation and can be cancelled.

Example confirmation:

```
You're about to change
  Lead:           Rahul Sharma
  Current status: Interested
  New status:     Qualified
[Confirm] [Cancel]
```

## 9. Architecture

```
Streamlit test UI  (later: Leadrat UI)
        │  HTTP + Authorization: Bearer <Leadrat JWT>
        ▼
   FastAPI  →  chat service  →  agent loop
                                  │
                      ┌───────────┼───────────┐
                      ▼           ▼           ▼
                 LLM (Ollama    CRM tools    RAG
                 or HF API)        │      (planned)
                                   ▼
                              Leadrat CRM API
                          (mock JSON in development)
```

## 10. Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI, Pydantic v2 |
| Agent | LangChain tool calling |
| LLM | Qwen via Ollama (local) or Hugging Face Inference API (hosted) |
| CRM | Leadrat REST API; mock JSON client for development |
| Test UI | Streamlit |
| RAG (planned) | ChromaDB + HuggingFace embeddings |

Development uses synthetic data only. No real customer data.

## 11. MVP scope

**In**
- Conversational interface with selected-lead context
- Lead and history summaries
- Follow-up question handling
- CRM-grounded answers with supporting record references
- Natural-language lead filtering, with the interpreted filters shown

**Out**
- Multi-agent orchestration
- Browser takeover
- Model fine-tuning
- Autonomous CRM administration

## 12. Success criteria

- Users can ask questions naturally and MUSO holds lead context.
- Summaries match CRM history; answers trace back to CRM records.
- Natural language becomes correct CRM filters, visible and editable by the user.
- User permissions are respected via the forwarded JWT.
- The assistant never fabricates CRM information.

## 13. Demo scenario

1. Salesperson opens Rahul Sharma's lead → "Summarize this lead." → MUSO summarizes.
2. "What was promised in the latest conversation?" → MUSO answers with the source call.
3. "Show Facebook leads from Bangalore not contacted for three days." → MUSO shows the
   interpreted filters, the user confirms, the filtered leads are displayed.

## 14. Principle

> MUSO should not simply chat about CRM data. It should understand CRM context,
> retrieve trusted information, explain its answers, and help users interact with
> the CRM through natural language.
