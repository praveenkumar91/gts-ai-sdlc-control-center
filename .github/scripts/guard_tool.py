#!/usr/bin/env python3
"""Copilot preToolUse hook that denies protected edits and dangerous commands."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


def root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_args(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def collect_values(value: Any, wanted_keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in wanted_keys and isinstance(child, str):
                found.append(child)
            found.extend(collect_values(child, wanted_keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_values(child, wanted_keys))
    return found


def deny(reason: str) -> dict:
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}


def evaluate_tool(payload: dict, policy: dict) -> dict:
    tool_name = str(payload.get("toolName") or payload.get("tool_name") or "").lower()
    args = normalize_args(payload.get("toolArgs", payload.get("tool_input", {})))
    serialized = json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args

    if tool_name in {"bash", "powershell", "execute", "shell"}:
        commands = collect_values(args, {"command", "cmd", "script"})
        if not commands:
            commands = [serialized]
        for command in commands:
            for pattern in policy.get("deny_command_patterns", []):
                if re.search(pattern, command):
                    return deny("Command denied by production safety policy.")

    if tool_name in {"edit", "create", "write", "apply_patch", "multiedit"}:
        paths = collect_values(
            args,
            {"path", "file", "filepath", "file_path", "filename", "target"},
        )
        paths.extend(re.findall(r"\*{3} (?:Add|Update|Delete) File:\s*(.+)", serialized))
        normalized_paths = [value.replace("\\", "/").lower() for value in paths]
        for protected in policy.get("deny_agent_edits", []):
            expected = protected.replace("\\", "/").lower().rstrip("/")
            if any(path == expected or path.startswith(expected + "/") for path in normalized_paths):
                return deny(f"Agent edit denied for protected path: {protected}")
        content_values = collect_values(
            args,
            {"content", "new_string", "newstring", "patch", "text"},
        )
        for content in content_values:
            for pattern in policy.get("deny_content_patterns", []):
                if re.search(pattern, content):
                    return deny("Potential secret or private key denied by content policy.")

    return {"permissionDecision": "allow"}


def main() -> int:
    payload = json.load(sys.stdin)
    policy = json.loads(
        (root_path() / ".github/sdlc/policies/protected-paths.json").read_text(encoding="utf-8")
    )
    print(json.dumps(evaluate_tool(payload, policy)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
