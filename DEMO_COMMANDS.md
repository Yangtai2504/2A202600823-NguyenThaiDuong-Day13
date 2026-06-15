# Day 13 — Demo Commands

---

## Bước 0 — Khởi động server

Mở **terminal 1**, chạy:

```cmd
cd "c:\VinAI\Lab coding\day13"
.venv\Scripts\activate
.venv\Scripts\uvicorn.exe app.main:app --port 8080
```

Chờ thấy dòng `Application startup complete.` thì server đã sẵn sàng.

---

## Bước 1 — Mở Swagger UI

Mở trình duyệt, vào: **http://127.0.0.1:8080/docs**

Sẽ thấy danh sách 5 endpoint:
- `GET /health`
- `GET /metrics`
- `POST /chat`
- `POST /incidents/{name}/enable`
- `POST /incidents/{name}/disable`

---

## Bước 2 — Health check

1. Click vào **`GET /health`**
2. Click **"Try it out"** (góc phải)
3. Click **"Execute"**
4. Kéo xuống xem **Response body** — phải thấy `"tracing_enabled": true`

---

## Bước 3 — Gửi request thường (show correlation ID)

1. Click vào **`POST /chat`**
2. Click **"Try it out"**
3. Xóa nội dung trong ô **Request body**, dán vào:

```json
{
  "user_id": "demo01",
  "session_id": "sess-abc",
  "feature": "qa",
  "message": "How do I request a refund?"
}
```

4. Click **"Execute"**
5. Xem **Response body** — chú ý trường `correlation_id` và `latency_ms`
6. Kéo lên xem **Response headers** — có `x-request-id` và `x-response-time-ms`

---

## Bước 4 — Gửi request có PII (show PII scrubbing)

1. Vẫn ở **`POST /chat`**, đổi body thành:

```json
{
  "user_id": "demo01",
  "session_id": "sess-pii",
  "feature": "qa",
  "message": "My email is test@example.com and phone 0901234567, how to refund?"
}
```

2. Click **"Execute"**
3. Sang **terminal 2**, xem log:

```cmd
cd "c:\VinAI\Lab coding\day13"
type data\logs.jsonl
```

Tìm dòng có `"event": "request_received"` — trường `message_preview` sẽ thấy `[REDACTED_EMAIL]` và `[REDACTED_PHONE_VN]`, không có email/SĐT thật.

---

## Bước 5 — Demo incident rag_slow + Alert tự động

**Enable incident:**

1. Click **`POST /incidents/{name}/enable`**
2. Click **"Try it out"**
3. Ô **name**: gõ `rag_slow`
4. Click **"Execute"** — response trả về `"rag_slow": true`

**Gửi 2 request để trigger alert (latency_p95 > 2000ms):**

1. Quay lại **`POST /chat`**, dùng body:

```json
{
  "user_id": "demo01",
  "session_id": "sess-incident",
  "feature": "qa",
  "message": "What monitoring tools should I use?"
}
```

2. Click **"Execute"** 2 lần — mỗi lần loading ~3 giây, `latency_ms` ~2600ms

**Xem alert đang fire — Bước 6 ngay bên dưới:**

1. Click **`GET /metrics`** → **"Try it out"** → **"Execute"**
2. Trong response thấy: `"alerts_firing": ["high_latency_p95"]`
3. Sang **terminal 2** xem log alert:

```cmd
cd "c:\VinAI\Lab coding\day13"
type data\logs.jsonl
```

Tìm dòng `"event": "alert_fired"` — thấy `severity: P2`, `value`, `threshold: 2000`, `runbook link`

**Disable incident (khôi phục):**

1. Click **`POST /incidents/{name}/disable`**
2. **name**: `rag_slow`
3. Click **"Execute"** — response trả về `"rag_slow": false`
4. Gửi lại `/chat` vài lần — `latency_ms` về ~150ms
5. Gọi lại `GET /metrics` — khi p95 xuống dưới 2000ms thì `alerts_firing` trở về `[]`

---

## Bước 6 — Xem metrics

1. Click **`GET /metrics`**
2. Click **"Try it out"** → **"Execute"**
3. Chú ý các trường: `latency_p95`, `total_cost_usd`, `error_rate_pct`, `quality_avg`, **`alerts_firing`**

---

## Bước 7 — Load test + traces (terminal 2)

```cmd
cd "c:\VinAI\Lab coding\day13"
.venv\Scripts\python.exe scripts\load_test.py --concurrency 3
```

Sau đó mở **https://cloud.langfuse.com** — vào **Traces** để thấy traces mới với `trace_name = chat/qa` hoặc `chat/summary`.

---

## Bước 8 — Validate logs (terminal 2)

```cmd
.venv\Scripts\python.exe scripts\validate_logs.py
```

Kết quả phải hiện: `Estimated Score: 100/100`

---

## Bước 9 — Xem audit log (bonus)

```cmd
type data\audit.jsonl
```

Thấy các sự kiện `request_audit`, `pii_redacted`, `incident_control` được ghi riêng.

---

## Bước 10 — Dừng server

Nhấn `Ctrl+C` trong terminal 1.
