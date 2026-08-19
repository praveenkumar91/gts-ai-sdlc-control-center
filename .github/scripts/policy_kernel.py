#!/usr/bin/env python3
"""Deterministic policy and evidence kernel for the agent-authored SDLC graph.

The kernel deliberately does not interpret requirements, select repositories,
design architecture, write product code, or decide whether tests are adequate.
Those decisions belong to the GTS agents and human gates. This module validates
declared graph structure, bounded transitions, evidence digests, and approvals.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
VALID_OUTCOMES = {"PASS", "FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"}
TERMINAL_STATUSES = {"PASS", "FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"}
NODE_TYPES = {
    "REQUIREMENTS",
    "IMPACT",
    "PLAN",
    "PLAN_REVIEW",
    "HUMAN_GATE_1",
    "CHECKOUT",
    "IMPLEMENT",
    "VERIFY",
    "INTEGRATE",
    "CLOSURE",
    "PR_DRAFT",
    "HUMAN_GATE_2",
}
AFTER_GATE_1_TYPES = {
    "CHECKOUT",
    "IMPLEMENT",
    "VERIFY",
    "INTEGRATE",
    "CLOSURE",
    "PR_DRAFT",
    "HUMAN_GATE_2",
}
GATE_TO_TYPE = {"gate-1": "HUMAN_GATE_1", "gate-2": "HUMAN_GATE_2"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DIGEST_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


class PolicyError(RuntimeError):
    """A deterministic policy check failed."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyError(f"Required JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PolicyError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PolicyError(f"Expected a JSON object in {path}")
    return value


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


@contextmanager
def exclusive_file_lock(path: Path, timeout_seconds: float = 30.0):
    """Serialize kernel state transitions across processes on Windows/POSIX."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    started = time.monotonic()
    locked = False
    try:
        while not locked:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except (OSError, BlockingIOError):
                if time.monotonic() - started >= timeout_seconds:
                    raise PolicyError(f"Timed out waiting for policy state lock: {path}")
                time.sleep(0.05)
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def ensure_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise PolicyError(f"{label} must match {ID_PATTERN.pattern}")
    return value


def ensure_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not DIGEST_PATTERN.fullmatch(value):
        raise PolicyError(f"{label} must be a sha256:<64 lowercase hex> digest")
    return value


def ensure_string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise PolicyError(f"{label} must be an array of non-empty strings")
    if not allow_empty and not value:
        raise PolicyError(f"{label} must not be empty")
    if len(value) != len(set(value)):
        raise PolicyError(f"{label} must contain unique values")
    return value


class PolicyKernel:
    def __init__(self, root: Path | str | None = None) -> None:
        default_root = Path(__file__).resolve().parents[2]
        self.root = Path(root or default_root).resolve()
        self.config_path = self.root / ".github" / "sdlc" / "program.json"
        self.config = load_json(self.config_path)
        self._validate_program_config(self.config)
        self.run_root = self._root_relative(self.config["runRoot"], "runRoot")
        self.audit_root = self._root_relative(self.config["auditRoot"], "auditRoot")

    def _root_relative(self, raw: str, label: str) -> Path:
        path = Path(raw)
        if path.is_absolute():
            raise PolicyError(f"{label} must be relative to the control repository")
        resolved = (self.root / path).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise PolicyError(f"{label} escapes the control repository: {raw}") from exc
        return resolved

    @staticmethod
    def _validate_program_config(config: dict[str, Any]) -> None:
        required = {
            "schemaVersion",
            "programId",
            "catalogGlobs",
            "repositoryLocalDescriptor",
            "workspaceSearchRoots",
            "worktreeRoot",
            "runRoot",
            "auditRoot",
            "defaults",
            "protectedBranches",
            "automationIdentities",
        }
        missing = sorted(required - config.keys())
        if missing:
            raise PolicyError(f"program.json missing fields: {', '.join(missing)}")
        if config["schemaVersion"] != SCHEMA_VERSION:
            raise PolicyError(f"Unsupported program schemaVersion: {config['schemaVersion']}")
        ensure_id(config["programId"], "programId")
        ensure_string_list(config["catalogGlobs"], "catalogGlobs", allow_empty=False)
        ensure_string_list(config["workspaceSearchRoots"], "workspaceSearchRoots", allow_empty=False)
        ensure_string_list(config["protectedBranches"], "protectedBranches", allow_empty=False)
        ensure_string_list(config["automationIdentities"], "automationIdentities")
        defaults = config["defaults"]
        if not isinstance(defaults, dict):
            raise PolicyError("defaults must be an object")
        numeric = {
            "maxCatalogRepositories": (1, 1000),
            "maxActiveRepositories": (1, 200),
            "maxParallelWorkers": (1, 64),
            "maxNodeAttempts": (1, 10),
            "maxPlanReviewCycles": (1, 10),
        }
        for key, (minimum, maximum) in numeric.items():
            value = defaults.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
                raise PolicyError(f"defaults.{key} must be an integer from {minimum} to {maximum}")
        if defaults.get("riskTier") not in {"low", "medium", "high", "critical"}:
            raise PolicyError("defaults.riskTier is invalid")
        if defaults.get("requireGate1") is not True or defaults.get("requireGate2") is not True:
            raise PolicyError("Both human gates must remain enabled")

    def catalog(self) -> dict[str, dict[str, Any]]:
        descriptors: dict[str, dict[str, Any]] = {}
        files: list[Path] = []
        for pattern in self.config["catalogGlobs"]:
            files.extend(path for path in self.root.glob(pattern) if path.is_file())
        for path in sorted(set(files)):
            descriptor = load_json(path)
            self._validate_repository_descriptor(descriptor, path)
            repository_id = descriptor["repositoryId"]
            if repository_id in descriptors:
                raise PolicyError(f"Duplicate repositoryId {repository_id}: {path}")
            descriptor = copy.deepcopy(descriptor)
            descriptor["_descriptorPath"] = str(path)
            descriptors[repository_id] = descriptor
        maximum = self.config["defaults"]["maxCatalogRepositories"]
        if len(descriptors) > maximum:
            raise PolicyError(f"Catalog has {len(descriptors)} repositories; maximum is {maximum}")
        for repository_id, descriptor in descriptors.items():
            for dependency in descriptor["dependencies"]:
                if dependency not in descriptors:
                    raise PolicyError(f"{repository_id} depends on unknown catalog repository {dependency}")
                if dependency == repository_id:
                    raise PolicyError(f"{repository_id} cannot depend on itself")
        return descriptors

    @staticmethod
    def _validate_repository_descriptor(descriptor: dict[str, Any], path: Path) -> None:
        required = {
            "schemaVersion",
            "repositoryId",
            "displayName",
            "system",
            "checkout",
            "ownership",
            "capabilities",
            "dependencies",
            "sharedResources",
            "customizations",
            "commands",
        }
        missing = sorted(required - descriptor.keys())
        if missing:
            raise PolicyError(f"{path} missing fields: {', '.join(missing)}")
        if descriptor["schemaVersion"] != SCHEMA_VERSION:
            raise PolicyError(f"Unsupported repository schemaVersion in {path}")
        ensure_id(descriptor["repositoryId"], f"{path}: repositoryId")
        if not isinstance(descriptor["displayName"], str) or not descriptor["displayName"]:
            raise PolicyError(f"{path}: displayName must not be empty")
        if not isinstance(descriptor["system"], str) or not descriptor["system"]:
            raise PolicyError(f"{path}: system must not be empty")
        checkout = descriptor["checkout"]
        if not isinstance(checkout, dict) or checkout.get("mode") not in {"existing-only", "existing-or-clone"}:
            raise PolicyError(f"{path}: checkout.mode is invalid")
        ensure_string_list(checkout.get("localCandidates"), f"{path}: checkout.localCandidates")
        if not isinstance(checkout.get("defaultBranch"), str) or not checkout["defaultBranch"]:
            raise PolicyError(f"{path}: checkout.defaultBranch must not be empty")
        for key in ("ownership", "capabilities", "customizations", "commands"):
            if not isinstance(descriptor[key], dict):
                raise PolicyError(f"{path}: {key} must be an object")
        ensure_string_list(descriptor["ownership"].get("components"), f"{path}: ownership.components")
        ensure_string_list(descriptor["ownership"].get("paths"), f"{path}: ownership.paths")
        for key in ("provides", "consumes", "contractsProduced", "contractsConsumed"):
            ensure_string_list(descriptor["capabilities"].get(key), f"{path}: capabilities.{key}")
        if not isinstance(descriptor["capabilities"].get("gui"), bool):
            raise PolicyError(f"{path}: capabilities.gui must be boolean")
        ensure_string_list(descriptor["dependencies"], f"{path}: dependencies")
        ensure_string_list(descriptor["sharedResources"], f"{path}: sharedResources")
        for key in ("instructions", "agents", "skills"):
            ensure_string_list(descriptor["customizations"].get(key), f"{path}: customizations.{key}")
        for key in ("bootstrap", "unit", "integration", "lint", "build", "security"):
            ensure_string_list(descriptor["commands"].get(key), f"{path}: commands.{key}")

    def validate(self) -> dict[str, Any]:
        catalog = self.catalog()
        schema_dir = self.root / ".github" / "sdlc" / "schemas"
        schemas = sorted(schema_dir.glob("*.schema.json"))
        for schema in schemas:
            load_json(schema)
        customization = self._validate_customizations()
        return {
            "status": "PASS",
            "programId": self.config["programId"],
            "catalogRepositories": len(catalog),
            "schemas": [path.name for path in schemas],
            **customization,
        }

    def digest_artifact(self, path: Path | str) -> dict[str, Any]:
        resolved = self._resolve_evidence_path(path)
        try:
            display_path = str(resolved.relative_to(self.root)).replace("\\", "/")
        except ValueError:
            display_path = str(resolved)
        return {"status": "PASS", "path": display_path, "sha256": digest_file(resolved), "size": resolved.stat().st_size}

    @staticmethod
    def _frontmatter(path: Path) -> str:
        text = path.read_text(encoding="utf-8").lstrip("\ufeff")
        if not text.startswith("---\n") and not text.startswith("---\r\n"):
            raise PolicyError(f"Missing YAML frontmatter in {path}")
        match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", text, re.DOTALL)
        if not match:
            raise PolicyError(f"Unterminated YAML frontmatter in {path}")
        return match.group(1)

    @staticmethod
    def _frontmatter_scalar(frontmatter: str, key: str, path: Path) -> str:
        match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
        if not match:
            raise PolicyError(f"Missing frontmatter field {key} in {path}")
        return match.group(1).strip().strip("\"'")

    def _validate_customizations(self) -> dict[str, Any]:
        agent_files = sorted((self.root / ".github" / "agents").glob("*.agent.md"))
        agents: dict[str, Path] = {}
        references: list[tuple[Path, str]] = []
        for path in agent_files:
            frontmatter = self._frontmatter(path)
            name = self._frontmatter_scalar(frontmatter, "name", path)
            ensure_id(name, f"{path}: name")
            if name in agents:
                raise PolicyError(f"Duplicate custom agent name {name}: {agents[name]} and {path}")
            agents[name] = path
            reference_match = re.search(r"(?m)^agents:\s*\[(.*?)\]\s*$", frontmatter)
            if reference_match:
                raw_references = [item.strip().strip("\"'") for item in reference_match.group(1).split(",")]
                references.extend((path, item) for item in raw_references if item and item != "*")
        for path, reference in references:
            if reference not in agents:
                raise PolicyError(f"{path} references unknown custom agent: {reference}")

        skill_files = sorted((self.root / ".agents" / "skills").glob("**/SKILL.md"))
        skills: dict[str, Path] = {}
        for path in skill_files:
            frontmatter = self._frontmatter(path)
            name = self._frontmatter_scalar(frontmatter, "name", path)
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
                raise PolicyError(f"Invalid Agent Skill name {name} in {path}")
            if name != path.parent.name:
                raise PolicyError(f"Agent Skill name {name} must match directory {path.parent.name}")
            if name in skills:
                raise PolicyError(f"Duplicate Agent Skill name {name}: {skills[name]} and {path}")
            skills[name] = path

        hook_files = sorted((self.root / ".github" / "hooks").glob("*.json"))
        for path in hook_files:
            hook_config = load_json(path)
            hooks = hook_config.get("hooks")
            if not isinstance(hooks, dict):
                raise PolicyError(f"{path} must contain a hooks object")
            valid_events = {
                "SessionStart",
                "UserPromptSubmit",
                "PreToolUse",
                "PostToolUse",
                "PreCompact",
                "SubagentStart",
                "SubagentStop",
                "Stop",
            }
            for event, commands in hooks.items():
                if event not in valid_events:
                    raise PolicyError(f"{path} contains unsupported hook event {event}")
                if not isinstance(commands, list) or not commands:
                    raise PolicyError(f"{path} hook {event} must contain commands")
                for command in commands:
                    if not isinstance(command, dict) or command.get("type") != "command":
                        raise PolicyError(f"{path} hook {event} entries must use type=command")
                    if not any(isinstance(command.get(key), str) and command[key] for key in ("command", "windows", "linux", "osx")):
                        raise PolicyError(f"{path} hook {event} has no command")

        for path in (
            self.root / ".vscode" / "settings.json",
            self.root / ".github" / "GTS-AI-SDLC.code-workspace",
        ):
            if path.exists():
                load_json(path)
        return {
            "customAgents": len(agents),
            "agentSkills": len(skills),
            "hookFiles": len(hook_files),
        }

    def _run_dir(self, change_id: str) -> Path:
        ensure_id(change_id, "changeId")
        return self.run_root / change_id

    def _load_run(self, change_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        run_dir = self._run_dir(change_id)
        manifest = load_json(run_dir / "manifest.json")
        state = load_json(run_dir / "state.json")
        if manifest.get("changeId") != change_id or state.get("changeId") != change_id:
            raise PolicyError("Run changeId does not match its directory")
        return run_dir, manifest, state

    def _existing_run_dir(self, change_id: str) -> Path:
        run_dir = self._run_dir(change_id)
        if not run_dir.is_dir():
            raise PolicyError(f"Run does not exist: {change_id}")
        return run_dir

    def init_run(self, change_id: str, request: str, requester: str, risk_tier: str) -> dict[str, Any]:
        ensure_id(change_id, "changeId")
        if not request.strip():
            raise PolicyError("request must not be empty")
        if not requester.strip():
            raise PolicyError("requester must not be empty")
        if risk_tier not in {"low", "medium", "high", "critical"}:
            raise PolicyError("riskTier must be low, medium, high, or critical")
        run_dir = self._run_dir(change_id)
        if run_dir.exists():
            raise PolicyError(f"Run already exists: {change_id}")
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "evidence").mkdir()
        manifest = {
            "schemaVersion": SCHEMA_VERSION,
            "changeId": change_id,
            "programId": self.config["programId"],
            "request": request.strip(),
            "requestDigest": sha256_bytes(request.strip().encode("utf-8")),
            "requester": requester.strip(),
            "riskTier": risk_tier,
            "createdAt": utc_now(),
        }
        state = {
            "schemaVersion": SCHEMA_VERSION,
            "changeId": change_id,
            "graphRevision": 0,
            "graphDigest": None,
            "status": "INTAKE",
            "nodes": {},
            "approvals": {},
            "updatedAt": utc_now(),
        }
        atomic_write_json(run_dir / "manifest.json", manifest)
        atomic_write_json(run_dir / "state.json", state)
        self._append_event(run_dir, "run_initialized", {"manifestDigest": digest_json(manifest)})
        return {"status": "INITIALIZED", "changeId": change_id, "runDirectory": str(run_dir)}

    @staticmethod
    def _graph_without_digest(graph: dict[str, Any]) -> dict[str, Any]:
        value = copy.deepcopy(graph)
        value.pop("graphDigest", None)
        return value

    def validate_graph(self, graph: dict[str, Any], expected_change_id: str | None = None) -> dict[str, Any]:
        required = {
            "schemaVersion",
            "changeId",
            "graphRevision",
            "requirementsDigest",
            "impactDigest",
            "planDigest",
            "repositories",
            "nodes",
        }
        missing = sorted(required - graph.keys())
        if missing:
            raise PolicyError(f"Graph missing fields: {', '.join(missing)}")
        if graph["schemaVersion"] != SCHEMA_VERSION:
            raise PolicyError(f"Unsupported graph schemaVersion: {graph['schemaVersion']}")
        change_id = ensure_id(graph["changeId"], "graph.changeId")
        if expected_change_id and change_id != expected_change_id:
            raise PolicyError(f"Graph changeId {change_id} does not match run {expected_change_id}")
        if not isinstance(graph["graphRevision"], int) or isinstance(graph["graphRevision"], bool) or graph["graphRevision"] < 1:
            raise PolicyError("graphRevision must be a positive integer")
        for key in ("requirementsDigest", "impactDigest", "planDigest"):
            ensure_digest(graph[key], f"graph.{key}")

        catalog = self.catalog()
        repositories = graph["repositories"]
        if not isinstance(repositories, list) or not repositories:
            raise PolicyError("Graph repositories must be a non-empty array")
        repository_map: dict[str, dict[str, Any]] = {}
        valid_dispositions = {"IMPLEMENTATION", "VALIDATION_ONLY", "CONTEXT_ONLY", "NOT_IMPACTED"}
        for repository in repositories:
            if not isinstance(repository, dict):
                raise PolicyError("Each graph repository must be an object")
            repository_id = ensure_id(repository.get("repositoryId"), "graph repositoryId")
            if repository_id in repository_map:
                raise PolicyError(f"Duplicate graph repositoryId: {repository_id}")
            if repository_id not in catalog:
                raise PolicyError(f"Graph references unregistered repository: {repository_id}")
            disposition = repository.get("disposition")
            if disposition not in valid_dispositions:
                raise PolicyError(f"Invalid disposition for {repository_id}: {disposition}")
            base_revision = repository.get("baseRevision")
            if not isinstance(base_revision, str) or not base_revision.strip():
                raise PolicyError(f"{repository_id} must declare a baseRevision")
            if base_revision.lower() in {"head", "latest", "main", "master", "develop"}:
                raise PolicyError(f"{repository_id} baseRevision must be immutable, not {base_revision}")
            dependencies = ensure_string_list(repository.get("dependsOn"), f"{repository_id}.dependsOn")
            ensure_string_list(repository.get("sharedResources"), f"{repository_id}.sharedResources")
            if repository_id in dependencies:
                raise PolicyError(f"{repository_id} cannot depend on itself")
            if disposition == "IMPLEMENTATION" and not isinstance(repository.get("worktree"), str):
                raise PolicyError(f"{repository_id} implementation disposition requires a planned worktree")
            repository_map[repository_id] = repository
        for repository_id, repository in repository_map.items():
            for dependency in repository["dependsOn"]:
                if dependency not in repository_map:
                    raise PolicyError(f"{repository_id} depends on graph repository not present: {dependency}")
        missing_catalog_entries = sorted(set(catalog) - set(repository_map))
        if missing_catalog_entries:
            raise PolicyError(
                "Graph must classify every catalog repository; missing: "
                + ", ".join(missing_catalog_entries)
            )
        active_count = sum(1 for item in repositories if item["disposition"] != "NOT_IMPACTED")
        maximum_active = self.config["defaults"]["maxActiveRepositories"]
        if active_count > maximum_active:
            raise PolicyError(f"Graph has {active_count} active repositories; maximum is {maximum_active}")

        nodes = graph["nodes"]
        if not isinstance(nodes, list) or not nodes:
            raise PolicyError("Graph nodes must be a non-empty array")
        node_map: dict[str, dict[str, Any]] = {}
        maximum_attempts = self.config["defaults"]["maxNodeAttempts"]
        for node in nodes:
            if not isinstance(node, dict):
                raise PolicyError("Each graph node must be an object")
            node_id = ensure_id(node.get("id"), "graph node id")
            if node_id in node_map:
                raise PolicyError(f"Duplicate graph node id: {node_id}")
            node_type = node.get("type")
            if node_type not in NODE_TYPES:
                raise PolicyError(f"Invalid node type for {node_id}: {node_type}")
            depends_on = ensure_string_list(node.get("dependsOn"), f"{node_id}.dependsOn")
            if node_id in depends_on:
                raise PolicyError(f"{node_id} cannot depend on itself")
            task = node.get("task")
            if not isinstance(task, str) or not task.strip():
                raise PolicyError(f"{node_id}.task must not be empty")
            budget = node.get("attemptBudget")
            if not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= maximum_attempts:
                raise PolicyError(f"{node_id}.attemptBudget must be 1..{maximum_attempts}")
            ensure_string_list(node.get("evidenceTypes"), f"{node_id}.evidenceTypes", allow_empty=False)
            ensure_string_list(node.get("requirementIds"), f"{node_id}.requirementIds")
            ensure_string_list(node.get("planTaskIds"), f"{node_id}.planTaskIds")
            ensure_string_list(node.get("sharedResources", []), f"{node_id}.sharedResources")
            repository_id = node.get("repositoryId")
            if repository_id is not None:
                ensure_id(repository_id, f"{node_id}.repositoryId")
                if repository_id not in repository_map:
                    raise PolicyError(f"{node_id} references graph repository not present: {repository_id}")
                disposition = repository_map[repository_id]["disposition"]
                if disposition == "NOT_IMPACTED":
                    raise PolicyError(f"{node_id} cannot target NOT_IMPACTED repository {repository_id}")
                if node_type == "IMPLEMENT" and disposition != "IMPLEMENTATION":
                    raise PolicyError(f"IMPLEMENT node {node_id} requires IMPLEMENTATION disposition")
                if node_type == "CHECKOUT" and disposition != "IMPLEMENTATION":
                    raise PolicyError(f"CHECKOUT node {node_id} requires IMPLEMENTATION disposition")
                if node_type == "VERIFY" and disposition not in {"IMPLEMENTATION", "VALIDATION_ONLY"}:
                    raise PolicyError(f"VERIFY node {node_id} requires IMPLEMENTATION or VALIDATION_ONLY disposition")
            node_map[node_id] = node
        for node_id, node in node_map.items():
            for dependency in node["dependsOn"]:
                if dependency not in node_map:
                    raise PolicyError(f"{node_id} depends on unknown node {dependency}")

        order = self._topological_order(node_map)
        present_types = {node["type"] for node in nodes}
        missing_types = sorted(NODE_TYPES - present_types)
        if missing_types:
            raise PolicyError(f"Graph must represent all 13 stages; missing node types: {', '.join(missing_types)}")
        for gate_type in GATE_TO_TYPE.values():
            count = sum(1 for node in nodes if node["type"] == gate_type)
            if count != 1:
                raise PolicyError(f"Graph must contain exactly one {gate_type} node; found {count}")
        gate_1_id = next(node["id"] for node in nodes if node["type"] == "HUMAN_GATE_1")
        gate_2_id = next(node["id"] for node in nodes if node["type"] == "HUMAN_GATE_2")
        ancestor_cache: dict[str, set[str]] = {}

        def ancestors(node_id: str) -> set[str]:
            if node_id in ancestor_cache:
                return ancestor_cache[node_id]
            result: set[str] = set()
            stack = list(node_map[node_id]["dependsOn"])
            while stack:
                current = stack.pop()
                if current in result:
                    continue
                result.add(current)
                stack.extend(node_map[current]["dependsOn"])
            ancestor_cache[node_id] = result
            return result

        gate_1_ancestors = ancestors(gate_1_id)
        if not any(node_map[node_id]["type"] == "PLAN_REVIEW" for node_id in gate_1_ancestors):
            raise PolicyError("HUMAN_GATE_1 must depend on an independently reviewed plan")
        for node in nodes:
            if node["type"] in AFTER_GATE_1_TYPES and gate_1_id not in ancestors(node["id"]):
                raise PolicyError(f"{node['id']} must be downstream of HUMAN_GATE_1")
        gate_2_ancestors = ancestors(gate_2_id)
        if not any(node_map[node_id]["type"] == "CLOSURE" for node_id in gate_2_ancestors):
            raise PolicyError("HUMAN_GATE_2 must depend on CLOSURE")
        if not any(node_map[node_id]["type"] == "PR_DRAFT" for node_id in gate_2_ancestors):
            raise PolicyError("HUMAN_GATE_2 must depend on PR_DRAFT")

        for repository_id, repository in repository_map.items():
            types = {node["type"] for node in nodes if node.get("repositoryId") == repository_id}
            if repository["disposition"] == "IMPLEMENTATION":
                required_repo_types = {"CHECKOUT", "IMPLEMENT", "VERIFY", "PR_DRAFT"}
                if not required_repo_types.issubset(types):
                    missing = ", ".join(sorted(required_repo_types - types))
                    raise PolicyError(f"Implementation repository {repository_id} lacks nodes: {missing}")
            if repository["disposition"] == "VALIDATION_ONLY" and "VERIFY" not in types:
                raise PolicyError(f"Validation-only repository {repository_id} requires a VERIFY node")

        return {
            "changeId": change_id,
            "graphRevision": graph["graphRevision"],
            "graphDigest": digest_json(self._graph_without_digest(graph)),
            "repositories": len(repository_map),
            "activeRepositories": active_count,
            "nodes": len(node_map),
            "topologicalOrder": order,
        }

    @staticmethod
    def _topological_order(node_map: dict[str, dict[str, Any]]) -> list[str]:
        indegree = {node_id: 0 for node_id in node_map}
        followers: dict[str, list[str]] = {node_id: [] for node_id in node_map}
        for node_id, node in node_map.items():
            for dependency in node["dependsOn"]:
                indegree[node_id] += 1
                followers[dependency].append(node_id)
        ready = sorted(node_id for node_id, count in indegree.items() if count == 0)
        result: list[str] = []
        while ready:
            node_id = ready.pop(0)
            result.append(node_id)
            for follower in sorted(followers[node_id]):
                indegree[follower] -= 1
                if indegree[follower] == 0:
                    ready.append(follower)
                    ready.sort()
        if len(result) != len(node_map):
            cyclic = sorted(node_id for node_id, count in indegree.items() if count > 0)
            raise PolicyError(f"Graph contains a cycle involving: {', '.join(cyclic)}")
        return result

    def register_graph(self, change_id: str, graph_path: Path | str) -> dict[str, Any]:
        run_dir = self._existing_run_dir(change_id)
        with exclusive_file_lock(run_dir / ".kernel.lock"):
            return self._register_graph_unlocked(change_id, graph_path)

    def _register_graph_unlocked(self, change_id: str, graph_path: Path | str) -> dict[str, Any]:
        run_dir, manifest, state = self._load_run(change_id)
        source_path = self._resolve_evidence_path(graph_path)
        graph = load_json(source_path)
        validation = self.validate_graph(graph, expected_change_id=change_id)
        implementation_count = sum(
            1 for repository in graph["repositories"] if repository["disposition"] == "IMPLEMENTATION"
        )
        if manifest["riskTier"] in {"high", "critical"} or implementation_count > 1:
            review_node = next(node for node in graph["nodes"] if node["type"] == "PLAN_REVIEW")
            if len(review_node["evidenceTypes"]) < 2:
                raise PolicyError(
                    "High-risk or multi-repository graphs require at least two independent PLAN_REVIEW evidence types"
                )
        graph_digest = validation["graphDigest"]
        if state["graphDigest"] == graph_digest:
            return {"status": "UNCHANGED", **validation}
        if state["graphRevision"] and graph["graphRevision"] <= state["graphRevision"]:
            raise PolicyError(
                f"Revised graphRevision must be greater than {state['graphRevision']}"
            )
        graph = self._graph_without_digest(graph)
        graph["graphDigest"] = graph_digest
        nodes = {
            node["id"]: {
                "status": "PENDING",
                "attempts": 0,
                "lastOutcome": None,
                "actor": None,
                "evidence": [],
                "updatedAt": None,
            }
            for node in graph["nodes"]
        }
        event_type = "graph_revised" if state["graphDigest"] else "graph_registered"
        state.update(
            {
                "graphRevision": graph["graphRevision"],
                "graphDigest": graph_digest,
                "status": "ACTIVE",
                "nodes": nodes,
                "approvals": {},
                "updatedAt": utc_now(),
            }
        )
        atomic_write_json(run_dir / "graph.json", graph)
        atomic_write_json(run_dir / "state.json", state)
        self._append_event(
            run_dir,
            event_type,
            {
                "graphDigest": graph_digest,
                "graphRevision": graph["graphRevision"],
                "nodeIds": sorted(nodes),
                "sourceDigest": digest_file(source_path),
            },
        )
        return {"status": event_type.upper(), **validation}

    def _resolve_evidence_path(self, raw: Path | str) -> Path:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = self.root / path
        path = path.resolve()
        if not path.is_file():
            raise PolicyError(f"Evidence file does not exist: {path}")
        return path

    @staticmethod
    def _node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {node["id"]: node for node in graph["nodes"]}

    @staticmethod
    def _repository_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {repository["repositoryId"]: repository for repository in graph["repositories"]}

    @staticmethod
    def _dependencies_pass(node: dict[str, Any], state: dict[str, Any]) -> bool:
        return all(state["nodes"][dependency]["status"] == "PASS" for dependency in node["dependsOn"])

    @staticmethod
    def _derive_run_status(state: dict[str, Any]) -> str:
        statuses = [node["status"] for node in state["nodes"].values()]
        if statuses and all(status == "PASS" for status in statuses):
            return "PASS"
        if "FAIL" in statuses:
            return "FAIL"
        if "BLOCKED_SPEC" in statuses:
            return "BLOCKED_SPEC"
        if "INCONCLUSIVE" in statuses:
            return "INCONCLUSIVE"
        return "ACTIVE"

    def ready(self, change_id: str) -> dict[str, Any]:
        run_dir = self._existing_run_dir(change_id)
        with exclusive_file_lock(run_dir / ".kernel.lock"):
            return self._ready_unlocked(change_id)

    def _ready_unlocked(self, change_id: str) -> dict[str, Any]:
        run_dir, _manifest, state = self._load_run(change_id)
        graph = load_json(run_dir / "graph.json")
        node_map = self._node_map(graph)
        repository_map = self._repository_map(graph)
        ready_nodes: list[dict[str, Any]] = []
        awaiting_approval: list[dict[str, Any]] = []
        dependency_blocked: list[dict[str, Any]] = []
        for node in graph["nodes"]:
            node_state = state["nodes"][node["id"]]
            if node_state["status"] != "PENDING":
                continue
            failed_dependencies = [
                dependency
                for dependency in node["dependsOn"]
                if state["nodes"][dependency]["status"] in {"FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"}
            ]
            if failed_dependencies:
                dependency_blocked.append({"id": node["id"], "blockedBy": failed_dependencies})
                continue
            if not self._dependencies_pass(node, state):
                continue
            item = {
                "id": node["id"],
                "type": node["type"],
                "repositoryId": node.get("repositoryId"),
                "nextAttempt": node_state["attempts"] + 1,
                "attemptBudget": node["attemptBudget"],
                "task": node["task"],
            }
            if node["type"] in GATE_TO_TYPE.values():
                awaiting_approval.append(item)
            else:
                ready_nodes.append(item)

        selected: list[dict[str, Any]] = []
        held_resources: set[str] = set()
        maximum_parallel = self.config["defaults"]["maxParallelWorkers"]
        for item in ready_nodes:
            if len(selected) >= maximum_parallel:
                break
            node = node_map[item["id"]]
            resources = set(node.get("sharedResources", []))
            repository_id = node.get("repositoryId")
            if repository_id:
                resources.add(f"repository:{repository_id}")
                resources.update(repository_map[repository_id].get("sharedResources", []))
            if resources & held_resources:
                continue
            held_resources.update(resources)
            selected.append({**item, "exclusiveResources": sorted(resources)})

        return {
            "changeId": change_id,
            "graphDigest": state["graphDigest"],
            "runStatus": self._derive_run_status(state),
            "scheduledWave": selected,
            "readyNodes": ready_nodes,
            "awaitingHumanApproval": awaiting_approval,
            "dependencyBlocked": dependency_blocked,
            "completed": sorted(node_id for node_id, value in state["nodes"].items() if value["status"] == "PASS"),
        }

    def _evidence_records(self, evidence_paths: Iterable[Path | str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for raw in evidence_paths:
            path = self._resolve_evidence_path(raw)
            try:
                display_path = str(path.relative_to(self.root)).replace("\\", "/")
            except ValueError:
                display_path = str(path)
            records.append(
                {
                    "path": display_path,
                    "sha256": digest_file(path),
                    "size": path.stat().st_size,
                    "recordedAt": utc_now(),
                }
            )
        if not records:
            raise PolicyError("At least one evidence file is required")
        return records

    def record(
        self,
        change_id: str,
        node_id: str,
        outcome: str,
        actor: str,
        evidence_paths: Iterable[Path | str],
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(change_id)
        with exclusive_file_lock(run_dir / ".kernel.lock"):
            return self._record_unlocked(change_id, node_id, outcome, actor, evidence_paths)

    def _record_unlocked(
        self,
        change_id: str,
        node_id: str,
        outcome: str,
        actor: str,
        evidence_paths: Iterable[Path | str],
    ) -> dict[str, Any]:
        if outcome not in VALID_OUTCOMES:
            raise PolicyError(f"Invalid outcome: {outcome}")
        if not actor.strip():
            raise PolicyError("actor must not be empty")
        run_dir, _manifest, state = self._load_run(change_id)
        graph = load_json(run_dir / "graph.json")
        node_map = self._node_map(graph)
        if node_id not in node_map:
            raise PolicyError(f"Unknown node: {node_id}")
        node = node_map[node_id]
        if node["type"] in GATE_TO_TYPE.values():
            raise PolicyError("Human gates can only be completed with the approve command")
        node_state = state["nodes"][node_id]
        if node_state["status"] != "PENDING":
            raise PolicyError(f"Node {node_id} is not pending; status is {node_state['status']}")
        if not self._dependencies_pass(node, state):
            raise PolicyError(f"Node {node_id} is not ready; dependencies have not all passed")
        if node_state["attempts"] >= node["attemptBudget"]:
            raise PolicyError(f"Node {node_id} exhausted its attempt budget")
        evidence = self._evidence_records(evidence_paths)
        if node["type"] == "PLAN_REVIEW" and len(node["evidenceTypes"]) >= 2 and len(evidence) < 2:
            raise PolicyError("PLAN_REVIEW requires separate evidence artifacts for both independent review lanes")
        node_state["attempts"] += 1
        node_state["lastOutcome"] = outcome
        node_state["actor"] = actor.strip()
        node_state["evidence"] = evidence
        node_state["updatedAt"] = utc_now()
        if outcome == "PASS":
            node_state["status"] = "PASS"
        elif outcome == "FAIL" and node_state["attempts"] < node["attemptBudget"]:
            node_state["status"] = "PENDING"
        else:
            node_state["status"] = outcome
        state["status"] = self._derive_run_status(state)
        state["updatedAt"] = utc_now()
        atomic_write_json(run_dir / "state.json", state)
        self._append_event(
            run_dir,
            "node_recorded",
            {
                "graphDigest": state["graphDigest"],
                "nodeId": node_id,
                "nodeState": copy.deepcopy(node_state),
            },
        )
        return {
            "status": node_state["status"],
            "outcome": outcome,
            "node": node_id,
            "attempts": node_state["attempts"],
            "attemptBudget": node["attemptBudget"],
            "runStatus": state["status"],
        }

    def approve(self, change_id: str, approval_path: Path | str) -> dict[str, Any]:
        run_dir = self._existing_run_dir(change_id)
        with exclusive_file_lock(run_dir / ".kernel.lock"):
            return self._approve_unlocked(change_id, approval_path)

    def _approve_unlocked(self, change_id: str, approval_path: Path | str) -> dict[str, Any]:
        run_dir, _manifest, state = self._load_run(change_id)
        graph = load_json(run_dir / "graph.json")
        path = self._resolve_evidence_path(approval_path)
        approval = load_json(path)
        required = {
            "schemaVersion",
            "changeId",
            "gate",
            "graphDigest",
            "decision",
            "approver",
            "approvedAt",
            "statement",
            "evidenceRef",
        }
        missing = sorted(required - approval.keys())
        if missing:
            raise PolicyError(f"Approval missing fields: {', '.join(missing)}")
        if approval["schemaVersion"] != SCHEMA_VERSION:
            raise PolicyError("Unsupported approval schemaVersion")
        if approval["changeId"] != change_id:
            raise PolicyError("Approval changeId does not match the run")
        gate = approval["gate"]
        if gate not in GATE_TO_TYPE:
            raise PolicyError("Approval gate must be gate-1 or gate-2")
        if approval["decision"] != "APPROVE":
            raise PolicyError("Only an explicit APPROVE decision can pass a human gate")
        if approval["graphDigest"] != state["graphDigest"]:
            raise PolicyError("Approval graphDigest does not match the current graph")
        approver = approval["approver"]
        if not isinstance(approver, str) or not approver.strip():
            raise PolicyError("Approval approver must identify a human")
        normalized = approver.strip().lower()
        automation = {item.lower() for item in self.config["automationIdentities"]}
        if normalized in automation or normalized.startswith(("agent:", "bot:", "copilot:")):
            raise PolicyError("Automation identities cannot approve human gates")
        for key in ("statement", "evidenceRef"):
            if not isinstance(approval[key], str) or not approval[key].strip():
                raise PolicyError(f"Approval {key} must not be empty")
        try:
            approved_at = dt.datetime.fromisoformat(approval["approvedAt"].replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise PolicyError("approvedAt must be an ISO-8601 date-time") from exc
        if approved_at.tzinfo is None:
            raise PolicyError("approvedAt must include a timezone")

        gate_type = GATE_TO_TYPE[gate]
        gate_nodes = [node for node in graph["nodes"] if node["type"] == gate_type]
        if len(gate_nodes) != 1:
            raise PolicyError(f"Current graph does not contain exactly one {gate_type}")
        node = gate_nodes[0]
        node_state = state["nodes"][node["id"]]
        if node_state["status"] == "PASS":
            previous = state["approvals"].get(gate, {})
            if previous.get("approvalDigest") == digest_file(path):
                return {"status": "UNCHANGED", "gate": gate, "node": node["id"]}
            raise PolicyError(f"{gate} already passed with different evidence")
        if node_state["status"] != "PENDING" or not self._dependencies_pass(node, state):
            raise PolicyError(f"{gate} is not ready for approval")
        if gate == "gate-2":
            incomplete = [
                node_id
                for node_id, value in state["nodes"].items()
                if node_id != node["id"] and value["status"] != "PASS"
            ]
            if incomplete:
                raise PolicyError(f"gate-2 cannot pass while nodes are incomplete: {', '.join(sorted(incomplete))}")
        evidence = self._evidence_records([path])
        node_state.update(
            {
                "status": "PASS",
                "attempts": 1,
                "lastOutcome": "PASS",
                "actor": approver.strip(),
                "evidence": evidence,
                "updatedAt": utc_now(),
            }
        )
        approval_record = {
            "approver": approver.strip(),
            "approvedAt": approval["approvedAt"],
            "graphDigest": approval["graphDigest"],
            "approvalDigest": digest_file(path),
            "evidenceRef": approval["evidenceRef"],
        }
        state["approvals"][gate] = approval_record
        state["status"] = self._derive_run_status(state)
        state["updatedAt"] = utc_now()
        atomic_write_json(run_dir / "state.json", state)
        self._append_event(
            run_dir,
            "gate_approved",
            {
                "graphDigest": state["graphDigest"],
                "gate": gate,
                "nodeId": node["id"],
                "nodeState": copy.deepcopy(node_state),
                "approval": copy.deepcopy(approval_record),
            },
        )
        return {"status": "PASS", "gate": gate, "node": node["id"], "graphDigest": state["graphDigest"]}

    def _append_event(self, run_dir: Path, event_type: str, payload: dict[str, Any]) -> None:
        path = run_dir / "events.jsonl"
        previous_hash = "GENESIS"
        sequence = 1
        if path.exists():
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                try:
                    previous = json.loads(lines[-1])
                except json.JSONDecodeError as exc:
                    raise PolicyError(f"Cannot append to corrupt event log: {path}") from exc
                previous_hash = previous.get("hash", "")
                sequence = previous.get("sequence", 0) + 1
        event = {
            "sequence": sequence,
            "timestamp": utc_now(),
            "eventType": event_type,
            "payload": payload,
            "previousHash": previous_hash,
        }
        event["hash"] = digest_json(event)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _read_and_verify_events(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            raise PolicyError(f"Missing event log: {path}")
        events: list[dict[str, Any]] = []
        previous_hash = "GENESIS"
        for expected_sequence, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PolicyError(f"Invalid event JSON at sequence {expected_sequence}") from exc
            if event.get("sequence") != expected_sequence:
                raise PolicyError(f"Event sequence mismatch at {expected_sequence}")
            if event.get("previousHash") != previous_hash:
                raise PolicyError(f"Event hash chain mismatch at sequence {expected_sequence}")
            recorded_hash = event.get("hash")
            unsigned = copy.deepcopy(event)
            unsigned.pop("hash", None)
            if recorded_hash != digest_json(unsigned):
                raise PolicyError(f"Event content digest mismatch at sequence {expected_sequence}")
            previous_hash = recorded_hash
            events.append(event)
        if not events:
            raise PolicyError("Event log is empty")
        return events

    def _resolve_recorded_path(self, raw: str) -> Path:
        path = Path(raw)
        if not path.is_absolute():
            path = self.root / path
        return path.resolve()

    def verify(self, change_id: str) -> dict[str, Any]:
        run_dir = self._existing_run_dir(change_id)
        with exclusive_file_lock(run_dir / ".kernel.lock"):
            return self._verify_unlocked(change_id)

    def _verify_unlocked(self, change_id: str) -> dict[str, Any]:
        errors: list[str] = []
        try:
            run_dir, manifest, state = self._load_run(change_id)
            graph = load_json(run_dir / "graph.json")
            self.validate_graph(graph, expected_change_id=change_id)
            graph_digest = digest_json(self._graph_without_digest(graph))
            if graph.get("graphDigest") != graph_digest or state.get("graphDigest") != graph_digest:
                errors.append("Graph digest does not match graph/state")
            if manifest.get("programId") != self.config["programId"]:
                errors.append("Manifest programId does not match program configuration")
            events = self._read_and_verify_events(run_dir / "events.jsonl")
            event_evidence: list[tuple[str, dict[str, Any]]] = []
            for event in events:
                payload = event.get("payload", {})
                if payload.get("graphDigest") != graph_digest:
                    continue
                if event["eventType"] in {"node_recorded", "gate_approved"}:
                    for evidence in payload.get("nodeState", {}).get("evidence", []):
                        event_evidence.append((payload.get("nodeId", "unknown"), evidence))
            for node_id, evidence in event_evidence:
                evidence_path = self._resolve_recorded_path(evidence["path"])
                if not evidence_path.is_file():
                    errors.append(f"Missing historical evidence for {node_id}: {evidence['path']}")
                elif digest_file(evidence_path) != evidence.get("sha256"):
                    errors.append(f"Historical evidence digest mismatch for {node_id}: {evidence['path']}")
            graph_events = [
                event
                for event in events
                if event["eventType"] in {"graph_registered", "graph_revised"}
                and event["payload"].get("graphDigest") == graph_digest
            ]
            if not graph_events:
                errors.append("No hash-chained registration event for the current graph")
            else:
                registration_sequence = graph_events[-1]["sequence"]
                reconstructed_nodes = {
                    node["id"]: {
                        "status": "PENDING",
                        "attempts": 0,
                        "lastOutcome": None,
                        "actor": None,
                        "evidence": [],
                        "updatedAt": None,
                    }
                    for node in graph["nodes"]
                }
                reconstructed_approvals: dict[str, Any] = {}
                for event in events:
                    if event["sequence"] <= registration_sequence:
                        continue
                    payload = event["payload"]
                    if payload.get("graphDigest") != graph_digest:
                        continue
                    if event["eventType"] == "node_recorded":
                        reconstructed_nodes[payload["nodeId"]] = payload["nodeState"]
                    elif event["eventType"] == "gate_approved":
                        reconstructed_nodes[payload["nodeId"]] = payload["nodeState"]
                        reconstructed_approvals[payload["gate"]] = payload["approval"]
                if canonical_json(reconstructed_nodes) != canonical_json(state.get("nodes")):
                    errors.append("state.json node transitions do not match the hash-chained event log")
                if canonical_json(reconstructed_approvals) != canonical_json(state.get("approvals")):
                    errors.append("state.json approvals do not match the hash-chained event log")

            node_map = self._node_map(graph)
            if set(state.get("nodes", {})) != set(node_map):
                errors.append("State node set does not match graph node set")
            for node_id, node_state in state.get("nodes", {}).items():
                node = node_map.get(node_id)
                if not node:
                    continue
                if node_state.get("attempts", 0) > node["attemptBudget"]:
                    errors.append(f"{node_id} exceeds its attempt budget")
                if node_state.get("status") == "PASS":
                    for dependency in node["dependsOn"]:
                        if state["nodes"][dependency]["status"] != "PASS":
                            errors.append(f"{node_id} passed before dependency {dependency}")
                    if not node_state.get("evidence"):
                        errors.append(f"{node_id} passed without evidence")
                for evidence in node_state.get("evidence", []):
                    evidence_path = self._resolve_recorded_path(evidence["path"])
                    if not evidence_path.is_file():
                        errors.append(f"Missing evidence for {node_id}: {evidence['path']}")
                    elif digest_file(evidence_path) != evidence.get("sha256"):
                        errors.append(f"Evidence digest mismatch for {node_id}: {evidence['path']}")
            for gate, approval in state.get("approvals", {}).items():
                if approval.get("graphDigest") != graph_digest:
                    errors.append(f"{gate} approval is bound to another graph digest")

            run_status = self._derive_run_status(state)
        except PolicyError as exc:
            errors.append(str(exc))
            run_status = "INCONCLUSIVE"
            graph_digest = None
        integrity = "PASS" if not errors else "FAIL"
        overall = run_status if integrity == "PASS" else "FAIL"
        return {
            "changeId": change_id,
            "graphDigest": graph_digest,
            "integrity": integrity,
            "result": overall,
            "errors": errors,
        }

    def generate_workspace(self, change_id: str, output: Path | str) -> dict[str, Any]:
        run_dir = self._existing_run_dir(change_id)
        with exclusive_file_lock(run_dir / ".kernel.lock"):
            return self._generate_workspace_unlocked(change_id, output)

    def _generate_workspace_unlocked(self, change_id: str, output: Path | str) -> dict[str, Any]:
        run_dir, _manifest, state = self._load_run(change_id)
        graph = load_json(run_dir / "graph.json")
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = self.root / output_path
        output_path = output_path.resolve()
        try:
            output_path.relative_to(self.root)
        except ValueError as exc:
            raise PolicyError("Generated workspace output must stay inside the control repository") from exc
        folders: list[dict[str, str]] = [{"name": "GTS SDLC Control", "path": str(self.root)}]
        for repository in graph["repositories"]:
            if repository["disposition"] == "NOT_IMPACTED" or not repository.get("worktree"):
                continue
            raw_path = Path(repository["worktree"])
            path = raw_path if raw_path.is_absolute() else self.root / raw_path
            path = path.resolve()
            if not path.is_dir():
                raise PolicyError(f"Active worktree does not exist for {repository['repositoryId']}: {path}")
            folders.append({"name": repository["repositoryId"], "path": str(path)})
        workspace = {
            "folders": folders,
            "settings": {
                "chat.useCustomAgentHooks": True,
                "chat.useCustomizationsInParentRepositories": True,
                "chat.subagents.allowInvocationsFromSubagents": True,
                "chat.subagents.useRichRendering": False,
                "chat.hookFilesLocations": {".github/hooks": True},
                "chat.agentSkillsLocations": {".agents/skills": True},
            },
            "gtsSdlc": {"changeId": change_id, "graphDigest": state["graphDigest"]},
        }
        atomic_write_json(output_path, workspace)
        return {"status": "PASS", "output": str(output_path), "folders": len(folders)}

    def handle_hook(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_name = payload.get("hook_event_name") or payload.get("hookEventName") or "Unknown"
        decision: str | None = None
        reason: str | None = None
        output: dict[str, Any] = {}
        if event_name == "PreToolUse":
            tool_name = str(payload.get("tool_name", ""))
            tool_input = payload.get("tool_input", {})
            text = canonical_json(tool_input).lower().replace("\\", "/")
            command = ""
            if isinstance(tool_input, dict):
                for key in ("command", "cmd", "script"):
                    if isinstance(tool_input.get(key), str):
                        command = tool_input[key].lower()
                        break
            protected_state = re.search(
                r"\.github/sdlc/runs/[^/]+/(manifest\.json|graph\.json|state\.json|events\.jsonl)",
                text,
            )
            deny_patterns = [
                r"\bgit\s+reset\s+--hard\b",
                r"\bgit\s+clean\s+-[^\s]*f",
                r"\bgit\s+push\b[^\n]*(--force(?:-with-lease)?|-f)(?:\s|$)",
                r"\bdrop\s+database\b",
                r"\btruncate\s+table\b",
            ]
            ask_patterns = [
                r"\bgit\s+push\b[^\n]*(?:origin\s+)?(?:head:|refs/heads/)?(?:main|master|develop)(?:\s|$)",
                r"\bgh\s+pr\s+merge\b",
                r"\bgit\s+merge\b",
                r"\bgit\s+branch\s+-[dD]\b",
                r"\bgts-deliver\b",
                r"\bkubectl\s+(?:apply|delete|rollout)\b",
                r"\bterraform\s+(?:apply|destroy)\b",
                r"\bhelm\s+(?:install|upgrade|uninstall)\b",
                r"\b(?:rm\s+-[^\s]*r|remove-item\b[^\n]*-recurse)\b",
            ]
            if protected_state and ("edit" in tool_name.lower() or command):
                decision = "deny"
                reason = "Control-plane state is kernel-owned; use policy_kernel.py commands instead of editing it directly."
            elif any(re.search(pattern, command) for pattern in deny_patterns):
                decision = "deny"
                reason = "Destructive or history-rewriting command blocked by GTS SDLC policy."
            elif any(re.search(pattern, command) for pattern in ask_patterns):
                decision = "ask"
                reason = "This operation changes shared, protected, delivery, merge, or destructive state and requires explicit human approval."
            if decision:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": decision,
                        "permissionDecisionReason": reason,
                        "additionalContext": "Human SDLC gates do not override repository or production controls.",
                    }
                }
        elif event_name == "SessionStart":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        "For code-changing GTS work, use gts-orchestrator/program-orchestrator. "
                        "Show all 13 SDLC stages, fail closed on missing specifications, and obtain both human gates."
                    ),
                }
            }
        elif event_name == "SubagentStart":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": (
                        "This subagent is stateless. Obey the complete supplied task envelope, write durable evidence, "
                        "and return INCONCLUSIVE or SCOPE_CHANGE instead of guessing."
                    ),
                }
            }
        elif event_name in {"Stop", "SubagentStop"} and payload.get("stop_hook_active"):
            output = {}
        self._audit_hook(payload, decision, reason)
        return output

    def _audit_hook(self, payload: dict[str, Any], decision: str | None, reason: str | None) -> None:
        session = str(payload.get("session_id", "unknown"))
        safe_session = re.sub(r"[^A-Za-z0-9._-]", "_", session)[:80] or "unknown"
        date = dt.datetime.now(dt.timezone.utc).date().isoformat()
        with exclusive_file_lock(self.audit_root / f".{date}-{safe_session}.lock"):
            self._audit_hook_unlocked(payload, decision, reason)

    def _audit_hook_unlocked(self, payload: dict[str, Any], decision: str | None, reason: str | None) -> None:
        self.audit_root.mkdir(parents=True, exist_ok=True)
        session = str(payload.get("session_id", "unknown"))
        safe_session = re.sub(r"[^A-Za-z0-9._-]", "_", session)[:80] or "unknown"
        date = dt.datetime.now(dt.timezone.utc).date().isoformat()
        path = self.audit_root / f"{date}-{safe_session}.jsonl"
        prompt = payload.get("prompt")
        summary = {
            "timestamp": utc_now(),
            "event": payload.get("hook_event_name") or payload.get("hookEventName") or "Unknown",
            "sessionId": session,
            "toolName": payload.get("tool_name"),
            "agentType": payload.get("agent_type"),
            "decision": decision,
            "reason": reason,
            "promptDigest": sha256_bytes(prompt.encode("utf-8")) if isinstance(prompt, str) else None,
            "promptLength": len(prompt) if isinstance(prompt, str) else None,
        }
        previous_hash = "GENESIS"
        sequence = 1
        if path.exists():
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                previous = json.loads(lines[-1])
                previous_hash = previous.get("hash", "")
                sequence = previous.get("sequence", 0) + 1
        record = {"sequence": sequence, "previousHash": previous_hash, **summary}
        record["hash"] = digest_json(record)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(record) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Control repository root (primarily for isolated validation)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate program configuration, catalog, and schema JSON")

    digest = subparsers.add_parser("digest", help="Calculate a canonical SHA-256 evidence digest")
    digest.add_argument("--file", required=True)

    init = subparsers.add_parser("init", help="Create a new run")
    init.add_argument("--change-id", required=True)
    init.add_argument("--request", required=True)
    init.add_argument("--requester", required=True)
    init.add_argument("--risk-tier", choices=["low", "medium", "high", "critical"], required=True)

    register = subparsers.add_parser("register-graph", help="Validate and register an agent-authored graph")
    register.add_argument("--change-id", required=True)
    register.add_argument("--graph", required=True)

    ready = subparsers.add_parser("ready", help="Return dependency-ready nodes and a safe execution wave")
    ready.add_argument("--change-id", required=True)

    record = subparsers.add_parser("record", help="Record one bounded node result and evidence")
    record.add_argument("--change-id", required=True)
    record.add_argument("--node", required=True)
    record.add_argument("--outcome", choices=sorted(VALID_OUTCOMES), required=True)
    record.add_argument("--actor", required=True)
    record.add_argument("--evidence", action="append", required=True)

    approve = subparsers.add_parser("approve", help="Record digest-bound human approval evidence")
    approve.add_argument("--change-id", required=True)
    approve.add_argument("--approval", required=True)

    verify = subparsers.add_parser("verify", help="Verify graph, state, event chain, and evidence integrity")
    verify.add_argument("--change-id", required=True)

    workspace = subparsers.add_parser("workspace", help="Generate a multi-root workspace for active repositories")
    workspace.add_argument("--change-id", required=True)
    workspace.add_argument("--output", required=True)

    subparsers.add_parser("hook", help="Handle a VS Code/Copilot hook JSON object from stdin")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        kernel = PolicyKernel(args.root)
        if args.command == "validate":
            result = kernel.validate()
        elif args.command == "digest":
            result = kernel.digest_artifact(args.file)
        elif args.command == "init":
            result = kernel.init_run(args.change_id, args.request, args.requester, args.risk_tier)
        elif args.command == "register-graph":
            result = kernel.register_graph(args.change_id, args.graph)
        elif args.command == "ready":
            result = kernel.ready(args.change_id)
        elif args.command == "record":
            result = kernel.record(args.change_id, args.node, args.outcome, args.actor, args.evidence)
        elif args.command == "approve":
            result = kernel.approve(args.change_id, args.approval)
        elif args.command == "verify":
            result = kernel.verify(args.change_id)
        elif args.command == "workspace":
            result = kernel.generate_workspace(args.change_id, args.output)
        elif args.command == "hook":
            try:
                payload = json.load(sys.stdin)
            except json.JSONDecodeError as exc:
                raise PolicyError(f"Hook stdin is not valid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise PolicyError("Hook stdin must be a JSON object")
            result = kernel.handle_hook(payload)
        else:  # pragma: no cover - argparse guarantees a known command
            raise PolicyError(f"Unknown command: {args.command}")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        if args.command == "verify" and result.get("result") != "PASS":
            return 2
        return 0
    except PolicyError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
