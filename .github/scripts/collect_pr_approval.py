#!/usr/bin/env python3
"""Collect exact-head GitHub PR reviews and required checks for Human Gate 2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import program_orchestrator


def gh_json(args: list[str], cwd: Path) -> object:
    text = program_orchestrator.run_command(["gh", *args], cwd)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise program_orchestrator.ProgramError(
            f"gh returned invalid JSON for {args!r}"
        ) from exc


def collect(
    engine: program_orchestrator.ProgramOrchestrator,
    change_id: str,
    gate_evidence_path: Path,
) -> dict:
    state = engine.read_state(change_id)
    if state["state"] != "AWAITING_PR_APPROVAL":
        raise program_orchestrator.ProgramError(
            "PR approval evidence may be collected only while awaiting PR approval"
        )
    gate = program_orchestrator.read_json(gate_evidence_path.resolve())
    engine._validate_human_evidence(
        state, gate, "pr-approval", state["pr_set_digest"]
    )
    approved_pull_requests = []
    for repository_id in state["implementation_scope"]:
        expected = state["pull_requests"][repository_id]
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        details = gh_json(
            [
                "pr",
                "view",
                expected["url"],
                "--json",
                "number,url,headRefOid,reviewDecision,latestReviews",
            ],
            worktree,
        )
        if not isinstance(details, dict):
            raise program_orchestrator.ProgramError(
                f"{repository_id}: PR details are not an object"
            )
        if (
            details.get("number") != expected["number"]
            or details.get("headRefOid") != expected["head_sha"]
            or details.get("reviewDecision") != "APPROVED"
        ):
            raise program_orchestrator.ProgramError(
                f"{repository_id}: exact PR head lacks an approving review decision"
            )
        checks = gh_json(
            [
                "pr",
                "checks",
                expected["url"],
                "--required",
                "--json",
                "name,state,bucket,link",
            ],
            worktree,
        )
        if not isinstance(checks, list) or not checks:
            raise program_orchestrator.ProgramError(
                f"{repository_id}: no required status checks were observed"
            )
        failed = [
            item.get("name", "unknown")
            for item in checks
            if not isinstance(item, dict)
            or str(item.get("bucket", "")).casefold() != "pass"
        ]
        if failed:
            raise program_orchestrator.ProgramError(
                f"{repository_id}: required checks are not PASS: {', '.join(failed)}"
            )
        reviewers = sorted(
            {
                review.get("author", {}).get("login")
                for review in details.get("latestReviews", [])
                if isinstance(review, dict)
                and review.get("state") == "APPROVED"
                and isinstance(review.get("author"), dict)
                and review["author"].get("login")
                and review["author"]["login"] != state["requested_by"]
            }
        )
        if not reviewers:
            raise program_orchestrator.ProgramError(
                f"{repository_id}: no independent approving reviewer was observed"
            )
        approved_pull_requests.append(
            {
                "repository_id": repository_id,
                "number": expected["number"],
                "head_sha": expected["head_sha"],
                "required_checks_passed": True,
                "approved_by": reviewers,
                "required_checks": checks,
            }
        )
    return {**gate, "approved_pull_requests": approved_pull_requests}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=program_orchestrator.repository_root())
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--gate-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    if manifest and not manifest.is_absolute():
        manifest = root / manifest
    try:
        engine = program_orchestrator.ProgramOrchestrator(root, manifest)
        evidence = collect(engine, args.change_id, args.gate_evidence)
        program_orchestrator.atomic_json(args.output.resolve(), evidence)
        if args.record:
            engine.approve_pr_set(args.change_id, args.output.resolve())
        print(json.dumps(evidence, indent=2))
        return 0
    except program_orchestrator.ProgramError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
