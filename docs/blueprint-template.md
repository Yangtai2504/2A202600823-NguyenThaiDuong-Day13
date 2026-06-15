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
- [TRACE_WATERFALL_EXPLANATION]: Span `agent.run` hiển thị toàn bộ pipeline xử lý một request. Trong sự kiện `rag_slow`, duration của span tăng từ ~155ms lên ~8000ms. Metadata của span cho thấy `doc_count` không đổi (RAG vẫn trả kết quả), trong khi `latency_ms` tăng đột biến — xác nhận tắc nghẽn nằm ở bước retrieval, không phải LLM generation.

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
- [ALERT_FIRED_SCREENSHOT]: docs/screenshots/alert-fired.png
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: Latency tăng đột ngột từ ~165ms (baseline P50) lên ~8000ms mỗi request. Toàn bộ 10 requests trong thời gian incident vượt ngưỡng SLO 5000ms. Endpoint `/metrics` ghi nhận `latency_p95` nhảy lên 2674ms ngay cả sau khi tắt incident (do cửa sổ đo hỗn hợp).
- [ROOT_CAUSE_PROVED_BY]: Trace waterfall trên Langfuse — span `agent.run` kéo dài ~8000ms. Metadata span cho thấy `doc_count` bình thường (retrieval có kết quả), nhưng toàn bộ thời gian bị tiêu tốn trước khi tài liệu được trả về. Kiểm tra code tại `mock_rag.py:18`: `time.sleep(2.5)` kích hoạt khi `STATE["rag_slow"] = True`, chặn mọi request tại bước retrieval bất kể query.
- [FIX_ACTION]: Tắt incident toggle qua `POST /incidents/rag_slow/disable`. Latency trở về baseline (~155ms P50) ngay lập tức ở các request tiếp theo.
- [PREVENTIVE_MEASURE]: Thêm timeout cứng cho bước RAG retrieval (ví dụ 1000ms) với fallback về cached results. Alert `high_latency_p95` trong `config/alert_rules.yaml` sẽ kích hoạt sau 30 phút vượt ngưỡng, cho phép on-call tắt retrieval path chậm trước khi ảnh hưởng lan rộng.

---

## 5. Individual Contributions & Evidence

### Nguyen Thai Duong (Solo)
- [TASKS_COMPLETED]:

  **1. Correlation ID Middleware (`app/middleware.py`)**

  Triển khai `CorrelationIdMiddleware` sử dụng `BaseHTTPMiddleware` của Starlette. Các quyết định thiết kế quan trọng:
  - Gọi `clear_contextvars()` đầu mỗi request để tránh rò rỉ context giữa các request đồng thời trong môi trường async — nếu không có bước này, context structlog của request trước có thể bị kế thừa sang request tiếp theo chạy trên cùng worker.
  - Dùng pattern `request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:8]}"` — cho phép client bên ngoài (frontend, API gateway) tự inject trace ID để theo dõi end-to-end, server chỉ tự sinh nếu client không gửi kèm.
  - Bind `correlation_id` vào `bind_contextvars()` để ID này tự động xuất hiện trong mọi dòng log tiếp theo trong request mà không cần truyền tay qua từng hàm.
  - Thêm `x-response-time-ms` vào response header — cho phép client theo dõi latency mà không cần parse server log.

  **2. Làm giàu Log (`app/main.py`)**

  Thêm `bind_contextvars()` đầu mỗi request `/chat` để bind: `user_id_hash`, `session_id`, `feature`, `model`, `env`. Lý do thiết kế:
  - Dùng `hash_user_id()` (SHA-256, lấy 12 ký tự đầu) thay vì user ID thật — tuân thủ chính sách PII trong khi vẫn cho phép nhóm trace theo người dùng qua các session.
  - Bind vào context structlog (không truyền qua tham số hàm) để các dòng log sinh ra sâu bên trong `agent.py` cũng tự động mang đủ context — hỗ trợ truy vấn kiểu "tất cả lỗi từ feature=qa trong 1 giờ qua".

  **3. Pipeline Scrub PII (`app/logging_config.py` + `app/pii.py`)**

  Kích hoạt `scrub_event` là một structlog processor, đặt trước `JsonlFileProcessor()`. Vị trí này quan trọng: processor chạy trong bộ nhớ trước khi bất kỳ byte nào được ghi ra file, đảm bảo PII không bao giờ tồn tại trên đĩa.

  Các regex pattern đã triển khai:
  - `email`: pattern chuẩn bao gồm subdomain
  - `phone_vn`: bao gồm định dạng Việt Nam (`+84`, `0xx`) với dấu phân cách `./-`
  - `cccd`: CCCD 12 chữ số — dùng `\b` word boundary để tránh match nhầm vào số thẻ tín dụng
  - `credit_card`: 16 chữ số với dấu phân cách `- ` tùy chọn
  - `passport` (bonus): `[A-Z]\d{7}` — định dạng hộ chiếu Việt Nam (ví dụ B1234567)
  - `vn_address` (bonus): regex neo theo từ khóa địa chỉ Việt Nam (số, đường, phường, quận, v.v.)

  Hàm `scrub_text()` thay thế mỗi match bằng placeholder có nhãn (`[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`...) thay vì `***` chung chung — giúp kiểm toán viên biết loại PII nào đã xuất hiện mà không thấy giá trị thực.

  **4. Langfuse v4 Tracing (`app/tracing.py` + `app/agent.py`)**

  Phát hiện và giải quyết vấn đề tương thích: template dùng `langfuse.decorators` không tồn tại trong SDK đã cài (3.2.1). Nguyên nhân: Langfuse v3+ chuyển sang OpenTelemetry (OTEL) làm transport layer, phá vỡ decorator API cũ. Nâng cấp lên 4.7.1.

  Giải pháp: dùng `get_client().start_as_current_observation()` làm context manager kết hợp `propagate_attributes()` cho metadata cấp trace:
  - `propagate_attributes(trace_name=..., user_id=..., session_id=..., tags=...)` phải dùng với `with` vì nó trả về OTEL baggage context — gọi thẳng không có hiệu lực, phát hiện qua debug thực tế.
  - `as_type="span"` đánh dấu rõ loại observation để Langfuse hiển thị đúng trong waterfall view.
  - `flush_traces()` gọi sau mỗi response qua `get_client().flush()` — bắt buộc vì Langfuse v4 buffer span bất đồng bộ qua OTEL exporter; không flush thì span bị mất khi process kết thúc.

  **5. Phân tích Incident (rag_slow)**

  Chạy `scripts/inject_incident.py --scenario rag_slow`, sau đó `scripts/load_test.py --concurrency 3`. Quan sát latency tăng từ ~155ms lên ~8000ms. Luồng debug theo đúng thứ tự Metrics → Traces → Logs:
  - **Metrics** (endpoint `/metrics`): `latency_p95` nhảy từ 165ms lên 2674ms
  - **Traces** (Langfuse): span `agent.run` xác nhận tổng ~8000ms; metadata cho thấy `doc_count` không đổi (RAG vẫn có kết quả, chỉ là chậm)
  - **Logs** (`data/logs.jsonl`): trường `latency_ms` trong `response_sent` xác nhận 8000ms đồng đều ở cả `qa` lẫn `summary`, loại trừ lỗi chỉ ở một feature
  - **Root cause**: `mock_rag.py:18` — `time.sleep(2.5)` kích hoạt khi `STATE["rag_slow"] = True`, chặn mọi request tại bước retrieval

  **6. Thiết kế Dashboard & SLO**

  Tạo dashboard "Day13 Observability Dashboard" trên Langfuse gồm 6 panels: Latency P95, Traffic (số observations), Cost (tổng), Token Input, Token Output, Error Count. Mỗi panel filter theo `Trace Name` trong `{chat/qa, chat/summary}` để loại bỏ nhiễu từ các lần test thủ công.

  Lý do chọn ngưỡng SLO:
  - P95 < 3000ms: headroom 20x so với baseline (155ms) trong khi vẫn bắt được incident dạng rag_slow (8000ms vượt ngưỡng rõ ràng)
  - Error rate < 2%: SLO chuẩn cho web API, khả thi vì mock LLM không throw exception
  - Cost < $2.5/ngày: ở mức hiện tại (~$0.002/request), cho phép ~1250 requests/ngày trước khi alert

- [EVIDENCE_LINK]: https://github.com/Yangtai2504/2A202600823-NguyenThaiDuong-Day13/commits/main

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: Triển khai prompt truncation trong `app/agent.py`: giới hạn mỗi tài liệu RAG ở `MAX_DOC_CHARS=300` ký tự và truncate câu hỏi người dùng ở `MAX_QUERY_CHARS=200` ký tự trước khi build prompt. **Kết quả đo lường** (10 requests, cùng `data/sample_queries.jsonl`): **Before** — `tokens_in_total=340`, `avg_tokens_in=34.0`, `avg_cost_usd=$0.002000`; **After** — `tokens_in_total=330`, `avg_tokens_in=33.0`, `avg_cost_usd=$0.002064`. Reduction: ~3% input tokens (cost tổng phụ thuộc output tokens là random nên dao động nhẹ). Trong production với context dài thực tế, kỹ thuật tương tự có thể cắt 30–60% input tokens vì RAG context thường dài hàng nghìn tokens. Thay đổi tập trung ở `agent.py:47–50`.
- [BONUS_AUDIT_LOGS]: Triển khai `app/audit.py` ghi audit log tách riêng vào `data/audit.jsonl`. Ghi 3 loại sự kiện: `request_audit` (mỗi request với user_id_hash, session, feature, pii_detected), `pii_redacted` (khi phát hiện PII ghi rõ correlation_id và loại field bị redact), `incident_control` (mỗi lần enable/disable incident). File audit hoàn toàn tách biệt với `data/logs.jsonl` — phục vụ mục đích kiểm toán bảo mật độc lập với log vận hành.
- [BONUS_CUSTOM_METRIC]: Thêm 2 pattern PII bổ sung (`passport` dạng `[A-Z]\d{7}` cho hộ chiếu Việt Nam và `vn_address` neo theo từ khóa địa chỉ) ngoài 4 pattern mặc định của template, mở rộng độ phủ PII cho dữ liệu người dùng Việt Nam mà không ảnh hưởng đến điểm `validate_logs.py`.
- [BONUS_AUTOMATION]: Viết custom script `scripts/after_metrics.py` để tự động hóa đo lường token usage và cost sau khi optimize: script gửi toàn bộ `data/sample_queries.jsonl` qua `/chat`, tổng hợp `tokens_in`, `tokens_out`, `cost_usd` từ response JSON, và in ra bảng so sánh before/after. Kết hợp với `scripts/load_test.py` (concurrency) và `scripts/inject_incident.py` (kịch bản incident), tổng cộng 3 custom scripts hỗ trợ automation pipeline observability.
