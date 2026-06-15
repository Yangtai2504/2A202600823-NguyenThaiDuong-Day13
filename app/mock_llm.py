from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .incidents import STATE


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    ANSWERS = {
        "refund": "Refunds are available within 7 days with valid proof of purchase. Contact support@example.com to initiate.",
        "monitor": "Metrics detect incidents at the system level, traces localize them to a specific service or span, and logs explain the root cause with full context.",
        "policy": "PII must never appear in logs. Use hashed user IDs, redact emails and phone numbers, and store only sanitized summaries.",
        "latency": "To debug tail latency: check P95/P99 in your metrics dashboard, identify the slowest trace in Langfuse, then drill into the slowest span (RAG vs LLM).",
        "alert": "Alerts should be symptom-based (e.g. latency_p95 > 5000ms) rather than cause-based. Each alert needs a runbook link and a clear owner.",
        "dashboard": "A good observability dashboard shows: Latency P50/P95/P99, Traffic QPS, Error rate, Cost over time, Token usage, and Quality score — all with SLO threshold lines.",
        "log": "Logs should be structured JSON, include a correlation_id per request, contain no PII, and be enriched with session/feature/user context.",
        "summary": "Observability = Metrics (what is wrong) + Traces (where it is wrong) + Logs (why it is wrong). Together they enable fast incident detection and root cause analysis.",
    }

    def generate(self, prompt: str) -> FakeResponse:
        time.sleep(0.15)
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = random.randint(80, 180)
        if STATE["cost_spike"]:
            output_tokens *= 4
        prompt_lower = prompt.lower()
        answer = next(
            (text for key, text in self.ANSWERS.items() if key in prompt_lower),
            "Based on the retrieved context, here is a concise answer to your question about observability best practices.",
        )
        return FakeResponse(text=answer, usage=FakeUsage(input_tokens, output_tokens), model=self.model)
