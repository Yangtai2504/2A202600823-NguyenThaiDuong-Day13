# Day 13 — Demo Commands

> Tất cả lệnh chạy trong **Command Prompt** (cmd), từ thư mục `day13\`.

---

## 1. Khởi động server

```cmd
cd "c:\VinAI\Lab coding\day13"
.venv\Scripts\activate
.venv\Scripts\uvicorn.exe app.main:app --port 8080
```

Mở trình duyệt: **http://127.0.0.1:8080/docs** (Swagger UI để demo click)

---

## 2. Kiểm tra nhanh (mở terminal thứ 2)

```cmd
cd "c:\VinAI\Lab coding\day13"
.venv\Scripts\activate
```

**Health check:**
```cmd
curl http://127.0.0.1:8080/health
```

**Xem metrics:**
```cmd
curl http://127.0.0.1:8080/metrics
```

---

## 3. Gửi request thường (show correlation ID + log enrichment)

```cmd
curl -X POST http://127.0.0.1:8080/chat -H "Content-Type: application/json" -d "{\"user_id\":\"demo01\",\"session_id\":\"sess-abc\",\"feature\":\"qa\",\"message\":\"How do I request a refund?\"}"
```

---

## 4. Gửi request có PII (show PII scrubbing)

```cmd
curl -X POST http://127.0.0.1:8080/chat -H "Content-Type: application/json" -d "{\"user_id\":\"demo01\",\"session_id\":\"sess-abc\",\"feature\":\"qa\",\"message\":\"My email is test@example.com and phone 0901234567, how to refund?\"}"
```

Kiểm tra log — PII đã bị redact:
```cmd
type data\logs.jsonl
```

---

## 5. Demo incident rag_slow (show latency spike)

**Enable incident:**
```cmd
curl -X POST http://127.0.0.1:8080/incidents/rag_slow/enable
```

**Gửi request — latency sẽ ~8000ms:**
```cmd
curl -X POST http://127.0.0.1:8080/chat -H "Content-Type: application/json" -d "{\"user_id\":\"demo01\",\"session_id\":\"sess-abc\",\"feature\":\"qa\",\"message\":\"What monitoring tools should I use?\"}"
```

**Disable incident (khôi phục):**
```cmd
curl -X POST http://127.0.0.1:8080/incidents/rag_slow/disable
```

---

## 6. Load test (tạo traces trên Langfuse)

```cmd
.venv\Scripts\python.exe scripts\load_test.py --concurrency 3
```

---

## 7. Validate logs (show 100/100)

```cmd
.venv\Scripts\python.exe scripts\validate_logs.py
```

---

## 8. Xem audit log (bonus)

```cmd
type data\audit.jsonl
```

---

## 9. Dừng server

Nhấn `Ctrl+C` trong terminal đang chạy uvicorn.
