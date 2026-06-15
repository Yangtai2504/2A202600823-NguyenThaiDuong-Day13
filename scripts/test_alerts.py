import httpx
import time

BASE = "http://127.0.0.1:8080"
BODY = {"user_id": "demo01", "session_id": "sess-alert", "feature": "qa", "message": "How do I request a refund?"}

with httpx.Client(timeout=30) as c:
    # Enable rag_slow để latency tăng
    r = c.post(BASE + "/incidents/rag_slow/enable")
    print("incident enabled:", r.json())

    # Gửi 2 request — latency ~8000ms mỗi cái, p95 sẽ vượt 5000ms
    for i in range(2):
        r = c.post(BASE + "/chat", json=BODY)
        d = r.json()
        print("request", i+1, "latency_ms:", d.get("latency_ms"), "cost:", d.get("cost_usd"))

    # Xem metrics — phải thấy alerts_firing
    r = c.get(BASE + "/metrics")
    print("metrics:", r.json())

    # Disable rag_slow
    r = c.post(BASE + "/incidents/rag_slow/disable")
    print("incident disabled:", r.json())

    # Gửi thêm request bình thường để xem alert resolved
    r = c.post(BASE + "/chat", json=BODY)
    print("normal request latency_ms:", r.json().get("latency_ms"))

    r = c.get(BASE + "/metrics")
    print("metrics after resolve:", r.json())
