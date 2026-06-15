from __future__ import annotations

import time
from dataclasses import dataclass

from langfuse import get_client as get_langfuse, propagate_attributes

from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


MAX_DOC_CHARS = 300   # truncate each retrieved doc
MAX_QUERY_CHARS = 200  # truncate user message in prompt


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        lf = get_langfuse()
        with propagate_attributes(
            trace_name=f"chat/{feature}",
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
        ), lf.start_as_current_observation(
            name="agent.run",
            as_type="span",
            input={"message": summarize_text(message), "feature": feature},
        ):
            started = time.perf_counter()
            docs = retrieve(message)
            # Cost optimization: truncate to first doc + cap query length
            top_doc = docs[0][:MAX_DOC_CHARS] if docs else ""
            short_query = message[:MAX_QUERY_CHARS]
            prompt = f"Feature={feature}\nDocs={top_doc}\nQuestion={short_query}"
            response = self.llm.generate(prompt)
            quality_score = self._heuristic_quality(message, response.text, docs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

            lf.update_current_span(
                output={"answer": summarize_text(response.text)},
                metadata={
                    "doc_count": len(docs),
                    "latency_ms": latency_ms,
                    "tokens_in": response.usage.input_tokens,
                    "tokens_out": response.usage.output_tokens,
                    "cost_usd": cost_usd,
                    "quality_score": quality_score,
                },
            )

            metrics.record_request(
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                quality_score=quality_score,
            )

            return AgentResult(
                answer=response.text,
                latency_ms=latency_ms,
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                cost_usd=cost_usd,
                quality_score=quality_score,
            )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
