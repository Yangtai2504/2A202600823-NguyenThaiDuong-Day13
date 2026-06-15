import httpx
import json
import pathlib

BASE = "http://127.0.0.1:8080"
lines = [
    line for line in
    pathlib.Path("data/sample_queries.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]

total_cost = 0
total_in = 0
total_out = 0
n = 0

with httpx.Client(timeout=30) as c:
    for line in lines:
        r = c.post(BASE + "/chat", json=json.loads(line))
        d = r.json()
        total_cost += d.get("cost_usd", 0)
        total_in += d.get("tokens_in", 0)
        total_out += d.get("tokens_out", 0)
        n += 1
        print("status=" + str(r.status_code) + " tokens_in=" + str(d.get("tokens_in")) + " cost=" + str(d.get("cost_usd")))

print("--- AFTER optimization (" + str(n) + " requests) ---")
print("avg_cost_usd: " + str(round(total_cost / n, 6)))
print("tokens_in_total: " + str(total_in))
print("tokens_out_total: " + str(total_out))
print("avg_tokens_in: " + str(round(total_in / n, 1)))
