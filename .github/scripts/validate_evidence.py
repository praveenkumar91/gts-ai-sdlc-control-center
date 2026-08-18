#!/usr/bin/env python3
"""Fail-closed validation of an SDLC evidence manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def current_commit(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def evaluate_manifest(manifest: dict, risk_policy: dict, expected_commit: str | None) -> list[str]:
    errors: list[str] = []
    for key in (
        "change_id",
        "commit_sha",
        "risk_tier",
        "requirements",
        "gates",
        "independent_reviews",
        "decision",
    ):
        if key not in manifest:
            errors.append(f"missing field: {key}")

    commit_sha = manifest.get("commit_sha")
    if not isinstance(commit_sha, str) or len(commit_sha) != 40:
        errors.append("commit_sha must be a full 40-character commit")
    elif expected_commit and commit_sha != expected_commit:
        errors.append(f"manifest commit {commit_sha} does not match expected commit {expected_commit}")

    requirements = manifest.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements must be a non-empty array")
    else:
        required_links = ("source_refs", "design_refs", "code_refs", "test_refs", "result_refs")
        seen: set[str] = set()
        for index, requirement in enumerate(requirements):
            if not isinstance(requirement, dict):
                errors.append(f"requirement {index} must be an object")
                continue
            requirement_id = requirement.get("id")
            if not requirement_id or requirement_id in seen:
                errors.append(f"requirement {index} has missing or duplicate id")
            seen.add(requirement_id)
            for link in required_links:
                if not isinstance(requirement.get(link), list) or not requirement.get(link):
                    errors.append(f"requirement {requirement_id!r} has no {link}")
            if requirement.get("status") != "PASS":
                errors.append(f"requirement {requirement_id!r} is not PASS")

    tier = manifest.get("risk_tier")
    tier_policy = risk_policy.get("tiers", {}).get(tier)
    if not tier_policy:
        errors.append(f"unknown risk tier: {tier!r}")
        required_gate_ids: set[str] = set()
        reviewer_count = 0
    else:
        required_gate_ids = set(tier_policy.get("required_gates", []))
        reviewer_count = int(tier_policy.get("independent_reviewers", 0))

    gates = {
        item.get("id"): item
        for item in manifest.get("gates", [])
        if isinstance(item, dict) and item.get("id")
    }
    for gate_id in sorted(required_gate_ids):
        gate = gates.get(gate_id)
        if not gate:
            errors.append(f"missing required gate: {gate_id}")
        elif gate.get("status") != "PASS":
            errors.append(f"required gate {gate_id!r} is {gate.get('status')!r}")
        elif gate.get("commit_sha") != commit_sha:
            errors.append(f"required gate {gate_id!r} is stale or for another commit")

    reviews = manifest.get("independent_reviews", [])
    passing_reviewers = {
        item.get("reviewer")
        for item in reviews
        if isinstance(item, dict)
        and item.get("status") == "PASS"
        and item.get("independent") is True
        and item.get("commit_sha") == commit_sha
        and item.get("reviewer")
    }
    if len(passing_reviewers) < reviewer_count:
        errors.append(
            f"risk tier {tier!r} requires {reviewer_count} independent passing reviewers; "
            f"found {len(passing_reviewers)}"
        )

    findings = manifest.get("open_findings", [])
    for finding in findings:
        if isinstance(finding, dict) and finding.get("severity") in {"critical", "high"}:
            errors.append(f"open {finding.get('severity')} finding: {finding.get('id', 'unknown')}")

    if manifest.get("decision") != "PASS":
        errors.append(f"manifest decision is {manifest.get('decision')!r}, not PASS")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--expected-commit")
    args = parser.parse_args()

    root = root_path()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    risk_policy = json.loads(
        (root / ".github/sdlc/policies/risk-tiers.json").read_text(encoding="utf-8")
    )
    expected = args.expected_commit or current_commit(root)
    errors = evaluate_manifest(manifest, risk_policy, expected)
    if errors:
        print("EVIDENCE_INCONCLUSIVE")
        for error in errors:
            print(f"- {error}")
        return 1
    print("EVIDENCE_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
