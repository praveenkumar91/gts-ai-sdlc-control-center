#!/usr/bin/env python3
"""Execute the approved cross-repository verification matrix and emit evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import program_orchestrator
import run_repository_gates


def generate(
    engine: program_orchestrator.ProgramOrchestrator,
    change_id: str,
) -> tuple[dict, Path]:
    state = engine.read_state(change_id)
    if state["state"] != "EXECUTING":
        raise program_orchestrator.ProgramError(
            "integration gates are permitted only after repository execution"
        )
    missing_repositories = [
        repository_id
        for repository_id in state["validation_scope"]
        if state["repository_results"].get(repository_id, {}).get("decision")
        != "PASS"
    ]
    if missing_repositories:
        raise program_orchestrator.ProgramError(
            "repositories without PASS evidence: " + ", ".join(missing_repositories)
        )

    current_vector = {
        repository_id: program_orchestrator.run_command(
            ["git", "rev-parse", "HEAD"],
            Path(state["commit_vector"][repository_id]["worktree"]),
        )
        for repository_id in state["validation_scope"]
    }
    matrix = program_orchestrator.integration_verification_matrix(
        state["requirement_obligations"]
    )
    config_value = engine.manifest.get("integration_quality_config")
    config_path = None
    if isinstance(config_value, str) and config_value:
        config_path = engine.root / program_orchestrator.safe_relative_path(
            config_value, "integration_quality_config"
        )

    output_dir = engine.run_dir(change_id) / "generated-evidence" / "integration"
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "quality-gates.json"
    reason = None
    configured: dict[str, dict] = {}
    if config_path is None:
        reason = "program manifest does not configure integration_quality_config"
    elif not config_path.is_file():
        reason = f"missing integration quality config: {config_path}"
    else:
        quality = program_orchestrator.read_json(config_path)
        configured = {
            item.get("id"): item
            for item in quality.get("commands", [])
            if isinstance(item, dict) and item.get("id")
        }
        unavailable = sorted(
            gate_id
            for gate_id in matrix
            if gate_id not in configured
            or configured[gate_id].get("enabled") is not True
            or configured[gate_id].get("required") is not True
        )
        if quality.get("adoption_complete") is not True:
            unavailable.append("integration-adoption")
        if unavailable:
            reason = "unavailable approved integration gates: " + ", ".join(
                unavailable
            )

    gate_results = []
    if reason is None:
        for gate_id in sorted(matrix):
            command = configured[gate_id]
            repository_id = command.get("repository")
            if repository_id is None:
                working_directory = engine.root
            elif repository_id not in state["checkout_scope"]:
                raise program_orchestrator.ProgramError(
                    f"{gate_id}: integration command repository is not checked out"
                )
            else:
                working_directory = Path(
                    state["commit_vector"][repository_id]["worktree"]
                )
            observed = run_repository_gates.execute(
                working_directory,
                command,
                log_dir,
                state["commit_vector_digest"],
            )
            observed.pop("commit_sha", None)
            expected = matrix[gate_id]
            observed.update(
                {
                    "commit_vector_digest": state["commit_vector_digest"],
                    "requirement_ids": sorted(expected["requirement_ids"]),
                    "source_refs": sorted(expected["source_refs"]),
                    "acceptance_criteria_ids": sorted(
                        expected["acceptance_criteria_ids"]
                    ),
                    "evidence_types": sorted(expected["evidence_types"]),
                    "evidence_refs": [observed["log"]],
                }
            )
            gate_results.append(observed)
    else:
        for gate_id in sorted(matrix):
            log_path = log_dir / f"{gate_id}.log"
            log_path.write_text(run_repository_gates.redact(reason), encoding="utf-8")
            expected = matrix[gate_id]
            gate_results.append(
                {
                    "id": gate_id,
                    "status": "INCONCLUSIVE",
                    "required": True,
                    "exit_code": None,
                    "command": configured.get(gate_id, {}).get("args", []),
                    "log": str(log_path),
                    "commit_vector_digest": state["commit_vector_digest"],
                    "requirement_ids": sorted(expected["requirement_ids"]),
                    "source_refs": sorted(expected["source_refs"]),
                    "acceptance_criteria_ids": sorted(
                        expected["acceptance_criteria_ids"]
                    ),
                    "evidence_types": sorted(expected["evidence_types"]),
                    "evidence_refs": [str(log_path)],
                }
            )

    required_statuses = {
        gate["status"] for gate in gate_results if gate["required"]
    }
    if reason or "INCONCLUSIVE" in required_statuses:
        decision = "INCONCLUSIVE"
    elif "BLOCKED_SPEC" in required_statuses:
        decision = "BLOCKED_SPEC"
    elif "FAIL" in required_statuses:
        decision = "FAIL"
    else:
        decision = "PASS"
    evidence = {
        "schema_version": "1.0",
        "change_id": change_id,
        "decision": decision,
        "commit_vector": current_vector,
        "commit_vector_digest": state["commit_vector_digest"],
        "cross_repository_gates": gate_results,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if reason:
        evidence["reason"] = reason
    program_orchestrator.atomic_json(evidence_path, evidence)
    return evidence, evidence_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=program_orchestrator.repository_root()
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    if manifest and not manifest.is_absolute():
        manifest = root / manifest
    try:
        engine = program_orchestrator.ProgramOrchestrator(root, manifest)
        evidence, path = generate(engine, args.change_id)
        if args.record:
            engine.record_integration_result(args.change_id, path)
        print(json.dumps({"evidence": str(path), **evidence}, indent=2))
        return {
            "PASS": 0,
            "FAIL": 1,
            "INCONCLUSIVE": 2,
            "BLOCKED_SPEC": 2,
        }[evidence["decision"]]
    except program_orchestrator.ProgramError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
