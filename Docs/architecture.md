## Market Analyst — Architecture

**Status**: Draft  
**Owner**: TBD  
**Last updated**: 2026-03-17  

### Scope
- Describes the end-to-end architecture of the Market Analyst system: UI → API → orchestration → agents → data sources → aggregation.
- Defines high-level responsibilities, runtime flow, and output formats for the system.

### Non-goals
- Exact implementation details for every module/function.
- Production deployment hardening (covered later as the system matures).

### Intended audience
- Engineers contributing to the codebase
- Anyone integrating with the API (internal)

---

## TL;DR
- A **Streamlit UI** collects user intent (stock / compare / portfolio) and renders results.
- A **FastAPI backend** validates requests and calls the orchestration layer.
- A **LangGraph orchestrator** runs specialized agents (fundamental/technical/sentiment/portfolio) **in parallel** with timeouts.
- Agents fetch data from **Yahoo Finance** and **DuckDuckGo/news search**, then produce structured outputs.
- An **aggregation layer** normalizes agent outputs onto a common scale and computes a final recommendation.
- The system returns a single **JSON response** which the UI renders into sections and charts.

---

## Glossary
- **Agent**: A specialized analysis module (e.g., fundamental, technical, sentiment).
- **Orchestrator**: The LangGraph DAG that routes and coordinates agent execution.
- **Score**: A 0–10 numeric rating emitted by an agent after analysis.
- **Signal**: A human-readable label supporting an agent’s analysis (e.g., “golden cross”).
- **Confidence**: A 0–1 value describing how certain a component is in its assessment.
- **TTL**: Cache “time to live” duration after which cached data is refreshed.

---

## Key decisions (v1)
- Use **Streamlit** to move quickly on UX and interactive visuals.
- Use **FastAPI** as an API gateway for validation, routing, and consistent response envelopes.
- Use **LangGraph** to model the analysis as a DAG with parallel branches and well-defined nodes.
- Use **yfinance** for market/fundamental data access and **duckduckgo-search** for public news discovery.
- Prefer **caching** (in-memory, optional Redis later) to reduce external calls and improve latency.
- Produce a single **structured JSON** response that includes agent breakdown + final recommendation.

---

## 2) Architecture Views (Phase 2)

### 2.1 System context (C4 L1)

**Primary actors**
- **User**: submits a query and consumes results.

**External systems**
- **Yahoo Finance**: price history + fundamentals/ratios (via `yfinance`).
- **DuckDuckGo search/news**: discover recent articles/headlines (via `duckduckgo-search`).
- **LLM provider** (optional): used by the sentiment agent for classification/summarization.

**Internal systems**
- **Streamlit UI**: collects intent and renders charts + narrative.
- **FastAPI backend**: validates requests, routes to orchestration, returns consistent response JSON.
- **LangGraph orchestrator**: coordinates agent execution, timeouts, aggregation, and final decision.
- **Agents**: fundamental / technical / sentiment / portfolio engine.
- **Data layer + cache**: normalizes and caches external data to reduce latency/cost.

**Trust boundaries**
- Calls from internal services to external providers cross a trust boundary and must be treated as **untrusted** (timeouts, partial data, format drift).
- Any LLM output is **untrusted** and must be validated/normalized before entering scoring/decisioning.

---

### 2.2 Container view (C4 L2)

```
[User]
  │ (UI interaction)
  ▼
[Streamlit UI]
  │ (HTTP/JSON)
  ▼
[FastAPI Service]
  │ (in-process call)
  ▼
[LangGraph Orchestrator]
  ├─► [Fundamental Agent] ─► [Yahoo Finance]
  ├─► [Technical Agent]   ─► [Yahoo Finance]
  ├─► [Sentiment Agent]   ─► [DuckDuckGo/news] ─► [LLM provider (optional)]
  └─► [Portfolio Engine]  ─► [Yahoo Finance]
            │
            ▼
     [Aggregation/Decision]
            │
            ▼
     [Response JSON → UI]
```

**Data movement**
- The orchestrator passes **a normalized internal request** to each agent (ticker(s), query type, options).
- Agents return **structured outputs** (score/signals/summary) and optionally raw data references.
- Aggregation combines agent outputs into a final recommendation and a single response envelope.

---

### 2.3 Component view (C4 L3)

**FastAPI service components**
- **Routers**: `/analyze/stock`, `/analyze/portfolio`, `/compare`.
- **Request validation**: schema validation + ticker normalization.
- **Orchestration adapter**: maps API request → internal orchestrator input.
- **Response formatter**: wraps output in a consistent response envelope and error format.

**LangGraph orchestrator components**
- **Intent parser node**: decides query type and required agents.
- **Parallel agent nodes**: run fundamental/technical/sentiment (and portfolio engine for portfolio queries).
- **Aggregation node**: normalizes scores to 0–10 and merges outputs.
- **Decision node**: applies weighting + thresholds to emit recommendation and confidence.

**Agent components (common pattern)**
- **Input normalization**: ticker normalization; time window defaults.
- **Data access**: uses the data layer + cache to fetch/refresh external data.
- **Signal extraction**: computes indicators/ratios/events.
- **Scoring**: emits score + signals + summary + confidence (where applicable).

---

## 3) API Contracts (Phase 3)

### 3.1 Conventions

**Content type**
- Requests and responses are JSON.

**Response envelope (success)**

```
{
  "request_id": "string",
  "status": "ok",
  "data": { ... }
}
```

**Response envelope (error)**

```
{
  "request_id": "string",
  "status": "error",
  "error": {
    "code": "string",
    "message": "string",
    "details": { ... }
  }
}
```

**Common error codes**
- `VALIDATION_ERROR`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_UNAVAILABLE`
- `PARTIAL_RESULTS`
- `INTERNAL_ERROR`

---

### 3.2 `POST /analyze/stock`

**Request**

```
{
  "ticker": "string",
  "options": {
    "period": "string (optional, e.g. 6mo, 1y)",
    "interval": "string (optional, e.g. 1d, 1h)",
    "include_portfolio_engine": false
  }
}
```

**Response (`data`)**

```
{
  "final_recommendation": "Strong Buy|Buy|Hold|Avoid|Sell",
  "confidence": 0-1,
  "final_score": 0-10,
  "agent_breakdown": {
    "fundamental": { "summary": "string", "score": 0-10, "signals": ["string"] },
    "technical": { "trend": "bullish|bearish|sideways", "signals": ["string"], "score": 0-10 },
    "sentiment": { "sentiment": "positive|neutral|negative", "confidence": 0-1, "key_events": ["string"] }
  },
  "explanation": "string"
}
```

**Example (request)**

```
{
  "ticker": "TATAMOTORS.NS",
  "options": { "period": "6mo", "interval": "1d" }
}
```

---

### 3.3 `POST /compare`

**Request**

```
{
  "stocks": ["string", "string"],
  "options": {
    "period": "string (optional)",
    "interval": "string (optional)"
  }
}
```

**Response (`data`)**

```
{
  "winner": "string",
  "reason": "string",
  "side_by_side": {
    "left": { "ticker": "string", "final_score": 0-10, "agent_breakdown": { ... } },
    "right": { "ticker": "string", "final_score": 0-10, "agent_breakdown": { ... } }
  }
}
```

**Example (request)**

```
{
  "stocks": ["TATAMOTORS.NS", "M&M.NS"]
}
```

---

### 3.4 `POST /analyze/portfolio`

**Request**

```
{
  "portfolio": [
    { "ticker": "string", "weight": 0-1 }
  ],
  "options": {
    "period": "string (optional)",
    "interval": "string (optional)"
  }
}
```

**Response (`data`)**

```
{
  "portfolio_health": "string",
  "summary": "string",
  "risk_level": "low|medium|high",
  "diversification_score": 0-10,
  "weakest": { "ticker": "string", "reason": "string" },
  "strongest": { "ticker": "string", "reason": "string" },
  "suggested_rebalance": [
    { "ticker": "string", "action": "increase|decrease|remove|add", "rationale": "string" }
  ],
  "per_stock": [
    { "ticker": "string", "final_score": 0-10, "agent_breakdown": { ... } }
  ]
}
```

**Example (request)**

```
{
  "portfolio": [
    { "ticker": "TATAMOTORS.NS", "weight": 0.5 },
    { "ticker": "M&M.NS", "weight": 0.5 }
  ],
  "options": { "period": "1y", "interval": "1d" }
}
```

---

## 4) Agent Contracts & Orchestration Semantics (Phase 4)

### 4.1 Internal contracts (shared across agents)

**Internal agent input**

```
{
  "request_id": "string",
  "query_type": "stock|compare|portfolio",
  "tickers": ["string"],
  "options": {
    "period": "string (optional)",
    "interval": "string (optional)",
    "locale": "string (optional)",
    "exchange": "string (optional)"
  }
}
```

**Internal agent output**

```
{
  "agent": "fundamental|technical|sentiment|portfolio",
  "status": "ok|partial|error",
  "summary": "string",
  "score": 0-10,
  "confidence": 0-1,
  "signals": ["string"],
  "key_events": ["string (optional)"],
  "metadata": {
    "provider": "string (optional)",
    "as_of": "string (optional, ISO-8601)",
    "timing_ms": "number (optional)"
  },
  "error": {
    "code": "string",
    "message": "string",
    "details": { ... }
  }
}
```

**Normalization rules**
- `status=partial` is used when an agent completes but with missing upstream fields or reduced coverage.
- `score` MUST be present for `status=ok|partial`. If not computable, return `status=error` and omit `score`.
- `confidence` is optional for agents that do not compute it; if omitted, aggregation treats it as unknown.

---

### 4.2 Orchestrator state (LangGraph)

**State shape (conceptual)**

```
{
  "request_id": "string",
  "query_type": "stock|compare|portfolio",
  "tickers": ["string"],
  "options": { ... },
  "inputs": { ... },
  "agent_results": {
    "fundamental": { ... },
    "technical": { ... },
    "sentiment": { ... },
    "portfolio": { ... }
  },
  "errors": [{ "code": "string", "message": "string" }],
  "timings_ms": { "total": 0, "by_node": { ... } }
}
```

---

### 4.3 Node responsibilities (minimum v1)
- **Intent parser node**
  - Determines `query_type` and required tickers.
  - Normalizes tickers and default `options` (period/interval).
- **Agent execution nodes (parallel)**
  - Execute fundamental/technical/sentiment in parallel.
  - Execute portfolio engine only for portfolio queries (and optionally when requested).
- **Aggregation node**
  - Normalizes heterogeneous outputs into a consistent structure.
  - Produces per-agent contribution and a unified final score.
- **Decision node**
  - Applies weights + thresholds.
  - Emits `final_recommendation` and overall confidence (if implemented).

---

### 4.4 Timeouts, retries, and partial results

**Timeouts**
- Per-agent timeout: configured (example target: 5–15s depending on provider).
- Global request timeout: bounded (example target: 20–30s).

**Retries (recommended defaults)**
- Retry transient upstream failures (timeouts/5xx) up to 2 times with backoff.
- Do NOT retry validation errors or deterministic parsing failures.

**Partial results behavior**
- If 1 agent fails, aggregation continues using available agent outputs.
- If all agents fail, return an API error with `INTERNAL_ERROR` or an upstream-specific code.

---

## 5) Data Architecture (Phase 5)

### 5.1 Data sources

**Yahoo Finance (`yfinance`)**
- Used for: price history, financials, ratios (as available).
- Expected failure modes: rate limiting, partial fields, stale values, symbol resolution issues.

**DuckDuckGo/news (`duckduckgo-search`)**
- Used for: discovery of top N recent articles/headlines.
- Expected failure modes: throttling, duplicates, low-quality sources, missing article metadata.

**LLM provider (optional)**
- Used for: sentiment classification and summarization of headlines.
- Expected failure modes: timeouts, non-deterministic output, hallucinations (must be treated as untrusted).

---

### 5.2 Data layer responsibilities
- Fetch raw upstream data (with timeouts).
- Normalize into internal canonical formats (prices, fundamentals, news items).
- Cache intermediate results to reduce repeated calls.
- Provide “as_of” timestamps and provenance metadata.

---

### 5.3 Canonical normalized formats (conceptual)

**Price series**

```
{
  "ticker": "string",
  "as_of": "string (ISO-8601)",
  "interval": "string",
  "period": "string",
  "rows": [
    { "ts": "string (ISO-8601)", "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0 }
  ]
}
```

**News item**

```
{
  "title": "string",
  "url": "string",
  "source": "string (optional)",
  "published_at": "string (optional, ISO-8601)",
  "snippet": "string (optional)"
}
```

---

### 5.4 Caching strategy (v1)

**Cache location**
- In-memory cache first; optional Redis can be added later without changing interfaces.

**Cache keys**
- Prices: `prices:{ticker}:{period}:{interval}`
- Fundamentals: `fundamentals:{ticker}`
- News: `news:{ticker}:{window}`

**TTLs (recommended starting points)**
- Prices (intraday): 5–15 minutes
- Prices (daily): 30–60 minutes
- Fundamentals: 12–24 hours
- News: 30–60 minutes

**Invalidation**
- TTL-based only for v1.
- On upstream errors, serve stale data only if explicitly enabled (otherwise fail fast for correctness).

---

### 5.5 Data quality rules
- **Ticker normalization**: enforce canonical tickers before fetching (e.g., exchange suffix rules like `.NS`).
- **Missing fields**: agents must handle absent ratios/financial fields by marking `status=partial`.
- **Timezone handling**: store timestamps in ISO-8601; convert for display only in UI.
- **Market closed**: allow stale-but-recent prices for daily interval with a clear `as_of`.

---

## 6) Scoring, Normalization, and Decisioning (Phase 6)

### 6.1 Scoring principles
- **All agent scores are normalized to a 0–10 scale** where:
  - 0 = strongly negative signal set
  - 5 = neutral / mixed
  - 10 = strongly positive signal set
- **Scores must be explainable**: each agent MUST provide `signals` supporting the score.
- **Partial data must not overstate confidence**: when an agent is `status=partial`, it should reduce confidence and/or keep score closer to neutral unless strong evidence exists.

---

### 6.2 Agent-level scoring semantics

**Fundamental agent (0–10)**
- **0–3**: weak fundamentals (deteriorating earnings, high leverage, poor returns)
- **4–6**: mixed/average fundamentals
- **7–10**: strong fundamentals (improving profitability, manageable leverage, attractive valuation vs history/peers)

**Technical agent (0–10)**
- **0–3**: bearish structure (downtrend, weak momentum, unfavorable MA alignment)
- **4–6**: sideways / uncertain (conflicting indicators)
- **7–10**: bullish structure (uptrend, momentum confirmation, favorable MA alignment)

**Sentiment agent (0–10)**
- Map headline sentiment into score bands:
  - **negative** → 0–3
  - **neutral** → 4–6
  - **positive** → 7–10
- If sentiment is derived from sparse/noisy sources, the agent should emit `status=partial` and lower confidence.

**Portfolio engine (0–10)**
- Used only for portfolio queries (and optional for stock queries if explicitly enabled).
- Represents **portfolio quality** (diversification + risk-adjusted profile), not “buy/sell”.

---

### 6.3 Normalization rules (agent outputs → comparable 0–10)

**Inputs**
- Each agent returns either:
  - a numeric `score` (already 0–10), or
  - categorical outputs that must be mapped to score bands.

**Categorical mapping (v1 defaults)**
- Technical `trend`:
  - `bullish` → 8
  - `sideways` → 5
  - `bearish` → 2
- Sentiment `sentiment`:
  - `positive` → 8
  - `neutral` → 5
  - `negative` → 2

**Clamping**
- Any computed score MUST be clamped into [0, 10].

**Partial adjustment (recommended)**
- If an agent emits `status=partial`, apply a conservative pull-to-neutral:
  - \(score' = 5 + 0.7 \times (score - 5)\)

---

### 6.4 Weighting model

**Weights (v1)**

```
final_score =
  0.40 * fundamental +
  0.35 * technical +
  0.25 * sentiment
```

**Missing agents**
- If an agent result is `status=error` (or missing), exclude it and **renormalize weights** across available agents.

---

### 6.5 Final recommendation thresholds

```
final_score > 7.5  → Strong Buy
5.5 – 7.5          → Buy
4.0 – 5.5          → Hold
final_score < 4.0  → Avoid/Sell
```

---

### 6.6 Overall confidence (v1 definition)
- If agent confidences are available, define overall confidence as:
  - weighted average of available agent confidences, using the same normalized weights.
- If confidences are missing, compute a heuristic confidence based on:
  - number of successful agents
  - presence of `partial` statuses
  - dispersion between agent scores (high disagreement → lower confidence)

---

### 6.7 Compare query tie-break rules
When two stocks have similar `final_score` (difference ≤ 0.5):
- Prefer higher **overall confidence**
- Prefer lower disagreement between agent scores
- Prefer stronger technical alignment with the chosen timeframe (period/interval)

---

### 6.8 Portfolio roll-up guidance
- Portfolio endpoints should report:
  - **portfolio-level score** (0–10) for diversification/risk quality
  - **per-stock final_score** for relative strength within the portfolio
- Portfolio “suggested rebalance” should reference the weakest/strongest constituents and explain which agent signals drove the recommendation.

---

## Phase 7 — Non-functional requirements (NFRs)

### Performance
- **Targets (initial)**
  - `POST /analyze/stock`: P50 < 8s, P95 < 20s
  - `POST /compare`: P50 < 16s, P95 < 40s (runs 2 analyses)
  - `POST /analyze/portfolio`: linear in N; cap N for v1 or use async execution
- **Budgets**
  - Per upstream call timeout: ~12s (configurable)
  - Prefer caching over repeated upstream calls

### Scalability
- v1 is designed for single-instance execution; scale by:
  - running multiple backend workers (process-level) and relying on caching
  - introducing Redis cache for shared caching across workers (optional)
- For portfolio analysis, consider async execution or background jobs for large N.

### Reliability & graceful degradation
- If an upstream provider fails:
  - return partial results if at least one agent succeeds
  - renormalize weights across available agents (Phase 6)
- If all agents fail: return `status=error` with `UPSTREAM_UNAVAILABLE` or `INTERNAL_ERROR`.

### Security
- Validate and sanitize user inputs (tickers, lists).
- Treat all upstream and LLM outputs as untrusted; normalize and clamp scores.
- Do not store secrets in git (`.env` is ignored by `.gitignore`).

### Observability
- Log key flows to `dump.log` (request start/end, upstream calls, cache hits, agent status).
- Include `request_id` in every API response and log line.

---

## Phase 8 — Observability & operations

### Logging
- **Sink**: `dump.log` (rotating file)
- **Format**: structured-ish key/value in message (e.g., `request_id=... agent=...`)
- **Correlation**:
  - API generates a `request_id` per request (returned to clients)
  - Orchestrator generates its own `request_id` for internal tracking (v1)

### Metrics (v1)
- Exposed via `GET /metrics` as JSON (in-process).
- **Captured metrics** (initial):
  - API request counts: `api_analyze_stock_requests`, `api_compare_requests`, `api_analyze_portfolio_requests`
  - API success/error counts: `*_ok`, `*_error`
  - Upstream timings (ms): `upstream_yahoo_prices_ms`, `upstream_yahoo_fundamentals_ms`, `upstream_ddg_news_ms`
  - Agent timings (ms): `agent_fundamental_ms`, `agent_technical_ms`, `agent_sentiment_ms`
  - Cache hit/miss counts: `cache_hit_prices`, `cache_miss_prices`, etc.

### Tracing (future)
- v1 uses timers + `request_id` logging; can be upgraded to OpenTelemetry spans later.

### Runbooks (v1)
- **Yahoo down / rate limited**
  - Symptoms: high `upstream_yahoo_*` latency, increased agent partial/error.
  - Actions: reduce request volume, increase caching TTL, retry with backoff, return partial results.
- **DuckDuckGo/news failing**
  - Symptoms: `upstream_ddg_news_ms` spikes, sentiment becomes `partial`.
  - Actions: reduce max_results, increase TTL, degrade sentiment weight if needed.
- **LLM provider errors** (if enabled later)
  - Symptoms: sentiment agent errors/timeouts.
  - Actions: fall back to heuristic sentiment, disable LLM usage temporarily.
- **Redis unavailable** (future)
  - Actions: fall back to in-process cache, reduce concurrency, monitor memory.

---

## Phase 9 — Deployment & configuration

### Local development
- **Install deps**: `make install`
- **Run backend**: `make dev-backend` (FastAPI on `:8000`)
- **Run frontend**: `make dev-frontend` (Streamlit on `:8501`)
- **Health checks**
  - `GET /health` for basic liveness
  - `GET /metrics` for in-process metrics snapshot

### Docker (v1)
- **Build**: `make docker-build`
- **Run**: `make docker-run` (exposes `:8000`)

### Production options (v1 guidance)
- Run the backend behind a reverse proxy (TLS termination, request limits).
- Scale by running multiple backend workers/instances; consider Redis for shared caching if needed.
- Keep Streamlit separate from the API in production if you want independent scaling/deploy.

### Configuration strategy
- Centralize defaults in `config/settings.py` (weights, TTLs, upstream timeouts).
- Prefer environment-variable overrides (future) for per-environment tuning.

### Cost controls (if/when LLM is enabled)
- Hard caps on max news results and frequency.
- Prefer cached results; avoid re-running full analysis on refresh loops.
- Always support a “no-LLM / heuristic sentiment” mode.

---

## Phase 10 — Testing strategy (implementation)

### Unit tests (already present)
- Scoring thresholds/renormalization.
- Sentiment agent with mocked news provider.

### API contract tests (add/maintain)
- Verify response envelope (`request_id`, `status`, `data|error`) for each endpoint.
- Verify basic validation behavior (e.g., compare requires exactly 2 tickers).

### Integration tests (mocked)
- End-to-end FastAPI route → orchestrator using monkeypatched orchestrator/service dependencies.
- No real upstream calls (Yahoo/DDG) during tests.

### E2E smoke test (manual for v1)
- Run backend + frontend locally and execute:
  - stock analysis
  - compare
  - portfolio analysis

---

## Phase 11 — Extensibility roadmap (actionable)

### Add a new agent (general plug-in steps)
- **Code**: implement a new agent module in `backend/agents/`.
- **Data**: add/extend a service in `backend/services/` if new upstream data is needed.
- **Orchestration**: call the agent from `backend/orchestrator/orchestrator.py` and include it in aggregation.
- **Scoring**: extend `backend/orchestrator/scoring.py`:
  - add weight/config in `config/settings.py`
  - define normalization rules and thresholds if needed
- **API**: extend response `agent_breakdown` schema (and UI rendering) to surface the agent output.
- **Tests**: add unit tests with mocks; never call real upstream providers during tests.
- **Metrics**: add agent timing/error metrics and any new upstream timing counters.

### Macro-economic agent
- **Plug-in point**: alongside fundamental/sentiment in stock analysis.
- **Inputs**: country/region, rates, inflation, FX, commodities proxy.
- **Outputs**: macro regime label + 0–10 score + signals.
- **Impact**: optional additional weight; can also modify thresholds for cyclical sectors.

### Sector rotation analysis
- **Plug-in point**: compare + portfolio analysis.
- **Inputs**: sector classification + relative strength over period.
- **Outputs**: sector momentum signals + diversification warnings.

### Backtesting engine
- **Plug-in point**: separate workflow (not on the critical path of the API).
- **Inputs**: strategy rules, lookback period, universe.
- **Outputs**: performance metrics, drawdown, win rate.
- **Ops**: run as async/background job; store results.

### Real-time alerts
- **Plug-in point**: separate service triggered by schedule/webhooks.
- **Inputs**: tickers + alert rules.
- **Outputs**: notifications (email/webhook).
- **Ops**: rate limiting + dedupe required.

---

## Phase 12 — Acceptance criteria (done means done)

### Documentation acceptance
- A new contributor can answer from `Docs/architecture.md`:
  - where request validation happens
  - how agents communicate outputs
  - what happens if sentiment fails
  - how final recommendation is computed
  - where to add a new agent

### Implementation acceptance (v1)
- Backend starts locally with `make dev-backend` and serves:
  - `GET /health` returns `{status: ok, request_id: ...}`
  - `GET /metrics` returns JSON with `counters` and `timers`
- Core flows work end-to-end:
  - `POST /analyze/stock` returns `status=ok` with `final_recommendation`, `final_score`, and `agent_breakdown`
  - `POST /compare` returns `status=ok` with `winner` and `side_by_side`
  - `POST /analyze/portfolio` returns `status=ok` with `per_stock`
- Tests are runnable with `make test` and use mocks (no real upstream calls required).
- Logs are written to `dump.log` for main flows.

## 1) High-Level Architecture

```
[ User (Streamlit UI) ]
            │
            ▼
[ FastAPI Backend ]
            │
            ▼
[ LangGraph Orchestrator (Master Node) ]
     ├───────────────┬───────────────┬───────────────┐
     ▼               ▼               ▼               ▼
[Fundamental]   [Technical]    [Sentiment]     [Portfolio Engine]
  Agent           Agent          Agent              (optional)
    │               │               │
    ├───────┬───────┴───────┬───────┘
            ▼               ▼
    [Yahoo Finance]   [DuckDuckGo Search]
            ▼               ▼
        [Data Layer / Cache / Preprocessing]
                        │
                        ▼
              [Result Aggregation Layer]
                        │
                        ▼
               [Final Response JSON]
                        │
                        ▼
               [Streamlit Rendering]
```

---

## 2) Core Components

### 2.1 Frontend (Streamlit)

**Responsibilities**
- **Input**:
  - Single stock query
  - Portfolio input (list + weights optional)
  - Comparison query
- **Output**:
  - Charts (price, indicators)
  - Agent-wise analysis sections
  - Final recommendation

**Key modules**
- Input parser
- Visualization (matplotlib/plotly)
- API client to FastAPI

---

### 2.2 Backend (FastAPI)

**Responsibilities**
- API gateway
- Request validation
- Route to LangGraph orchestrator

**Endpoints**

```
POST /analyze/stock
POST /analyze/portfolio
POST /compare
```

**Request example**

```
{
  "query_type": "compare",
  "stocks": ["TATAMOTORS.NS", "M&M.NS"]
}
```

---

### 2.3 Orchestration Layer (LangGraph)

**Master node responsibilities**
- Parse intent
- Spawn agents in parallel
- Collect outputs
- Normalize outputs
- Aggregate into final decision

**Flow**

```
START
  ↓
Intent Parser Node
  ↓
Parallel Execution:
  → Fundamental Agent
  → Technical Agent
  → Sentiment Agent
  ↓
Aggregation Node
  ↓
Decision Node
  ↓
END
```

**Execution type**
- Parallel branches using LangGraph DAG
- Timeout handling per agent

---

## 3) Agents Design

### 3.1 Fundamental Analyst Agent

**Input**
- Stock ticker

**Data source**
- Yahoo Finance API

**Processing**
- Financial ratios:
  - P/E
  - EPS
  - ROE
  - Debt/Equity
- Revenue + profit trends
- Sector comparison (optional)

**Output**

```
{
  "summary": "...",
  "score": 0-10,
  "signals": ["undervalued", "strong earnings"]
}
```

---

### 3.2 Technical Analyst Agent

**Input**
- Historical price data

**Processing**
- Indicators:
  - Moving Averages (50, 200)
  - RSI
  - MACD
  - Volume trends
- Pattern detection (basic)

**Output**

```
{
  "trend": "bullish/bearish/sideways",
  "signals": ["golden cross", "overbought"],
  "score": 0-10
}
```

---

### 3.3 Sentiment Analyst Agent

**Input**
- Company name / ticker

**Data source**
- DuckDuckGo search (news scraping)

**Processing**
- Extract top N news articles
- LLM-based sentiment classification
- Headline clustering

**Output**

```
{
  "sentiment": "positive/neutral/negative",
  "confidence": 0-1,
  "key_events": ["earnings beat", "regulatory issue"]
}
```

---

### 3.4 Portfolio Engine (Optional but required for query 2)

**Input**
- List of stocks

**Processing**
- Aggregate returns
- Risk metrics:
  - Volatility
  - Correlation
- Sector diversification

**Output**

```
{
  "performance": "...",
  "risk_level": "...",
  "diversification_score": ...
}
```

---

## 4) Data Layer

### Sources

#### Yahoo Finance
- Price history
- Financials
- Ratios

**Library**
- `yfinance`

#### DuckDuckGo
- News search
- Public sentiment signals

**Library**
- `duckduckgo-search`

---

### Caching Layer

**Purpose**
- Avoid repeated API calls
- Improve latency

**Options**
- In-memory (Redis optional)
- TTL: 5–15 minutes for price data

---

## 5) Aggregation & Decision Logic

**Input**
- Scores + outputs from all agents

**Normalization**
- Convert all outputs → common scoring scale (0–10)

**Weighted model**

```
Final Score =
  0.4 * Fundamental +
  0.35 * Technical +
  0.25 * Sentiment
```

**Decision mapping**

```
Score > 7.5 → Strong Buy
5.5–7.5 → Buy
4–5.5 → Hold
< 4 → Avoid/Sell
```

---

## 6) Comparison Logic

For queries like: “Tata Motors vs Mahindra”

**Steps**
- Run all agents for both stocks
- Compare:
  - Scores
  - Risk
  - Trend alignment

**Output**

```
{
  "winner": "TATAMOTORS",
  "reason": "...",
  "side_by_side": {...}
}
```

---

## 7) Portfolio Analysis Logic

**Steps**
- Fetch all stock data
- Compute:
  - Individual returns
  - Weighted return
  - Risk metrics
- Run agents per stock
- Aggregate insights

**Output**
- Portfolio health
- Weakest/strongest stock
- Suggested rebalance

---

## 8) Tech Stack

**Backend**
- FastAPI
- LangGraph
- Python

**Agents**
- OpenAI / local LLM (optional)
- yfinance
- duckduckgo-search

**Frontend**
- Streamlit

**Infra**
- Docker (optional)
- Redis (optional caching)

---

## 9) File Structure

```
project/
│
├── backend/
│   ├── main.py (FastAPI)
│   ├── routes/
│   ├── orchestrator/
│   │     └── langgraph_flow.py
│   ├── agents/
│   │     ├── fundamental.py
│   │     ├── technical.py
│   │     ├── sentiment.py
│   ├── services/
│   │     ├── yahoo_service.py
│   │     ├── search_service.py
│   ├── utils/
│
├── frontend/
│   └── streamlit_app.py
│
├── models/
│   └── schemas.py
│
└── config/
    └── settings.py
```

---

## 10) Execution Flow Example

**User query**: “Compare Tata Motors and Mahindra”

**Flow**
1. UI → FastAPI
2. FastAPI → LangGraph
3. LangGraph runs all agents for both stocks
4. Aggregator scores + compares
5. Response → UI

---

## 11) Failure Handling
- API timeout → fallback message
- Missing data → partial scoring
- Agent failure → exclude from weighting

---

## 12) Extensibility

**Future additions**
- Macro-economic agent
- Sector rotation analysis
- Real-time alerts
- Backtesting engine

---

## 13) Output Format (Final Response)

```
{
  "final_recommendation": "Buy",
  "confidence": 0.78,
  "agent_breakdown": {
    "fundamental": {...},
    "technical": {...},
    "sentiment": {...}
  },
  "explanation": "..."
}
```

