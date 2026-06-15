# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: 2A202600823
- [REPO_URL]: https://github.com/Yangtai2504/2A202600823-NguyenThaiDuong-Day13
- [MEMBERS]:
  - Member A: Nguyen Thai Duong | Role: Logging & PII & Tracing & SLO & Alerts & Load Test & Dashboard & Demo & Report (Solo)

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 33
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: docs/screenshots/correlation-id.png
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: docs/screenshots/redacted-email.png
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: docs/screenshots/Trace-waterfall.png
- [TRACE_WATERFALL_EXPLANATION]: The `LabAgent.run` span shows two child spans: the RAG retrieval step and the LLM generation step. During the `rag_slow` incident, the retrieval span ballooned to ~2500ms (vs. ~50ms baseline), while the LLM span remained stable — confirming RAG latency as the sole root cause.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: docs/screenshots/Dashboards _ Langfuse.html
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | 2674ms |
| Error Rate | < 2% | 28d | 0% |
| Cost Budget | < $2.5/day | 1d | $0.04 |
| Quality Score Avg | > 0.75 | 28d | 0.88 |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: docs/screenshots/alert-rules.png
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: Latency spiked from ~165ms (P50 baseline) to ~8000ms per request. All 10 requests during the incident breached the 5000ms P95 SLO threshold. The `/metrics` endpoint showed `latency_p95` jumping to 2674ms even after incident was disabled (mixed window).
- [ROOT_CAUSE_PROVED_BY]: Langfuse trace waterfall — the `retrieve()` span inside `LabAgent.run` showed a 2500ms sleep introduced by `STATE["rag_slow"] = True` in `mock_rag.py:18`. The LLM generation span duration was unchanged, isolating the fault to the RAG layer.
- [FIX_ACTION]: Disabled `rag_slow` incident toggle via `POST /incidents/rag_slow/disable`. Latency returned to baseline (~165ms P50) immediately on next requests.
- [PREVENTIVE_MEASURE]: Add a per-span timeout on the RAG retrieval call (e.g., 1000ms hard limit with fallback to cached results). Alert `high_latency_p95` in `config/alert_rules.yaml` would fire within 30m of sustained breach, enabling on-call to disable the slow retrieval path before user impact compounds.

---

## 5. Individual Contributions & Evidence

### Nguyen Thai Duong (Solo)
- [TASKS_COMPLETED]:

  **1. Correlation ID Middleware (`app/middleware.py`)**

  Implemented `CorrelationIdMiddleware` using Starlette's `BaseHTTPMiddleware`. Key design decisions:
  - Called `clear_contextvars()` at the start of every request to prevent context leakage between concurrent requests in async environments — without this, structlog context from a previous request could bleed into the next one sharing the same worker.
  - Used `request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:8]}"` — the `or` pattern means external clients (e.g. a frontend or API gateway) can inject their own trace ID for end-to-end correlation, while the server generates one if absent.
  - Bound `correlation_id` via `bind_contextvars()` so it appears automatically in every subsequent log line within the request without passing it manually through function calls.
  - Added `x-response-time-ms` to response headers — enables client-side latency monitoring without needing to parse server logs.

  **2. Log Enrichment (`app/main.py`)**

  Added `bind_contextvars()` at the start of each `/chat` request binding: `user_id_hash`, `session_id`, `feature`, `model`, `env`. Key decisions:
  - Used `hash_user_id()` (SHA-256, 12-char prefix) instead of raw user ID — satisfies PII policy while still allowing grouping of traces by user across sessions.
  - Binding to structlog context (not passing as args) means all log lines — including those emitted deep inside `agent.py` — automatically carry these fields, enabling log-based fan-out queries like "all errors from feature=qa in the last hour".

  **3. PII Scrubbing Pipeline (`app/logging_config.py` + `app/pii.py`)**

  Activated `scrub_event` as a structlog processor inserted before `JsonlFileProcessor()`. This placement is critical: the processor runs in-memory before any bytes are written to disk, guaranteeing PII never persists.

  Regex patterns implemented:
  - `email`: standard RFC-like pattern covering subdomains
  - `phone_vn`: covers Vietnamese formats including `+84`, `0xx`, with `./-` separators
  - `cccd`: 12-digit Vietnamese national ID — uses `\b` word boundary to avoid matching credit card substrings
  - `credit_card`: 16 digits with optional `- ` separators
  - `passport` (bonus): `[A-Z]\d{7}` — Vietnamese passport format (e.g. B1234567)
  - `vn_address` (bonus): keyword-anchored regex matching common Vietnamese address prefixes (số, đường, phường, quận, etc.)

  The `scrub_text()` function replaces each match with a labeled placeholder (`[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, etc.) rather than a generic `***` — this allows auditors to know *what type* of PII was present without seeing the value.

  **4. Langfuse v4 Tracing (`app/tracing.py` + `app/agent.py`)**

  Encountered and resolved a major compatibility issue: the template used `langfuse.decorators` which does not exist in the installed SDK version (3.2.1 → upgraded to 4.7.1). Root cause: Langfuse v3+ migrated to OpenTelemetry (OTEL) as the underlying transport, breaking the v2 decorator API.

  Solution: used `get_client().start_as_current_observation()` as a context manager with `propagate_attributes()` for trace-level metadata:
  - `propagate_attributes(trace_name=..., user_id=..., session_id=..., tags=...)` must be called as a context manager (returns an OTEL baggage context), not a plain function call — this was a subtle API requirement discovered through testing.
  - `as_type="span"` explicitly marks the observation type for correct rendering in Langfuse waterfall view.
  - `flush_traces()` called after each response via `get_client().flush()` — necessary because Langfuse v4 buffers spans asynchronously via OTEL exporter; without an explicit flush, spans remain in memory and are lost if the process exits or between load test runs.

  **5. Incident Analysis (rag_slow)**

  Ran `scripts/inject_incident.py --scenario rag_slow`, then `scripts/load_test.py --concurrency 3`. Observed latency jump from ~155ms to ~8000ms. Debug flow:
  - **Metrics** (`/metrics` endpoint): `latency_p95` jumped from 165ms to 2674ms (mixed window after disable)
  - **Traces** (Langfuse): `agent.run` span duration confirmed ~8000ms total; metadata showed `doc_count` unchanged (RAG returned results, just slowly)
  - **Logs** (`data/logs.jsonl`): `latency_ms` field in `response_sent` events confirmed 8000ms consistently across all features (qa and summary), ruling out feature-specific regression
  - **Root cause**: `mock_rag.py:18` — `time.sleep(2.5)` triggered by `STATE["rag_slow"] = True`. The sleep happens before document retrieval returns, so every request regardless of query hits this bottleneck.

  **6. Dashboard & SLO Design**

  Created 6-panel "Day13 Observability Dashboard" in Langfuse covering: Latency P95, Traffic (observation count), Cost (sum), Token Input, Token Output, Error Count. Each panel filtered by `Trace Name ∈ {chat/qa, chat/summary}` to isolate lab traffic from test noise.

  SLO rationale:
  - P95 < 3000ms: allows 20x headroom over baseline (155ms) while catching rag_slow-class incidents (8000ms)
  - Error rate < 2%: standard web API SLO, achievable given mock LLM never throws
  - Cost < $2.5/day: at current rate ($0.002/req avg), allows ~1250 requests/day before alerting

- [EVIDENCE_LINK]: https://github.com/Yangtai2504/2A202600823-NguyenThaiDuong-Day13/commits/main

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: N/A
- [BONUS_AUDIT_LOGS]: N/A
- [BONUS_CUSTOM_METRIC]: Added two extra PII redaction patterns (`passport`, `vn_address`) beyond the template's 4 defaults, improving PII coverage for Vietnamese user data without impacting `validate_logs.py` score.
