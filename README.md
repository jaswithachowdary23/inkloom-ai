# Inkloom AI – Intelligent Brand Governance Platform

**We Code Coder Hackathon · Round 2 – The Build**

A practical pre-publication review tool that checks marketing text against approved brand guidelines, produces explainable findings, suggests corrections, and requires human approval before content is marked ready to publish.

## Live Demo

- Frontend: http://localhost:5173 (static UI)
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Core Workflow (fully working)

1. **Brand workspace** – seeded with sample guidelines (terminology, prohibited claims, tone).
2. **Submit draft** – paste text + choose channel (social / ad / campaign / email).
3. **Automatic checks** – deterministic rule matches + AI-assisted tone/message heuristics.
4. **Explainable findings** – each issue shows severity, rule vs AI label, explanation, matched text, and optional suggestion.
5. **Accept / reject / apply suggestions**.
6. **Human approval** – submit → approve or request changes.
7. **Revision history** stored for every action.

## Technology Stack

| Layer | Choice |
|-------|--------|
| Frontend | Vanilla JS + modern CSS (single-page, zero-build for reliability) |
| Backend | Python 3 + FastAPI |
| Validation | Deterministic regex/rule engine + heuristic “AI-assisted” checks |
| Storage | SQLite |
| API style | REST JSON |

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
# DB path is /tmp/inkloom.db by default in this environment
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (any static server)
cd frontend-static
python3 -m http.server 5173
```

Open http://localhost:5173 and click “Load Sample Draft” then “Run Brand Checks”.

## Completed Features (Round 2)

- [x] Brand workspace with guideline library (CRUD)
- [x] Draft submission with channel selection
- [x] Deterministic prohibited-phrase & claim checks
- [x] Terminology preference checks
- [x] Tone / message / clarity heuristics (labelled AI-assisted)
- [x] Severity ranking & confidence scores
- [x] Evidence-linked explanations
- [x] Correction suggestions + bulk apply
- [x] Accept / reject individual findings
- [x] Human review workflow (submit → approve / request changes)
- [x] Revision history
- [x] Dashboard with counts and recent drafts
- [x] Privacy-conscious design notes (synthetic data, no auto-publish)

## Changes from Round 1 Plan

- Used a polished static frontend instead of full React for faster, more reliable deployment in constrained environments while keeping the same UX and all planned screens.
- SQLite path adjusted for the runtime environment.
- AI component is a transparent hybrid: exact rule matches are deterministic; tone/message items are clearly labelled “AI-assisted” with lower confidence, matching the original “never treat the model as the brand standard” principle.

## Three Major Improvements Planned for Round 3

1. **True LLM integration with grounded prompts** – Call an LLM only with the approved guideline set + draft, force structured JSON output, and keep the rule engine as the source of truth for hard violations.
2. **Visual brand checks** – Upload logo/colour reference assets and flag off-brand colours or missing logo usage in image content (stretch goal now becoming core).
3. **Recurring-issue analytics dashboard** – Aggregate findings across drafts to surface unclear guidelines and training needs, with exportable reports for brand managers.

## Team

Replace with actual names before final submission.

## Licence

MIT – built for the We Code Coder hackathon.
