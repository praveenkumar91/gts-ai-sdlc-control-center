#!/usr/bin/env python3
"""Run durable repository worker loops above the deterministic SDLC control plane."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import importlib.metadata
import importlib.util
import json
import os
import re
import string
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

import program_orchestrator
import run_integration_gates
import run_repository_gates


SUPERVISOR_STATES = {
    "IDLE",
    "RUNNING",
    "PAUSED_CLARIFICATION",
    "PAUSED_PLANNING",
    "PAUSED_PLAN_REVIEW",
    "PAUSED_HUMAN_GATE_1",
    "PAUSED_PLAN_CLOSURE",
    "PAUSED_PR_CREATION",
    "PAUSED_HUMAN_GATE_2",
    "PAUSED_INCONCLUSIVE",
    "PAUSED_WORKER",
    "PAUSED_VSCODE_WORKER",
    "PAUSED_POLICY_MUTATION",
    "PAUSED_STEP_BUDGET",
    "BLOCKED_SPEC",
    "FAILED",
    "COMPLETED",
}
WAITABLE_STATES = {
    "PAUSED_CLARIFICATION",
    "PAUSED_PLANNING",
    "PAUSED_PLAN_REVIEW",
    "PAUSED_HUMAN_GATE_1",
    "PAUSED_PLAN_CLOSURE",
    "PAUSED_PR_CREATION",
    "PAUSED_HUMAN_GATE_2",
    "PAUSED_VSCODE_WORKER",
}
ALLOWED_PLACEHOLDERS = {
    "change_id",
    "repository_id",
    "attempt",
    "phase",
    "prompt",
    "prompt_file",
    "worktree",
    "control_plane",
}
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_PROTECTED_PATHS = [
    ".github/sdlc/project.json",
    ".github/sdlc/extensions.json",
    ".github/workflows/**",
    ".github/CODEOWNERS",
    "CODEOWNERS",
]


class SupervisorError(RuntimeError):
    """A fail-closed execution-supervisor error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def validate_runtime_config(config: dict[str, Any], adoption: bool = False) -> list[str]:
    errors: list[str] = []
    if config.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if not isinstance(config.get("adoption_complete"), bool):
        errors.append("adoption_complete must be boolean")
    elif adoption and config["adoption_complete"] is not True:
        errors.append("agent runtime adoption_complete must be true")
    worker = config.get("worker")
    if not isinstance(worker, dict):
        return errors + ["worker must be an object"]
    if not isinstance(worker.get("enabled"), bool):
        errors.append("worker.enabled must be boolean")
    if worker.get("enabled") is not True and adoption:
        errors.append("worker.enabled must be true for execution")
    mode = worker.get("mode", "command")
    if mode not in {"command", "vscode-chat", "copilot-sdk"}:
        errors.append("worker.mode must be command, vscode-chat or copilot-sdk")
    argv = worker.get("argv")
    if mode == "command" and (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        errors.append("worker.argv must be a non-empty string array in command mode")
    elif mode == "command":
        formatter = string.Formatter()
        observed: set[str] = set()
        for index, item in enumerate(argv):
            if "REPLACE_" in item and adoption:
                errors.append(f"worker.argv[{index}] contains a placeholder command")
            try:
                fields = {
                    field_name
                    for _, field_name, _, _ in formatter.parse(item)
                    if field_name is not None
                }
            except ValueError as exc:
                errors.append(f"worker.argv[{index}] has invalid formatting: {exc}")
                continue
            unknown = fields - ALLOWED_PLACEHOLDERS
            if unknown:
                errors.append(
                    f"worker.argv[{index}] has unknown placeholders: "
                    + ", ".join(sorted(unknown))
                )
            observed.update(fields)
        if not ({"prompt", "prompt_file"} & observed):
            errors.append("worker.argv must pass {prompt} or {prompt_file}")
    elif argv not in (None, []):
        errors.append("worker.argv must be omitted or empty outside command mode")
    if mode == "copilot-sdk":
        runner = worker.get("sdk_runner")
        if not isinstance(runner, str) or not runner:
            errors.append("worker.sdk_runner must be a non-empty path in copilot-sdk mode")
        model = worker.get("model")
        if not isinstance(model, str) or not model:
            errors.append("worker.model must be a non-empty string in copilot-sdk mode")
        roles = worker.get("required_specialist_roles")
        if (
            not isinstance(roles, list)
            or not roles
            or not all(isinstance(role, str) and role for role in roles)
            or len(set(roles)) != len(roles)
        ):
            errors.append(
                "worker.required_specialist_roles must be a non-empty unique string array "
                "in copilot-sdk mode"
            )
        if not isinstance(worker.get("honor_agent_models", False), bool):
            errors.append("worker.honor_agent_models must be boolean")
        sdk_version = worker.get("sdk_version")
        if not isinstance(sdk_version, str) or not sdk_version:
            errors.append("worker.sdk_version must be a non-empty string")
    numeric_bounds = {
        "timeout_seconds": (1, 28_800),
        "max_output_bytes": (1_024, 50 * 1024 * 1024),
        "max_prompt_bytes": (1_024, 1_000_000),
        "maximum_worker_attempts": (1, 10),
        "stale_lock_seconds": (60, 86_400),
    }
    for field, (minimum, maximum) in numeric_bounds.items():
        value = worker.get(field)
        if not isinstance(value, int) or not minimum <= value <= maximum:
            errors.append(
                f"worker.{field} must be between {minimum} and {maximum}"
            )
    if worker.get("working_directory") not in {"worktree", "control-plane"}:
        errors.append("worker.working_directory must be worktree or control-plane")
    environment = worker.get("environment_allowlist")
    if not isinstance(environment, list) or not all(
        isinstance(item, str) and ENV_NAME_RE.fullmatch(item)
        for item in environment
    ):
        errors.append("worker.environment_allowlist must contain valid variable names")
    protected = worker.get("protected_paths", DEFAULT_PROTECTED_PATHS)
    if not isinstance(protected, list) or not protected or not all(
        isinstance(item, str)
        and item.strip()
        and not Path(item).is_absolute()
        and ".." not in Path(item).parts
        for item in protected
    ):
        errors.append("worker.protected_paths must contain safe relative patterns")
    for field in ("git_author_name", "git_author_email"):
        value = worker.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"worker.{field} must be a non-empty string")
    for field in ("blocked_spec_exit_code", "inconclusive_exit_code"):
        value = worker.get(field)
        if not isinstance(value, int) or not 1 <= value <= 255:
            errors.append(f"worker.{field} must be between 1 and 255")
    if worker.get("blocked_spec_exit_code") == worker.get(
        "inconclusive_exit_code"
    ):
        errors.append("worker blocked and inconclusive exit codes must differ")
    return errors


class AgentSupervisor:
    """Drive model workers while leaving authoritative state to ProgramOrchestrator."""

    def __init__(
        self,
        root: Path,
        manifest_path: Path | None = None,
        runtime_config_path: Path | None = None,
    ):
        self.root = root.resolve()
        self.engine = program_orchestrator.ProgramOrchestrator(
            self.root, manifest_path
        )
        if runtime_config_path is None:
            configured = self.engine.manifest.get(
                "agent_runtime_config", ".github/sdlc/agent-runtime.json"
            )
            relative = program_orchestrator.safe_relative_path(
                configured, "agent_runtime_config"
            )
            runtime_config_path = self.root / relative
        self.runtime_config_path = runtime_config_path.resolve()
        if not self.runtime_config_path.is_file():
            raise SupervisorError(
                f"agent runtime config is missing: {self.runtime_config_path}"
            )
        self.config = program_orchestrator.read_json(self.runtime_config_path)
        errors = validate_runtime_config(self.config)
        if errors:
            raise SupervisorError(
                "invalid agent runtime config:\n- " + "\n- ".join(errors)
            )
        self.worker = self.config["worker"]

    def adoption_errors(self) -> list[str]:
        errors = validate_runtime_config(self.config, adoption=True)
        if self.worker.get("mode") != "copilot-sdk":
            return errors
        try:
            relative = program_orchestrator.safe_relative_path(
                self.worker.get("sdk_runner"), "worker.sdk_runner"
            )
        except program_orchestrator.ProgramError as exc:
            errors.append(str(exc))
        else:
            runner = (self.root / relative).resolve()
            if not runner.is_file() or not runner.is_relative_to(self.root):
                errors.append(f"Copilot SDK runner is unavailable: {runner}")
        if importlib.util.find_spec("copilot") is None:
            errors.append(
                "github-copilot-sdk is not installed in the supervisor Python environment"
            )
        else:
            try:
                copilot_module = __import__("copilot", fromlist=["CopilotClient"])
                permission_handler = getattr(copilot_module, "PermissionHandler", None)
                if not hasattr(copilot_module, "CopilotClient") or not hasattr(
                    permission_handler, "approve_all"
                ):
                    errors.append(
                        "installed Copilot SDK lacks the required client/permission API"
                    )
            except ImportError as exc:
                errors.append(f"installed Copilot SDK cannot be imported: {exc}")
            try:
                installed = importlib.metadata.version("github-copilot-sdk")
            except importlib.metadata.PackageNotFoundError:
                errors.append("github-copilot-sdk distribution metadata is unavailable")
            else:
                if installed != self.worker.get("sdk_version"):
                    errors.append(
                        "github-copilot-sdk version mismatch: "
                        f"expected {self.worker.get('sdk_version')}, found {installed}"
                    )
        return errors

    def supervisor_dir(self, change_id: str) -> Path:
        return self.engine.run_dir(change_id) / "supervisor"

    def state_path(self, change_id: str) -> Path:
        return self.supervisor_dir(change_id) / "state.json"

    def events_path(self, change_id: str) -> Path:
        return self.supervisor_dir(change_id) / "events.jsonl"

    def lock_path(self, change_id: str) -> Path:
        return self.supervisor_dir(change_id) / "active.lock"

    def _new_state(self, change_id: str) -> dict[str, Any]:
        state: dict[str, Any] = {
            "schema_version": "1.0",
            "change_id": change_id,
            "status": "IDLE",
            "reason": "supervisor initialized",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "event_count": 0,
            "last_event_hash": "0" * 64,
            "worker_attempts": {},
            "worker_runs": [],
            "active_task": None,
            "integration_remediated_cycle": 0,
            "inconclusive_integration_cycle": 0,
        }
        self._append_event(
            change_id,
            state,
            "SUPERVISOR_INITIALIZED",
            {"runtime_config_sha256": program_orchestrator.file_digest(
                self.runtime_config_path
            )},
        )
        self._write_state(change_id, state)
        return state

    def read_state(self, change_id: str) -> dict[str, Any]:
        path = self.state_path(change_id)
        if not path.is_file():
            return self._new_state(change_id)
        state = program_orchestrator.read_json(path)
        if state.get("status") not in SUPERVISOR_STATES:
            raise SupervisorError("supervisor state has an invalid status")
        return state

    def _write_state(self, change_id: str, state: dict[str, Any]) -> None:
        if state.get("status") not in SUPERVISOR_STATES:
            raise SupervisorError(f"invalid supervisor status: {state.get('status')}")
        state["updated_at"] = utc_now()
        program_orchestrator.atomic_json(self.state_path(change_id), state)

    def _append_event(
        self,
        change_id: str,
        state: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        event = {
            "sequence": int(state.get("event_count", 0)) + 1,
            "timestamp": utc_now(),
            "type": event_type,
            "payload": payload,
            "previous_hash": state.get("last_event_hash", "0" * 64),
        }
        event["hash"] = program_orchestrator.digest(event)
        path = self.events_path(change_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(program_orchestrator.canonical_json(event) + "\n")
        state["event_count"] = event["sequence"]
        state["last_event_hash"] = event["hash"]

    def _transition(
        self,
        change_id: str,
        state: dict[str, Any],
        status: str,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state["status"] = status
        state["reason"] = reason
        self._append_event(
            change_id,
            state,
            "SUPERVISOR_STATUS_CHANGED",
            {"status": status, "reason": reason, **(payload or {})},
        )
        self._write_state(change_id, state)
        return state

    @contextmanager
    def _lock(
        self, change_id: str, recover_stale_lock: bool
    ) -> Iterator[None]:
        path = self.lock_path(change_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and recover_stale_lock:
            age = time.time() - path.stat().st_mtime
            if age >= int(self.worker["stale_lock_seconds"]):
                path.unlink()
        token = str(uuid.uuid4())
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SupervisorError(
                "another supervisor owns this change; recover only after the "
                "configured stale-lock interval"
            ) from exc
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {"token": token, "pid": os.getpid(), "created_at": utc_now()}
                    )
                )
            yield
        finally:
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                current = {}
            if current.get("token") == token:
                path.unlink(missing_ok=True)

    def _relative_artifact(self, change_id: str, path: Path) -> str:
        try:
            return path.resolve().relative_to(
                self.engine.run_dir(change_id)
            ).as_posix()
        except ValueError as exc:
            raise SupervisorError("supervisor artifact escapes the change run") from exc

    def _failure_context(
        self, change_id: str, repository_id: str, phase: str
    ) -> str:
        program_state = self.engine.read_state(change_id)
        documents: list[dict[str, Any]] = []
        if phase == "integration-remediation":
            integration = program_state.get("integration_result")
            if isinstance(integration, dict):
                path = self.engine.run_dir(change_id) / str(
                    integration.get("evidence_path", "")
                )
                if path.is_file():
                    documents.append(program_orchestrator.read_json(path))
        repository_result = program_state.get("repository_results", {}).get(
            repository_id
        )
        if isinstance(repository_result, dict):
            path = self.engine.run_dir(change_id) / str(
                repository_result.get("evidence_path", "")
            )
            if path.is_file():
                documents.append(program_orchestrator.read_json(path))
        if not documents:
            return "No previous failed evidence is recorded."
        encoded = json.dumps(documents, indent=2, ensure_ascii=False)
        return encoded[:24_000]

    def _visible_work_plan(
        self, change_id: str, repository_id: str, phase: str
    ) -> list[dict[str, Any]]:
        """Build the visible Ralph-style checklist for one repository lease."""
        program_state = self.engine.read_state(change_id)
        obligations = [
            item
            for item in program_state.get("requirement_obligations", [])
            if repository_id in item.get("repositories", [])
        ]
        criteria = [
            {
                "requirement_id": obligation["id"],
                "criterion_id": criterion["id"],
                "statement": criterion["statement"],
            }
            for obligation in obligations
            for criterion in obligation.get("acceptance_criteria", [])
        ]
        required_evidence = {
            evidence
            for obligation in obligations
            for evidence in obligation.get("required_evidence", [])
        }
        tasks: list[dict[str, Any]] = [
            {
                "id": "orient",
                "status": "pending",
                "title": "Read specs, plan, architecture and selected GTS/local resources",
            },
            {
                "id": "investigate",
                "status": "pending",
                "title": "Search existing code and confirm the real gap",
            },
            {
                "id": "red",
                "status": "pending",
                "title": "Add or identify tests that fail for the approved gap",
                "acceptance_criteria": criteria,
            },
            {
                "id": "green",
                "status": "pending",
                "title": "Implement the smallest complete change satisfying every criterion",
            },
            {
                "id": "verify",
                "status": "pending",
                "title": "Run focused and regression checks",
            },
            {
                "id": "expert-review",
                "status": "pending",
                "title": "Apply GTS conformance, review and system verification lenses",
            },
            {
                "id": "build",
                "status": "pending",
                "title": "Build, lint and type-check affected components",
            },
        ]
        if "gui-validation" in required_evidence:
            tasks.append(
                {
                    "id": "gui-validation",
                    "status": "pending",
                    "title": "Exercise responsive GUI, accessibility and visual evidence",
                }
            )
        tasks.append(
            {
                "id": "handoff",
                "status": "pending",
                "title": "Leave an uncommitted diff and invoke complete-task",
            }
        )
        return tasks

    @staticmethod
    def _specialist_usage_requirements(
        packet: dict[str, Any], phase: str
    ) -> list[dict[str, Any]]:
        """Select auditable guidance files for legacy VS Code Chat mode.

        A Chat-side command cannot prove that a separate custom agent ran, so
        agent profiles are intentionally excluded. Real agent lifecycle evidence
        is available only through copilot-sdk mode.
        """
        result: list[dict[str, Any]] = []
        used: set[tuple[str, str]] = set()

        def choose(
            kind: str, purpose: str, predicates: list[str]
        ) -> None:
            candidates = [
                item
                for item in packet.get(kind, [])
                if any(token in str(item.get("id", "")) for token in predicates)
            ]
            if not candidates:
                return
            candidates.sort(
                key=lambda item: (
                    str(item.get("id", "")).startswith("common-"),
                    str(item.get("id", "")).startswith("gts-"),
                    str(item.get("id", "")),
                )
            )
            selected = candidates[0]
            key = (kind, str(selected.get("id")))
            if key in used:
                return
            used.add(key)
            result.append(
                {
                    "kind": kind,
                    "id": selected.get("id"),
                    "sha256": selected.get("sha256"),
                    "role": selected.get("role"),
                    "purpose": purpose,
                    "status": "pending",
                }
            )

        choose("skills", "implementation guidance", ["-code", "coding-guidelines"])
        choose("skills", "verification guidance", ["verification"])
        choose("skills", "independent review lens", ["code-review"])
        if "remediation" in phase:
            choose("skills", "failure diagnosis", ["debugging"])
        for kind in ("skills",):
            if any(item["kind"] == kind for item in result):
                continue
            items = packet.get(kind, [])
            if items:
                item = items[0]
                result.append(
                    {
                        "kind": kind,
                        "id": item.get("id"),
                        "sha256": item.get("sha256"),
                        "role": item.get("role"),
                        "purpose": "repository specialist guidance",
                        "status": "pending",
                    }
                )
        return result

    def _write_task_board(
        self,
        change_id: str,
        state: dict[str, Any],
        program_state: dict[str, Any],
    ) -> None:
        active = state.get("active_task")
        active_repository = (
            active.get("repository_id") if isinstance(active, dict) else None
        )
        board: list[dict[str, Any]] = []
        for wave_index, wave in enumerate(
            program_state.get("execution_waves", []), 1
        ):
            for repository_id in wave:
                decision = program_state.get("repository_results", {}).get(
                    repository_id, {}
                ).get("decision")
                status = "completed" if decision == "PASS" else "pending"
                if repository_id == active_repository:
                    status = "in_progress"
                board.append(
                    {
                        "wave": wave_index,
                        "repository_id": repository_id,
                        "mode": program_state.get("commit_vector", {}).get(
                            repository_id, {}
                        ).get("mode", "unprepared"),
                        "status": status,
                        "decision": decision,
                        "requirement_ids": [
                            item["id"]
                            for item in program_state.get(
                                "requirement_obligations", []
                            )
                            if repository_id in item.get("repositories", [])
                        ],
                    }
                )
        state["task_board"] = board
        lines = [
            f"# Implementation plan: {change_id}",
            "",
            f"Plan digest: `{program_state.get('plan_digest', 'unavailable')}`",
            "",
            "Supervisor progress. Mirror this in the VS Code Chat todo list.",
            "",
        ]
        for item in board:
            check = "x" if item["status"] == "completed" else " "
            marker = " (active)" if item["status"] == "in_progress" else ""
            requirements = ", ".join(item["requirement_ids"]) or "validation scope"
            lines.append(
                f"- [{check}] Wave {item['wave']} / {item['repository_id']} "
                f"[{item['mode']}] - {requirements}{marker}"
            )
        path = self.supervisor_dir(change_id) / "IMPLEMENTATION_PLAN.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        state["implementation_plan_path"] = self._relative_artifact(
            change_id, path
        )
        state["implementation_plan_sha256"] = program_orchestrator.file_digest(path)

    def _prompt(
        self,
        change_id: str,
        repository_id: str,
        attempt: int,
        phase: str,
    ) -> str:
        program_state = self.engine.read_state(change_id)
        vector = program_state["commit_vector"][repository_id]
        packet = program_state.get("repository_extensions", {}).get(
            repository_id, {}
        )
        obligations = [
            item
            for item in program_state.get("requirement_obligations", [])
            if repository_id in item["repositories"]
        ]
        selected_extensions = {
            kind: [
                {
                    "id": item.get("id"),
                    "path": item.get("path"),
                    "sha256": item.get("sha256"),
                    "role": item.get("role"),
                    "source": item.get("source", "repository"),
                    "resolved_path": str(
                        (
                            self.root.parent / str(item.get("path", ""))
                            if item.get("source") == "central-gts-ai-sdlc-fallback"
                            else Path(vector["worktree"]) / str(item.get("path", ""))
                        ).resolve()
                    ),
                }
                for item in packet.get(kind, [])
            ]
            for kind in program_orchestrator.EXTENSION_KINDS
        }
        visible_work_plan = self._visible_work_plan(change_id, repository_id, phase)
        prompt = f"""You are an implementation worker for one repository in a governed financial-system change.

Change ID: {change_id}
Repository: {repository_id}
Phase: {phase}
Attempt: {attempt}
Mode: {vector['mode']}
Plan digest: {program_state['plan_digest']}
Requirements digest: {program_state['requirements_digest']}
Base commit: {vector['base_sha']}
Current commit before this attempt: {program_orchestrator.run_command(['git', 'rev-parse', 'HEAD'], Path(vector['worktree']))}

Program request:
{program_state['request']}

Repository requirement slice:
{json.dumps(obligations, indent=2, ensure_ascii=False)}

Selected repository extensions. Read the relevant files before editing. The
resolved_path is authoritative for this task; central GTS fallback resources
are outside the repository worktree and remain read-only:
{json.dumps(selected_extensions, indent=2, ensure_ascii=False)}

Previous deterministic failure evidence:
{self._failure_context(change_id, repository_id, phase)}

Visible task/subtask checklist. Mirror these exact items in the VS Code Chat
todo UI and update them as work progresses:
{json.dumps(visible_work_plan, indent=2, ensure_ascii=False)}

Execution rules:
- Work only inside the current repository worktree.
- Implement the complete requirement slice; inspect existing architecture before editing.
- Do not approve plans or PRs, push, merge, deploy, change remotes, or create external evidence.
- Do not weaken or edit SDLC quality configuration, extension manifests, workflows, or CODEOWNERS.
- Do not commit. The supervisor will inspect and commit the resulting worktree.
- Run useful local checks while developing, but the supervisor-owned deterministic gates are authoritative.
- If the specification is contradictory or materially ambiguous, exit with code {self.worker['blocked_spec_exit_code']} and explain the exact conflict.
- If required context, tooling, or infrastructure is unavailable, exit with code {self.worker['inconclusive_exit_code']} and explain what is missing.
- Exit 0 only when the repository slice is ready for deterministic gates.
- In VS Code Chat mode, do not claim completion in prose. Run the exact
  complete-task command from the task JSON after leaving the worktree ready.
- Do not collapse RED, GREEN, verification, expert review and build into one
  hidden step. Keep the checklist visible throughout the attempt.
- In VS Code Chat mode, run every exact `specialist_usage_commands` entry from
  the leased task after applying that named GTS/local resource. Completion is
  rejected until every required usage receipt is recorded and visible.
"""
        size = len(prompt.encode("utf-8"))
        if size > int(self.worker["max_prompt_bytes"]):
            raise SupervisorError(
                f"{repository_id}: worker prompt is {size} bytes and exceeds the "
                "configured maximum; split or reduce the requirement slice"
            )
        return prompt

    def _prepare_vscode_task(
        self,
        change_id: str,
        state: dict[str, Any],
        repository_id: str,
        phase: str,
    ) -> dict[str, Any]:
        active = state.get("active_task")
        if isinstance(active, dict):
            return active
        attempt = int(state["worker_attempts"].get(repository_id, 0)) + 1
        prompt = self._prompt(change_id, repository_id, attempt, phase)
        directory = (
            self.supervisor_dir(change_id)
            / "workers"
            / repository_id
            / f"attempt-{attempt}"
        )
        directory.mkdir(parents=True, exist_ok=True)
        prompt_path = directory / "prompt.md"
        task_path = directory / "task.json"
        prompt_path.write_text(prompt, encoding="utf-8")
        program_state = self.engine.read_state(change_id)
        vector = program_state["commit_vector"][repository_id]
        packet = program_state.get("repository_extensions", {}).get(repository_id, {})
        task_id = str(uuid.uuid4())
        usage_requirements = self._specialist_usage_requirements(packet, phase)
        visible_work_plan = self._visible_work_plan(
            change_id, repository_id, phase
        )
        for item in visible_work_plan:
            if item["id"] == "expert-review":
                item["specialists"] = [
                    {
                        "kind": requirement["kind"],
                        "id": requirement["id"],
                        "purpose": requirement["purpose"],
                        "status": "pending",
                    }
                    for requirement in usage_requirements
                ]
        task = {
            "schema_version": "1.0",
            "task_id": task_id,
            "change_id": change_id,
            "repository_id": repository_id,
            "attempt": attempt,
            "phase": phase,
            "worktree": vector["worktree"],
            "start_head_sha": program_orchestrator.run_command(
                ["git", "rev-parse", "HEAD"], Path(vector["worktree"])
            ),
            "plan_digest": program_state["plan_digest"],
            "requirements_digest": program_state["requirements_digest"],
            "repository_extension_digest": packet.get("digest"),
            "visible_work_plan": visible_work_plan,
            "specialist_usage_requirements": usage_requirements,
            "specialist_usage_commands": [
                [
                    sys.executable,
                    str((self.root / ".github/scripts/agent_supervisor.py").resolve()),
                    "--root",
                    str(self.root),
                    "--manifest",
                    str(self.engine.manifest_path),
                    "--runtime-config",
                    str(self.runtime_config_path),
                    "record-specialist-usage",
                    "--change-id",
                    change_id,
                    "--task-id",
                    task_id,
                    "--kind",
                    requirement["kind"],
                    "--resource-id",
                    str(requirement["id"]),
                ]
                for requirement in usage_requirements
            ],
            "prompt_path": self._relative_artifact(change_id, prompt_path),
            "prompt_sha256": program_orchestrator.file_digest(prompt_path),
            "created_at": utc_now(),
            "completion_command": [
                sys.executable,
                str((self.root / ".github/scripts/agent_supervisor.py").resolve()),
                "--root",
                str(self.root),
                "--manifest",
                str(self.engine.manifest_path),
                "--runtime-config",
                str(self.runtime_config_path),
                "complete-task",
                "--change-id",
                change_id,
                "--task-id",
                task_id,
                "--outcome",
                "ready",
            ],
        }
        program_orchestrator.atomic_json(task_path, task)
        active = {
            **task,
            "task_path": self._relative_artifact(change_id, task_path),
            "task_sha256": program_orchestrator.file_digest(task_path),
            "specialist_usage_receipts": [],
        }
        state["active_task"] = active
        self._write_task_board(change_id, state, program_state)
        self._append_event(
            change_id,
            state,
            "VSCODE_TASK_LEASED",
            {
                "task_id": task_id,
                "repository_id": repository_id,
                "attempt": attempt,
                "phase": phase,
                "start_head_sha": task["start_head_sha"],
                "prompt_sha256": task["prompt_sha256"],
                "task_sha256": active["task_sha256"],
                "repository_extension_digest": task["repository_extension_digest"],
            },
        )
        self._write_state(change_id, state)
        return active

    def _expand_argv(
        self,
        change_id: str,
        repository_id: str,
        attempt: int,
        phase: str,
        prompt: str,
        prompt_path: Path,
        worktree: Path,
    ) -> list[str]:
        values = {
            "change_id": change_id,
            "repository_id": repository_id,
            "attempt": str(attempt),
            "phase": phase,
            "prompt": prompt,
            "prompt_file": str(prompt_path),
            "worktree": str(worktree),
            "control_plane": str(self.root),
        }
        return [item.format(**values) for item in self.worker["argv"]]

    def _worker_environment(
        self, change_id: str, repository_id: str, worktree: Path
    ) -> dict[str, str]:
        environment = {
            name: os.environ[name]
            for name in self.worker["environment_allowlist"]
            if name in os.environ
        }
        environment.update(
            {
                "SDLC_CHANGE_ID": change_id,
                "SDLC_REPOSITORY_ID": repository_id,
                "SDLC_WORKTREE": str(worktree),
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        hooks = self.supervisor_dir(change_id) / "worker-git-hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        pre_push = hooks / "pre-push"
        if not pre_push.exists():
            pre_push.write_text(
                "#!/bin/sh\necho 'SDLC supervisor denies worker git push' >&2\nexit 1\n",
                encoding="utf-8",
            )
        environment["GIT_CONFIG_COUNT"] = "1"
        environment["GIT_CONFIG_KEY_0"] = "core.hooksPath"
        environment["GIT_CONFIG_VALUE_0"] = str(hooks)
        return environment

    def _copilot_sdk_argv(
        self,
        *,
        change_id: str,
        repository_id: str,
        attempt: int,
        phase: str,
        worktree: Path,
        start_head_sha: str,
        prompt_path: Path,
        packet_path: Path,
        result_path: Path,
        events_path: Path,
        board_path: Path,
    ) -> list[str]:
        runner_relative = program_orchestrator.safe_relative_path(
            self.worker.get("sdk_runner"), "worker.sdk_runner"
        )
        runner = (self.root / runner_relative).resolve()
        if not runner.is_file() or not runner.is_relative_to(self.root):
            raise SupervisorError(f"Copilot SDK runner is unavailable: {runner}")
        session_id = re.sub(
            r"[^A-Za-z0-9._-]", "-", f"sdlc-{change_id}-{repository_id}-{attempt}"
        )
        argv = [
            sys.executable,
            str(runner),
            "--prompt-file",
            str(prompt_path),
            "--extension-packet",
            str(packet_path),
            "--result",
            str(result_path),
            "--events",
            str(events_path),
            "--board",
            str(board_path),
            "--worktree",
            str(worktree),
            "--change-id",
            change_id,
            "--repository-id",
            repository_id,
            "--attempt",
            str(attempt),
            "--phase",
            phase,
            "--session-id",
            session_id,
            "--start-head-sha",
            start_head_sha,
            "--model",
            str(self.worker["model"]),
        ]
        for role in self.worker["required_specialist_roles"]:
            argv.extend(["--required-role", role])
        if self.worker.get("honor_agent_models", False):
            argv.append("--honor-agent-models")
        return argv

    def _runtime_extension_packet(
        self, packet: dict[str, Any], worktree: Path
    ) -> dict[str, Any]:
        """Add central generic agents only for capabilities absent from the packet."""
        runtime_packet = json.loads(json.dumps(packet))
        catalog_root: Path | None = None
        for kind in ("skills", "agents"):
            for item in runtime_packet.setdefault(kind, []):
                relative = program_orchestrator.safe_relative_path(
                    item.get("path"), f"runtime extension {kind} path"
                )
                candidates = [
                    (worktree / relative).resolve(),
                    (self.root / relative).resolve(),
                    (self.root.parent / relative).resolve(),
                ]
                if item.get("source") == "central-gts-ai-sdlc-fallback":
                    if catalog_root is None:
                        catalog_root = self.engine._gts_catalog_root()
                    parts = relative.parts
                    if parts and parts[0] in {"gts.ai.sdlc", "gts.ai.sdlc-master"}:
                        candidates.insert(0, (catalog_root / Path(*parts[1:])).resolve())
                resolved = next((path for path in candidates if path.is_file()), None)
                if resolved is None:
                    raise SupervisorError(
                        f"selected {kind[:-1]} is unavailable: {relative.as_posix()}"
                    )
                if program_orchestrator.file_digest(resolved) != item.get("sha256"):
                    raise SupervisorError(
                        f"selected {kind[:-1]} digest mismatch: {relative.as_posix()}"
                    )
                item["resolved_path"] = str(resolved)
        agents = runtime_packet.setdefault("agents", [])
        fallback = {
            "implementation": "implementation.agent.md",
            "build": "build-verifier.agent.md",
            "testing": "verification.agent.md",
            "independent-domain-review": "adversarial-reviewer.agent.md",
        }
        name_tokens = {
            "implementation": ("developer", "implement"),
            "build": ("builder", "build"),
            "testing": ("tester", "test", "verification"),
            "independent-domain-review": ("reviewer", "review"),
        }
        for role in self.worker.get("required_specialist_roles", []):
            tokens = name_tokens.get(role, (role,))
            if any(
                item.get("role") == role
                or any(token in str(item.get("id", "")).lower() for token in tokens)
                for item in agents
            ):
                continue
            path = (self.root / ".github/agents" / fallback[role]).resolve()
            if not path.is_file():
                raise SupervisorError(
                    f"central fallback agent for role {role} is missing: {path}"
                )
            agents.append(
                {
                    "id": path.name.removesuffix(".md"),
                    "path": str(path.relative_to(self.root).as_posix()),
                    "resolved_path": str(path),
                    "sha256": program_orchestrator.file_digest(path),
                    "role": role,
                    "source": "central-control-plane-fallback",
                }
            )
        runtime_packet["runtime_catalog_digest"] = program_orchestrator.digest(
            {"agents": agents, "skills": runtime_packet.get("skills", [])}
        )
        return runtime_packet

    def _validate_copilot_runtime_result(
        self,
        path: Path,
        events_path: Path,
        board_path: Path,
        *,
        change_id: str,
        repository_id: str,
        attempt: int,
        phase: str,
        start_head_sha: str,
        prompt_path: Path,
        packet_path: Path,
    ) -> str | None:
        if not path.is_file():
            return "Copilot SDK runtime result is missing"
        if not events_path.is_file():
            return "Copilot SDK subagent event stream is missing"
        if not board_path.is_file():
            return "Copilot SDK runtime task board is missing"
        try:
            result = program_orchestrator.read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            return f"Copilot SDK runtime result is invalid: {exc}"
        expected = {
            "schema_version": "1.0",
            "change_id": change_id,
            "repository_id": repository_id,
            "attempt": attempt,
            "phase": phase,
            "start_head_sha": start_head_sha,
            "prompt_sha256": program_orchestrator.file_digest(prompt_path),
            "extension_packet_sha256": program_orchestrator.file_digest(packet_path),
            "events_sha256": program_orchestrator.file_digest(events_path),
            "task_board_sha256": program_orchestrator.file_digest(board_path),
            "decision": "PASS",
        }
        for field, value in expected.items():
            if result.get(field) != value:
                return f"Copilot SDK runtime result has stale or invalid {field}"
        recorded_digest = result.get("digest")
        payload = dict(result)
        payload.pop("digest", None)
        if recorded_digest != program_orchestrator.digest(payload):
            return "Copilot SDK runtime result digest mismatch"
        required = result.get("required_agents")
        executions = result.get("executions")
        if not isinstance(required, dict) or not isinstance(executions, list):
            return "Copilot SDK runtime result lacks required agent evidence"
        completed = {
            item.get("agent_name")
            for item in executions
            if isinstance(item, dict)
            and item.get("status") == "completed"
            and item.get("tool_call_id")
            and item.get("output_sha256")
            and item.get("output_message_count", 0) > 0
            and isinstance(item.get("result_contract"), dict)
            and item["result_contract"].get("decision") == "PASS"
            and isinstance(item["result_contract"].get("evidence"), list)
            and bool(item["result_contract"]["evidence"])
        }
        missing = sorted(set(required.values()) - completed)
        if missing:
            return "Copilot SDK required subagent evidence is missing: " + ", ".join(
                missing
            )
        implementation_name = required.get("implementation")
        implementation_end = max(
            (
                int(item.get("completed_sequence", 0))
                for item in executions
                if isinstance(item, dict)
                and item.get("status") == "completed"
                and item.get("agent_name") == implementation_name
            ),
            default=0,
        )
        for role in ("build", "testing", "independent-domain-review"):
            name = required.get(role)
            if name and not any(
                isinstance(item, dict)
                and item.get("status") == "completed"
                and item.get("agent_name") == name
                and isinstance(item.get("result_contract"), dict)
                and item["result_contract"].get("decision") == "PASS"
                and int(item.get("started_sequence", 0)) > implementation_end
                for item in executions
            ):
                return (
                    f"Copilot SDK {role} evidence is stale relative to implementation"
                )
        return None

    def _invoke_worker(
        self,
        change_id: str,
        repository_id: str,
        attempt: int,
        phase: str,
    ) -> dict[str, Any]:
        program_state = self.engine.read_state(change_id)
        worktree = Path(program_state["commit_vector"][repository_id]["worktree"])
        prompt = self._prompt(change_id, repository_id, attempt, phase)
        directory = (
            self.supervisor_dir(change_id)
            / "workers"
            / repository_id
            / f"attempt-{attempt}"
        )
        directory.mkdir(parents=True, exist_ok=True)
        prompt_path = directory / "prompt.md"
        log_path = directory / "worker.log"
        raw_path = directory / "worker.raw"
        prompt_path.write_text(prompt, encoding="utf-8")
        start_head_sha = program_orchestrator.run_command(
            ["git", "rev-parse", "HEAD"], worktree
        )
        packet_path = directory / "extension-packet.json"
        result_path = directory / "copilot-runtime-result.json"
        events_path = directory / "copilot-runtime-events.jsonl"
        board_path = directory / "RUNTIME_TASK_BOARD.md"
        if self.worker.get("mode") == "copilot-sdk":
            packet = self._runtime_extension_packet(
                program_state.get("repository_extensions", {}).get(repository_id, {}),
                worktree,
            )
            program_orchestrator.atomic_json(packet_path, packet)
            argv = self._copilot_sdk_argv(
                change_id=change_id,
                repository_id=repository_id,
                attempt=attempt,
                phase=phase,
                worktree=worktree,
                start_head_sha=start_head_sha,
                prompt_path=prompt_path,
                packet_path=packet_path,
                result_path=result_path,
                events_path=events_path,
                board_path=board_path,
            )
        else:
            argv = self._expand_argv(
                change_id,
                repository_id,
                attempt,
                phase,
                prompt,
                prompt_path,
                worktree,
            )
        cwd = (
            worktree
            if self.worker["working_directory"] == "worktree"
            else self.root
        )
        started_at = utc_now()
        before = time.monotonic()
        exit_code: int | None = None
        outcome = "ERROR"
        detail = ""
        maximum = int(self.worker["max_output_bytes"])
        try:
            with raw_path.open("wb") as raw:
                process = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    stdin=subprocess.DEVNULL,
                    stdout=raw,
                    stderr=subprocess.STDOUT,
                    shell=False,
                    env=self._worker_environment(change_id, repository_id, worktree),
                )
                deadline = time.monotonic() + int(self.worker["timeout_seconds"])
                while process.poll() is None:
                    if time.monotonic() >= deadline:
                        process.kill()
                        outcome = "TIMEOUT"
                        detail = "worker exceeded timeout"
                        break
                    raw.flush()
                    if raw_path.stat().st_size > maximum:
                        process.kill()
                        outcome = "OUTPUT_LIMIT"
                        detail = "worker exceeded output limit"
                        break
                    time.sleep(0.1)
                exit_code = process.wait()
                if outcome == "ERROR":
                    outcome = "EXITED"
        except OSError as exc:
            detail = f"worker could not start: {exc}"
        raw_bytes = raw_path.read_bytes()[:maximum] if raw_path.is_file() else b""
        output = raw_bytes.decode("utf-8", errors="replace")
        runtime_error = None
        if self.worker.get("mode") == "copilot-sdk" and outcome == "EXITED":
            runtime_error = self._validate_copilot_runtime_result(
                result_path,
                events_path,
                board_path,
                change_id=change_id,
                repository_id=repository_id,
                attempt=attempt,
                phase=phase,
                start_head_sha=start_head_sha,
                prompt_path=prompt_path,
                packet_path=packet_path,
            )
            if runtime_error and exit_code == 0:
                exit_code = int(self.worker["inconclusive_exit_code"])
            if runtime_error:
                output = runtime_error + "\n" + output
        if detail:
            output = detail + "\n" + output
        redacted = run_repository_gates.redact(output)
        log_path.write_text(redacted, encoding="utf-8")
        raw_path.unlink(missing_ok=True)
        safe_argv = ["<PROMPT>" if item == prompt else item for item in argv]
        worker_run = {
            "repository_id": repository_id,
            "attempt": attempt,
            "phase": phase,
            "outcome": outcome,
            "exit_code": exit_code,
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - before, 3),
            "argv": safe_argv,
            "prompt_path": self._relative_artifact(change_id, prompt_path),
            "prompt_sha256": program_orchestrator.file_digest(prompt_path),
            "log_path": self._relative_artifact(change_id, log_path),
            "log_sha256": program_orchestrator.file_digest(log_path),
        }
        if self.worker.get("mode") == "copilot-sdk":
            worker_run.update(
                {
                    "start_head_sha": start_head_sha,
                    "extension_packet_path": self._relative_artifact(
                        change_id, packet_path
                    ),
                    "extension_packet_sha256": program_orchestrator.file_digest(
                        packet_path
                    ),
                    "copilot_runtime_result_path": self._relative_artifact(
                        change_id, result_path
                    )
                    if result_path.is_file()
                    else None,
                    "copilot_runtime_result_sha256": program_orchestrator.file_digest(
                        result_path
                    )
                    if result_path.is_file()
                    else None,
                    "copilot_runtime_events_path": self._relative_artifact(
                        change_id, events_path
                    )
                    if events_path.is_file()
                    else None,
                    "copilot_runtime_events_sha256": program_orchestrator.file_digest(
                        events_path
                    )
                    if events_path.is_file()
                    else None,
                    "copilot_runtime_task_board_path": self._relative_artifact(
                        change_id, board_path
                    )
                    if board_path.is_file()
                    else None,
                    "copilot_runtime_task_board_sha256": program_orchestrator.file_digest(
                        board_path
                    )
                    if board_path.is_file()
                    else None,
                }
            )
        return worker_run

    def _record_worker_run(
        self, change_id: str, state: dict[str, Any], worker_run: dict[str, Any]
    ) -> None:
        repository_id = worker_run["repository_id"]
        state["worker_attempts"][repository_id] = worker_run["attempt"]
        state["worker_runs"].append(worker_run)
        self._append_event(
            change_id,
            state,
            "WORKER_COMPLETED",
            {
                "repository_id": repository_id,
                "attempt": worker_run["attempt"],
                "phase": worker_run["phase"],
                "outcome": worker_run["outcome"],
                "exit_code": worker_run["exit_code"],
                "prompt_sha256": worker_run["prompt_sha256"],
                "log_sha256": worker_run["log_sha256"],
            },
        )
        self._write_state(change_id, state)

    def _changed_paths(self, worktree: Path, base_sha: str) -> set[str]:
        tracked = {
            item
            for item in program_orchestrator.run_command(
                ["git", "diff", "--name-only", base_sha], worktree
            ).splitlines()
            if item
        }
        untracked = {
            item
            for item in program_orchestrator.run_command(
                ["git", "ls-files", "--others", "--exclude-standard"], worktree
            ).splitlines()
            if item
        }
        return tracked | untracked

    def _protected_changes(self, worktree: Path, base_sha: str) -> list[str]:
        patterns = self.worker.get("protected_paths", DEFAULT_PROTECTED_PATHS)
        return sorted(
            path
            for path in self._changed_paths(worktree, base_sha)
            if any(PurePosixPath(path).match(pattern) for pattern in patterns)
        )

    def _commit_worker_changes(
        self,
        change_id: str,
        repository_id: str,
        attempt: int,
    ) -> tuple[bool, str]:
        program_state = self.engine.read_state(change_id)
        vector = program_state["commit_vector"][repository_id]
        worktree = Path(vector["worktree"])
        protected = self._protected_changes(worktree, vector["base_sha"])
        if protected:
            raise SupervisorError(
                f"{repository_id}: worker changed protected policy paths: "
                + ", ".join(protected)
            )
        status = program_orchestrator.run_command(
            ["git", "status", "--porcelain"], worktree
        )
        if status:
            program_orchestrator.run_command(["git", "add", "-A"], worktree)
            program_orchestrator.run_command(
                [
                    "git",
                    "-c",
                    f"user.name={self.worker['git_author_name']}",
                    "-c",
                    f"user.email={self.worker['git_author_email']}",
                    "commit",
                    "-m",
                    f"{change_id}: implement {repository_id} attempt {attempt}",
                ],
                worktree,
            )
        head = program_orchestrator.run_command(["git", "rev-parse", "HEAD"], worktree)
        if program_orchestrator.run_command(
            ["git", "status", "--porcelain"], worktree
        ):
            raise SupervisorError(f"{repository_id}: worktree is not clean after commit")
        return head != vector["head_sha"], head

    def _run_repository_gates(
        self,
        change_id: str,
        repository_id: str,
        state: dict[str, Any],
    ) -> str:
        evidence, path = run_repository_gates.generate(
            self.engine, change_id, repository_id
        )
        self.engine.record_repository_result(
            change_id, repository_id, evidence["decision"], path
        )
        self._append_event(
            change_id,
            state,
            "REPOSITORY_GATES_RECORDED",
            {
                "repository_id": repository_id,
                "decision": evidence["decision"],
                "evidence_sha256": program_orchestrator.file_digest(path),
            },
        )
        self._write_state(change_id, state)
        return evidence["decision"]

    def _handle_worker_run(
        self,
        change_id: str,
        state: dict[str, Any],
        worker_run: dict[str, Any],
    ) -> tuple[str, str]:
        self._record_worker_run(change_id, state, worker_run)
        repository_id = worker_run["repository_id"]
        exit_code = worker_run["exit_code"]
        if exit_code == self.worker["blocked_spec_exit_code"]:
            return "BLOCKED", f"{repository_id}: worker reported BLOCKED_SPEC"
        if exit_code == self.worker["inconclusive_exit_code"]:
            return (
                "INCONCLUSIVE",
                f"{repository_id}: worker reported INCONCLUSIVE",
            )
        if worker_run["outcome"] != "EXITED" or exit_code != 0:
            if worker_run["attempt"] >= int(
                self.worker["maximum_worker_attempts"]
            ):
                return "FAIL", f"{repository_id}: worker attempt limit reached"
            return "RETRY", f"{repository_id}: worker process did not succeed"
        try:
            changed, _head = self._commit_worker_changes(
                change_id, repository_id, worker_run["attempt"]
            )
        except SupervisorError as exc:
            if "protected policy paths" in str(exc):
                return "POLICY", str(exc)
            raise
        if not changed:
            return "NO_CHANGE", f"{repository_id}: worker produced no committed change"
        decision = self._run_repository_gates(change_id, repository_id, state)
        return (
            f"GATE_{decision}",
            f"{repository_id}: repository gates returned {decision}",
        )

    def record_specialist_usage(
        self,
        change_id: str,
        task_id: str,
        kind: str,
        resource_id: str,
    ) -> dict[str, Any]:
        """Record explicit application of one leased specialist resource."""
        if self.worker.get("mode", "command") != "vscode-chat":
            raise SupervisorError(
                "specialist usage receipts are available only in vscode-chat mode"
            )
        if kind == "agents":
            raise SupervisorError(
                "an agent receipt cannot prove subagent execution; use copilot-sdk mode"
            )
        with self._lock(change_id, recover_stale_lock=False):
            state = self.read_state(change_id)
            active = state.get("active_task")
            if not isinstance(active, dict) or active.get("task_id") != task_id:
                raise SupervisorError("task ID is not the active VS Code lease")
            task_path = (
                self.engine.run_dir(change_id)
                / program_orchestrator.safe_relative_path(
                    active.get("task_path"), "active task path"
                )
            )
            if (
                not task_path.is_file()
                or program_orchestrator.file_digest(task_path)
                != active.get("task_sha256")
            ):
                raise SupervisorError("active VS Code task artifact digest mismatch")
            task = program_orchestrator.read_json(task_path)
            requirement = next(
                (
                    item
                    for item in task.get("specialist_usage_requirements", [])
                    if item.get("kind") == kind and item.get("id") == resource_id
                ),
                None,
            )
            if not isinstance(requirement, dict):
                raise SupervisorError(
                    "specialist resource is not required by the active lease"
                )
            receipts = active.setdefault("specialist_usage_receipts", [])
            if any(
                item.get("kind") == kind and item.get("id") == resource_id
                for item in receipts
            ):
                raise SupervisorError("specialist usage was already recorded")
            receipt = {
                "kind": kind,
                "id": resource_id,
                "sha256": requirement.get("sha256"),
                "role": requirement.get("role"),
                "purpose": requirement.get("purpose"),
                "recorded_at": utc_now(),
            }
            receipts.append(receipt)
            required_keys = {
                (item.get("kind"), item.get("id"))
                for item in task.get("specialist_usage_requirements", [])
            }
            receipt_keys = {
                (item.get("kind"), item.get("id")) for item in receipts
            }
            for item in active.get("visible_work_plan", []):
                if item.get("id") == "expert-review":
                    item["status"] = (
                        "completed" if required_keys <= receipt_keys else "in_progress"
                    )
                    for specialist in item.get("specialists", []):
                        if (
                            specialist.get("kind") == kind
                            and specialist.get("id") == resource_id
                        ):
                            specialist["status"] = "completed"
            self._append_event(
                change_id,
                state,
                "SPECIALIST_RESOURCE_APPLIED",
                {"task_id": task_id, **receipt},
            )
            self._write_state(change_id, state)
            return active

    def complete_vscode_task(
        self,
        change_id: str,
        task_id: str,
        outcome: str,
        summary: str,
        *,
        continue_run: bool = True,
    ) -> dict[str, Any]:
        """Accept an IDE worker handoff only after checking the leased workspace."""
        if self.worker.get("mode", "command") != "vscode-chat":
            raise SupervisorError("complete-task is available only in vscode-chat mode")
        exit_codes = {
            "ready": 0,
            "failed": 1,
            "blocked-spec": int(self.worker["blocked_spec_exit_code"]),
            "inconclusive": int(self.worker["inconclusive_exit_code"]),
        }
        if outcome not in exit_codes:
            raise SupervisorError("outcome must be ready, failed, blocked-spec, or inconclusive")
        with self._lock(change_id, recover_stale_lock=False):
            state = self.read_state(change_id)
            active = state.get("active_task")
            if not isinstance(active, dict) or active.get("task_id") != task_id:
                raise SupervisorError("task ID is not the active VS Code lease")
            task_path = self.engine.run_dir(change_id) / program_orchestrator.safe_relative_path(
                active.get("task_path"), "active task path"
            )
            if not task_path.is_file():
                raise SupervisorError("active VS Code task artifact is missing")
            if program_orchestrator.file_digest(task_path) != active.get("task_sha256"):
                raise SupervisorError("active VS Code task artifact digest mismatch")
            task = program_orchestrator.read_json(task_path)
            requirements = task.get("specialist_usage_requirements", [])
            receipts = active.get("specialist_usage_receipts", [])
            required_keys = {
                (item.get("kind"), item.get("id")) for item in requirements
            }
            receipt_keys = {
                (item.get("kind"), item.get("id")) for item in receipts
            }
            missing_usage = sorted(required_keys - receipt_keys)
            if outcome == "ready" and missing_usage:
                rendered = ", ".join(
                    f"{kind}:{resource_id}" for kind, resource_id in missing_usage
                )
                raise SupervisorError(
                    "required GTS/local specialist usage receipts are missing: "
                    + rendered
                )
            program_state = self.engine.read_state(change_id)
            repository_id = str(active["repository_id"])
            vector = program_state.get("commit_vector", {}).get(repository_id)
            if not isinstance(vector, dict):
                raise SupervisorError("leased repository is no longer in the commit vector")
            current_packet = program_state.get("repository_extensions", {}).get(
                repository_id, {}
            )
            invariant_pairs = {
                "plan digest": (task.get("plan_digest"), program_state.get("plan_digest")),
                "requirements digest": (
                    task.get("requirements_digest"),
                    program_state.get("requirements_digest"),
                ),
                "extension digest": (
                    task.get("repository_extension_digest"),
                    current_packet.get("digest"),
                ),
            }
            for label, (leased, current) in invariant_pairs.items():
                if not leased or leased != current:
                    raise SupervisorError(f"leased {label} is stale or invalid")
            worktree = Path(vector["worktree"])
            current_head = program_orchestrator.run_command(
                ["git", "rev-parse", "HEAD"], worktree
            )
            if current_head != task.get("start_head_sha"):
                raise SupervisorError(
                    "VS Code worker committed or changed HEAD; only the supervisor may commit"
                )
            directory = task_path.parent
            log_path = directory / "worker.log"
            safe_summary = run_repository_gates.redact(summary.strip())
            log_path.write_text(
                (safe_summary or f"VS Code Chat reported {outcome}") + "\n",
                encoding="utf-8",
            )
            usage_path = directory / "specialist-usage.json"
            usage_artifact = {
                "schema_version": "1.0",
                "change_id": change_id,
                "task_id": task_id,
                "repository_id": repository_id,
                "requirements": requirements,
                "receipts": receipts,
            }
            usage_artifact["digest"] = program_orchestrator.digest(usage_artifact)
            program_orchestrator.atomic_json(usage_path, usage_artifact)
            worker_run = {
                "repository_id": repository_id,
                "attempt": int(task["attempt"]),
                "phase": task["phase"],
                "outcome": "EXITED",
                "exit_code": exit_codes[outcome],
                "started_at": task["created_at"],
                "duration_seconds": 0,
                "argv": ["vscode-chat", task_id],
                "prompt_path": task["prompt_path"],
                "prompt_sha256": task["prompt_sha256"],
                "log_path": self._relative_artifact(change_id, log_path),
                "log_sha256": program_orchestrator.file_digest(log_path),
                "task_id": task_id,
                "task_sha256": active["task_sha256"],
                "specialist_usage_path": self._relative_artifact(
                    change_id, usage_path
                ),
                "specialist_usage_sha256": program_orchestrator.file_digest(
                    usage_path
                ),
                "specialist_usage_count": len(receipts),
            }
            result, reason = self._handle_worker_run(change_id, state, worker_run)
            state["active_task"] = None
            self._append_event(
                change_id,
                state,
                "VSCODE_TASK_ACCEPTED",
                {
                    "task_id": task_id,
                    "repository_id": repository_id,
                    "reported_outcome": outcome,
                    "verified_result": result,
                    "specialist_usage_count": len(receipts),
                },
            )
            transitions = {
                "POLICY": "PAUSED_POLICY_MUTATION",
                "FAIL": "FAILED",
                "BLOCKED": "BLOCKED_SPEC",
                "INCONCLUSIVE": "PAUSED_INCONCLUSIVE",
                "NO_CHANGE": "PAUSED_WORKER",
                "GATE_INCONCLUSIVE": "PAUSED_INCONCLUSIVE",
                "GATE_BLOCKED_SPEC": "BLOCKED_SPEC",
            }
            status = transitions.get(result, "RUNNING")
            self._transition(change_id, state, status, reason)
        if continue_run and status == "RUNNING":
            return self.run(change_id)
        return self.read_state(change_id)

    def _pending_wave(self, program_state: dict[str, Any]) -> list[str]:
        for wave in program_state["execution_waves"]:
            pending = [
                repository_id
                for repository_id in wave
                if program_state.get("repository_results", {})
                .get(repository_id, {})
                .get("decision")
                != "PASS"
            ]
            if pending:
                return pending
        return []

    def _process_wave(
        self,
        change_id: str,
        state: dict[str, Any],
        repositories: list[str],
        phase: str,
        capacity: int | None,
    ) -> tuple[int, tuple[str, str] | None]:
        selected = repositories if capacity is None else repositories[:capacity]
        program_state = self.engine.read_state(change_id)
        implementation = [
            repository_id
            for repository_id in selected
            if program_state["commit_vector"][repository_id]["mode"]
            == "implementation"
        ]
        validation = [
            repository_id
            for repository_id in selected
            if repository_id not in implementation
        ]
        worker_runs: dict[str, dict[str, Any]] = {}
        if implementation and self.worker.get("mode", "command") == "vscode-chat":
            repository_id = implementation[0]
            task = self._prepare_vscode_task(
                change_id, state, repository_id, phase
            )
            return 0, (
                "PAUSED_VSCODE_WORKER",
                f"VS Code Chat task {task['task_id']} is ready for {repository_id}; "
                f"read {task['prompt_path']} and complete the leased worktree",
            )
        maximum_parallel = min(
            int(self.engine.manifest["maximum_parallel_repositories"]),
            max(1, len(implementation)),
        )
        if implementation:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=maximum_parallel
            ) as executor:
                futures = {}
                for repository_id in implementation:
                    attempt = int(
                        state["worker_attempts"].get(repository_id, 0)
                    ) + 1
                    futures[repository_id] = executor.submit(
                        self._invoke_worker,
                        change_id,
                        repository_id,
                        attempt,
                        phase,
                    )
                for repository_id in implementation:
                    worker_runs[repository_id] = futures[repository_id].result()
        pause: tuple[str, str] | None = None
        for repository_id in selected:
            if repository_id in worker_runs:
                outcome, reason = self._handle_worker_run(
                    change_id, state, worker_runs[repository_id]
                )
                if outcome == "POLICY":
                    pause = ("PAUSED_POLICY_MUTATION", reason)
                elif outcome == "FAIL":
                    pause = ("FAILED", reason)
                elif outcome == "BLOCKED":
                    pause = ("BLOCKED_SPEC", reason)
                elif outcome == "INCONCLUSIVE":
                    pause = ("PAUSED_INCONCLUSIVE", reason)
                elif outcome == "NO_CHANGE":
                    pause = ("PAUSED_WORKER", reason)
                elif outcome == "GATE_INCONCLUSIVE":
                    pause = ("PAUSED_INCONCLUSIVE", reason)
                elif outcome == "GATE_BLOCKED_SPEC":
                    pause = ("BLOCKED_SPEC", reason)
            else:
                decision = self._run_repository_gates(
                    change_id, repository_id, state
                )
                if decision == "INCONCLUSIVE":
                    pause = (
                        "PAUSED_INCONCLUSIVE",
                        f"{repository_id}: validation gates are inconclusive",
                    )
                elif decision == "BLOCKED_SPEC":
                    pause = (
                        "BLOCKED_SPEC",
                        f"{repository_id}: validation reported blocked specification",
                    )
            if self.engine.read_state(change_id)["state"] == "FAIL":
                pause = ("FAILED", "program remediation limit reached")
        return len(selected), pause

    def _run_integration(
        self, change_id: str, state: dict[str, Any]
    ) -> tuple[str, str]:
        evidence, path = run_integration_gates.generate(self.engine, change_id)
        self.engine.record_integration_result(change_id, path)
        self._append_event(
            change_id,
            state,
            "INTEGRATION_GATES_RECORDED",
            {
                "decision": evidence["decision"],
                "evidence_sha256": program_orchestrator.file_digest(path),
            },
        )
        self._write_state(change_id, state)
        return evidence["decision"], str(path)

    def run(
        self,
        change_id: str,
        *,
        allow_clone: bool = False,
        max_steps: int | None = None,
        retry_inconclusive: bool = False,
        recover_stale_lock: bool = False,
    ) -> dict[str, Any]:
        errors = self.adoption_errors()
        if errors:
            raise SupervisorError(
                "agent execution is not adopted:\n- " + "\n- ".join(errors)
            )
        if max_steps is not None and max_steps < 1:
            raise SupervisorError("max_steps must be positive")
        with self._lock(change_id, recover_stale_lock):
            state = self.read_state(change_id)
            self._transition(
                change_id, state, "RUNNING", "supervisor execution started"
            )
            steps = 0
            while True:
                program_state = self.engine.read_state(change_id)
                program_status = program_state["state"]
                state["last_program_state"] = program_status
                self._write_task_board(change_id, state, program_state)
                self._write_state(change_id, state)
                if program_status == "AWAITING_CLARIFICATION":
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_CLARIFICATION",
                        "show the visible intake questions and wait for user answers",
                    )
                if program_status == "INTAKE":
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_PLANNING",
                        "requirements and a digest-bound plan must be prepared",
                    )
                if program_status == "AWAITING_PLAN_REVIEW":
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_PLAN_REVIEW",
                        "the exact plan digest requires independent review and revision cycles",
                    )
                if program_status == "AWAITING_PLAN_APPROVAL":
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_HUMAN_GATE_1",
                        "waiting for independent approval of the exact plan digest",
                    )
                if program_status == "PLAN_APPROVED":
                    self.engine.prepare_workspaces(
                        change_id, execute=True, allow_clone=allow_clone
                    )
                    self._append_event(
                        change_id,
                        state,
                        "WORKSPACES_PREPARED",
                        {"allow_clone": allow_clone},
                    )
                    self._write_state(change_id, state)
                    steps += 1
                elif program_status in {"WORKSPACES_READY", "EXECUTING"}:
                    pending = self._pending_wave(program_state)
                    if pending:
                        remaining = (
                            None if max_steps is None else max_steps - steps
                        )
                        if remaining is not None and remaining <= 0:
                            return self._transition(
                                change_id,
                                state,
                                "PAUSED_STEP_BUDGET",
                                "supervisor step budget reached",
                            )
                        used, pause = self._process_wave(
                            change_id,
                            state,
                            pending,
                            "implementation",
                            remaining,
                        )
                        steps += used
                        if pause:
                            return self._transition(
                                change_id, state, pause[0], pause[1]
                            )
                    else:
                        integration_result = program_state.get(
                            "integration_result"
                        )
                        if (
                            isinstance(integration_result, dict)
                            and integration_result.get("decision") == "INCONCLUSIVE"
                            and not retry_inconclusive
                        ):
                            return self._transition(
                                change_id,
                                state,
                                "PAUSED_INCONCLUSIVE",
                                "integration evidence is inconclusive; fix the "
                                "missing harness or context before retrying",
                            )
                        cycle = int(
                            program_state.get("integration_remediation_cycles", 0)
                        )
                        if (
                            isinstance(integration_result, dict)
                            and integration_result.get("decision") == "FAIL"
                            and cycle
                            > int(state.get("integration_remediated_cycle", 0))
                        ):
                            repositories = list(
                                program_state["implementation_scope"]
                            )
                            remaining = (
                                None if max_steps is None else max_steps - steps
                            )
                            used, pause = self._process_wave(
                                change_id,
                                state,
                                repositories,
                                "integration-remediation",
                                remaining,
                            )
                            steps += used
                            state["integration_remediated_cycle"] = cycle
                            self._write_state(change_id, state)
                            if pause:
                                return self._transition(
                                    change_id, state, pause[0], pause[1]
                                )
                        else:
                            if max_steps is not None and steps >= max_steps:
                                return self._transition(
                                    change_id,
                                    state,
                                    "PAUSED_STEP_BUDGET",
                                    "supervisor step budget reached",
                                )
                            decision, _path = self._run_integration(
                                change_id, state
                            )
                            steps += 1
                            if decision == "INCONCLUSIVE":
                                latest = self.engine.read_state(change_id)
                                state["inconclusive_integration_cycle"] = int(
                                    latest.get("integration_remediation_cycles", 0)
                                )
                                self._write_state(change_id, state)
                                return self._transition(
                                    change_id,
                                    state,
                                    "PAUSED_INCONCLUSIVE",
                                    "integration gates are inconclusive",
                                )
                            if decision == "BLOCKED_SPEC":
                                return self._transition(
                                    change_id,
                                    state,
                                    "BLOCKED_SPEC",
                                    "integration reported a blocked specification",
                                )
                elif program_status == "INTEGRATION_PASSED":
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_PLAN_CLOSURE",
                        "waiting for distinct independent verification and "
                        "adversarial-review evidence",
                    )
                elif program_status == "PLAN_CLOSED":
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_PR_CREATION",
                        "plan is closed; PR creation requires authorized external write",
                    )
                elif program_status in {"PR_SET_READY", "AWAITING_PR_APPROVAL"}:
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_HUMAN_GATE_2",
                        "waiting for exact-head PR checks and independent approval",
                    )
                elif program_status == "PR_APPROVED":
                    return self._transition(
                        change_id,
                        state,
                        "COMPLETED",
                        "program change reached independently approved PR state",
                    )
                elif program_status == "BLOCKED_SPEC":
                    return self._transition(
                        change_id,
                        state,
                        "BLOCKED_SPEC",
                        "program state reports unresolved specification ambiguity",
                    )
                elif program_status in {"FAIL", "INCONCLUSIVE"}:
                    return self._transition(
                        change_id,
                        state,
                        "FAILED",
                        f"program reached terminal state {program_status}",
                    )
                else:
                    raise SupervisorError(
                        f"unsupported program state: {program_status}"
                    )
                if max_steps is not None and steps >= max_steps:
                    return self._transition(
                        change_id,
                        state,
                        "PAUSED_STEP_BUDGET",
                        "supervisor step budget reached",
                    )

    def verify(self, change_id: str) -> list[str]:
        errors = self.engine.verify(change_id)
        state = self.read_state(change_id)
        previous = "0" * 64
        count = 0
        try:
            lines = self.events_path(change_id).read_text(
                encoding="utf-8"
            ).splitlines()
        except OSError as exc:
            return errors + [f"cannot read supervisor event log: {exc}"]
        for count, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"supervisor event {count}: invalid JSON: {exc}")
                continue
            claimed = event.pop("hash", None)
            if event.get("sequence") != count:
                errors.append(f"supervisor event {count}: invalid sequence")
            if event.get("previous_hash") != previous:
                errors.append(f"supervisor event {count}: previous hash mismatch")
            calculated = program_orchestrator.digest(event)
            if claimed != calculated:
                errors.append(f"supervisor event {count}: hash mismatch")
            previous = claimed or calculated
        if count != state.get("event_count"):
            errors.append("supervisor event_count does not match event log")
        if previous != state.get("last_event_hash"):
            errors.append("supervisor last_event_hash does not match event log")
        for index, worker_run in enumerate(state.get("worker_runs", []), 1):
            for label in ("prompt", "log"):
                relative = worker_run.get(f"{label}_path")
                expected = worker_run.get(f"{label}_sha256")
                try:
                    path = self.engine.run_dir(change_id) / program_orchestrator.safe_relative_path(
                        relative, f"worker run {index} {label}_path"
                    )
                except program_orchestrator.ProgramError as exc:
                    errors.append(str(exc))
                    continue
                if not path.is_file():
                    errors.append(f"worker run {index}: {label} artifact is missing")
                elif program_orchestrator.file_digest(path) != expected:
                    errors.append(
                        f"worker run {index}: {label} artifact digest mismatch"
                    )
            for label in (
                "extension_packet",
                "copilot_runtime_result",
                "copilot_runtime_events",
                "copilot_runtime_task_board",
            ):
                relative = worker_run.get(f"{label}_path")
                if relative is None:
                    continue
                expected = worker_run.get(f"{label}_sha256")
                try:
                    path = self.engine.run_dir(
                        change_id
                    ) / program_orchestrator.safe_relative_path(
                        relative, f"worker run {index} {label}_path"
                    )
                except program_orchestrator.ProgramError as exc:
                    errors.append(str(exc))
                    continue
                if not path.is_file():
                    errors.append(f"worker run {index}: {label} artifact is missing")
                elif program_orchestrator.file_digest(path) != expected:
                    errors.append(
                        f"worker run {index}: {label} artifact digest mismatch"
                    )
            if worker_run.get("task_id"):
                relative = worker_run.get("prompt_path")
                task_path = (
                    self.engine.run_dir(change_id)
                    / program_orchestrator.safe_relative_path(
                        relative, f"worker run {index} prompt_path"
                    )
                ).parent / "task.json"
                if not task_path.is_file():
                    errors.append(f"worker run {index}: task artifact is missing")
                elif program_orchestrator.file_digest(task_path) != worker_run.get(
                    "task_sha256"
                ):
                    errors.append(f"worker run {index}: task artifact digest mismatch")
                usage_relative = worker_run.get("specialist_usage_path")
                try:
                    usage_path = (
                        self.engine.run_dir(change_id)
                        / program_orchestrator.safe_relative_path(
                            usage_relative,
                            f"worker run {index} specialist_usage_path",
                        )
                    )
                except program_orchestrator.ProgramError as exc:
                    errors.append(str(exc))
                else:
                    if not usage_path.is_file():
                        errors.append(
                            f"worker run {index}: specialist usage artifact is missing"
                        )
                    elif program_orchestrator.file_digest(
                        usage_path
                    ) != worker_run.get("specialist_usage_sha256"):
                        errors.append(
                            f"worker run {index}: specialist usage artifact "
                            "digest mismatch"
                        )
        active = state.get("active_task")
        if isinstance(active, dict):
            try:
                task_path = self.engine.run_dir(change_id) / program_orchestrator.safe_relative_path(
                    active.get("task_path"), "active task path"
                )
                if not task_path.is_file():
                    errors.append("active VS Code task artifact is missing")
                elif program_orchestrator.file_digest(task_path) != active.get(
                    "task_sha256"
                ):
                    errors.append("active VS Code task artifact digest mismatch")
            except program_orchestrator.ProgramError as exc:
                errors.append(str(exc))
        implementation_plan = state.get("implementation_plan_path")
        if implementation_plan:
            try:
                plan_path = self.engine.run_dir(change_id) / program_orchestrator.safe_relative_path(
                    implementation_plan, "implementation_plan_path"
                )
                if not plan_path.is_file():
                    errors.append("supervisor implementation plan is missing")
                elif program_orchestrator.file_digest(plan_path) != state.get(
                    "implementation_plan_sha256"
                ):
                    errors.append("supervisor implementation plan digest mismatch")
            except program_orchestrator.ProgramError as exc:
                errors.append(str(exc))
        return errors


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=repository_root())
    result.add_argument("--manifest", type=Path)
    result.add_argument("--runtime-config", type=Path)
    subparsers = result.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--adoption", action="store_true")
    run = subparsers.add_parser("run")
    run.add_argument("--change-id", required=True)
    run.add_argument("--allow-clone", action="store_true")
    run.add_argument("--max-steps", type=int)
    run.add_argument("--retry-inconclusive", action="store_true")
    run.add_argument("--recover-stale-lock", action="store_true")
    run.add_argument("--watch", action="store_true")
    run.add_argument("--poll-seconds", type=int, default=10)
    status = subparsers.add_parser("status")
    status.add_argument("--change-id", required=True)
    task = subparsers.add_parser("task")
    task.add_argument("--change-id", required=True)
    usage = subparsers.add_parser("record-specialist-usage")
    usage.add_argument("--change-id", required=True)
    usage.add_argument("--task-id", required=True)
    usage.add_argument("--kind", choices=["skills", "agents"], required=True)
    usage.add_argument("--resource-id", required=True)
    complete = subparsers.add_parser("complete-task")
    complete.add_argument("--change-id", required=True)
    complete.add_argument("--task-id", required=True)
    complete.add_argument(
        "--outcome",
        choices=["ready", "failed", "blocked-spec", "inconclusive"],
        required=True,
    )
    complete.add_argument("--summary", default="")
    complete.add_argument("--no-continue", action="store_true")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--change-id", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    runtime_config = args.runtime_config
    if manifest and not manifest.is_absolute():
        manifest = root / manifest
    if runtime_config and not runtime_config.is_absolute():
        runtime_config = root / runtime_config
    try:
        supervisor = AgentSupervisor(root, manifest, runtime_config)
        if args.command == "validate":
            errors = (
                supervisor.adoption_errors()
                if args.adoption
                else validate_runtime_config(supervisor.config)
            )
            if errors:
                print("AGENT_RUNTIME_INVALID")
                for error in errors:
                    print(f"- {error}")
                return 1
            print("AGENT_RUNTIME_VALID")
            return 0
        if args.command == "status":
            output = supervisor.read_state(args.change_id)
        elif args.command == "task":
            state = supervisor.read_state(args.change_id)
            output = state.get("active_task")
            if not isinstance(output, dict):
                raise SupervisorError("no active VS Code task lease")
        elif args.command == "record-specialist-usage":
            output = supervisor.record_specialist_usage(
                args.change_id,
                args.task_id,
                args.kind,
                args.resource_id,
            )
        elif args.command == "complete-task":
            output = supervisor.complete_vscode_task(
                args.change_id,
                args.task_id,
                args.outcome,
                args.summary,
                continue_run=not args.no_continue,
            )
        elif args.command == "verify":
            errors = supervisor.verify(args.change_id)
            if errors:
                print("SUPERVISOR_RUN_INVALID")
                for error in errors:
                    print(f"- {error}")
                return 1
            print("SUPERVISOR_RUN_VALID")
            return 0
        elif args.command == "run":
            if not 1 <= args.poll_seconds <= 60:
                raise SupervisorError("poll-seconds must be between 1 and 60")
            while True:
                output = supervisor.run(
                    args.change_id,
                    allow_clone=args.allow_clone,
                    max_steps=args.max_steps,
                    retry_inconclusive=args.retry_inconclusive,
                    recover_stale_lock=args.recover_stale_lock,
                )
                print(json.dumps(output, indent=2))
                if not args.watch or output["status"] not in WAITABLE_STATES:
                    break
                time.sleep(args.poll_seconds)
        else:
            raise SupervisorError(f"unsupported command: {args.command}")
        if args.command not in {"run", "complete-task"}:
            print(json.dumps(output, indent=2))
        elif args.command == "complete-task":
            print(json.dumps(output, indent=2))
        output_status = output.get("status") if isinstance(output, dict) else None
        return 0 if output_status not in {
            "FAILED",
            "BLOCKED_SPEC",
            "PAUSED_INCONCLUSIVE",
            "PAUSED_WORKER",
            "PAUSED_POLICY_MUTATION",
        } else 2
    except (SupervisorError, program_orchestrator.ProgramError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
