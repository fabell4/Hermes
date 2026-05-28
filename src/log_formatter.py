"""src/log_formatter.py — JSON structured log formatter."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Formats each log record as a single-line JSON object.

    Output fields:

    - ``time``     — ISO-8601 UTC timestamp with millisecond precision (e.g. ``2026-05-18T14:23:45.123Z``)
    - ``level``    — Log level name (``INFO``, ``WARNING``, ``ERROR``, …)
    - ``logger``   — Logger name (dotted module path)
    - ``message``  — Formatted log message
    - ``exc_info`` — Exception traceback string; only present when the record carries exception info

    When ``LOG_FORMAT=json`` is set, Grafana Alloy's ``loki.process`` pipeline can parse these
    fields and promote ``level`` as a Loki stream label for efficient filtering.
    """

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        payload: dict[str, object] = {
            "time": ts.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
