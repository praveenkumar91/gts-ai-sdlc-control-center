#!/usr/bin/env python3
"""Write non-sensitive Copilot lifecycle metadata to a local, uncommitted audit log."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path


def root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    payload = json.load(sys.stdin)
    session = str(payload.get("sessionId") or payload.get("session_id") or "")
    event = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "event": payload.get("hook_event_name") or payload.get("eventName") or "unknown",
        "session_hash": hashlib.sha256(session.encode("utf-8")).hexdigest()[:16] if session else None,
        "tool": payload.get("toolName") or payload.get("tool_name"),
    }
    log_path = root_path() / ".git" / "copilot-audit.jsonl"
    if log_path.parent.is_dir():
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
