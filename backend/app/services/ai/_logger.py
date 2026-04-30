"""AI call logger — every provider call is recorded to ``ai_call_log``.

This buys us:

* **Auditability** — when real providers come online we can replay decisions.
* **Cost tracking** — latency + provider name on every call.
* **Drift detection** — once production traffic flows, sample input shapes
  to compare against training data.

Logging is best-effort: if the DB write fails we log a warning and move on,
never blocking the actual provider response.

Importantly, the DB module is imported **lazily inside the wrapper** rather
than at decoration time, so test environments without Motor / Mongo can
still load mock providers without dragging the network stack in.
"""
from __future__ import annotations
import logging
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("mypay.ai.calls")


def _safe_serialize(value: Any) -> Any:
    """Convert a value to something Mongo will accept; truncate long strings."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:200]
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            return str(value)[:200]
    return str(value)[:200]


def _resolve_db(db_provider: Optional[Callable[[], Any]]):
    """Return a Motor DB or None if Mongo is unavailable in this environment."""
    if db_provider is not None:
        try:
            return db_provider()
        except Exception:
            return None
    try:
        from app.db import get_db  # local import: keeps Motor out of the import graph until needed
        return get_db()
    except Exception:
        return None


def log_ai_call(
    *,
    service: str,
    db_provider: Optional[Callable[[], Any]] = None,
):
    """Decorator factory wrapping an async provider method.

    Pass ``db_provider`` to inject a fake DB in tests; otherwise the global
    Motor client is resolved lazily at call time.
    """
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapped(self, *args, **kwargs):
            t0 = time.perf_counter()
            err: Optional[str] = None
            result: Any = None
            try:
                result = await func(self, *args, **kwargs)
                return result
            except Exception as e:
                err = str(e)[:300]
                raise
            finally:
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                db = _resolve_db(db_provider)
                if db is None:
                    # Mongo not available (tests / cold boot) — skip logging silently.
                    return
                try:
                    await db.ai_call_log.insert_one({
                        "id": str(uuid.uuid4()),
                        "service": service,
                        "provider": getattr(self, "name", self.__class__.__name__),
                        "input": {k: _safe_serialize(v) for k, v in kwargs.items()},
                        "output": _safe_serialize(result),
                        "latency_ms": latency_ms,
                        "error": err,
                        "called_at": datetime.now(timezone.utc),
                    })
                except Exception as log_err:        # noqa: BLE001
                    logger.warning("ai_call_log insert failed: %s", log_err)
        return wrapped
    return decorator
