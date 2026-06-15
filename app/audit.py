from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))


def _write(event: dict) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def audit_request(user_id_hash: str, session_id: str, feature: str, pii_detected: bool) -> None:
    _write({
        "event": "request_audit",
        "user_id_hash": user_id_hash,
        "session_id": session_id,
        "feature": feature,
        "pii_detected": pii_detected,
    })


def audit_incident(name: str, action: str, actor: str = "api") -> None:
    _write({
        "event": "incident_control",
        "incident": name,
        "action": action,
        "actor": actor,
    })


def audit_pii_redaction(correlation_id: str, fields_redacted: list[str]) -> None:
    _write({
        "event": "pii_redacted",
        "correlation_id": correlation_id,
        "fields_redacted": fields_redacted,
    })
