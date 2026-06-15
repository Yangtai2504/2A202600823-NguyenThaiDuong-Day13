from __future__ import annotations

from collections import Counter
from statistics import mean

REQUEST_LATENCIES: list[int] = []
REQUEST_COSTS: list[float] = []
REQUEST_TOKENS_IN: list[int] = []
REQUEST_TOKENS_OUT: list[int] = []
ERRORS: Counter[str] = Counter()
TRAFFIC: int = 0
QUALITY_SCORES: list[float] = []

# Alert thresholds (mirrors config/alert_rules.yaml)
ALERT_RULES = {
    "high_latency_p95": {"threshold": 2000, "severity": "P2", "runbook": "docs/alerts.md#1-high-latency-p95"},
    "high_error_rate":  {"threshold": 5.0,  "severity": "P1", "runbook": "docs/alerts.md#2-high-error-rate"},
    "cost_budget_spike":{"threshold": 2.5,  "severity": "P2", "runbook": "docs/alerts.md#3-cost-budget-spike"},
}

# Track which alerts are currently firing to avoid log spam
_firing: set[str] = set()


def record_request(latency_ms: int, cost_usd: float, tokens_in: int, tokens_out: int, quality_score: float) -> None:
    global TRAFFIC
    TRAFFIC += 1
    REQUEST_LATENCIES.append(latency_ms)
    REQUEST_COSTS.append(cost_usd)
    REQUEST_TOKENS_IN.append(tokens_in)
    REQUEST_TOKENS_OUT.append(tokens_out)
    QUALITY_SCORES.append(quality_score)


def record_error(error_type: str) -> None:
    ERRORS[error_type] += 1


def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def check_alerts(log) -> list[dict]:
    """Check all alert rules against current metrics. Log and return any that are firing."""
    fired = []
    s = snapshot()

    total = TRAFFIC
    error_total = sum(ERRORS.values())
    error_rate = (error_total / total * 100) if total > 0 else 0.0

    checks = {
        "high_latency_p95": s["latency_p95"],
        "high_error_rate":  error_rate,
        "cost_budget_spike": s["total_cost_usd"],
    }

    for rule_name, current_value in checks.items():
        rule = ALERT_RULES[rule_name]
        threshold = rule["threshold"]
        is_firing = current_value > threshold

        if is_firing and rule_name not in _firing:
            _firing.add(rule_name)
            log.warning(
                "alert_fired",
                service="alerting",
                alert=rule_name,
                severity=rule["severity"],
                value=round(current_value, 2),
                threshold=threshold,
                runbook=rule["runbook"],
            )
            fired.append({"alert": rule_name, "severity": rule["severity"], "value": round(current_value, 2)})

        elif not is_firing and rule_name in _firing:
            _firing.discard(rule_name)
            log.info(
                "alert_resolved",
                service="alerting",
                alert=rule_name,
                value=round(current_value, 2),
                threshold=threshold,
            )

    return fired


def snapshot() -> dict:
    total = TRAFFIC
    error_total = sum(ERRORS.values())
    return {
        "traffic": total,
        "latency_p50": percentile(REQUEST_LATENCIES, 50),
        "latency_p95": percentile(REQUEST_LATENCIES, 95),
        "latency_p99": percentile(REQUEST_LATENCIES, 99),
        "avg_cost_usd": round(mean(REQUEST_COSTS), 4) if REQUEST_COSTS else 0.0,
        "total_cost_usd": round(sum(REQUEST_COSTS), 4),
        "tokens_in_total": sum(REQUEST_TOKENS_IN),
        "tokens_out_total": sum(REQUEST_TOKENS_OUT),
        "error_rate_pct": round(error_total / total * 100, 2) if total > 0 else 0.0,
        "error_breakdown": dict(ERRORS),
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
        "alerts_firing": list(_firing),
    }
