#!/usr/bin/env python3
"""Execute one explicitly configured SDLC operation without a shell."""

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


ALLOWED = {
    "preproduction-validation",
    "business-invariant-tests",
    "deploy-canary",
    "canary-health",
    "production-reconciliation",
    "rollback",
}
CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SECRET = re.compile(r"(?i)(token|secret|password|api[_-]?key)(\s*[:=]\s*)(\S+)")
GITHUB_TOKEN = re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")


def root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def git_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
        timeout=20,
    )
    return result.stdout.strip().lower()


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", required=True, choices=sorted(ALLOWED))
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--config", type=Path, default=Path(".github/sdlc/project.json"))
    args = parser.parse_args()

    root = root_path()
    if not CHANGE_ID.fullmatch(args.change_id):
        print("FAIL: invalid change ID")
        return 2
    expected = args.expected_commit.lower()
    actual = git_sha(root)
    if not COMMIT_SHA.fullmatch(expected) or actual != expected:
        print(f"FAIL: checked-out commit {actual!r} does not match expected commit {expected!r}")
        return 2

    config_path = args.config if args.config.is_absolute() else root / args.config
    project = json.loads(config_path.read_text(encoding="utf-8"))
    operations = project.get("operations", {})
    if project.get("adoption_complete") is not True or operations.get("enabled") is not True:
        print("INCONCLUSIVE: project operations adoption is incomplete")
        return 2
    configured = {
        item.get("id"): item
        for item in operations.get("commands", [])
        if isinstance(item, dict) and item.get("id")
    }
    command = configured.get(args.operation)
    if not command or command.get("enabled") is not True:
        print(f"INCONCLUSIVE: operation is missing or disabled: {args.operation}")
        return 2
    command_args = command.get("args")
    if (
        not isinstance(command_args, list)
        or not command_args
        or not all(isinstance(value, str) and value for value in command_args)
        or any("REPLACE_" in value for value in command_args)
    ):
        print(f"INCONCLUSIVE: invalid command configuration: {args.operation}")
        return 2

    started = dt.datetime.now(dt.timezone.utc)
    before = time.monotonic()
    try:
        result = subprocess.run(
            command_args,
            cwd=root,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
            timeout=int(command.get("timeout_seconds", 1800)),
            env=os.environ.copy(),
        )
        output = GITHUB_TOKEN.sub(
            "[REDACTED_GITHUB_TOKEN]",
            SECRET.sub(r"\1\2[REDACTED]", result.stdout + "\n" + result.stderr),
        )
        status = "PASS" if result.returncode == 0 else "FAIL"
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        output = GITHUB_TOKEN.sub(
            "[REDACTED_GITHUB_TOKEN]",
            SECRET.sub(
                r"\1\2[REDACTED]",
                f"TIMEOUT\n{exc.stdout or ''}\n{exc.stderr or ''}",
            ),
        )
        status = "FAIL"
        exit_code = None
    except OSError as exc:
        output = f"ERROR: {exc}"
        status = "FAIL"
        exit_code = None

    output_dir = root / ".github" / "sdlc" / "evidence" / args.change_id / "operations"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{args.operation}.log"
    log_path.write_text(output, encoding="utf-8")
    evidence = {
        "schema_version": "1.0",
        "change_id": args.change_id,
        "operation": args.operation,
        "commit_sha": actual,
        "status": status,
        "exit_code": exit_code,
        "started_at": started.isoformat(),
        "duration_seconds": round(time.monotonic() - before, 3),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_actor": os.environ.get("GITHUB_ACTOR"),
        "log_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
    }
    atomic_write(output_dir / f"{args.operation}.json", evidence)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
