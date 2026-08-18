#!/usr/bin/env python3
"""Run configured quality gates without invoking a shell and emit reproducible evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key)(\s*[:=]\s*)(\S+)"),
]


def root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def redact(text: str) -> str:
    value = text
    value = SECRET_PATTERNS[0].sub("[REDACTED_GITHUB_TOKEN]", value)
    value = SECRET_PATTERNS[1].sub(r"\1\2[REDACTED]", value)
    return value


def git_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNCOMMITTED"


def execute_gate(root: Path, gate: dict, log_dir: Path, commit_sha: str) -> dict:
    gate_id = gate["id"]
    args = gate.get("args")
    started = dt.datetime.now(dt.timezone.utc)
    before = time.monotonic()
    status = "ERROR"
    exit_code = None
    output = ""
    try:
        if not isinstance(args, list) or not args or not all(isinstance(v, str) for v in args):
            raise ValueError("args must be a non-empty string array")
        if any("REPLACE_" in value for value in args):
            raise ValueError("gate contains placeholder arguments")
        result = subprocess.run(
            args,
            cwd=root,
            capture_output=True,
            text=True,
            shell=False,
            timeout=int(gate.get("timeout_seconds", 900)),
            check=False,
            env=os.environ.copy(),
        )
        exit_code = result.returncode
        output = redact(result.stdout + "\n" + result.stderr)
        status = "PASS" if result.returncode == 0 else "FAIL"
    except subprocess.TimeoutExpired as exc:
        output = redact(f"TIMEOUT\n{exc.stdout or ''}\n{exc.stderr or ''}")
        status = "FAIL"
    except (OSError, ValueError) as exc:
        output = redact(f"ERROR: {exc}")
        status = "ERROR"

    duration = round(time.monotonic() - before, 3)
    log_path = log_dir / f"{gate_id}.log"
    log_path.write_text(output, encoding="utf-8")
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
    return {
        "id": gate_id,
        "status": status,
        "required": bool(gate.get("required")),
        "exit_code": exit_code,
        "started_at": started.isoformat(),
        "duration_seconds": duration,
        "commit_sha": commit_sha,
        "command": args,
        "log": log_path.as_posix(),
        "log_sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(".github/sdlc/project.json"))
    parser.add_argument("--change-id", default=os.environ.get("CHANGE_ID", "local-validation"))
    args = parser.parse_args()

    root = root_path()
    config_path = args.config if args.config.is_absolute() else root / args.config
    project = json.loads(config_path.read_text(encoding="utf-8"))
    if project.get("adoption_complete") is not True:
        print("INCONCLUSIVE: project adoption is incomplete")
        return 2

    tier = project.get("default_risk_tier")
    risk_policy = json.loads(
        (root / ".github/sdlc/policies/risk-tiers.json").read_text(encoding="utf-8")
    )
    required_ids = set(risk_policy["tiers"][tier]["required_gates"])
    commands = {
        gate["id"]: gate
        for gate in project.get("commands", [])
        if isinstance(gate, dict) and gate.get("id")
    }
    unavailable = [
        gate_id
        for gate_id in sorted(required_ids)
        if gate_id not in commands
        or commands[gate_id].get("enabled") is not True
        or commands[gate_id].get("required") is not True
    ]
    if unavailable:
        print("INCONCLUSIVE: mandatory gates are missing or disabled: " + ", ".join(unavailable))
        return 2

    evidence_root = root / project.get("evidence_directory", ".github/sdlc/evidence")
    output_dir = evidence_root / args.change_id
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    commit_sha = git_sha(root)
    results = []
    for gate in project.get("commands", []):
        if gate.get("enabled") is True:
            result = execute_gate(root, gate, log_dir, commit_sha)
            results.append(result)
            print(f"{result['id']}: {result['status']}")

    decision = "PASS"
    if any(item["required"] and item["status"] != "PASS" for item in results):
        decision = "FAIL"
    evidence = {
        "schema_version": "1.0",
        "change_id": args.change_id,
        "commit_sha": commit_sha,
        "risk_tier": tier,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "decision": decision,
        "gates": results,
    }
    (output_dir / "quality-gates.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
