## Market Analyst

A multi-agent market analysis system that ingests financial + web data, runs specialized analyses, and produces a unified recommendation through orchestration.

### Documentation
- **Architecture (canonical)**: `Docs/architecture.md`
- **Architecture build checklist (phased)**: `Docs/To-do.md`
- **Project rules**: `Docs/Rules.md`

### High-level flow
- **Streamlit UI** → **FastAPI** → **LangGraph orchestrator** → agents (fundamental/technical/sentiment/portfolio) → aggregation → response JSON → UI rendering.


