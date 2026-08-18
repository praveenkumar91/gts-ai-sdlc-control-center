#!/usr/bin/env python3
"""Emit commit-bound evidence that a protected production job was released."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path


CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()

    if not CHANGE_ID.fullmatch(args.change_id):
        print("FAIL: invalid change ID")
        return 2
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    actual = result.stdout.strip().lower()
    expected = args.expected_commit.lower()
    if not COMMIT_SHA.fullmatch(expected) or actual != expected:
        print("FAIL: approval evidence commit does not match checked-out commit")
        return 2
    server = os.environ.get("GITHUB_SERVER_URL")
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    if not all((server, repository, run_id, attempt)):
        print("FAIL: approval evidence must run in GitHub Actions")
        return 2
    evidence = {
        "schema_version": "1.0",
        "change_id": args.change_id,
        "approved_commit": actual,
        "environment": "production",
        "released_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "requested_by": os.environ.get("GITHUB_ACTOR"),
        "workflow_run_id": run_id,
        "workflow_run_attempt": attempt,
        "workflow_run_url": f"{server}/{repository}/actions/runs/{run_id}/attempts/{attempt}",
        "note": (
            "This proves the protected job was released. Retrieve the actual "
            "environment reviewer identity from GitHub before creating the "
            "human-approval-attestation envelope."
        ),
    }
    output = (
        root
        / ".github"
        / "sdlc"
        / "evidence"
        / args.change_id
        / "operations"
        / "production-approval-evidence.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
