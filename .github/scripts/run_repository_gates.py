#!/usr/bin/env python3
"""Run one program repository's configured gates and optionally record the result."""

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

import program_orchestrator


SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key)(\s*[:=]\s*)(\S+)"),
]


def redact(text: str) -> str:
    value = SECRET_PATTERNS[0].sub("[REDACTED_GITHUB_TOKEN]", text)
    return SECRET_PATTERNS[1].sub(r"\1\2[REDACTED]", value)


def execute(worktree: Path, command: dict, log_dir: Path, commit_sha: str) -> dict:
    command_id = command["id"]
    if (
        not isinstance(command_id, str)
        or not program_orchestrator.GATE_ID_RE.fullmatch(command_id)
    ):
        raise program_orchestrator.ProgramError(
            "gate command id must be safe for an evidence filename"
        )
    args = command.get("args")
    started = dt.datetime.now(dt.timezone.utc)
    before = time.monotonic()
    status = "ERROR"
    exit_code = None
    output = ""
    try:
        if (
            not isinstance(args, list)
            or not args
            or not all(isinstance(item, str) and item for item in args)
        ):
            raise ValueError("args must be a non-empty string array")
        if any("REPLACE_" in item for item in args):
            raise ValueError("command contains placeholder arguments")
        result = subprocess.run(
            args,
            cwd=worktree,
            capture_output=True,
            text=True,
            shell=False,
            timeout=int(command.get("timeout_seconds", 900)),
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
    duration = round(time.monotonic() - before, 3)
    log_path = log_dir / f"{command_id}.log"
    log_path.write_text(output, encoding="utf-8")
    return {
        "id": command_id,
        "status": status,
        "required": bool(command.get("required")),
        "exit_code": exit_code,
        "started_at": started.isoformat(),
        "duration_seconds": duration,
        "commit_sha": commit_sha,
        "command": args,
        "log": str(log_path),
        "log_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
    }


def generate(
    engine: program_orchestrator.ProgramOrchestrator,
    change_id: str,
    repository_id: str,
) -> tuple[dict, Path]:
    state = engine.read_state(change_id)
    if state["state"] not in {"WORKSPACES_READY", "EXECUTING"}:
        raise program_orchestrator.ProgramError(
            "repository gates are not permitted in the current program state"
        )
    if repository_id not in state["validation_scope"]:
        raise program_orchestrator.ProgramError(
            f"{repository_id}: repository is not in validation scope"
        )
    extension_packet = engine.refresh_repository_extensions(
        change_id, repository_id
    )
    state = engine.read_state(change_id)
    repository = engine.repositories[repository_id]
    worktree = Path(state["commit_vector"][repository_id]["worktree"])
    commit_sha = program_orchestrator.run_command(["git", "rev-parse", "HEAD"], worktree)
    quality = extension_packet["quality_config"]
    quality_path = None
    if quality.get("configured") is True:
        quality_base = (
            worktree if quality.get("base") == "repository" else engine.root
        )
        quality_path = quality_base / quality["path"]
    adapter_path = (
        engine.root / ".github/sdlc/stack-adapters" / f"{repository['stack']}.json"
    )
    output_dir = (
        engine.run_dir(change_id) / "generated-evidence" / repository_id
    )
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "quality-gates.json"

    missing_reason = None
    if quality_path is None:
        missing_reason = (
            "no repository quality config or central stack default is configured"
        )
    elif not quality_path.is_file():
        missing_reason = f"missing configured quality config: {quality_path}"
    elif not adapter_path.is_file():
        missing_reason = f"missing stack adapter: {adapter_path}"
    if missing_reason:
        evidence = {
            "schema_version": "1.0",
            "change_id": change_id,
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "repository_extension_digest": extension_packet["digest"],
            "selected_extensions": {
                kind: [item["id"] for item in extension_packet[kind]]
                for kind in program_orchestrator.EXTENSION_KINDS
            },
            "decision": "INCONCLUSIVE",
            "reason": missing_reason,
            "gates": [],
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        program_orchestrator.atomic_json(evidence_path, evidence)
        return evidence, evidence_path

    quality = program_orchestrator.read_json(quality_path)
    adapter = program_orchestrator.read_json(adapter_path)
    configured = {
        item.get("id"): item
        for item in quality.get("commands", [])
        if isinstance(item, dict) and item.get("id")
    }
    repository_verification = {
        obligation["id"]: [
            entry
            for entry in obligation.get("verification", [])
            if entry.get("scope") == "repository"
            and entry.get("repository") == repository_id
        ]
        for obligation in state.get("requirement_obligations", [])
        if repository_id in obligation["repositories"]
    }
    planned_gate_ids = {
        gate_id
        for entries in repository_verification.values()
        for entry in entries
        for gate_id in entry["gate_ids"]
    }
    required = set(adapter.get("required_capabilities", []))
    unavailable = {
        command_id
        for command_id in required
        if command_id not in configured
        or configured[command_id].get("enabled") is not True
        or configured[command_id].get("required") is not True
    }
    unavailable.update(
        f"verification:{command_id}"
        for command_id in planned_gate_ids
        if command_id not in configured
        or configured[command_id].get("enabled") is not True
        or configured[command_id].get("required") is not True
    )
    if quality.get("adoption_complete") is not True:
        unavailable.add("repository-adoption")
    unavailable = sorted(unavailable)
    results = []
    if not unavailable:
        for command in quality.get("commands", []):
            if command.get("enabled") is True:
                results.append(execute(worktree, command, log_dir, commit_sha))
    decision = "INCONCLUSIVE" if unavailable else "PASS"
    if any(item["required"] and item["status"] != "PASS" for item in results):
        decision = "FAIL"
    changed_files = [
        item
        for item in program_orchestrator.run_command(
            [
                "git",
                "diff",
                "--name-only",
                state["commit_vector"][repository_id]["base_sha"],
                commit_sha,
            ],
            worktree,
        ).splitlines()
        if item
    ]
    requirement_coverage = []
    for obligation in state.get("requirement_obligations", []):
        if repository_id not in obligation["repositories"]:
            continue
        verification_entries = repository_verification[obligation["id"]]
        matching_ids = {
            gate_id
            for entry in verification_entries
            for gate_id in entry["gate_ids"]
        }
        matching_results = [
            item
            for item in results
            if item["id"] in matching_ids and item["status"] == "PASS"
        ]
        passed_ids = {item["id"] for item in matching_results}
        proven_entries = [
            entry
            for entry in verification_entries
            if set(entry["gate_ids"]).issubset(passed_ids)
        ]
        requirement_coverage.append(
            {
                "requirement_id": obligation["id"],
                "implementation_files": changed_files,
                "test_ids": [item["id"] for item in matching_results],
                "acceptance_criteria_ids": sorted(
                    {
                        criterion_id
                        for entry in proven_entries
                        for criterion_id in entry["acceptance_criteria_ids"]
                    }
                ),
                "evidence_types": sorted(
                    {
                        evidence_type
                        for entry in proven_entries
                        for evidence_type in entry["evidence_types"]
                    }
                ),
                "evidence_refs": [
                    item["log"] for item in matching_results
                ],
            }
        )
    evidence = {
        "schema_version": "1.0",
        "change_id": change_id,
        "repository_id": repository_id,
        "stack": repository["stack"],
        "commit_sha": commit_sha,
        "repository_extension_digest": extension_packet["digest"],
        "selected_extensions": {
            kind: [item["id"] for item in extension_packet[kind]]
            for kind in program_orchestrator.EXTENSION_KINDS
        },
        "decision": decision,
        "missing_required_capabilities": unavailable,
        "gates": results,
        "requirement_coverage": requirement_coverage,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    program_orchestrator.atomic_json(evidence_path, evidence)
    return evidence, evidence_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=program_orchestrator.repository_root())
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    if manifest and not manifest.is_absolute():
        manifest = root / manifest
    try:
        engine = program_orchestrator.ProgramOrchestrator(root, manifest)
        evidence, path = generate(engine, args.change_id, args.repository)
        if args.record:
            engine.record_repository_result(
                args.change_id, args.repository, evidence["decision"], path
            )
        print(json.dumps({"evidence": str(path), **evidence}, indent=2))
        return {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}[evidence["decision"]]
    except program_orchestrator.ProgramError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
