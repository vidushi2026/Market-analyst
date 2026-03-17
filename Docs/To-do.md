## Architecture doc build plan (copy/paste checklist)

**Goal**: produce a complete, implementable `Docs/architecture.md` (previously drafted as `Docs/Architechture.md`) that clearly describes the system architecture, interfaces, data flow, and operational concerns.

---

## Phase 0 — File hygiene (naming + placement)
- [ ] **Choose canonical filename**: standardize on `Docs/architecture.md`.
- [ ] **Rename/move content**: migrate content from `Docs/Architechture.md` → `Docs/architecture.md`.
- [ ] **Redirect/stub** (optional): leave a short note in `Docs/Architechture.md` pointing to `Docs/architecture.md`, or delete `Docs/Architechture.md`.
- [ ] **Fix heading consistency**: ensure heading levels are consistent and not mixed (e.g., keep `##` for major sections, `###` for subsections).

---

## Phase 1 — Document framing (make it readable as a spec)
- [ ] **Add header block**:
  - [ ] Title: “Market Analyst — Architecture”
  - [ ] Status: Draft / In review / Approved
  - [ ] Owner + Last updated
  - [ ] Scope + Non-goals
  - [ ] Intended audience
- [ ] **Add TL;DR**: 5–10 bullets summarizing what the system is, what it does, and how it is structured.
- [ ] **Add glossary**: define key terms (ticker, query_type, agent, orchestrator, scoring, confidence, TTL, etc.).
- [ ] **Add “Key decisions”**: list 5–10 architectural decisions and rationale (LangGraph, FastAPI, Streamlit, caching approach, optional Redis, etc.).

---

## Phase 2 — Architecture views (Context → Container → Component)
- [ ] **System context (C4 L1)**:
  - [ ] Identify actors: user, UI, backend, orchestration, external providers (Yahoo Finance, DuckDuckGo/news), LLM provider (if used), cache (Redis/in-memory), optional DB.
  - [ ] Mark trust boundaries (internal vs external).
- [ ] **Container view (C4 L2)**:
  - [ ] Streamlit UI
  - [ ] FastAPI backend (API gateway)
  - [ ] LangGraph orchestrator (master node)
  - [ ] Agents modules (fundamental/technical/sentiment/portfolio)
  - [ ] Data layer (fetch + normalization + cache)
  - [ ] Result aggregation/formatting layer
  - [ ] Document protocols: HTTP/JSON, internal calls, async execution (if any).
- [ ] **Component view (C4 L3)**:
  - [ ] FastAPI: routers, schemas, services, orchestrator adapter, error handling.
  - [ ] Orchestrator: state model, nodes, parallel branches, aggregation, decision node.
  - [ ] Agents: inputs/outputs, scoring, data dependencies, failure modes.

---

## Phase 3 — API contracts (make the interfaces concrete)
- [ ] **Define request/response schemas for endpoints**:
  - [ ] `POST /analyze/stock`
  - [ ] `POST /analyze/portfolio`
  - [ ] `POST /compare`
- [ ] For each endpoint:
  - [ ] Request fields (required vs optional), types, constraints (e.g., ticker format).
  - [ ] Response fields (guaranteed vs optional), types, nullability.
  - [ ] At least 1 request example + 1 response example.
  - [ ] Define error format (standard JSON), error codes, and HTTP statuses.
- [ ] **Define versioning approach** (even if “v1 implicit”): how you’ll evolve schemas without breaking clients.

---

## Phase 4 — Agent contracts + orchestration semantics
- [ ] **Define a shared internal agent interface**:
  - [ ] Agent input object (ticker(s), time window, interval, locale/exchange, options).
  - [ ] Agent output object (score 0–10, summary, signals list, confidence, metadata/citations).
  - [ ] Error object structure (timeouts, missing data, provider failure).
- [ ] **LangGraph state definition**:
  - [ ] What lives in graph state (query, tickers, fetched datasets/references, partial results, errors, timings).
- [ ] **Node list and responsibilities**:
  - [ ] Intent parser
  - [ ] Data fetch/preprocess nodes (if separated)
  - [ ] Parallel agent nodes
  - [ ] Aggregation node
  - [ ] Decision node
  - [ ] Response formatting node
- [ ] **Parallelism and timeouts**:
  - [ ] Per-agent timeouts
  - [ ] Global timeout
  - [ ] Partial results rules (what is returned when an agent fails)
- [ ] **Retry policy**:
  - [ ] Which errors retry (network/provider) vs don’t retry (validation).
  - [ ] Max retries + backoff.

---

## Phase 5 — Data architecture (sources, caching, lifecycle)
- [ ] **Document data sources**:
  - [ ] Yahoo Finance: what is fetched (price history, financials, ratios), normalization rules.
  - [ ] DuckDuckGo/news: what is fetched (top N results), dedupe/clustering rules, how you select sources.
- [ ] **Caching strategy**:
  - [ ] Choose cache type: in-process vs Redis vs hybrid.
  - [ ] Cache keys (ticker + range + interval + query_type).
  - [ ] TTLs per data type (prices vs fundamentals vs news).
  - [ ] Invalidation rules and stale-data behavior.
- [ ] **Data quality rules**:
  - [ ] Missing/partial fields handling.
  - [ ] Market-closed behavior and timezone handling.
  - [ ] Ticker normalization (e.g., `.NS` handling).
- [ ] **Persistence decision** (optional):
  - [ ] Decide if you store results; if yes: schema, retention, privacy.

---

## Phase 6 — Scoring, normalization, and decision logic (pin down semantics)
- [ ] **Define scoring scale semantics**:
  - [ ] What does 0 / 5 / 10 mean for each agent?
  - [ ] Normalization formulas and clamping rules.
- [ ] **Define weighting model**:
  - [ ] Confirm/adjust current weights:
    - Fundamental \(0.4\)
    - Technical \(0.35\)
    - Sentiment \(0.25\)
  - [ ] Decide if weights are configurable (config file/env vars).
- [ ] **Decision thresholds**:
  - [ ] Confirm/adjust current thresholds:
    - > 7.5 → Strong Buy
    - 5.5–7.5 → Buy
    - 4–5.5 → Hold
    - < 4 → Avoid/Sell
  - [ ] Add rationale and edge-case rules.
- [ ] **Compare logic details**:
  - [ ] Tie-break rules (e.g., confidence, risk, trend alignment).
  - [ ] Ensure `side_by_side` schema is consistent.
- [ ] **Portfolio logic details**:
  - [ ] Clarify required inputs (weights optional?), output metrics definitions.
  - [ ] Decide whether portfolio engine is always run for portfolio queries.

---

## Phase 7 — Non-functional requirements (NFRs)
- [ ] **Performance targets**:
  - [ ] Target P50/P95 latency per endpoint.
  - [ ] Per-agent time budget.
- [ ] **Scalability**:
  - [ ] Concurrency expectations and how to handle them (async, threadpool, queue).
- [ ] **Reliability**:
  - [ ] Degradation strategy: partial results, fallback messages.
  - [ ] Circuit-breaker behavior (optional).
- [ ] **Security**:
  - [ ] Secrets management (API keys, LLM keys).
  - [ ] Input validation and sanitization.
  - [ ] CORS policy between Streamlit and FastAPI.
  - [ ] SSRF protections for any web fetching.
- [ ] **Privacy**:
  - [ ] What user inputs are logged; redaction rules.

---

## Phase 8 — Observability & operations
- [ ] **Logging**:
  - [ ] Correlation/request ID from UI → API → graph → agents.
  - [ ] Structured logs; log levels.
- [ ] **Metrics**:
  - [ ] Latency, error rates, cache hit rate, agent failure/timeout counts.
  - [ ] LLM token usage/cost (if applicable).
- [ ] **Tracing** (optional):
  - [ ] Spans per orchestrator node/agent.
- [ ] **Runbooks**:
  - [ ] “Yahoo down”
  - [ ] “DuckDuckGo/news failing”
  - [ ] “LLM provider errors”
  - [ ] “Redis unavailable”

---

## Phase 9 — Deployment & configuration
- [ ] **Local dev runbook**:
  - [ ] How to run Streamlit + FastAPI (ports, env vars).
  - [ ] How to run with/without cache.
- [ ] **Production deployment options**:
  - [ ] Single container vs split services.
  - [ ] Reverse proxy + TLS termination.
  - [ ] Redis topology (if used).
- [ ] **Configuration strategy**:
  - [ ] Env vars + config defaults.
  - [ ] Per-environment overrides.
- [ ] **Cost controls**:
  - [ ] Rate limiting, caching policy, LLM usage caps (if applicable).

---

## Phase 10 — Testing strategy (architecture-level)
- [ ] **Contract tests** for API schemas.
- [ ] **Unit tests**:
  - [ ] scoring normalization
  - [ ] decision mapping
  - [ ] ticker parsing
  - [ ] caching key/TTL logic
- [ ] **Integration tests**:
  - [ ] orchestrator end-to-end with mocked providers
  - [ ] agent behavior under missing data/timeouts
- [ ] **E2E smoke tests**:
  - [ ] Streamlit → FastAPI for stock, compare, and portfolio flows
- [ ] **Golden/snapshot outputs** (optional):
  - [ ] stable fixtures with stubs/mocks.

---

## Phase 11 — Extensibility roadmap (actionable)
- [ ] For each planned future addition (macro agent, sector rotation, alerts, backtesting):
  - [ ] Where it plugs into the graph
  - [ ] New data dependencies
  - [ ] Changes to scoring/weights
  - [ ] API/UI changes
  - [ ] Operational considerations (cost/latency)

---

## Phase 12 — Acceptance criteria (done means done)
- [ ] New contributor can answer from the doc:
  - [ ] Where request validation happens
  - [ ] How agents communicate outputs
  - [ ] What happens if sentiment fails
  - [ ] How the final recommendation is computed
  - [ ] Where to add a new agent
- [ ] Diagrams match the real file structure and runtime flow.
- [ ] Schemas are consistent across sections (names/types don’t drift).
- [ ] Failure modes are explicit (timeouts, partial scoring, missing data).
