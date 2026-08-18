#!/usr/bin/env python3
"""Auto-fill two-agent SDLC scorecard for a program run."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
from typing import Any


STATE_ORDER = [
    "AWAITING_CLARIFICATION",
    "INTAKE",
    "AWAITING_PLAN_REVIEW",
    "AWAITING_PLAN_APPROVAL",
    "PLAN_APPROVED",
    "WORKSPACES_READY",
    "EXECUTING",
    "INTEGRATION_PASSED",
    "PLAN_CLOSED",
    "PR_SET_READY",
    "AWAITING_PR_APPROVAL",
    "PR_APPROVED",
]

CHECKPOINTS = [
    ("PROGRAM_CHANGE_STARTED", "AWAITING_CLARIFICATION"),
    ("INTAKE_READY", "INTAKE"),
    ("PLAN_PREPARED", "AWAITING_PLAN_REVIEW"),
    ("PLAN_REVIEW_COMPLETED", "AWAITING_PLAN_APPROVAL"),
    ("PLAN_APPROVED", "PLAN_APPROVED"),
    ("WORKSPACES_PREPARED", "WORKSPACES_READY"),
    ("INTEGRATION_PASSED", "INTEGRATION_PASSED"),
    ("PLAN_CLOSED", "PLAN_CLOSED"),
    ("PR_SET_PREPARED", "PR_SET_READY"),
    ("PULL_REQUEST_RECORDED", "AWAITING_PR_APPROVAL"),
    ("PR_SET_APPROVED", "PR_APPROVED"),
]

TERMINAL_STATES = {"PR_APPROVED", "FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json(path)


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def safe_div(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def score_ratio(max_points: int, numerator: int, denominator: int) -> int:
    if max_points <= 0 or denominator <= 0:
        return 0
    return int(round(max_points * safe_div(numerator, denominator)))


def find_state_rank(state: str) -> int:
    try:
        return STATE_ORDER.index(state)
    except ValueError:
        return -1


def git_head(path: Path) -> str | None:
    if not path.exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def has_runtime_e2e_requirement(requirements: list[dict[str, Any]]) -> bool:
    required_tokens = {
        "ui-test",
        "end-to-end-test",
        "end-to-end-tests",
        "integration-test",
    }
    for req in requirements:
        evidence_types = req.get("required_evidence")
        if isinstance(evidence_types, list):
            normalized = {
                str(item).strip().lower() for item in evidence_types if isinstance(item, str)
            }
            if required_tokens & normalized:
                return True
    return False


def evidence_types_from_plan_closure(plan_closure: dict[str, Any] | None) -> set[str]:
    if not isinstance(plan_closure, dict):
        return set()
    coverage = plan_closure.get("coverage")
    if not isinstance(coverage, list):
        return set()
    values: set[str] = set()
    for item in coverage:
        if not isinstance(item, dict):
            continue
        evidence_types = item.get("evidence_types")
        if not isinstance(evidence_types, list):
            continue
        for ev in evidence_types:
            if isinstance(ev, str):
                values.add(ev.strip().lower())
    return values


def stage(status: str, evidence: dict[str, Any], note: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "evidence": evidence,
        "note": note,
    }


def status_rating(status: str) -> int:
    if status == "PASS":
        return 5
    if status == "PARTIAL":
        return 3
    return 0


def participant(kind: str, identifier: str, status: str, note: str = "") -> dict[str, Any]:
    return {
        "kind": kind,
        "id": identifier,
        "path": "",
        "rating": status_rating(status),
        "max_rating": 5,
        "status": status,
        "note": note,
    }


def participant_with_path(
    kind: str,
    identifier: str,
    status: str,
    path: str,
    note: str = "",
) -> dict[str, Any]:
    item = participant(kind, identifier, status, note)
    item["path"] = path
    return item


def workspace_relative(path: Path, workspace_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace_root.resolve()))
    except Exception:
        return str(path)


def _entry_called_for_stage(entry: dict[str, Any], stage_name: str) -> bool:
    identifier = str(entry.get("id", "")).lower()
    role = str(entry.get("role", "")).lower()

    plan_tokens = {
        "planner",
        "spec-author",
        "jira",
        "requirement-conformance",
        "brainstorm",
    }
    implement_tokens = {
        "developer",
        "builder",
        "tester",
        "reviewer",
        "code",
        "debug",
        "verification",
        "code-review",
    }
    gate2_tokens = {
        "pr-author",
        "github",
        "reviewer",
        "orchestrator",
    }

    if stage_name == "plan":
        return any(token in identifier for token in plan_tokens) or role == "spec-authoring"
    if stage_name == "implement":
        return any(token in identifier for token in implement_tokens) or role in {
            "implementation",
            "testing",
            "independent-domain-review",
        }
    if stage_name == "gate2":
        return any(token in identifier for token in gate2_tokens) or role == "independent-domain-review"
    return False


def _participants_for_stage(
    entries: list[dict[str, Any]],
    stage_name: str,
    status: str,
    note: str,
    *,
    max_items: int = 14,
) -> list[dict[str, Any]]:
    participants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if not _entry_called_for_stage(entry, stage_name):
            continue
        repo_id = str(entry.get("repo_id", "unknown"))
        item_id = str(entry.get("id", "unknown"))
        unique_id = f"{repo_id}/{item_id}"
        if unique_id in seen:
            continue
        seen.add(unique_id)
        participants.append(
            participant_with_path(
                str(entry.get("kind", "gts.ai.sdlc-agent")),
                unique_id,
                status,
                str(entry.get("path", "")),
                note,
            )
        )
        if len(participants) >= max_items:
            break
    return participants


def build_pipeline_coverage(
    root: Path,
    run: dict[str, Any],
    run_dir: Path,
    event_types: set[str],
    plan_closure: dict[str, Any] | None,
) -> dict[str, Any]:
    workspace_root = root.parent
    state = str(run.get("state", "UNKNOWN"))
    state_rank = find_state_rank(state)

    requirements_payload = read_optional_json(run_dir / "requirements.json")
    source_set_digest_ok = False
    req_count = 0
    if isinstance(requirements_payload, dict):
        source_set_digest = requirements_payload.get("source_set_digest")
        source_set_digest_ok = isinstance(source_set_digest, str) and source_set_digest.startswith("sha256:")
        reqs = requirements_payload.get("requirements")
        if isinstance(reqs, list):
            req_count = len(reqs)

    extensions_payload = read_optional_json(run_dir / "repository-extensions.json")
    program_payload = read_optional_json(root / ".github" / "sdlc" / "program.json")
    extension_file_present = extensions_payload is not None
    extension_digest_present = bool(run.get("repository_extensions_digest"))
    extensions_loaded = extension_file_present and extension_digest_present

    selected_skills = 0
    selected_agents = 0
    selected_instructions = 0
    if isinstance(extensions_payload, dict):
        repos = extensions_payload.get("repositories")
        if isinstance(repos, dict):
            for extension in repos.values():
                if not isinstance(extension, dict):
                    continue
                skills = extension.get("skills")
                agents = extension.get("agents")
                instructions = extension.get("instructions")
                if isinstance(skills, list):
                    selected_skills += len(skills)
                if isinstance(agents, list):
                    selected_agents += len(agents)
                if isinstance(instructions, list):
                    selected_instructions += len(instructions)

    plan_approval = run.get("plan_approval")
    has_plan_approval = isinstance(plan_approval, dict) and bool(plan_approval.get("evidence_sha256"))

    commit_vector = run.get("commit_vector")
    has_workspaces = isinstance(commit_vector, dict) and len(commit_vector) > 0 and "WORKSPACES_PREPARED" in event_types

    repository_results = run.get("repository_results")
    has_repo_results = isinstance(repository_results, dict) and len(repository_results) > 0
    all_repo_pass = has_repo_results and all(
        isinstance(result, dict) and str(result.get("decision")) == "PASS"
        for result in repository_results.values()
    )
    integration_passed = "INTEGRATION_PASSED" in event_types and isinstance(run.get("integration_evidence_path"), str)

    pr_set_prepared = "PR_SET_PREPARED" in event_types
    has_plan_closure = isinstance(plan_closure, dict) and "PLAN_CLOSED" in event_types
    pr_approval = run.get("pr_approval")
    has_pr_approval = isinstance(pr_approval, dict) and bool(pr_approval.get("evidence_sha256"))

    stages: dict[str, dict[str, Any]] = {}
    selected_entries: list[dict[str, Any]] = []
    repo_selection_counts: dict[str, dict[str, int]] = {}
    manifest_status_by_repo: dict[str, str] = {}
    repo_extensions_path_by_id: dict[str, str] = {}

    if isinstance(program_payload, dict):
        workspace_root_entry = program_payload.get("workspace_root")
        repositories_entry = program_payload.get("repositories")
        repos_root = root / str(workspace_root_entry) if isinstance(workspace_root_entry, str) else None
        if isinstance(repositories_entry, list) and isinstance(repos_root, Path):
            for repo_entry in repositories_entry:
                if not isinstance(repo_entry, dict):
                    continue
                repo_id = repo_entry.get("id")
                local_path = repo_entry.get("local_path")
                ext_cfg = repo_entry.get("extensions_config", ".github/sdlc/extensions.json")
                if isinstance(repo_id, str) and isinstance(local_path, str):
                    expected = repos_root / local_path / str(ext_cfg)
                    repo_extensions_path_by_id[repo_id] = workspace_relative(expected, workspace_root)

    user_status = "PASS" if isinstance(run.get("request"), str) and run.get("request") else "PENDING"
    stages["user_request"] = stage(
        user_status,
        {"request_present": bool(run.get("request"))},
        "Input request captured in run.json",
    )
    stages["user_request"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/intake",
            user_status,
            workspace_relative(root / ".github" / "scripts" / "program_orchestrator.py", workspace_root),
            "Request intake",
        )
    ]

    orch_status = "PASS" if "PROGRAM_CHANGE_STARTED" in event_types else "PENDING"
    stages["control_plane_orchestration"] = stage(
        orch_status,
        {"event_present": "PROGRAM_CHANGE_STARTED" in event_types},
        "Main orchestrator has initialized a tracked run",
    )
    stages["control_plane_orchestration"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/main-orchestrator",
            orch_status,
            workspace_relative(root / ".github" / "scripts" / "program_orchestrator.py", workspace_root),
            "program_orchestrator flow",
        )
    ]

    ingest_status = "PASS" if source_set_digest_ok and req_count > 0 else "PENDING"
    stages["ingest_sources"] = stage(
        ingest_status,
        {"source_set_digest": source_set_digest_ok, "requirements_count": req_count},
        "sources.json + requirement extraction captured",
    )
    stages["ingest_sources"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/ingest-specifications",
            ingest_status,
            workspace_relative(root / ".github" / "scripts" / "program_orchestrator.py", workspace_root),
            "requirements normalization from sources",
        )
    ]

    plan_status = "PASS" if "PLAN_APPROVED" in event_types and has_plan_approval else "PENDING"
    stages["plan_and_human_gate_1"] = stage(
        plan_status,
        {
            "plan_prepared": "PLAN_PREPARED" in event_types,
            "plan_approved": "PLAN_APPROVED" in event_types,
            "approval_evidence": has_plan_approval,
        },
        "Plan prepared and approved with independent evidence",
    )
    stages["plan_and_human_gate_1"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/plan-orchestrator",
            plan_status,
            workspace_relative(root / ".github" / "scripts" / "program_orchestrator.py", workspace_root),
            "plan lifecycle and gate-1 enforcement",
        )
    ]

    workspace_status = "PASS" if has_workspaces else "PENDING"
    stages["prepare_workspaces"] = stage(
        workspace_status,
        {
            "workspaces_prepared": "WORKSPACES_PREPARED" in event_types,
            "repositories_in_commit_vector": len(commit_vector) if isinstance(commit_vector, dict) else 0,
        },
        "Repository workspaces prepared for execution",
    )
    stages["prepare_workspaces"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/workspace-preparer",
            workspace_status,
            workspace_relative(root / ".github" / "scripts" / "program_orchestrator.py", workspace_root),
            "checkout + commit vector preparation",
        )
    ]

    extension_status = "PASS" if extensions_loaded else "PENDING"
    stages["load_repository_extensions"] = stage(
        extension_status,
        {
            "repository_extensions_digest": extension_digest_present,
            "repository_extensions_file": extension_file_present,
        },
        "Repository extension packets resolved and digested",
    )
    stages["load_repository_extensions"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/extensions-loader",
            extension_status,
            workspace_relative(root / ".github" / "scripts" / "program_orchestrator.py", workspace_root),
            "repository extension resolution",
        )
    ]

    if selected_skills + selected_agents > 0:
        skill_stage_status = "PASS"
        skill_note = "Reusable skills/agents selected and active"
    elif extensions_loaded:
        skill_stage_status = "PARTIAL"
        skill_note = "Extensions loaded but no skills/agents selected for this run"
    else:
        skill_stage_status = "PENDING"
        skill_note = "Extensions are not yet loaded"

    stages["gts_ai_sdlc_skills_agents"] = stage(
        skill_stage_status,
        {
            "skills_selected": selected_skills,
            "agents_selected": selected_agents,
            "instructions_selected": selected_instructions,
        },
        skill_note,
    )
    if isinstance(extensions_payload, dict):
        repos = extensions_payload.get("repositories")
        if isinstance(repos, dict):
            for repo_id, extension in repos.items():
                if not isinstance(extension, dict):
                    continue
                manifest = extension.get("manifest")
                if isinstance(manifest, dict):
                    manifest_status_by_repo[str(repo_id)] = str(manifest.get("status", "UNKNOWN"))
                for key, kind in (("skills", "gts.ai.sdlc-skill"), ("agents", "gts.ai.sdlc-agent")):
                    values = extension.get(key)
                    if isinstance(values, list):
                        repo_counts = repo_selection_counts.setdefault(str(repo_id), {"skills": 0, "agents": 0})
                        for value in values:
                            repo_path = repo_extensions_path_by_id.get(str(repo_id), "")
                            if isinstance(value, dict):
                                item_id = str(value.get("id", "unknown"))
                                item_path = str(value.get("path", ""))
                                item_role = str(value.get("role", ""))
                            else:
                                item_id = str(value)
                                item_path = ""
                                item_role = ""
                            resolved_path = item_path
                            if (
                                item_path
                                and repo_path
                                and not item_path.startswith(
                                    (
                                        "workspace/",
                                        "gts-ai-sdlc-control-center/",
                                        "gts.ai.sdlc/",
                                    )
                                )
                                and not item_path.startswith("/")
                            ):
                                # repo_path points to extensions.json in repository root; strip config path.
                                repo_root_hint = Path(repo_path).parent.parent.parent
                                resolved_path = str(repo_root_hint / item_path)
                            selected_entries.append(
                                {
                                    "repo_id": str(repo_id),
                                    "kind": kind,
                                    "id": item_id,
                                    "path": resolved_path,
                                    "role": item_role,
                                }
                            )
                            if key == "skills":
                                repo_counts["skills"] += 1
                            else:
                                repo_counts["agents"] += 1
    global_skills_dir = root.parent / "gts.ai.sdlc" / ".agents" / "skills"
    global_skill_files = sorted(global_skills_dir.glob("**/SKILL.md")) if global_skills_dir.exists() else []
    global_skill_ids = [str(path.parent.relative_to(global_skills_dir)) for path in global_skill_files]

    gts_stage_participants: list[dict[str, Any]] = []
    if repo_selection_counts:
        for repo_id in sorted(repo_selection_counts):
            counts = repo_selection_counts[repo_id]
            gts_stage_participants.append(
                participant_with_path(
                    "gts.ai.sdlc-agent",
                    f"{repo_id}/catalog-selection",
                    skill_stage_status,
                    "gts.ai.sdlc/.agents",
                    f"skills={counts['skills']}, agents={counts['agents']} selected",
                )
            )

    if not selected_entries:
        if manifest_status_by_repo:
            for repo_id in sorted(manifest_status_by_repo):
                status = manifest_status_by_repo[repo_id]
                selected_entries.append(
                    {
                        "repo_id": repo_id,
                        "kind": "gts.ai.sdlc-agent",
                        "id": f"manifest-{status.lower()}",
                        "path": repo_extensions_path_by_id.get(repo_id, ""),
                        "role": "",
                    }
                )
                if not gts_stage_participants:
                    gts_stage_participants.append(
                        participant_with_path(
                            "gts.ai.sdlc-agent",
                            f"{repo_id}/manifest-{status.lower()}",
                            "PENDING",
                            repo_extensions_path_by_id.get(repo_id, ""),
                            "no repository extension manifest available for skill selection",
                        )
                    )
        elif not gts_stage_participants:
            gts_stage_participants.append(
                participant_with_path(
                    "gts.ai.sdlc-agent",
                    "none-selected",
                    "PENDING",
                    "",
                    "no repository skills/agents matched this run",
                )
            )

    stages["gts_ai_sdlc_skills_agents"]["participants"] = gts_stage_participants
    stages["gts_ai_sdlc_skills_agents"]["evidence"]["called_plan"] = len(
        _participants_for_stage(
            selected_entries,
            "plan",
            plan_status,
            "called for planning/issue/spec traceability",
        )
    )
    stages["gts_ai_sdlc_skills_agents"]["evidence"]["called_implement"] = len(
        _participants_for_stage(
            selected_entries,
            "implement",
            "PASS" if integration_passed and all_repo_pass else "PARTIAL" if has_repo_results or state_rank >= find_state_rank("EXECUTING") else "PENDING",
            "called for development/testing/review",
        )
    )
    stages["gts_ai_sdlc_skills_agents"]["evidence"]["called_gate2"] = len(
        _participants_for_stage(
            selected_entries,
            "gate2",
            "PASS" if "PR_SET_APPROVED" in event_types and has_pr_approval else "PARTIAL" if state in {"AWAITING_PR_APPROVAL", "PR_SET_READY"} else "PENDING",
            "called for PR approval and release readiness",
        )
    )
    stages["gts_ai_sdlc_skills_agents"]["evidence"]["global_skill_catalog_count"] = len(global_skill_ids)
    stages["gts_ai_sdlc_skills_agents"]["evidence"]["global_skill_catalog_sample"] = global_skill_ids[:10]

    if integration_passed and all_repo_pass:
        impl_status = "PASS"
        impl_note = "Implementation, repository verification and integration passed"
    elif has_repo_results or state_rank >= find_state_rank("EXECUTING"):
        impl_status = "PARTIAL"
        impl_note = "Implementation/verification started but not fully integrated yet"
    else:
        impl_status = "PENDING"
        impl_note = "Implementation/verification has not started"

    stages["implement_verify_integrate"] = stage(
        impl_status,
        {
            "repository_results_count": len(repository_results) if isinstance(repository_results, dict) else 0,
            "all_repository_results_pass": bool(all_repo_pass),
            "integration_passed": integration_passed,
        },
        impl_note,
    )
    stages["implement_verify_integrate"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/repository-gates",
            impl_status,
            workspace_relative(root / ".github" / "scripts" / "run_repository_gates.py", workspace_root),
            "repository and integration evidence evaluation",
        )
    ]

    if has_plan_closure and pr_set_prepared:
        close_status = "PASS"
    elif has_plan_closure or pr_set_prepared:
        close_status = "PARTIAL"
    else:
        close_status = "PENDING"
    stages["plan_closure_and_pr_set"] = stage(
        close_status,
        {
            "plan_closed": "PLAN_CLOSED" in event_types,
            "plan_closure_file": isinstance(plan_closure, dict),
            "pr_set_prepared": pr_set_prepared,
            "pull_requests_recorded": isinstance(run.get("pull_requests"), dict) and len(run.get("pull_requests", {})) > 0,
        },
        "Plan closure and PR-set readiness",
    )
    stages["plan_closure_and_pr_set"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/plan-closure-prset",
            close_status,
            workspace_relative(root / ".github" / "scripts" / "program_orchestrator.py", workspace_root),
            "plan closure + PR set preparation",
        )
    ]

    if "PR_SET_APPROVED" in event_types and has_pr_approval:
        gate2_status = "PASS"
    elif state in {"AWAITING_PR_APPROVAL", "PR_SET_READY"}:
        gate2_status = "PARTIAL"
    else:
        gate2_status = "PENDING"
    stages["human_gate_2_and_release_evidence"] = stage(
        gate2_status,
        {
            "pr_set_approved": "PR_SET_APPROVED" in event_types,
            "pr_approval_evidence": has_pr_approval,
            "state": state,
        },
        "Independent gate-2 approval and release evidence",
    )
    stages["human_gate_2_and_release_evidence"]["participants"] = [
        participant_with_path(
            "control-plane-agent",
            "gts-ai-sdlc-control-center/pr-approval-collector",
            gate2_status,
            workspace_relative(root / ".github" / "scripts" / "collect_pr_approval.py", workspace_root),
            "independent gate-2 approval evidence",
        )
    ]

    plan_called_participants = _participants_for_stage(
        selected_entries,
        "plan",
        plan_status,
        "called for planning/issue/spec traceability",
    )
    impl_called_participants = _participants_for_stage(
        selected_entries,
        "implement",
        impl_status,
        "called for development/testing/review",
    )
    gate2_called_participants = _participants_for_stage(
        selected_entries,
        "gate2",
        gate2_status,
        "called for PR approval and release readiness",
    )

    stages["plan_and_human_gate_1"]["participants"] += plan_called_participants
    stages["implement_verify_integrate"]["participants"] += impl_called_participants
    stages["human_gate_2_and_release_evidence"]["participants"] += gate2_called_participants

    pass_count = sum(1 for item in stages.values() if item.get("status") == "PASS")
    partial_count = sum(1 for item in stages.values() if item.get("status") == "PARTIAL")
    pending_count = sum(1 for item in stages.values() if item.get("status") == "PENDING")

    return {
        "summary": {
            "pass": pass_count,
            "partial": partial_count,
            "pending": pending_count,
            "total": len(stages),
        },
        "stages": stages,
    }


def evaluate(change_id: str, root: Path, template: dict[str, Any]) -> dict[str, Any]:
    runs_root = root / ".github" / "sdlc" / "program-runs"
    run_dir = runs_root / change_id
    run = read_json(run_dir / "run.json")
    events = read_events(run_dir / "events.jsonl")
    event_types = {str(event.get("type")) for event in events}

    plan_closure_path = run.get("plan_closure_path")
    plan_closure = (
        read_optional_json(run_dir / str(plan_closure_path))
        if isinstance(plan_closure_path, str)
        else None
    )

    program = read_json(root / ".github" / "sdlc" / "program.json")
    max_remediation = int(program.get("controls", {}).get("maximum_remediation_cycles", 3))

    state = str(run.get("state", "UNKNOWN"))
    state_rank = find_state_rank(state)

    weights = template.get("weights", {})
    cp_weights = weights.get("control_plane", {}) if isinstance(weights, dict) else {}
    sdlc_weights = weights.get("gts_ai_sdlc", {}) if isinstance(weights, dict) else {}

    cp_max = sum(int(value) for value in cp_weights.values()) if isinstance(cp_weights, dict) else 0
    sdlc_max = sum(int(value) for value in sdlc_weights.values()) if isinstance(sdlc_weights, dict) else 0

    dimensions: dict[str, dict[str, Any]] = {}

    # control-plane.stage_correctness
    cp_stage_max = int(cp_weights.get("stage_correctness", 10))
    expected_events = [
        name
        for (name, min_state) in CHECKPOINTS
        if state_rank >= 0 and find_state_rank(min_state) <= state_rank
    ]
    expected_events = expected_events or ["PROGRAM_CHANGE_STARTED"]
    stage_hits = sum(1 for name in expected_events if name in event_types)
    cp_stage_score = score_ratio(cp_stage_max, stage_hits, len(expected_events))
    dimensions["control_plane.stage_correctness"] = {
        "awarded": cp_stage_score,
        "max": cp_stage_max,
        "evidence": {
            "state": state,
            "expected_events": expected_events,
            "present": stage_hits,
        },
    }

    # control-plane.evidence_completeness
    cp_evidence_max = int(cp_weights.get("evidence_completeness", 10))
    required_artifacts = [
        run_dir / "run.json",
        run_dir / "plan.json",
        run_dir / "requirements.json",
        run_dir / "commit-vector.json",
        run_dir / "events.jsonl",
    ]
    checks: list[bool] = [path.exists() for path in required_artifacts]

    if state_rank >= find_state_rank("PLAN_APPROVED"):
        plan_approval = run.get("plan_approval")
        checks.append(isinstance(plan_approval, dict) and bool(plan_approval.get("evidence_sha256")))

    if state_rank >= find_state_rank("INTEGRATION_PASSED"):
        integration_path = run.get("integration_evidence_path")
        checks.append(isinstance(integration_path, str) and (run_dir / integration_path).exists())

    if state_rank >= find_state_rank("AWAITING_PR_APPROVAL"):
        pull_requests = run.get("pull_requests")
        checks.append(isinstance(pull_requests, dict) and len(pull_requests) > 0)

    cp_evidence_score = score_ratio(cp_evidence_max, sum(1 for ok in checks if ok), len(checks))
    dimensions["control_plane.evidence_completeness"] = {
        "awarded": cp_evidence_score,
        "max": cp_evidence_max,
        "evidence": {
            "checks_passed": sum(1 for ok in checks if ok),
            "checks_total": len(checks),
        },
    }

    # control-plane.traceability_integrity
    cp_trace_max = int(cp_weights.get("traceability_integrity", 10))
    trace_checks: list[bool] = []
    trace_checks.append(str(run.get("change_id", "")) == change_id)

    plan_approval = run.get("plan_approval")
    trace_checks.append(isinstance(plan_approval, dict) and isinstance(plan_approval.get("source_url"), str))

    requirements = run.get("requirement_obligations", [])
    trace_checks.append(isinstance(requirements, list) and len(requirements) > 0)

    commit_vector = run.get("commit_vector", {})
    repository_results = run.get("repository_results", {})
    aligned_repo_results = 0
    if isinstance(repository_results, dict):
        for repo_id, result in repository_results.items():
            if not isinstance(result, dict):
                continue
            cv = commit_vector.get(repo_id, {}) if isinstance(commit_vector, dict) else {}
            if isinstance(cv, dict) and result.get("commit_sha") == cv.get("head_sha"):
                aligned_repo_results += 1
    trace_checks.append(
        not repository_results
        or aligned_repo_results == len(repository_results)
    )

    pull_requests = run.get("pull_requests", {})
    aligned_prs = 0
    if isinstance(pull_requests, dict):
        for repo_id, pr in pull_requests.items():
            if not isinstance(pr, dict):
                continue
            cv = commit_vector.get(repo_id, {}) if isinstance(commit_vector, dict) else {}
            if isinstance(cv, dict) and pr.get("head_sha") == cv.get("head_sha"):
                aligned_prs += 1
    trace_checks.append(not pull_requests or aligned_prs == len(pull_requests))

    cp_trace_score = score_ratio(cp_trace_max, sum(1 for ok in trace_checks if ok), len(trace_checks))
    dimensions["control_plane.traceability_integrity"] = {
        "awarded": cp_trace_score,
        "max": cp_trace_max,
        "evidence": {
            "checks_passed": sum(1 for ok in trace_checks if ok),
            "checks_total": len(trace_checks),
            "aligned_repository_results": aligned_repo_results,
            "aligned_pull_requests": aligned_prs,
        },
    }

    # control-plane.drift_detection_handling
    cp_drift_max = int(cp_weights.get("drift_detection_handling", 10))
    drift_detect_points = cp_drift_max // 2
    drift_handle_points = cp_drift_max - drift_detect_points

    drift_total = 0
    drift_checked = 0
    if isinstance(commit_vector, dict):
        for info in commit_vector.values():
            if not isinstance(info, dict):
                continue
            worktree = info.get("worktree")
            recorded_head = info.get("head_sha")
            if not isinstance(worktree, str) or not isinstance(recorded_head, str):
                continue
            drift_checked += 1
            current_head = git_head(Path(worktree))
            if current_head is not None and current_head != recorded_head:
                drift_total += 1

    drift_detect_score = drift_detect_points if drift_checked > 0 else 0
    drift_handled = drift_total == 0 or state in {
        "AWAITING_CLARIFICATION",
        "INTAKE",
        "AWAITING_PLAN_REVIEW",
        "AWAITING_PLAN_APPROVAL",
        "PLAN_APPROVED",
        "WORKSPACES_READY",
        "EXECUTING",
    }
    drift_handle_score = drift_handle_points if drift_handled else 0
    cp_drift_score = drift_detect_score + drift_handle_score
    dimensions["control_plane.drift_detection_handling"] = {
        "awarded": cp_drift_score,
        "max": cp_drift_max,
        "evidence": {
            "repositories_checked": drift_checked,
            "drift_count": drift_total,
            "handled": drift_handled,
        },
    }

    # control-plane.failure_recovery_behavior
    cp_recovery_max = int(cp_weights.get("failure_recovery_behavior", 10))
    remediation = run.get("remediation_cycles", {})
    remediation_count = len(remediation) if isinstance(remediation, dict) else 0
    repo_failures = 0
    if isinstance(repository_results, dict):
        for result in repository_results.values():
            if not isinstance(result, dict):
                continue
            if str(result.get("decision")) in {"FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"}:
                repo_failures += 1
    failure_seen = state in {"FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"} or repo_failures > 0

    if failure_seen:
        if remediation_count > 0 and remediation_count <= max_remediation:
            cp_recovery_score = cp_recovery_max
        elif remediation_count > max_remediation:
            cp_recovery_score = max(0, cp_recovery_max - 6)
        else:
            cp_recovery_score = max(0, cp_recovery_max - 8)
    else:
        # Not exercised fully; keep score below max.
        cp_recovery_score = max(0, cp_recovery_max - 3)

    dimensions["control_plane.failure_recovery_behavior"] = {
        "awarded": cp_recovery_score,
        "max": cp_recovery_max,
        "evidence": {
            "failure_seen": failure_seen,
            "repository_failures": repo_failures,
            "remediation_cycles": remediation_count,
            "maximum_allowed": max_remediation,
        },
    }

    # gts.ai.sdlc.requirement_coverage
    sdlc_req_max = int(sdlc_weights.get("requirement_coverage", 10))
    obligations = requirements if isinstance(requirements, list) else []
    if isinstance(plan_closure, dict) and isinstance(plan_closure.get("coverage"), list):
        covered_req_ids = {
            str(item.get("requirement_id"))
            for item in plan_closure["coverage"]
            if isinstance(item, dict)
        }
        all_req_ids = {
            str(item.get("id"))
            for item in obligations
            if isinstance(item, dict)
        }
        sdlc_req_score = score_ratio(sdlc_req_max, len(covered_req_ids & all_req_ids), max(1, len(all_req_ids)))
    else:
        # Run not yet closed; partial credit only for having obligations.
        sdlc_req_score = score_ratio(sdlc_req_max, 1 if obligations else 0, 2)
    dimensions["gts_ai_sdlc.requirement_coverage"] = {
        "awarded": sdlc_req_score,
        "max": sdlc_req_max,
        "evidence": {
            "obligations": len(obligations),
            "has_plan_closure": isinstance(plan_closure, dict),
        },
    }

    # gts.ai.sdlc.code_correctness
    sdlc_code_max = int(sdlc_weights.get("code_correctness", 15))
    impl_scope = run.get("implementation_scope", [])
    impl_repos = impl_scope if isinstance(impl_scope, list) else []
    pass_count = 0
    evaluated = 0
    if isinstance(repository_results, dict):
        for repo_id in impl_repos:
            result = repository_results.get(str(repo_id))
            if isinstance(result, dict):
                evaluated += 1
                if str(result.get("decision")) == "PASS":
                    pass_count += 1
    # If no repository results yet, this remains low by design.
    sdlc_code_score = score_ratio(sdlc_code_max, pass_count, max(1, len(impl_repos))) if impl_repos else 0
    dimensions["gts_ai_sdlc.code_correctness"] = {
        "awarded": sdlc_code_score,
        "max": sdlc_code_max,
        "evidence": {
            "implementation_repositories": len(impl_repos),
            "repositories_with_pass": pass_count,
            "repositories_evaluated": evaluated,
        },
    }

    # gts.ai.sdlc.test_adequacy
    sdlc_test_max = int(sdlc_weights.get("test_adequacy", 10))
    required_evidence = set()
    for req in obligations:
        if not isinstance(req, dict):
            continue
        values = req.get("required_evidence")
        if isinstance(values, list):
            required_evidence.update(
                str(item).strip().lower()
                for item in values
                if isinstance(item, str)
            )

    observed_evidence = evidence_types_from_plan_closure(plan_closure)
    if isinstance(run.get("integration_evidence_path"), str):
        observed_evidence.add("integration-test")
    if repository_results:
        observed_evidence.add("repository-test")

    if required_evidence:
        matched = len(required_evidence & observed_evidence)
        sdlc_test_score = score_ratio(sdlc_test_max, matched, len(required_evidence))
    else:
        sdlc_test_score = 0

    dimensions["gts_ai_sdlc.test_adequacy"] = {
        "awarded": sdlc_test_score,
        "max": sdlc_test_max,
        "evidence": {
            "required_evidence": sorted(required_evidence),
            "observed_evidence": sorted(observed_evidence),
        },
    }

    # gts.ai.sdlc.regression_safety
    sdlc_reg_max = int(sdlc_weights.get("regression_safety", 10))
    integration_passed = "INTEGRATION_PASSED" in event_types
    no_repo_failures = repo_failures == 0
    # Full points require integration evidence and no failures.
    if integration_passed and no_repo_failures:
        sdlc_reg_score = sdlc_reg_max
    elif no_repo_failures:
        sdlc_reg_score = max(0, sdlc_reg_max - 4)
    else:
        sdlc_reg_score = max(0, sdlc_reg_max - 8)

    dimensions["gts_ai_sdlc.regression_safety"] = {
        "awarded": sdlc_reg_score,
        "max": sdlc_reg_max,
        "evidence": {
            "integration_passed": integration_passed,
            "repository_failures": repo_failures,
        },
    }

    # gts.ai.sdlc.change_hygiene
    sdlc_hygiene_max = int(sdlc_weights.get("change_hygiene", 5))
    pr_alignment_ok = True
    if isinstance(pull_requests, dict) and isinstance(commit_vector, dict):
        for repo_id, pr in pull_requests.items():
            if not isinstance(pr, dict):
                continue
            cv = commit_vector.get(repo_id)
            if not isinstance(cv, dict) or pr.get("head_sha") != cv.get("head_sha"):
                pr_alignment_ok = False
                break
    hygiene_checks = [pr_alignment_ok, drift_total == 0 or state_rank <= find_state_rank("WORKSPACES_READY")]
    sdlc_hygiene_score = score_ratio(sdlc_hygiene_max, sum(1 for ok in hygiene_checks if ok), len(hygiene_checks))
    dimensions["gts_ai_sdlc.change_hygiene"] = {
        "awarded": sdlc_hygiene_score,
        "max": sdlc_hygiene_max,
        "evidence": {
            "pr_commit_alignment": pr_alignment_ok,
            "drift_count": drift_total,
        },
    }

    control_plane_score = sum(
        item["awarded"]
        for key, item in dimensions.items()
        if key.startswith("control_plane.")
    )
    gts_score = sum(
        item["awarded"]
        for key, item in dimensions.items()
        if key.startswith("gts_ai_sdlc.")
    )
    total_score = control_plane_score + gts_score
    total_max = cp_max + sdlc_max

    hard_gates: list[dict[str, Any]] = []

    trace_gate_pass = True
    trace_gate_reasons: list[str] = []
    if state_rank >= find_state_rank("AWAITING_PR_APPROVAL"):
        if not isinstance(plan_approval, dict) or not plan_approval.get("source_url"):
            trace_gate_pass = False
            trace_gate_reasons.append("plan_approval.source_url is missing")
        if not isinstance(pull_requests, dict) or not pull_requests:
            trace_gate_pass = False
            trace_gate_reasons.append("pull_requests are missing")
        if not isinstance(commit_vector, dict) or not commit_vector:
            trace_gate_pass = False
            trace_gate_reasons.append("commit_vector is missing")
        if not (run_dir / "events.jsonl").exists():
            trace_gate_pass = False
            trace_gate_reasons.append("events.jsonl is missing")

    hard_gates.append(
        {
            "id": "trace-link-present",
            "pass": trace_gate_pass,
            "reasons": trace_gate_reasons,
        }
    )

    hidden_blocker_pass = True
    hidden_blocker_reasons: list[str] = []
    approved_like = state in {"PR_APPROVED", "AWAITING_PR_APPROVAL", "PR_SET_READY"}
    if approved_like:
        if repo_failures > 0:
            hidden_blocker_pass = False
            hidden_blocker_reasons.append("repository_results contain non-PASS decisions")
        if state == "PR_APPROVED" and isinstance(repository_results, dict):
            scope = run.get("validation_scope")
            if isinstance(scope, list):
                missing = [repo for repo in scope if repo not in repository_results]
                if missing:
                    hidden_blocker_pass = False
                    hidden_blocker_reasons.append(
                        "validation_scope repositories missing repository_results"
                    )

    hard_gates.append(
        {
            "id": "no-hidden-blocker",
            "pass": hidden_blocker_pass,
            "reasons": hidden_blocker_reasons,
        }
    )

    runtime_req = has_runtime_e2e_requirement(obligations)
    observed = evidence_types_from_plan_closure(plan_closure)
    runtime_evidence_pass = True
    runtime_reasons: list[str] = []
    if runtime_req and state in TERMINAL_STATES:
        has_ui_or_e2e = bool({"ui-test", "end-to-end-test", "end-to-end-tests"} & observed)
        if not has_ui_or_e2e:
            runtime_evidence_pass = False
            runtime_reasons.append("terminal run requires ui-test/end-to-end evidence in plan closure")

    hard_gates.append(
        {
            "id": "runtime-e2e-evidence",
            "pass": runtime_evidence_pass,
            "reasons": runtime_reasons,
        }
    )

    hard_gate_pass = all(item.get("pass") for item in hard_gates)

    pipeline_coverage = build_pipeline_coverage(root, run, run_dir, event_types, plan_closure)

    return {
        "schema_version": "1.0",
        "change_id": change_id,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_state": state,
        "template_id": template.get("template_id", "agent-chain-scorecard-v1"),
        "scores": {
            "control_plane": {
                "score": control_plane_score,
                "max": cp_max,
            },
            "gts_ai_sdlc": {
                "score": gts_score,
                "max": sdlc_max,
            },
            "chain": {
                "score": total_score,
                "max": total_max,
                "hard_gates_pass": hard_gate_pass,
            },
        },
        "dimensions": dimensions,
        "hard_gates": hard_gates,
        "pipeline_coverage": pipeline_coverage,
    }


def to_markdown(payload: dict[str, Any]) -> str:
    scores = payload.get("scores", {})
    cp = scores.get("control_plane", {})
    sdlc = scores.get("gts_ai_sdlc", {})
    chain = scores.get("chain", {})
    dimensions = payload.get("dimensions", {})
    hard_gates = payload.get("hard_gates", [])
    pipeline_coverage = payload.get("pipeline_coverage", {})

    lines: list[str] = []
    lines.append(f"# Agent Chain Scorecard: {payload.get('change_id', '-')}")
    lines.append("")
    lines.append(f"Generated: {payload.get('generated_at', '-')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Score | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Control Plane | {cp.get('score', 0)}/{cp.get('max', 0)} |")
    lines.append(f"| gts.ai.sdlc | {sdlc.get('score', 0)}/{sdlc.get('max', 0)} |")
    lines.append(f"| Chain | {chain.get('score', 0)}/{chain.get('max', 0)} |")
    lines.append(f"| Hard Gates | {'PASS' if chain.get('hard_gates_pass') else 'FAIL'} |")
    lines.append("")

    lines.append("## Dimensions")
    lines.append("")
    lines.append("| Dimension | Score |")
    lines.append("|---|---:|")
    for key in sorted(dimensions):
        item = dimensions.get(key, {})
        lines.append(f"| {key} | {item.get('awarded', 0)}/{item.get('max', 0)} |")
    lines.append("")

    lines.append("## Hard Gates")
    lines.append("")
    for item in hard_gates:
        gate_id = item.get("id", "-")
        passed = bool(item.get("pass"))
        lines.append(f"- [{'x' if passed else ' '}] {gate_id}")
        reasons = item.get("reasons", [])
        if isinstance(reasons, list):
            for reason in reasons:
                lines.append(f"  - {reason}")
    lines.append("")

    stages = pipeline_coverage.get("stages", {}) if isinstance(pipeline_coverage, dict) else {}
    summary = pipeline_coverage.get("summary", {}) if isinstance(pipeline_coverage, dict) else {}
    lines.append("## Pipeline Coverage")
    lines.append("")
    lines.append("| Stage | Status | Used By | Used Paths | Rating |")
    lines.append("|---|---|---|---|---:|")
    for key in [
        "user_request",
        "control_plane_orchestration",
        "ingest_sources",
        "plan_and_human_gate_1",
        "prepare_workspaces",
        "load_repository_extensions",
        "gts_ai_sdlc_skills_agents",
        "implement_verify_integrate",
        "plan_closure_and_pr_set",
        "human_gate_2_and_release_evidence",
    ]:
        item = stages.get(key, {}) if isinstance(stages, dict) else {}
        participants = item.get("participants", []) if isinstance(item, dict) else []
        names: list[str] = []
        paths: list[str] = []
        ratings: list[str] = []
        if isinstance(participants, list):
            for p in participants:
                if not isinstance(p, dict):
                    continue
                names.append(str(p.get("id", "unknown")))
                path_value = str(p.get("path", "")).strip()
                paths.append(path_value if path_value else "-")
                ratings.append(f"{int(p.get('rating', 0))}/{int(p.get('max_rating', 5))}")
        used_by = ", ".join(names) if names else "-"
        used_paths = ", ".join(paths) if paths else "-"
        rating = ", ".join(ratings) if ratings else "-"
        lines.append(f"| {key} | {item.get('status', 'PENDING')} | {used_by} | {used_paths} | {rating} |")
    lines.append("")
    lines.append(
        "Coverage summary: "
        f"pass={summary.get('pass', 0)}, "
        f"partial={summary.get('partial', 0)}, "
        f"pending={summary.get('pending', 0)}, "
        f"total={summary.get('total', 0)}"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-fill two-agent SDLC scorecard")
    parser.add_argument("--change-id", required=True, help="Program change ID")
    parser.add_argument(
        "--template",
        type=Path,
        default=Path(".github/sdlc/evaluations/agent-scorecard.template.json"),
        help="Relative path to scorecard template",
    )
    parser.add_argument("--write", action="store_true", help="Write scorecard artifacts to the run directory")
    args = parser.parse_args()

    root = repo_root()
    template = read_json(root / args.template)
    payload = evaluate(args.change_id, root, template)

    if args.write:
        run_dir = root / ".github" / "sdlc" / "program-runs" / args.change_id
        json_path = run_dir / "agent-scorecard.json"
        md_path = run_dir / "agent-scorecard.md"
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        md_path.write_text(to_markdown(payload), encoding="utf-8")
        print(str(json_path))
    else:
        print(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
