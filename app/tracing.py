from __future__ import annotations

import os
from typing import Any

try:
    from langfuse import Langfuse, get_client, observe, propagate_attributes
    _has_langfuse = True
except Exception:  # pragma: no cover
    _has_langfuse = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func
        return decorator

    def propagate_attributes(**kwargs: Any) -> None:
        return None


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def flush_traces() -> None:
    if _has_langfuse:
        get_client().flush()
