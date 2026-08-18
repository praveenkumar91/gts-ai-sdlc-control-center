#!/usr/bin/env python3
"""Emit human-gate evidence from GitHub's workflow-run review history."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


CHANGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def independent_approver(
    history: list[dict], environment: str, requested_by: str
) -> str | None:
    for review in reversed(history):
        environments = review.get("environments", [])
        names = {
            item.get("name")
            for item in environments
            if isinstance(item, dict)
        }
        user = review.get("user") if isinstance(review.get("user"), dict) else {}
        login = user.get("login")
        if (
            str(review.get("state", "")).casefold() == "approved"
            and environment in names
            and isinstance(login, str)
            and login
            and login.casefold() != requested_by.casefold()
        ):
            return login
    return None


def review_history(api_url: str, repository: str, run_id: str, token: str) -> list[dict]:
    url = f"{api_url.rstrip('/')}/repos/{repository}/actions/runs/{run_id}/approvals"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": os.environ.get(
                "GITHUB_API_VERSION", "2022-11-28"
            ),
            "User-Agent": "gts-ai-sdlc-control-center",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot retrieve workflow approval history: {exc}") from exc
    if not isinstance(value, list):
        raise RuntimeError("workflow approval history response is not an array")
    return [item for item in value if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--change-id", required=True)
    parser.add_argument(
        "--gate", choices=("plan-approval", "pr-approval"), required=True
    )
    parser.add_argument("--reviewed-digest", required=True)
    parser.add_argument("--reviewed-artifact-url", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not CHANGE_ID_RE.fullmatch(args.change_id):
        print("invalid change ID", file=sys.stderr)
        return 2
    if not DIGEST_RE.fullmatch(args.reviewed_digest):
        print("reviewed digest must be a lowercase SHA-256 value", file=sys.stderr)
        return 2
    if not args.reviewed_artifact_url.startswith("https://"):
        print("reviewed artifact URL must use HTTPS", file=sys.stderr)
        return 2

    required_environment = {
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN"),
        "GITHUB_API_URL": os.environ.get("GITHUB_API_URL"),
        "GITHUB_SERVER_URL": os.environ.get("GITHUB_SERVER_URL"),
        "GITHUB_REPOSITORY": os.environ.get("GITHUB_REPOSITORY"),
        "GITHUB_RUN_ID": os.environ.get("GITHUB_RUN_ID"),
        "GITHUB_ACTOR": os.environ.get("GITHUB_ACTOR"),
    }
    missing = [key for key, value in required_environment.items() if not value]
    if missing:
        print("missing GitHub environment: " + ", ".join(missing), file=sys.stderr)
        return 2

    approver = None
    last_error = None
    for _ in range(5):
        try:
            history = review_history(
                required_environment["GITHUB_API_URL"],
                required_environment["GITHUB_REPOSITORY"],
                required_environment["GITHUB_RUN_ID"],
                required_environment["GITHUB_TOKEN"],
            )
            approver = independent_approver(
                history, args.environment, required_environment["GITHUB_ACTOR"]
            )
            if approver:
                break
        except RuntimeError as exc:
            last_error = exc
        time.sleep(2)
    if not approver:
        detail = f": {last_error}" if last_error else ""
        print(
            "no independent approved environment review was observed" + detail,
            file=sys.stderr,
        )
        return 2

    evidence = {
        "schema_version": "1.0",
        "change_id": args.change_id,
        "gate": args.gate,
        "decision": "APPROVED",
        "approver": approver,
        "independent": True,
        "reviewed_digest": args.reviewed_digest,
        "reviewed_artifact_url": args.reviewed_artifact_url,
        "source_url": (
            f"{required_environment['GITHUB_SERVER_URL']}/"
            f"{required_environment['GITHUB_REPOSITORY']}/actions/runs/"
            f"{required_environment['GITHUB_RUN_ID']}"
        ),
        "requested_by": required_environment["GITHUB_ACTOR"],
        "environment": args.environment,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
