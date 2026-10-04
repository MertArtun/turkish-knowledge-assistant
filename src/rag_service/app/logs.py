"""JSON log lines. uvicorn installs this formatter through `--log-config log_config.json`.

Each record becomes one JSON object: time, level, logger and message, plus the structured fields
a call passes as `extra={"fields": {...}}` (request ID, mode, outcome, chunk and version IDs,
timings, error codes). Calls pass identifiers, codes, counts and timings only, never the
question, an answer or document text. JSON escaping also stops a value from forging a new line.
"""

import json
import logging
import traceback
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info and record.exc_info[0] is not None:
            # Type and stack only: an exception's message can quote request data (pydantic, for
            # one, repeats the invalid input), so it never reaches the log.
            error_type, _, trace = record.exc_info
            line["error_type"] = error_type.__name__
            line["stack"] = [
                f"{frame.filename}:{frame.lineno} {frame.name}"
                for frame in traceback.extract_tb(trace)
            ]
        return json.dumps(line, ensure_ascii=False, default=str)
