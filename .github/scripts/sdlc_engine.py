#!/usr/bin/env python3
"""Durable, fail-closed SDLC state-machine runtime.

The engine controls process state and evidence integrity. It does not decide
whether business logic is correct and it does not replace GitHub branch or
environment protection.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
ARTIFACT_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*\.json$")
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
DECISIONS = {"PASS", "FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"}
BLOCKING_STATES = {"BLOCKED_SPEC", "FAIL", "INCONCLUSIVE"}
EXCLUDED_PARTS = {".git", "__pycache__"}


class SdlcError(RuntimeError):
    """Expected fail-closed error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SdlcError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SdlcError(f"{path} must contain a JSON object")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_within(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise SdlcError(f"path escapes repository root: {candidate}") from exc
    return resolved


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    commit = result.stdout.strip().lower()
    if result.returncode != 0 or not COMMIT_SHA.fullmatch(commit):
        raise SdlcError("cannot determine an exact 40-character Git commit")
    return commit


def require_clean_worktree(root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise SdlcError("cannot inspect Git worktree status")
    if result.stdout.strip():
        raise SdlcError("worktree must be clean before starting or binding a commit")


@contextlib.contextmanager
def run_lock(run_dir: Path, stale_seconds: int = 300) -> Iterator[None]:
    lock = run_dir / ".lock"
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError as exc:
        age = time.time() - lock.stat().st_mtime
        if age <= stale_seconds:
            raise SdlcError(f"run is locked: {run_dir.name}") from exc
        try:
            lock.rmdir()
            lock.mkdir()
        except OSError as retry_exc:
            raise SdlcError(f"stale run lock could not be recovered: {run_dir.name}") from retry_exc
    try:
        (lock / "owner.json").write_text(
            json.dumps({"pid": os.getpid(), "created_at": utc_now()}), encoding="utf-8"
        )
        yield
    finally:
        (lock / "owner.json").unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            lock.rmdir()


class Engine:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.sdlc = self.root / ".github" / "sdlc"
        self.runs = self.sdlc / "runs"
        self.policy = load_json(self.sdlc / "policies" / "state-machine.json")
        self.risk_policy = load_json(self.sdlc / "policies" / "risk-tiers.json")
        self.artifact_contracts = load_json(
            self.sdlc / "policies" / "artifact-contracts.json"
        ).get("contracts", {})
        project_path = self.sdlc / "project.json"
        self.project = load_json(project_path) if project_path.is_file() else {}

    def run_dir(self, change_id: str) -> Path:
        if not CHANGE_ID.fullmatch(change_id):
            raise SdlcError("change ID must use 1-80 letters, digits, dots, underscores, or hyphens")
        return self.runs / change_id

    def state_path(self, change_id: str) -> Path:
        return self.run_dir(change_id) / "run.json"

    def read_state(self, change_id: str) -> dict[str, Any]:
        path = self.state_path(change_id)
        if not path.is_file():
            raise SdlcError(f"run does not exist: {change_id}")
        return load_json(path)

    def save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = utc_now()
        atomic_json(self.state_path(state["change_id"]), state)

    def append_event(
        self, state: dict[str, Any], kind: str, actor: str, detail: dict[str, Any]
    ) -> dict[str, Any]:
        path = self.run_dir(state["change_id"]) / "events.jsonl"
        previous = state.get("event_head", "0" * 64)
        event = {
            "sequence": state.get("event_count", 0) + 1,
            "occurred_at": utc_now(),
            "kind": kind,
            "actor": actor,
            "state": state["state"],
            "target_commit": state["target_commit"],
            "detail": detail,
            "previous_hash": previous,
        }
        event["hash"] = digest_bytes(canonical(event))
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        state["event_count"] = event["sequence"]
        state["event_head"] = event["hash"]
        return event

    def transition(self, state_name: str) -> dict[str, Any] | None:
        matches = [item for item in self.policy["transitions"] if item["from"] == state_name]
        if len(matches) > 1:
            raise SdlcError(f"policy has ambiguous transitions from {state_name}")
        return matches[0] if matches else None

    def start(self, change_id: str, request: str, risk_tier: str) -> dict[str, Any]:
        if not request.strip():
            raise SdlcError("request must not be empty")
        if risk_tier not in self.risk_policy.get("tiers", {}):
            raise SdlcError(f"unknown risk tier: {risk_tier}")
        run_dir = self.run_dir(change_id)
        with run_lock(run_dir):
            if self.state_path(change_id).exists():
                raise SdlcError(f"run already exists: {change_id}")
            require_clean_worktree(self.root)
            now = utc_now()
            state = {
                "schema_version": "1.0",
                "change_id": change_id,
                "request": request.strip(),
                "risk_tier": risk_tier,
                "state": self.policy["initial_state"],
                "target_commit": git_commit(self.root),
                "remediation_cycles": 0,
                "maximum_remediation_cycles": self.policy["rules"][
                    "maximum_remediation_cycles"
                ],
                "artifacts": {},
                "event_count": 0,
                "event_head": "0" * 64,
                "started_at": now,
                "updated_at": now,
            }
            self.append_event(
                state,
                "RUN_STARTED",
                "sdlc-orchestrator",
                {"request": request, "risk_tier": risk_tier},
            )
            self.save_state(state)
            return state

    def _artifact_producer(self, name: str) -> str | None:
        return self.policy.get("artifact_producers", {}).get(name)

    def payload_contract_errors(
        self, name: str, payload: dict[str, Any], target_commit: str
    ) -> list[str]:
        contract = self.artifact_contracts.get(name)
        if not isinstance(contract, dict):
            return []
        errors: list[str] = []
        for field in contract.get("required", []):
            if field not in payload:
                errors.append(f"{name} payload is missing {field}")
        for field, expected in contract.get("equals", {}).items():
            if payload.get(field) != expected:
                errors.append(f"{name} payload field {field} must equal {expected!r}")
        for field in contract.get("non_empty", []):
            value = payload.get(field)
            if value is None or value == "" or value == [] or value == {}:
                errors.append(f"{name} payload field {field} must be non-empty")
        for field, minimum in contract.get("minimum", {}).items():
            value = payload.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < minimum:
                errors.append(f"{name} payload field {field} must be at least {minimum}")
        for field, allowed in contract.get("allowed", {}).items():
            if payload.get(field) not in allowed:
                errors.append(f"{name} payload field {field} must be one of {allowed}")
        for field, pattern in contract.get("patterns", {}).items():
            if not re.fullmatch(pattern, str(payload.get(field, ""))):
                errors.append(f"{name} payload field {field} has invalid format")
        operations = self.project.get("operations", {})
        context = {
            "target_commit": target_commit,
            "production_environment": operations.get(
                "production_environment", "production"
            ),
            "preproduction_environment": operations.get(
                "preproduction_environment", "preproduction"
            ),
        }
        for field, context_name in contract.get("matches_context", {}).items():
            if payload.get(field) != context.get(context_name):
                errors.append(f"{name} payload field {field} does not match {context_name}")
        return errors

    def record_artifact(
        self,
        change_id: str,
        name: str,
        producer: str,
        decision: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not ARTIFACT_NAME.fullmatch(name):
            raise SdlcError("artifact name must be a lowercase JSON filename without path separators")
        if decision not in DECISIONS:
            raise SdlcError(f"decision must be one of {sorted(DECISIONS)}")
        expected = self._artifact_producer(name)
        if expected and producer != expected:
            raise SdlcError(f"{name} must be produced by {expected}, not {producer}")
        run_dir = self.run_dir(change_id)
        with run_lock(run_dir):
            state = self.read_state(change_id)
            self.ensure_integrity(change_id)
            if state["state"] in self.policy["terminal_states"]:
                raise SdlcError(f"terminal run cannot accept evidence: {state['state']}")
            if decision == "PASS":
                contract_errors = self.payload_contract_errors(
                    name, payload, state["target_commit"]
                )
                if contract_errors:
                    raise SdlcError("; ".join(contract_errors))
            envelope = {
                "schema_version": "1.0",
                "change_id": change_id,
                "artifact_name": name,
                "producer": producer,
                "decision": decision,
                "commit_sha": state["target_commit"],
                "created_at": utc_now(),
                "payload_sha256": digest_bytes(canonical(payload)),
                "payload": payload,
            }
            envelope_digest = digest_bytes(canonical(envelope))
            revision = state.get("event_count", 0) + 1
            relative = Path("artifacts") / name.removesuffix(".json") / (
                f"{revision:04d}-{envelope_digest[:16]}.json"
            )
            path = run_dir / relative
            atomic_json(path, envelope)
            state["artifacts"][name] = {
                "path": relative.as_posix(),
                "sha256": digest_bytes(path.read_bytes()),
                "decision": decision,
                "producer": producer,
                "commit_sha": state["target_commit"],
            }
            self.append_event(
                state,
                "ARTIFACT_RECORDED",
                producer,
                {"name": name, **state["artifacts"][name]},
            )
            self.save_state(state)
            return envelope

    def bind_commit(self, change_id: str, actor: str, commit: str | None) -> dict[str, Any]:
        run_dir = self.run_dir(change_id)
        with run_lock(run_dir):
            state = self.read_state(change_id)
            self.ensure_integrity(change_id)
            if actor != "implementation":
                raise SdlcError("only the implementation agent may bind an implementation commit")
            if state["state"] not in {"DESIGN_READY", "IMPLEMENTED"}:
                raise SdlcError("commit binding is allowed only during implementation or remediation")
            require_clean_worktree(self.root)
            chosen = (commit or git_commit(self.root)).lower()
            if not COMMIT_SHA.fullmatch(chosen):
                raise SdlcError("commit must be an exact lowercase 40-character SHA")
            if commit and chosen != git_commit(self.root):
                raise SdlcError("bound commit must equal the repository HEAD")
            prior = state["target_commit"]
            state["target_commit"] = chosen
            self.append_event(
                state, "COMMIT_BOUND", actor, {"prior_commit": prior, "new_commit": chosen}
            )
            self.save_state(state)
            return state

    def advance(self, change_id: str, actor: str) -> dict[str, Any]:
        run_dir = self.run_dir(change_id)
        with run_lock(run_dir):
            state = self.read_state(change_id)
            self.ensure_integrity(change_id)
            transition = self.transition(state["state"])
            if transition is None:
                raise SdlcError(f"no forward transition exists from {state['state']}")
            if actor != transition["owner"]:
                raise SdlcError(f"transition is owned by {transition['owner']}, not {actor}")
            failures: list[str] = []
            evidence: dict[str, str] = {}
            for name in transition["required_artifacts"]:
                metadata = state["artifacts"].get(name)
                if not metadata:
                    failures.append(f"missing artifact {name}")
                    continue
                path = ensure_within(run_dir, run_dir / metadata["path"])
                if not path.is_file():
                    failures.append(f"artifact file missing: {name}")
                    continue
                actual = digest_bytes(path.read_bytes())
                if actual != metadata["sha256"]:
                    failures.append(f"artifact digest mismatch: {name}")
                    continue
                envelope = load_json(path)
                if envelope.get("decision") != "PASS":
                    failures.append(f"artifact is not PASS: {name}")
                if envelope.get("commit_sha") != state["target_commit"]:
                    failures.append(f"artifact is stale or for another commit: {name}")
                if envelope.get("payload_sha256") != digest_bytes(
                    canonical(envelope.get("payload"))
                ):
                    failures.append(f"payload digest mismatch: {name}")
                failures.extend(
                    self.payload_contract_errors(
                        name,
                        envelope.get("payload", {}),
                        state["target_commit"],
                    )
                )
                evidence[name] = actual
            if failures:
                raise SdlcError("; ".join(failures))
            previous = state["state"]
            state["state"] = transition["to"]
            self.append_event(
                state,
                "STATE_ADVANCED",
                actor,
                {"from": previous, "to": state["state"], "evidence": evidence},
            )
            if state["state"] in self.policy["terminal_states"]:
                state["completed_at"] = utc_now()
            self.save_state(state)
            return state

    def failure(self, change_id: str, actor: str, reason: str) -> dict[str, Any]:
        run_dir = self.run_dir(change_id)
        with run_lock(run_dir):
            state = self.read_state(change_id)
            self.ensure_integrity(change_id)
            transition = self.transition(state["state"])
            if not transition or actor != transition["owner"]:
                expected = transition["owner"] if transition else "none"
                raise SdlcError(f"failure at {state['state']} must be reported by {expected}")
            state["remediation_cycles"] += 1
            if state["remediation_cycles"] >= state["maximum_remediation_cycles"]:
                prior = state["state"]
                state["state"] = "FAIL"
                state["completed_at"] = utc_now()
                self.append_event(
                    state,
                    "REMEDIATION_EXHAUSTED",
                    actor,
                    {"from": prior, "reason": reason, "cycles": state["remediation_cycles"]},
                )
            else:
                prior = state["state"]
                states = [item["from"] for item in self.policy["transitions"]]
                implementation_index = states.index("DESIGN_READY")
                prior_index = states.index(prior) if prior in states else 0
                reset = "DESIGN_READY" if prior_index >= implementation_index else prior
                invalidated: list[str] = []
                if reset == "DESIGN_READY":
                    downstream = self.policy.get("implementation_and_later_artifacts", [])
                    for name in downstream:
                        if state["artifacts"].pop(name, None):
                            invalidated.append(name)
                state["state"] = reset
                self.append_event(
                    state,
                    "REMEDIATION_REQUIRED",
                    actor,
                    {
                        "from": prior,
                        "reset_to": reset,
                        "reason": reason,
                        "cycle": state["remediation_cycles"],
                        "invalidated_artifacts": invalidated,
                    },
                )
            self.save_state(state)
            return state

    def terminate(self, change_id: str, actor: str, terminal_state: str, reason: str) -> dict[str, Any]:
        if terminal_state not in BLOCKING_STATES:
            raise SdlcError(f"terminal state must be one of {sorted(BLOCKING_STATES)}")
        run_dir = self.run_dir(change_id)
        with run_lock(run_dir):
            state = self.read_state(change_id)
            self.ensure_integrity(change_id)
            if state["state"] in self.policy["terminal_states"]:
                raise SdlcError(f"run is already terminal: {state['state']}")
            allowed = self.policy.get("termination_actors", {}).get(terminal_state, [])
            if actor not in allowed:
                raise SdlcError(f"{actor} cannot terminate a run as {terminal_state}")
            prior = state["state"]
            state["state"] = terminal_state
            state["completed_at"] = utc_now()
            self.append_event(
                state, "RUN_TERMINATED", actor, {"from": prior, "reason": reason}
            )
            self.save_state(state)
            return state

    def rollback(self, change_id: str, actor: str, reason: str) -> dict[str, Any]:
        run_dir = self.run_dir(change_id)
        with run_lock(run_dir):
            state = self.read_state(change_id)
            self.ensure_integrity(change_id)
            if actor not in {"deployment-controller", "operations-validator"}:
                raise SdlcError("rollback must be recorded by deployment-controller or operations-validator")
            if state["state"] not in {"PRODUCTION_APPROVED", "PRODUCTION_DEPLOYED"}:
                raise SdlcError("rollback is only valid after production approval or deployment")
            metadata = state["artifacts"].get("rollback-execution.json")
            if not metadata or metadata.get("decision") != "PASS":
                raise SdlcError("PASS rollback-execution.json evidence is required")
            prior = state["state"]
            state["state"] = "ROLLED_BACK"
            state["completed_at"] = utc_now()
            self.append_event(
                state, "PRODUCTION_ROLLED_BACK", actor, {"from": prior, "reason": reason}
            )
            self.save_state(state)
            return state

    def _source_files(self, location: Path) -> list[Path]:
        if location.is_file():
            return [location]
        if not location.is_dir():
            return []
        if location.resolve() == self.root:
            result = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=self.root,
                check=False,
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise SdlcError("cannot enumerate tracked repository files")
            tracked = [
                ensure_within(self.root, self.root / item.decode("utf-8"))
                for item in result.stdout.split(b"\0")
                if item
            ]
            return sorted(
                [item for item in tracked if item.is_file()],
                key=lambda item: item.as_posix(),
            )
        files: list[Path] = []
        for path in location.rglob("*"):
            relative = path.relative_to(self.root)
            control_output = relative.parts[:3] in {
                (".github", "sdlc", "runs"),
                (".github", "sdlc", "evidence"),
            }
            if (
                not path.is_file()
                or any(part in EXCLUDED_PARTS for part in relative.parts)
                or control_output
            ):
                continue
            files.append(path)
        return sorted(files, key=lambda item: item.as_posix())

    def snapshot_sources(self, change_id: str) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "INTAKE":
            raise SdlcError("sources can be snapshotted only in INTAKE")
        sources = load_json(self.sdlc / "sources.json").get("sources", [])
        if not isinstance(sources, list) or not sources:
            raise SdlcError("sources.json must contain at least one source")
        manifest: list[dict[str, Any]] = []
        errors: list[str] = []
        for item in sources:
            if not isinstance(item, dict):
                errors.append("source entry is not an object")
                continue
            source_id = str(item.get("id", "missing-id"))
            location_text = str(item.get("location", ""))
            entry: dict[str, Any] = {
                key: item.get(key)
                for key in ("id", "type", "authority", "version", "owner", "required")
            }
            required_metadata = ("id", "type", "authority", "version", "owner")
            incomplete = [
                key
                for key in required_metadata
                if not str(item.get(key, "")).strip() or "REPLACE_" in str(item.get(key, ""))
            ]
            if incomplete:
                entry["status"] = "MISSING_METADATA"
                if item.get("required"):
                    errors.append(
                        f"{source_id}: required source metadata is incomplete: {', '.join(incomplete)}"
                    )
            elif "REPLACE_" in location_text or not location_text:
                entry["status"] = "MISSING"
                if item.get("required"):
                    errors.append(f"{source_id}: required source location is not configured")
            elif location_text.startswith(("https://", "http://")):
                declared = str(item.get("sha256", "")).lower()
                materialized_text = str(item.get("materialized_path", ""))
                if re.fullmatch(r"[0-9a-f]{64}", declared) and materialized_text:
                    materialized = ensure_within(self.root, self.root / materialized_text)
                    files = self._source_files(materialized)
                    inventory = [
                        {
                            "path": path.relative_to(self.root).as_posix(),
                            "size": path.stat().st_size,
                            "sha256": digest_bytes(path.read_bytes()),
                        }
                        for path in files
                    ]
                    actual = (
                        inventory[0]["sha256"]
                        if len(inventory) == 1
                        else digest_bytes(canonical(inventory))
                    )
                    if files and actual == declared:
                        entry.update(
                            {
                                "status": "SNAPSHOTTED_REMOTE",
                                "location": location_text,
                                "materialized_path": materialized_text,
                                "content_sha256": actual,
                                "files": inventory,
                            }
                        )
                    else:
                        entry["status"] = "DIGEST_MISMATCH"
                        if item.get("required"):
                            errors.append(
                                f"{source_id}: materialized remote source is missing or has wrong digest"
                            )
                elif re.fullmatch(r"[0-9a-f]{64}", declared):
                    entry.update(
                        {
                            "status": "UNMATERIALIZED_REMOTE",
                            "location": location_text,
                            "content_sha256": declared,
                        }
                    )
                    if item.get("required"):
                        errors.append(
                            f"{source_id}: pinned remote source must be materialized locally"
                        )
                else:
                    entry["status"] = "UNVERIFIED_REMOTE"
                    if item.get("required"):
                        errors.append(f"{source_id}: remote source requires a pinned sha256")
            else:
                location = ensure_within(self.root, self.root / location_text)
                files = self._source_files(location)
                if not files:
                    entry["status"] = "MISSING"
                    if item.get("required"):
                        errors.append(f"{source_id}: no readable source files at {location_text}")
                else:
                    inventory = []
                    for path in files:
                        inventory.append(
                            {
                                "path": path.relative_to(self.root).as_posix(),
                                "size": path.stat().st_size,
                                "sha256": digest_bytes(path.read_bytes()),
                            }
                        )
                    entry.update(
                        {
                            "status": "SNAPSHOTTED",
                            "location": location_text,
                            "file_count": len(inventory),
                            "content_sha256": digest_bytes(canonical(inventory)),
                            "files": inventory,
                        }
                    )
            manifest.append(entry)
        decision = "INCONCLUSIVE" if errors else "PASS"
        self.record_artifact(
            change_id,
            "source-snapshot.json",
            "spec-ingestion",
            decision,
            {"errors": errors, "source_count": len(manifest), "sources": manifest},
        )
        return {"decision": decision, "errors": errors, "sources": manifest}

    def verify(self, change_id: str) -> list[str]:
        state = self.read_state(change_id)
        errors: list[str] = []
        events_path = self.run_dir(change_id) / "events.jsonl"
        previous = "0" * 64
        count = 0
        parsed_events: list[dict[str, Any]] = []
        recorded_artifacts: dict[str, dict[str, Any]] = {}
        try:
            lines = events_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return [f"cannot read event log: {exc}"]
        for index, line in enumerate(lines, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"event {index} is invalid JSON")
                continue
            supplied = event.get("hash")
            unsigned = {key: value for key, value in event.items() if key != "hash"}
            expected = digest_bytes(canonical(unsigned))
            if supplied != expected:
                errors.append(f"event {index} hash mismatch")
            if event.get("previous_hash") != previous:
                errors.append(f"event {index} previous hash mismatch")
            if event.get("sequence") != index:
                errors.append(f"event {index} sequence mismatch")
            previous = supplied or ""
            count = index
            parsed_events.append(event)
            if event.get("kind") == "ARTIFACT_RECORDED":
                detail = event.get("detail", {})
                if isinstance(detail, dict) and isinstance(detail.get("name"), str):
                    recorded_artifacts[detail["name"]] = {
                        key: detail.get(key)
                        for key in ("path", "sha256", "decision", "producer", "commit_sha")
                    }
        if state.get("event_count") != count or state.get("event_head") != previous:
            errors.append("state event head/count does not match event log")
        if parsed_events:
            first = parsed_events[0]
            last = parsed_events[-1]
            if first.get("kind") != "RUN_STARTED":
                errors.append("first event is not RUN_STARTED")
            if first.get("detail", {}).get("request") != state.get("request"):
                errors.append("state request does not match start event")
            if first.get("detail", {}).get("risk_tier") != state.get("risk_tier"):
                errors.append("state risk tier does not match start event")
            if last.get("state") != state.get("state"):
                errors.append("state does not match last event")
            if last.get("target_commit") != state.get("target_commit"):
                errors.append("target commit does not match last event")
        if state.get("maximum_remediation_cycles") != self.policy["rules"].get(
            "maximum_remediation_cycles"
        ):
            errors.append("maximum remediation cycles differs from policy")
        observed_cycles = 0
        for event in parsed_events:
            detail = event.get("detail", {})
            if isinstance(detail, dict):
                value = detail.get("cycle", detail.get("cycles", 0))
                if isinstance(value, int):
                    observed_cycles = max(observed_cycles, value)
        if state.get("remediation_cycles") != observed_cycles:
            errors.append("remediation cycle count does not match event log")
        for name, metadata in state.get("artifacts", {}).items():
            if recorded_artifacts.get(name) != metadata:
                errors.append(f"artifact state does not match event log: {name}")
            try:
                path = ensure_within(self.run_dir(change_id), self.run_dir(change_id) / metadata["path"])
                content = path.read_bytes()
                if digest_bytes(content) != metadata["sha256"]:
                    errors.append(f"artifact digest mismatch: {name}")
                    continue
                envelope = json.loads(content)
                for field, expected_value in {
                    "change_id": change_id,
                    "artifact_name": name,
                    "producer": metadata["producer"],
                    "decision": metadata["decision"],
                    "commit_sha": metadata["commit_sha"],
                }.items():
                    if envelope.get(field) != expected_value:
                        errors.append(f"artifact envelope {field} mismatch: {name}")
                if envelope.get("payload_sha256") != digest_bytes(
                    canonical(envelope.get("payload"))
                ):
                    errors.append(f"artifact payload digest mismatch: {name}")
                if envelope.get("decision") == "PASS":
                    errors.extend(
                        self.payload_contract_errors(
                            name,
                            envelope.get("payload", {}),
                            state["target_commit"],
                        )
                    )
            except (OSError, KeyError, SdlcError) as exc:
                errors.append(f"cannot verify artifact {name}: {exc}")
        return errors

    def ensure_integrity(self, change_id: str) -> None:
        errors = self.verify(change_id)
        if errors:
            raise SdlcError("run integrity verification failed: " + "; ".join(errors))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    commands = result.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("--change-id", required=True)
    start.add_argument("--request", required=True)
    start.add_argument("--risk-tier", required=True)
    for name in ("status", "snapshot-sources", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--change-id", required=True)
    record = commands.add_parser("record-artifact")
    record.add_argument("--change-id", required=True)
    record.add_argument("--name", required=True)
    record.add_argument("--producer", required=True)
    record.add_argument("--decision", required=True)
    record.add_argument("--input", type=Path, required=True)
    advance = commands.add_parser("advance")
    advance.add_argument("--change-id", required=True)
    advance.add_argument("--actor", required=True)
    bind = commands.add_parser("bind-commit")
    bind.add_argument("--change-id", required=True)
    bind.add_argument("--actor", required=True)
    bind.add_argument("--commit")
    failure = commands.add_parser("failure")
    failure.add_argument("--change-id", required=True)
    failure.add_argument("--actor", required=True)
    failure.add_argument("--reason", required=True)
    terminate = commands.add_parser("terminate")
    terminate.add_argument("--change-id", required=True)
    terminate.add_argument("--actor", required=True)
    terminate.add_argument("--state", required=True)
    terminate.add_argument("--reason", required=True)
    rollback = commands.add_parser("rollback")
    rollback.add_argument("--change-id", required=True)
    rollback.add_argument("--actor", required=True)
    rollback.add_argument("--reason", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        engine = Engine(args.root)
        if args.command == "start":
            output: Any = engine.start(args.change_id, args.request, args.risk_tier)
        elif args.command == "status":
            output = engine.read_state(args.change_id)
        elif args.command == "snapshot-sources":
            output = engine.snapshot_sources(args.change_id)
        elif args.command == "record-artifact":
            input_path = ensure_within(engine.root, engine.root / args.input)
            output = engine.record_artifact(
                args.change_id,
                args.name,
                args.producer,
                args.decision,
                load_json(input_path),
            )
        elif args.command == "advance":
            output = engine.advance(args.change_id, args.actor)
        elif args.command == "bind-commit":
            output = engine.bind_commit(args.change_id, args.actor, args.commit)
        elif args.command == "failure":
            output = engine.failure(args.change_id, args.actor, args.reason)
        elif args.command == "terminate":
            output = engine.terminate(args.change_id, args.actor, args.state, args.reason)
        elif args.command == "rollback":
            output = engine.rollback(args.change_id, args.actor, args.reason)
        else:
            errors = engine.verify(args.change_id)
            output = {"decision": "PASS" if not errors else "FAIL", "errors": errors}
            print(json.dumps(output, indent=2, sort_keys=True))
            return 0 if not errors else 1
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (SdlcError, OSError, KeyError, ValueError) as exc:
        print(json.dumps({"decision": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
