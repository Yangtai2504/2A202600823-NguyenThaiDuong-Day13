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
- [TOTAL_TRACES_COUNT]: 20
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: [Path to image]
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: [Path to image]
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: [Path to image]
- [TRACE_WATERFALL_EXPLANATION]: The `LabAgent.run` span shows two child spans: the RAG retrieval step and the LLM generation step. During the `rag_slow` incident, the retrieval span ballooned to ~2500ms (vs. ~50ms baseline), while the LLM span remained stable — confirming RAG latency as the sole root cause.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: [Path to image]
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | 2674ms |
| Error Rate | < 2% | 28d | 0% |
| Cost Budget | < $2.5/day | 1d | $0.04 |
| Quality Score Avg | > 0.75 | 28d | 0.88 |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: [Path to image]
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
  - Implemented `CorrelationIdMiddleware` in `app/middleware.py`: clear contextvars, generate `req-<8hex>` IDs, bind to structlog, propagate in response headers
  - Enriched request logs in `app/main.py`: bind `user_id_hash`, `session_id`, `feature`, `model`, `env` per request
  - Activated PII scrubbing processor in `app/logging_config.py`
  - Extended PII patterns in `app/pii.py`: added `passport` (VN format) and `vn_address` patterns
  - Added `load_dotenv()` to `app/main.py` to enable Langfuse tracing
  - Ran `scripts/load_test.py` (20 total requests, 10 normal + 10 during rag_slow incident)
  - Injected and analyzed `rag_slow` incident, documented root cause above
  - `validate_logs.py` final score: 100/100
- [EVIDENCE_LINK]: https://github.com/Yangtai2504/2A202600823-NguyenThaiDuong-Day13

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: N/A
- [BONUS_AUDIT_LOGS]: N/A
- [BONUS_CUSTOM_METRIC]: Added two extra PII redaction patterns (`passport`, `vn_address`) beyond the template's 4 defaults, improving PII coverage for Vietnamese user data without impacting `validate_logs.py` score.
