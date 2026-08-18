#!/usr/bin/env python3
"""Coordinate evidence-gated changes across a graph of Git repositories."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


CHANGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
REPOSITORY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}$")
SYSTEM_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")
EXTENSION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}$")
BRANCH_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,79}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIREMENT_ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]+-[0-9]{3,}$")
SOURCE_SET_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
GATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
MAX_EXTENSION_FILE_BYTES = 256 * 1024
DECISIONS = {"PASS", "FAIL", "INCONCLUSIVE", "BLOCKED_SPEC"}
PLAN_REVIEW_DECISIONS = {"PASS", "CHANGES_REQUIRED"}
PLAN_REVIEW_TYPES = {
    "requirements",
    "architecture",
    "testing",
    "security",
    "adversarial",
}
PLAN_REVIEW_MINIMUMS = {"low": 1, "medium": 1, "high": 2, "critical": 3}
PLACEHOLDER_RE = re.compile(
    r"(?:REPLACE(?:_WITH)?|PLACEHOLDER|\bTBD\b|\bTODO\b|\bUNKNOWN\b|<[^>]+>)",
    re.IGNORECASE,
)
EXTENSION_KINDS = ("instructions", "skills", "agents")
RUN_STATES = {
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
    "BLOCKED_SPEC",
    "FAIL",
    "INCONCLUSIVE",
}

PROGRAM_STEP_DEFINITIONS = [
    ("intake", "Clarify request and prove source sufficiency"),
    ("requirements", "Freeze cited requirements and acceptance criteria"),
    ("plan-review", "Review and revise the digest-bound plan"),
    ("human-gate-1", "Obtain independent Human Gate 1 approval"),
    ("implementation", "Implement leased repository tasks"),
    ("repository-gates", "Run exact-commit repository and GUI gates"),
    ("integration", "Run cross-repository integration gates"),
    ("plan-closure", "Prove every approved acceptance criterion"),
    ("pr-set", "Prepare linked pull requests"),
    ("human-gate-2", "Obtain independent exact-head PR approval"),
]


class ProgramError(RuntimeError):
    """A fail-closed program orchestration error."""


def reject_placeholder(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProgramError(f"{label} must be a non-empty string")
    normalized = value.strip()
    if PLACEHOLDER_RE.search(normalized):
        raise ProgramError(f"{label} contains placeholder content")
    return normalized


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProgramError(f"{path}: cannot read valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProgramError(f"{path}: top-level value must be an object")
    return value


def validate_pass_gates(
    gates: Any, label: str, *, allow_optional_non_pass: bool
) -> None:
    if not isinstance(gates, list) or not gates:
        raise ProgramError(f"PASS {label} evidence must contain gate results")
    seen: set[str] = set()
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            raise ProgramError(f"{label} gate {index} must be an object")
        gate_id = gate.get("id")
        status = gate.get("status")
        if not isinstance(gate_id, str) or not GATE_ID_RE.fullmatch(gate_id):
            raise ProgramError(f"{label} gate {index} must have a non-empty id")
        if gate_id in seen:
            raise ProgramError(f"{label} gate IDs must be unique: {gate_id}")
        seen.add(gate_id)
        required = gate.get("required", True) is not False
        if status != "PASS" and (required or not allow_optional_non_pass):
            raise ProgramError(
                f"required {label} gate did not PASS: {gate_id}={status!r}"
            )


def normalize_requirement_obligations(
    payload: dict[str, Any],
    change_id: str,
    implementation_scope: set[str],
) -> list[dict[str, Any]]:
    if payload.get("change_id") != change_id:
        raise ProgramError("requirements change_id does not match the program change")
    source_set_digest = payload.get("source_set_digest")
    if (
        not isinstance(source_set_digest, str)
        or not SOURCE_SET_DIGEST_RE.fullmatch(source_set_digest)
    ):
        raise ProgramError("requirements require a valid source_set_digest")
    source_set = payload.get("source_set")
    if not isinstance(source_set, list) or not source_set:
        raise ProgramError("requirements require a frozen source_set")
    source_index: dict[str, dict[str, Any]] = {}
    for source_index_number, source in enumerate(source_set, 1):
        if not isinstance(source, dict):
            raise ProgramError(
                f"source_set entry {source_index_number} must be an object"
            )
        source_id = source.get("source_id")
        version = source.get("version")
        content_sha256 = source.get("content_sha256")
        locator = source.get("locator")
        if (
            not isinstance(source_id, str)
            or not source_id.strip()
            or not isinstance(version, str)
            or not version.strip()
            or not isinstance(content_sha256, str)
            or not SOURCE_SET_DIGEST_RE.fullmatch(content_sha256)
            or not isinstance(locator, str)
            or not locator.strip()
        ):
            raise ProgramError(
                f"source_set entry {source_index_number} requires source_id, "
                "version, content_sha256 and locator"
            )
        if source_id in source_index:
            raise ProgramError(f"duplicate source_set source_id: {source_id}")
        source_index[source_id] = source
    calculated_source_set_digest = "sha256:" + digest(source_set)
    if source_set_digest != calculated_source_set_digest:
        raise ProgramError(
            "source_set_digest does not match the frozen source_set"
        )
    requirements = payload.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ProgramError("requirements must contain at least one atomic requirement")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    covered_repositories: set[str] = set()
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            raise ProgramError(f"requirement {index} must be an object")
        requirement_id = requirement.get("id")
        if (
            not isinstance(requirement_id, str)
            or not REQUIREMENT_ID_RE.fullmatch(requirement_id)
        ):
            raise ProgramError(f"requirement {index} has an invalid id")
        if requirement_id in seen:
            raise ProgramError(f"duplicate requirement id: {requirement_id}")
        seen.add(requirement_id)
        statement = requirement.get("statement")
        if not isinstance(statement, str) or len(statement.strip()) < 10:
            raise ProgramError(f"{requirement_id}: statement is missing or too short")
        sources = requirement.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ProgramError(f"{requirement_id}: at least one source is required")
        normalized_sources: list[dict[str, Any]] = []
        for citation_index, source in enumerate(sources, 1):
            if not isinstance(source, dict):
                raise ProgramError(
                    f"{requirement_id}: source {citation_index} must identify a "
                    "versioned source and section"
                )
            for field in ("source_id", "version", "section"):
                if not isinstance(source.get(field), str) or not source[field].strip():
                    raise ProgramError(
                        f"{requirement_id}: source {citation_index} requires {field}"
                    )
            source_definition = source_index.get(source["source_id"])
            if source_definition is None:
                raise ProgramError(
                    f"{requirement_id}: source {source['source_id']} is not in "
                    "the frozen source_set"
                )
            if source["version"].strip() != source_definition["version"].strip():
                raise ProgramError(
                    f"{requirement_id}: source {source['source_id']} version does "
                    "not match the frozen source_set"
                )
            normalized_source = dict(source)
            for field in ("source_id", "version", "section"):
                normalized_source[field] = source[field].strip()
            normalized_sources.append(normalized_source)
        repositories = requirement.get("repositories")
        if (
            not isinstance(repositories, list)
            or not repositories
            or not all(isinstance(item, str) and item for item in repositories)
        ):
            raise ProgramError(
                f"{requirement_id}: repositories must identify implementation owners"
            )
        repository_set = set(repositories)
        if len(repository_set) != len(repositories):
            raise ProgramError(f"{requirement_id}: repositories must be unique")
        outside_scope = repository_set - implementation_scope
        if outside_scope:
            raise ProgramError(
                f"{requirement_id}: repositories outside implementation scope: "
                + ", ".join(sorted(outside_scope))
            )
        criteria = requirement.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria:
            raise ProgramError(
                f"{requirement_id}: measurable acceptance criteria are required"
            )
        normalized_criteria: list[dict[str, str]] = []
        criterion_ids: set[str] = set()
        for criterion_index, criterion in enumerate(criteria, 1):
            generated_id = f"{requirement_id}-AC-{criterion_index:03d}"
            if isinstance(criterion, str):
                criterion_id = generated_id
                criterion_statement = criterion
            elif isinstance(criterion, dict):
                criterion_id = criterion.get("id")
                criterion_statement = criterion.get("statement")
            else:
                raise ProgramError(
                    f"{requirement_id}: acceptance criterion {criterion_index} "
                    "must be a string or object"
                )
            if (
                not isinstance(criterion_id, str)
                or not REQUIREMENT_ID_RE.fullmatch(criterion_id)
                or not isinstance(criterion_statement, str)
                or not criterion_statement.strip()
            ):
                raise ProgramError(
                    f"{requirement_id}: acceptance criterion {criterion_index} "
                    "requires a stable id and statement"
                )
            if criterion_id in criterion_ids:
                raise ProgramError(
                    f"{requirement_id}: duplicate acceptance criterion id: "
                    f"{criterion_id}"
                )
            criterion_ids.add(criterion_id)
            normalized_criteria.append(
                {"id": criterion_id, "statement": criterion_statement.strip()}
            )
        evidence_types = requirement.get("required_evidence")
        if (
            not isinstance(evidence_types, list)
            or not evidence_types
            or not all(
                isinstance(item, str) and item.strip() for item in evidence_types
            )
        ):
            raise ProgramError(f"{requirement_id}: required_evidence is missing")
        if len(set(evidence_types)) != len(evidence_types):
            raise ProgramError(f"{requirement_id}: required_evidence must be unique")
        evidence_type_set = set(evidence_types)
        normalized_gui_contract: dict[str, Any] | None = None
        if "gui-validation" in evidence_type_set:
            gui_contract = requirement.get("gui_contract")
            if not isinstance(gui_contract, dict):
                raise ProgramError(
                    f"{requirement_id}: GUI validation requires an approved "
                    "gui_contract; return to intake clarification"
                )
            normalized_gui_contract = {}
            for field in (
                "affected_views",
                "user_journeys",
                "viewports",
                "states",
                "baseline_refs",
            ):
                values = gui_contract.get(field)
                if not isinstance(values, list) or not values or not all(
                    isinstance(item, str) and item.strip() for item in values
                ):
                    raise ProgramError(
                        f"{requirement_id}: gui_contract.{field} must be a "
                        "non-empty string array"
                    )
                normalized_gui_contract[field] = [item.strip() for item in values]
            normalized_gui_contract["approval_ref"] = reject_placeholder(
                gui_contract.get("approval_ref"),
                f"{requirement_id}: gui_contract.approval_ref",
            )
        verification = requirement.get("verification")
        if not isinstance(verification, list) or not verification:
            raise ProgramError(
                f"{requirement_id}: a frozen verification matrix is required"
            )
        normalized_verification: list[dict[str, Any]] = []
        verified_repositories: set[str] = set()
        verified_criteria: set[str] = set()
        verified_evidence: set[str] = set()
        integration_entries = 0
        for verification_index, entry in enumerate(verification, 1):
            if not isinstance(entry, dict):
                raise ProgramError(
                    f"{requirement_id}: verification entry {verification_index} "
                    "must be an object"
                )
            scope = entry.get("scope")
            if scope not in {"repository", "integration"}:
                raise ProgramError(
                    f"{requirement_id}: verification entry {verification_index} "
                    "scope must be repository or integration"
                )
            repository_id = entry.get("repository")
            if scope == "repository":
                if repository_id not in repository_set:
                    raise ProgramError(
                        f"{requirement_id}: repository verification entry must "
                        "name an owning repository"
                    )
                verified_repositories.add(repository_id)
            else:
                if repository_id is not None:
                    raise ProgramError(
                        f"{requirement_id}: integration verification must not "
                        "name one repository"
                    )
                integration_entries += 1
            gate_ids = entry.get("gate_ids")
            entry_criteria = entry.get("acceptance_criteria_ids", [])
            entry_evidence = entry.get("evidence_types", [])
            for label, values, allow_empty in (
                ("gate_ids", gate_ids, False),
                ("acceptance_criteria_ids", entry_criteria, True),
                ("evidence_types", entry_evidence, True),
            ):
                if (
                    not isinstance(values, list)
                    or (not allow_empty and not values)
                    or not all(
                        isinstance(value, str)
                        and value.strip()
                        and (
                            label != "gate_ids"
                            or GATE_ID_RE.fullmatch(value)
                        )
                        for value in values
                    )
                    or len(set(values)) != len(values)
                ):
                    raise ProgramError(
                        f"{requirement_id}: verification {label} must be a "
                        "unique string array"
                    )
            unknown_criteria = set(entry_criteria) - criterion_ids
            unknown_evidence = set(entry_evidence) - evidence_type_set
            if unknown_criteria:
                raise ProgramError(
                    f"{requirement_id}: verification references unknown acceptance "
                    "criteria: " + ", ".join(sorted(unknown_criteria))
                )
            if unknown_evidence:
                raise ProgramError(
                    f"{requirement_id}: verification references unknown evidence "
                    "types: " + ", ".join(sorted(unknown_evidence))
                )
            verified_criteria.update(entry_criteria)
            verified_evidence.update(entry_evidence)
            normalized_entry = {
                "scope": scope,
                "gate_ids": sorted(gate_ids),
                "acceptance_criteria_ids": sorted(entry_criteria),
                "evidence_types": sorted(entry_evidence),
            }
            if scope == "repository":
                normalized_entry["repository"] = repository_id
            normalized_verification.append(normalized_entry)
        if verified_repositories != repository_set:
            raise ProgramError(
                f"{requirement_id}: verification matrix does not cover owning "
                "repositories: "
                + ", ".join(sorted(repository_set - verified_repositories))
            )
        if integration_entries == 0:
            raise ProgramError(
                f"{requirement_id}: at least one integration verification is required"
            )
        if verified_criteria != criterion_ids:
            raise ProgramError(
                f"{requirement_id}: verification matrix does not cover acceptance "
                "criteria: " + ", ".join(sorted(criterion_ids - verified_criteria))
            )
        if verified_evidence != evidence_type_set:
            raise ProgramError(
                f"{requirement_id}: verification matrix does not cover evidence "
                "types: " + ", ".join(sorted(evidence_type_set - verified_evidence))
            )
        covered_repositories.update(repository_set)
        normalized_requirement = {
            "id": requirement_id,
            "statement": statement.strip(),
            "type": requirement.get("type"),
            "criticality": requirement.get("criticality"),
            "repositories": sorted(repository_set),
            "sources": normalized_sources,
            "acceptance_criteria": normalized_criteria,
            "required_evidence": sorted(set(evidence_types)),
            "verification": normalized_verification,
        }
        if normalized_gui_contract is not None:
            normalized_requirement["gui_contract"] = normalized_gui_contract
        normalized.append(normalized_requirement)
    uncovered = implementation_scope - covered_repositories
    if uncovered:
        raise ProgramError(
            "implementation repositories without an atomic requirement: "
            + ", ".join(sorted(uncovered))
        )
    return normalized


def integration_verification_matrix(
    obligations: list[dict[str, Any]],
) -> dict[str, dict[str, set[str]]]:
    matrix: dict[str, dict[str, set[str]]] = {}
    for obligation in obligations:
        for entry in obligation.get("verification", []):
            if entry["scope"] != "integration":
                continue
            for gate_id in entry["gate_ids"]:
                expected = matrix.setdefault(
                    gate_id,
                    {
                        "requirement_ids": set(),
                        "acceptance_criteria_ids": set(),
                        "evidence_types": set(),
                        "source_refs": set(),
                    },
                )
                expected["requirement_ids"].add(obligation["id"])
                expected["acceptance_criteria_ids"].update(
                    entry["acceptance_criteria_ids"]
                )
                expected["evidence_types"].update(entry["evidence_types"])
                expected["source_refs"].update(
                    source["source_id"] for source in obligation["sources"]
                )
    return matrix


def run_command(args: list[str], cwd: Path, *, check: bool = True) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    if check and result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        raise ProgramError(f"command failed in {cwd}: {args!r}: {output}")
    return result.stdout.strip()


def normalize_remote(value: str) -> str:
    normalized = value.strip().replace("\\", "/").removesuffix("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized.lower()


def safe_relative_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ProgramError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ProgramError(f"{label} must be a safe relative path")
    return path


def workspace_relative(path: Path, workspace_root: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def validate_extension_manifest(
    extension: dict[str, Any], repository_id: str
) -> list[str]:
    errors: list[str] = []
    if extension.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if extension.get("repository_id") != repository_id:
        errors.append(f"repository_id must be {repository_id!r}")
    allowed_top_level = {
        "schema_version",
        "repository_id",
        "quality_config",
        "instructions",
        "skills",
        "agents",
    }
    unknown_top_level = set(extension) - allowed_top_level
    if unknown_top_level:
        errors.append(
            "unknown top-level fields: " + ", ".join(sorted(unknown_top_level))
        )
    if "quality_config" in extension:
        try:
            safe_relative_path(extension["quality_config"], "quality_config")
        except ProgramError as exc:
            errors.append(str(exc))

    seen: set[tuple[str, str]] = set()
    for kind in EXTENSION_KINDS:
        entries = extension.get(kind, [])
        if not isinstance(entries, list):
            errors.append(f"{kind} must be an array")
            continue
        if len(entries) > 32:
            errors.append(f"{kind} may contain at most 32 entries")
        for index, entry in enumerate(entries):
            prefix = f"{kind}[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be an object")
                continue
            allowed = {"id", "path", "enabled", "required", "activate_when"}
            if kind == "agents":
                allowed.add("role")
            unknown = set(entry) - allowed
            if unknown:
                errors.append(
                    f"{prefix} has unknown fields: " + ", ".join(sorted(unknown))
                )
            extension_id = entry.get("id")
            if not isinstance(extension_id, str) or not EXTENSION_ID_RE.fullmatch(
                extension_id
            ):
                errors.append(f"{prefix}.id must match {EXTENSION_ID_RE.pattern}")
            elif (kind, extension_id) in seen:
                errors.append(f"duplicate {kind} id: {extension_id}")
            else:
                seen.add((kind, extension_id))
            try:
                declared_path = safe_relative_path(
                    entry.get("path"), f"{prefix}.path"
                )
                if kind == "skills" and declared_path.name != "SKILL.md":
                    errors.append(f"{prefix}.path must point to SKILL.md")
                if kind == "agents" and not declared_path.name.endswith(
                    ".agent.md"
                ):
                    errors.append(f"{prefix}.path must point to an .agent.md file")
                if kind == "instructions" and declared_path.suffix != ".md":
                    errors.append(f"{prefix}.path must point to a Markdown file")
            except ProgramError as exc:
                errors.append(str(exc))
            for boolean_field in ("enabled", "required"):
                if boolean_field in entry and not isinstance(
                    entry[boolean_field], bool
                ):
                    errors.append(f"{prefix}.{boolean_field} must be boolean")
            activation = entry.get("activate_when", {})
            if not isinstance(activation, dict):
                errors.append(f"{prefix}.activate_when must be an object")
                continue
            unknown_activation = set(activation) - {
                "modes",
                "risk_tiers",
                "request_terms",
            }
            if unknown_activation:
                errors.append(
                    f"{prefix}.activate_when has unknown fields: "
                    + ", ".join(sorted(unknown_activation))
                )
            modes = activation.get("modes", [])
            if not isinstance(modes, list) or not all(
                item in {"implementation", "validation"} for item in modes
            ):
                errors.append(
                    f"{prefix}.activate_when.modes must contain implementation or validation"
                )
            risk_tiers = activation.get("risk_tiers", [])
            if not isinstance(risk_tiers, list) or not all(
                item in {"low", "medium", "high", "critical"}
                for item in risk_tiers
            ):
                errors.append(
                    f"{prefix}.activate_when.risk_tiers contains an invalid tier"
                )
            request_terms = activation.get("request_terms", [])
            if not isinstance(request_terms, list) or not all(
                isinstance(item, str) and item.strip() for item in request_terms
            ):
                errors.append(
                    f"{prefix}.activate_when.request_terms must be non-empty strings"
                )
            if kind == "agents" and (
                not isinstance(entry.get("role"), str)
                or not entry["role"].strip()
            ):
                errors.append(f"{prefix}.role must be a non-empty string")
    return errors


def extension_is_active(
    entry: dict[str, Any], *, mode: str, risk_tier: str, request: str
) -> bool:
    if entry.get("enabled", True) is not True:
        return False
    activation = entry.get("activate_when", {})
    modes = activation.get("modes", [])
    if modes and mode not in modes:
        return False
    risk_tiers = activation.get("risk_tiers", [])
    if risk_tiers and risk_tier not in risk_tiers:
        return False
    request_terms = activation.get("request_terms", [])
    normalized_request = request.casefold()
    if request_terms and not any(
        term.casefold() in normalized_request for term in request_terms
    ):
        return False
    return True


def validate_manifest(manifest: dict[str, Any], adoption: bool = False) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    program_id = manifest.get("program_id")
    if not isinstance(program_id, str) or not program_id.strip():
        errors.append("program_id must be a non-empty string")
    if adoption and manifest.get("adoption_complete") is not True:
        errors.append("adoption_complete must be true")
    for field in ("workspace_root", "worktree_root", "runs_directory", "branch_prefix"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"{field} must be a non-empty string")
    if isinstance(manifest.get("branch_prefix"), str) and not BRANCH_PREFIX_RE.fullmatch(
        manifest["branch_prefix"]
    ):
        errors.append(f"branch_prefix must match {BRANCH_PREFIX_RE.pattern}")
    parallel = manifest.get("maximum_parallel_repositories")
    if not isinstance(parallel, int) or not 1 <= parallel <= 32:
        errors.append("maximum_parallel_repositories must be between 1 and 32")

    controls = manifest.get("controls")
    if not isinstance(controls, dict):
        errors.append("controls must be an object")
    else:
        if controls.get("human_plan_approval") is not True:
            errors.append("controls.human_plan_approval must be true")
        if controls.get("human_pr_approval") is not True:
            errors.append("controls.human_pr_approval must be true")
        if controls.get("human_production_approval") is not True:
            errors.append("controls.human_production_approval must be true")
        if controls.get("allow_agent_self_approval") is not False:
            errors.append("controls.allow_agent_self_approval must be false")
        attempts = controls.get("maximum_remediation_cycles")
        if not isinstance(attempts, int) or not 1 <= attempts <= 10:
            errors.append("controls.maximum_remediation_cycles must be between 1 and 10")

    default_quality_configs = manifest.get("default_quality_configs", {})
    if not isinstance(default_quality_configs, dict):
        errors.append("default_quality_configs must be an object")
    else:
        for stack, configured_path in default_quality_configs.items():
            try:
                safe_relative_path(
                    configured_path, f"default_quality_configs.{stack}"
                )
            except ProgramError as exc:
                errors.append(str(exc))
    integration_quality_config = manifest.get("integration_quality_config")
    if integration_quality_config is None:
        if adoption:
            errors.append("integration_quality_config is required for adoption")
    else:
        try:
            safe_relative_path(
                integration_quality_config, "integration_quality_config"
            )
        except ProgramError as exc:
            errors.append(str(exc))
    agent_runtime_config = manifest.get("agent_runtime_config")
    if agent_runtime_config is None:
        if adoption:
            errors.append("agent_runtime_config is required for adoption")
    else:
        try:
            safe_relative_path(agent_runtime_config, "agent_runtime_config")
        except ProgramError as exc:
            errors.append(str(exc))

    repositories = manifest.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        errors.append("repositories must be a non-empty array")
        return errors

    indexed: dict[str, dict[str, Any]] = {}
    paths: set[str] = set()
    for index, repository in enumerate(repositories):
        prefix = f"repositories[{index}]"
        if not isinstance(repository, dict):
            errors.append(f"{prefix} must be an object")
            continue
        repository_id = repository.get("id")
        if not isinstance(repository_id, str) or not REPOSITORY_ID_RE.fullmatch(repository_id):
            errors.append(f"{prefix}.id must match {REPOSITORY_ID_RE.pattern}")
            continue
        if repository_id in indexed:
            errors.append(f"duplicate repository id: {repository_id}")
        indexed[repository_id] = repository
        system = repository.get("system")
        if system is None:
            if adoption:
                errors.append(f"{prefix}.system is required for adoption")
        elif not isinstance(system, str) or not SYSTEM_ID_RE.fullmatch(system):
            errors.append(f"{prefix}.system must match {SYSTEM_ID_RE.pattern}")
        local_path = repository.get("local_path")
        if (
            not isinstance(local_path, str)
            or not local_path
            or Path(local_path).is_absolute()
            or ".." in Path(local_path).parts
        ):
            errors.append(f"{prefix}.local_path must be a safe relative path")
        elif local_path.casefold() in paths:
            errors.append(f"duplicate local_path: {local_path}")
        else:
            paths.add(local_path.casefold())
        for field in ("url", "default_branch", "stack", "criticality"):
            if not isinstance(repository.get(field), str) or not repository[field].strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
            elif repository[field].startswith("-"):
                errors.append(f"{prefix}.{field} must not start with '-'")
        if adoption and "example" in str(repository.get("url", "")).casefold():
            errors.append(f"{prefix}.url is still an example")
        dependencies = repository.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            errors.append(f"{prefix}.depends_on must be a string array")
        if "quality_config" in repository:
            try:
                safe_relative_path(
                    repository["quality_config"], f"{prefix}.quality_config"
                )
            except ProgramError as exc:
                errors.append(str(exc))
        if "extensions_config" in repository:
            try:
                safe_relative_path(
                    repository["extensions_config"], f"{prefix}.extensions_config"
                )
            except ProgramError as exc:
                errors.append(str(exc))
        if "extensions_required" in repository and not isinstance(
            repository["extensions_required"], bool
        ):
            errors.append(f"{prefix}.extensions_required must be boolean")
        if (
            adoption
            and "quality_config" not in repository
            and repository.get("stack") not in default_quality_configs
        ):
            errors.append(
                f"{prefix} needs quality_config or a central default for "
                f"stack {repository.get('stack')!r}"
            )

    enabled = {
        key: value for key, value in indexed.items() if value.get("enabled", True) is True
    }
    if adoption and not enabled:
        errors.append("at least one repository must be enabled")
    if adoption and (
        not isinstance(program_id, str)
        or "CHANGE" in program_id.upper()
        or "REPLACE" in program_id.upper()
    ):
        errors.append("program_id is still a placeholder")
    for repository_id, repository in indexed.items():
        for dependency in repository.get("depends_on", []):
            if dependency not in indexed:
                errors.append(f"{repository_id}: unknown dependency {dependency!r}")
            elif dependency == repository_id:
                errors.append(f"{repository_id}: repository cannot depend on itself")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(repository_id: str, trail: list[str]) -> None:
        if repository_id in visited or repository_id not in enabled:
            return
        if repository_id in visiting:
            errors.append("dependency cycle: " + " -> ".join(trail + [repository_id]))
            return
        visiting.add(repository_id)
        for dependency in enabled[repository_id].get("depends_on", []):
            if dependency in enabled:
                visit(dependency, trail + [repository_id])
        visiting.remove(repository_id)
        visited.add(repository_id)

    for repository_id in sorted(enabled):
        visit(repository_id, [])
    return errors


class ProgramOrchestrator:
    def __init__(self, root: Path, manifest_path: Path | None = None):
        self.root = root.resolve()
        self.manifest_path = (
            manifest_path.resolve()
            if manifest_path
            else self.root / ".github" / "sdlc" / "program.json"
        )
        self.manifest = read_json(self.manifest_path)
        errors = validate_manifest(self.manifest)
        if errors:
            raise ProgramError("invalid program manifest:\n- " + "\n- ".join(errors))
        self.repositories = {
            item["id"]: item
            for item in self.manifest["repositories"]
            if item.get("enabled", True) is True
        }

    @property
    def runs_root(self) -> Path:
        configured = self.manifest.get("runs_directory", ".github/sdlc/program-runs")
        path = Path(configured)
        return path.resolve() if path.is_absolute() else (self.root / path).resolve()

    @property
    def workspace_root(self) -> Path:
        configured = Path(self.manifest["workspace_root"])
        return configured.resolve() if configured.is_absolute() else (self.root / configured).resolve()

    @property
    def worktree_root(self) -> Path:
        configured = Path(self.manifest["worktree_root"])
        return configured.resolve() if configured.is_absolute() else (self.root / configured).resolve()

    def run_dir(self, change_id: str) -> Path:
        if not CHANGE_ID_RE.fullmatch(change_id):
            raise ProgramError(f"change ID must match {CHANGE_ID_RE.pattern}")
        path = (self.runs_root / change_id).resolve()
        try:
            path.relative_to(self.runs_root)
        except ValueError as exc:
            raise ProgramError("change run path escapes the configured run directory") from exc
        return path

    def state_path(self, change_id: str) -> Path:
        return self.run_dir(change_id) / "run.json"

    def read_state(self, change_id: str) -> dict[str, Any]:
        path = self.state_path(change_id)
        if not path.is_file():
            raise ProgramError(f"unknown change ID: {change_id}")
        return read_json(path)

    @staticmethod
    def _visible_program_steps(state: dict[str, Any]) -> list[dict[str, str]]:
        current_by_state = {
            "AWAITING_CLARIFICATION": "intake",
            "INTAKE": "requirements",
            "AWAITING_PLAN_REVIEW": "plan-review",
            "AWAITING_PLAN_APPROVAL": "human-gate-1",
            "PLAN_APPROVED": "implementation",
            "WORKSPACES_READY": "implementation",
            "EXECUTING": "implementation",
            "INTEGRATION_PASSED": "plan-closure",
            "PLAN_CLOSED": "pr-set",
            "PR_SET_READY": "human-gate-2",
            "AWAITING_PR_APPROVAL": "human-gate-2",
        }
        terminal = state.get("state") in {
            "PR_APPROVED",
            "BLOCKED_SPEC",
            "FAIL",
            "INCONCLUSIVE",
        }
        current_id = current_by_state.get(state.get("state"))
        current_index = next(
            (
                index
                for index, (step_id, _) in enumerate(PROGRAM_STEP_DEFINITIONS)
                if step_id == current_id
            ),
            len(PROGRAM_STEP_DEFINITIONS) if state.get("state") == "PR_APPROVED" else 0,
        )
        result: list[dict[str, str]] = []
        for index, (step_id, title) in enumerate(PROGRAM_STEP_DEFINITIONS):
            if state.get("state") == "PR_APPROVED" or index < current_index:
                status = "completed"
            elif index == current_index:
                status = "blocked" if terminal else "in_progress"
            else:
                status = "pending"
            result.append({"id": step_id, "title": title, "status": status})
        return result

    def _write_visible_program_steps(
        self, change_id: str, state: dict[str, Any]
    ) -> None:
        steps = state["visible_steps"]
        review_count = len(
            [
                item
                for item in state.get("plan_reviews", [])
                if item.get("decision") == "PASS"
                and item.get("reviewed_digest") == state.get("plan_digest")
            ]
        )
        required_reviews = state.get(
            "required_plan_reviews",
            PLAN_REVIEW_MINIMUMS.get(state.get("risk_tier"), 1),
        )
        lines = [
            f"# Visible SDLC steps: {change_id}",
            "",
            f"State: `{state['state']}`",
            f"Plan revision: `{state.get('plan_revision', 0)}`",
            f"Current-plan reviews: `{review_count}/{required_reviews}`",
            "",
            "Mirror this checklist in the VS Code Chat todo control.",
            "",
        ]
        markers = {
            "completed": "x",
            "in_progress": " ",
            "pending": " ",
            "blocked": "!",
        }
        for step in steps:
            lines.append(
                f"- [{markers[step['status']]}] {step['title']} "
                f"(`{step['status']}`)"
            )
        lines.append("")
        visible_steps_path = self.run_dir(change_id) / "VISIBLE_STEPS.md"
        # Python 3.9 Path.write_text has no newline argument; use explicit open.
        with visible_steps_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines))

    def write_state(self, change_id: str, state: dict[str, Any]) -> None:
        if state.get("state") not in RUN_STATES:
            raise ProgramError(f"invalid run state: {state.get('state')!r}")
        state["visible_steps"] = self._visible_program_steps(state)
        state["updated_at"] = now()
        atomic_json(self.state_path(change_id), state)
        self._write_visible_program_steps(change_id, state)

    def persist_commit_vector(self, change_id: str, state: dict[str, Any]) -> str:
        artifact = {
            "schema_version": "1.0",
            "change_id": change_id,
            "repositories": state["commit_vector"],
            "generated_at": now(),
        }
        artifact["digest"] = digest(
            {key: value for key, value in artifact.items() if key != "digest"}
        )
        atomic_json(self.run_dir(change_id) / "commit-vector.json", artifact)
        state["commit_vector_digest"] = artifact["digest"]
        return artifact["digest"]

    def append_event(
        self, change_id: str, state: dict[str, Any], event_type: str, payload: dict[str, Any]
    ) -> None:
        event = {
            "sequence": int(state.get("event_count", 0)) + 1,
            "timestamp": now(),
            "type": event_type,
            "payload": payload,
            "previous_hash": state.get("last_event_hash", "0" * 64),
        }
        event["hash"] = digest(event)
        event_path = self.run_dir(change_id) / "events.jsonl"
        event_path.parent.mkdir(parents=True, exist_ok=True)
        with event_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(event) + "\n")
        state["event_count"] = event["sequence"]
        state["last_event_hash"] = event["hash"]

    def start(self, change_id: str, request: str, requested_by: str, risk_tier: str) -> dict[str, Any]:
        if not request.strip() or not requested_by.strip():
            raise ProgramError("request and requested_by must be non-empty")
        if risk_tier not in PLAN_REVIEW_MINIMUMS:
            raise ProgramError("risk_tier must be low, medium, high or critical")
        if self.run_dir(change_id).exists():
            raise ProgramError(f"change run already exists: {change_id}")
        state: dict[str, Any] = {
            "schema_version": "1.0",
            "change_id": change_id,
            "program_id": self.manifest["program_id"],
            "request": request.strip(),
            "requested_by": requested_by.strip(),
            "risk_tier": risk_tier,
            "state": "AWAITING_CLARIFICATION",
            "created_at": now(),
            "event_count": 0,
            "last_event_hash": "0" * 64,
            "commit_vector": {},
            "repository_extensions": {},
            "repository_results": {},
            "pull_requests": {},
            "remediation_cycles": {},
            "integration_remediation_cycles": 0,
            "clarification_rounds": [],
            "plan_revision": 0,
            "plan_reviews": [],
            "required_plan_reviews": PLAN_REVIEW_MINIMUMS[risk_tier],
        }
        atomic_json(
            self.run_dir(change_id) / "intake-assessment.template.json",
            {
                "change_id": change_id,
                "decision": "NEEDS_CLARIFICATION",
                "assessor": "REPLACE_WITH_ASSESSOR",
                "source_facts": [],
                "open_questions": ["REPLACE_WITH_CONCRETE_QUESTION"],
                "inaccessible_sources": [],
                "unverified_assumptions": [],
                "user_answers": [],
                "evidence_refs": [],
            },
        )
        self.append_event(change_id, state, "PROGRAM_CHANGE_STARTED", {"risk_tier": risk_tier})
        self.write_state(change_id, state)
        return state

    def assess_intake(
        self, change_id: str, evidence_path: Path
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "AWAITING_CLARIFICATION":
            raise ProgramError("intake assessment is not expected in the current state")
        evidence = read_json(evidence_path.resolve())
        if evidence.get("change_id") != change_id:
            raise ProgramError("intake assessment change_id does not match the run")
        decision = evidence.get("decision")
        if decision not in {"READY", "NEEDS_CLARIFICATION"}:
            raise ProgramError(
                "intake assessment decision must be READY or NEEDS_CLARIFICATION"
            )
        assessor = reject_placeholder(evidence.get("assessor"), "intake assessor")
        source_facts = evidence.get("source_facts")
        if not isinstance(source_facts, list):
            raise ProgramError("intake source_facts must be an array")
        for index, fact in enumerate(source_facts, 1):
            if not isinstance(fact, dict):
                raise ProgramError(f"intake source fact {index} must be an object")
            for field in ("source_id", "fact", "citation"):
                reject_placeholder(fact.get(field), f"intake source fact {index} {field}")
        questions = evidence.get("open_questions", [])
        inaccessible = evidence.get("inaccessible_sources", [])
        assumptions = evidence.get("unverified_assumptions", [])
        answers = evidence.get("user_answers", [])
        evidence_refs = evidence.get("evidence_refs", [])
        for label, values in (
            ("open_questions", questions),
            ("inaccessible_sources", inaccessible),
            ("unverified_assumptions", assumptions),
            ("evidence_refs", evidence_refs),
        ):
            if not isinstance(values, list) or not all(
                isinstance(item, str) and item.strip() for item in values
            ):
                raise ProgramError(f"intake {label} must be a string array")
        if not isinstance(answers, list):
            raise ProgramError("intake user_answers must be an array")
        for index, answer in enumerate(answers, 1):
            if not isinstance(answer, dict):
                raise ProgramError(f"intake user answer {index} must be an object")
            for field in ("question", "answer", "answered_by"):
                reject_placeholder(
                    answer.get(field), f"intake user answer {index} {field}"
                )

        prior_questions = any(
            item.get("decision") == "NEEDS_CLARIFICATION"
            for item in state.get("clarification_rounds", [])
        )
        if decision == "NEEDS_CLARIFICATION":
            if not questions:
                raise ProgramError(
                    "NEEDS_CLARIFICATION must contain concrete open_questions"
                )
        else:
            if questions or inaccessible or assumptions:
                raise ProgramError(
                    "READY intake cannot contain open questions, inaccessible "
                    "sources or unverified assumptions"
                )
            if not source_facts or not evidence_refs:
                raise ProgramError(
                    "READY intake requires cited source facts and evidence references"
                )
            if prior_questions and not answers:
                raise ProgramError(
                    "READY intake after clarification requires recorded user answers"
                )

        round_number = len(state.get("clarification_rounds", [])) + 1
        destination = (
            self.run_dir(change_id)
            / "intake"
            / f"round-{round_number}.json"
        )
        atomic_json(destination, evidence)
        summary = {
            "round": round_number,
            "decision": decision,
            "assessor": assessor,
            "evidence_path": str(
                destination.relative_to(self.run_dir(change_id))
            ).replace("\\", "/"),
            "evidence_sha256": file_digest(destination),
            "open_questions": questions,
        }
        state.setdefault("clarification_rounds", []).append(summary)
        if decision == "READY":
            state["state"] = "INTAKE"
            event_type = "INTAKE_READY"
        else:
            event_type = "INTAKE_CLARIFICATION_REQUESTED"
        self.append_event(change_id, state, event_type, summary)
        self.write_state(change_id, state)
        return state

    def downstream_closure(self, seeds: set[str]) -> set[str]:
        reverse: dict[str, set[str]] = {repository_id: set() for repository_id in self.repositories}
        for repository_id, repository in self.repositories.items():
            for dependency in repository.get("depends_on", []):
                if dependency in reverse:
                    reverse[dependency].add(repository_id)
        result = set(seeds)
        queue = list(seeds)
        while queue:
            current = queue.pop(0)
            for dependent in sorted(reverse[current]):
                if dependent not in result:
                    result.add(dependent)
                    queue.append(dependent)
        return result

    def upstream_closure(self, repositories: set[str]) -> set[str]:
        result = set(repositories)
        queue = list(repositories)
        while queue:
            current = queue.pop(0)
            for dependency in self.repositories[current].get("depends_on", []):
                if dependency in self.repositories and dependency not in result:
                    result.add(dependency)
                    queue.append(dependency)
        return result

    def waves(self, repositories: set[str]) -> list[list[str]]:
        pending = set(repositories)
        complete: set[str] = set()
        waves: list[list[str]] = []
        while pending:
            ready = sorted(
                repository_id
                for repository_id in pending
                if not (
                    set(self.repositories[repository_id].get("depends_on", []))
                    & repositories
                    - complete
                )
            )
            if not ready:
                raise ProgramError("dependency graph contains a cycle")
            waves.append(ready)
            complete.update(ready)
            pending.difference_update(ready)
        return waves

    def plan(
        self,
        change_id: str,
        seed_repositories: list[str],
        requirements_path: Path,
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        first_plan = state["state"] == "INTAKE"
        revising = (
            state["state"] == "AWAITING_PLAN_REVIEW"
            and state.get("plan_review_status") == "CHANGES_REQUIRED"
        )
        if not first_plan and not revising:
            raise ProgramError(
                "planning is permitted only after READY intake or requested plan changes"
            )
        seeds = set(seed_repositories)
        unknown = seeds - self.repositories.keys()
        if unknown:
            raise ProgramError("unknown or disabled repositories: " + ", ".join(sorted(unknown)))
        if not seeds:
            raise ProgramError("at least one seed repository is required")
        requirements = read_json(requirements_path.resolve())
        obligations = normalize_requirement_obligations(
            requirements, change_id, seeds
        )
        requirements_digest = digest(requirements)
        frozen_requirements = dict(requirements)
        frozen_requirements["digest"] = requirements_digest
        atomic_json(
            self.run_dir(change_id) / "requirements.json", frozen_requirements
        )
        validation_scope = self.downstream_closure(seeds)
        checkout_scope = self.upstream_closure(validation_scope)
        repository_impact = []
        for repository_id in sorted(self.repositories):
            if repository_id in seeds:
                disposition = "IMPLEMENTATION"
                reason = "directly implicated by the frozen requirements"
            elif repository_id in validation_scope:
                disposition = "VALIDATION_ONLY"
                reason = "downstream dependency requires regression validation"
            elif repository_id in checkout_scope:
                disposition = "CONTEXT_ONLY"
                reason = "upstream dependency is required to reproduce the tested graph"
            else:
                disposition = "NOT_IMPACTED"
                reason = "outside the approved dependency closure"
            repository_impact.append(
                {
                    "repository_id": repository_id,
                    "disposition": disposition,
                    "reason": reason,
                }
            )
        plan_revision = int(state.get("plan_revision", 0)) + 1
        plan = {
            "schema_version": "1.0",
            "change_id": change_id,
            "program_id": self.manifest["program_id"],
            "request": state["request"],
            "risk_tier": state["risk_tier"],
            "revision": plan_revision,
            "implementation_scope": sorted(seeds),
            "validation_scope": sorted(validation_scope),
            "checkout_scope": sorted(checkout_scope),
            "execution_waves": self.waves(validation_scope),
            "repository_impact": repository_impact,
            "requirements_digest": requirements_digest,
            "requirement_obligations": obligations,
            "human_gates": ["plan-approval", "pr-approval"],
            "generated_at": now(),
        }
        plan["digest"] = digest({key: value for key, value in plan.items() if key != "digest"})
        atomic_json(self.run_dir(change_id) / "plan.json", plan)
        atomic_json(
            self.run_dir(change_id) / "plan-review.template.json",
            {
                "change_id": change_id,
                "gate": "plan-review",
                "decision": "PASS",
                "reviewer": "REPLACE_WITH_INDEPENDENT_REVIEWER",
                "independent": True,
                "review_type": "REPLACE_WITH_REVIEW_TYPE",
                "reviewed_digest": plan["digest"],
                "findings": [],
                "source_url": "https://REPLACE_WITH_AUDITABLE_REVIEW_RECORD",
            },
        )
        state.update(
            {
                "state": "AWAITING_PLAN_REVIEW",
                "plan_revision": plan_revision,
                "plan_review_status": "PENDING",
                "plan_reviews": [],
                "plan_digest": plan["digest"],
                "implementation_scope": plan["implementation_scope"],
                "validation_scope": plan["validation_scope"],
                "checkout_scope": plan["checkout_scope"],
                "execution_waves": plan["execution_waves"],
                "repository_impact": plan["repository_impact"],
                "requirements_digest": requirements_digest,
                "requirement_obligations": obligations,
            }
        )
        self.append_event(
            change_id,
            state,
            "PLAN_PREPARED" if first_plan else "PLAN_REVISED",
            {
                "plan_digest": plan["digest"],
                "requirements_digest": requirements_digest,
                "requirement_ids": [item["id"] for item in obligations],
                "repositories": plan["validation_scope"],
                "repository_impact_count": len(plan["repository_impact"]),
            },
        )
        self.write_state(change_id, state)
        return plan

    def record_plan_review(
        self, change_id: str, evidence_path: Path
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "AWAITING_PLAN_REVIEW":
            raise ProgramError("plan review is not expected in the current state")
        if state.get("plan_review_status") == "CHANGES_REQUIRED":
            raise ProgramError(
                "the plan must be revised before it can be reviewed again"
            )
        evidence = read_json(evidence_path.resolve())
        if evidence.get("change_id") != change_id:
            raise ProgramError("plan review change_id does not match the run")
        if evidence.get("gate") != "plan-review":
            raise ProgramError("plan review evidence must identify plan-review")
        decision = evidence.get("decision")
        if decision not in PLAN_REVIEW_DECISIONS:
            raise ProgramError(
                "plan review decision must be PASS or CHANGES_REQUIRED"
            )
        if evidence.get("reviewed_digest") != state.get("plan_digest"):
            raise ProgramError("plan review is stale or bound to a different plan")
        reviewer = reject_placeholder(evidence.get("reviewer"), "plan reviewer")
        if reviewer.casefold() == str(state.get("requested_by", "")).casefold():
            raise ProgramError("plan reviewer must be independent from the requester")
        if evidence.get("independent") is not True:
            raise ProgramError("plan review must attest independent review")
        review_type = evidence.get("review_type")
        if review_type not in PLAN_REVIEW_TYPES:
            raise ProgramError(
                "plan review_type must be requirements, architecture, testing, "
                "security or adversarial"
            )
        source_url = reject_placeholder(
            evidence.get("source_url"), "plan review source_url"
        )
        if not source_url.startswith("https://"):
            raise ProgramError("plan review source_url must use HTTPS")
        findings = evidence.get("findings", [])
        if not isinstance(findings, list) or not all(
            isinstance(item, str) and item.strip() for item in findings
        ):
            raise ProgramError("plan review findings must be a string array")
        if decision == "CHANGES_REQUIRED" and not findings:
            raise ProgramError("CHANGES_REQUIRED review must contain findings")

        current_passes = [
            item
            for item in state.get("plan_reviews", [])
            if item.get("decision") == "PASS"
            and item.get("reviewed_digest") == state.get("plan_digest")
        ]
        if any(
            item["reviewer"].casefold() == reviewer.casefold()
            for item in current_passes
        ):
            raise ProgramError("each passing plan review requires a distinct reviewer")
        if decision == "PASS" and any(
            item["review_type"] == review_type for item in current_passes
        ):
            raise ProgramError(
                "each passing plan review requires a distinct review_type"
            )

        round_number = len(state.get("plan_reviews", [])) + 1
        destination = (
            self.run_dir(change_id)
            / "plan-reviews"
            / f"revision-{state['plan_revision']}"
            / f"round-{round_number}.json"
        )
        atomic_json(destination, evidence)
        review = {
            "round": round_number,
            "revision": state["plan_revision"],
            "decision": decision,
            "reviewer": reviewer,
            "review_type": review_type,
            "reviewed_digest": state["plan_digest"],
            "findings": findings,
            "evidence_path": str(
                destination.relative_to(self.run_dir(change_id))
            ).replace("\\", "/"),
            "evidence_sha256": file_digest(destination),
        }
        state.setdefault("plan_reviews", []).append(review)
        if decision == "CHANGES_REQUIRED":
            state["plan_review_status"] = "CHANGES_REQUIRED"
            event_type = "PLAN_REVIEW_CHANGES_REQUIRED"
        else:
            passes = [
                item
                for item in state["plan_reviews"]
                if item.get("decision") == "PASS"
                and item.get("reviewed_digest") == state.get("plan_digest")
            ]
            required = int(state["required_plan_reviews"])
            if len(passes) >= required:
                state["state"] = "AWAITING_PLAN_APPROVAL"
                state["plan_review_status"] = "PASS"
                event_type = "PLAN_REVIEW_COMPLETED"
            else:
                state["plan_review_status"] = "IN_PROGRESS"
                event_type = "PLAN_REVIEW_PASSED"
        self.append_event(change_id, state, event_type, review)
        self.write_state(change_id, state)
        return state

    def _validated_current_plan_reviews(
        self, change_id: str, state: dict[str, Any]
    ) -> list[dict[str, Any]]:
        reviews = [
            item
            for item in state.get("plan_reviews", [])
            if item.get("decision") == "PASS"
            and item.get("reviewed_digest") == state.get("plan_digest")
        ]
        seen_reviewers: set[str] = set()
        seen_types: set[str] = set()
        for review in reviews:
            path = self.run_dir(change_id) / safe_relative_path(
                review.get("evidence_path"), "plan review evidence_path"
            )
            if (
                not path.is_file()
                or file_digest(path) != review.get("evidence_sha256")
            ):
                raise ProgramError(
                    "plan review evidence is missing or digest-mismatched"
                )
            evidence = read_json(path)
            if (
                evidence.get("decision") != "PASS"
                or evidence.get("reviewed_digest") != state.get("plan_digest")
                or evidence.get("reviewer") != review.get("reviewer")
                or evidence.get("review_type") != review.get("review_type")
            ):
                raise ProgramError("plan review evidence does not match durable state")
            reviewer_key = str(review["reviewer"]).casefold()
            if reviewer_key in seen_reviewers or review["review_type"] in seen_types:
                raise ProgramError("plan review independence is not unique")
            seen_reviewers.add(reviewer_key)
            seen_types.add(review["review_type"])
        return reviews

    def approve_plan(self, change_id: str, evidence_path: Path) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "AWAITING_PLAN_APPROVAL":
            raise ProgramError("plan approval is not expected in the current state")
        evidence = read_json(evidence_path.resolve())
        passing_reviews = self._validated_current_plan_reviews(change_id, state)
        if len(passing_reviews) < int(state.get("required_plan_reviews", 1)):
            raise ProgramError("plan has not completed the required review cycles")
        self._validate_human_evidence(
            state, evidence, "plan-approval", state["plan_digest"]
        )
        destination = self.run_dir(change_id) / "approvals" / "plan-approval.json"
        atomic_json(destination, evidence)
        state["state"] = "PLAN_APPROVED"
        state["plan_approval"] = {
            "approver": evidence["approver"],
            "source_url": evidence["source_url"],
            "reviewed_artifact_url": evidence["reviewed_artifact_url"],
            "evidence_sha256": file_digest(destination),
        }
        self.append_event(change_id, state, "PLAN_APPROVED", state["plan_approval"])
        self.write_state(change_id, state)
        return state

    @staticmethod
    def _validate_human_evidence(
        state: dict[str, Any],
        evidence: dict[str, Any],
        gate: str,
        reviewed_digest: str,
    ) -> None:
        if evidence.get("change_id") != state["change_id"]:
            raise ProgramError("approval change_id does not match the run")
        if evidence.get("gate") != gate or evidence.get("decision") != "APPROVED":
            raise ProgramError(f"evidence must explicitly approve {gate}")
        if evidence.get("reviewed_digest") != reviewed_digest:
            raise ProgramError("approval is stale or bound to a different artifact")
        approver = evidence.get("approver")
        approver = reject_placeholder(approver, "approval approver")
        if approver.casefold() == str(state.get("requested_by", "")).casefold():
            raise ProgramError("approval must be independent from the change requester")
        if evidence.get("independent") is not True:
            raise ProgramError("approval evidence must attest independent review")
        source_url = evidence.get("source_url")
        source_url = reject_placeholder(source_url, "approval source_url")
        if not source_url.startswith("https://"):
            raise ProgramError("approval must include an HTTPS source URL")
        reviewed_artifact_url = evidence.get("reviewed_artifact_url")
        if (
            not reject_placeholder(
                reviewed_artifact_url, "approval reviewed_artifact_url"
            ).startswith("https://")
        ):
            raise ProgramError(
                "approval must link the immutable plan or PR-set artifact reviewed "
                "by the human"
            )

    def repository_path(self, repository_id: str) -> Path:
        path = (self.workspace_root / self.repositories[repository_id]["local_path"]).resolve()
        try:
            path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ProgramError(
                f"{repository_id}: local path escapes workspace_root"
            ) from exc
        return path

    @staticmethod
    def _extension_resource(
        worktree: Path, kind: str, entry: dict[str, Any]
    ) -> dict[str, Any]:
        relative = safe_relative_path(entry["path"], f"{kind}.{entry['id']}.path")
        path = (worktree / relative).resolve()
        try:
            path.relative_to(worktree.resolve())
        except ValueError as exc:
            raise ProgramError(
                f"{kind}.{entry['id']}: extension path escapes the repository"
            ) from exc
        if not path.is_file():
            raise ProgramError(
                f"{kind}.{entry['id']}: declared extension file is missing: {relative}"
            )
        size = path.stat().st_size
        if size > MAX_EXTENSION_FILE_BYTES:
            raise ProgramError(
                f"{kind}.{entry['id']}: extension file exceeds "
                f"{MAX_EXTENSION_FILE_BYTES} bytes"
            )
        result = {
            "id": entry["id"],
            "path": relative.as_posix(),
            "sha256": file_digest(path),
            "size_bytes": size,
            "required": entry.get("required", True) is True,
        }
        if kind == "agents":
            result["role"] = entry["role"]
        return result

    def _gts_catalog_root(self) -> Path:
        """Resolve the in-repository GTS catalog or a compatible external source."""
        candidates: list[Path] = [self.root]
        configured = os.environ.get("GTS_AI_SDLC_ROOT")
        if configured:
            candidates.append(Path(configured).expanduser().resolve())
        candidates.append((self.root.parent / "gts.ai.sdlc").resolve())
        for candidate in candidates:
            if (
                (candidate / ".agents/skills").is_dir()
                and (candidate / ".github/agents").is_dir()
            ):
                return candidate

        archive = (self.root.parent / "sdlc" / "sdlc-master.zip").resolve()
        if not archive.is_file():
            return candidates[-1]
        archive_sha = file_digest(archive)
        cache_parent = (
            self.root / ".github/sdlc/expert-cache/gts-ai-sdlc" / archive_sha
        ).resolve()
        catalog_root = cache_parent / "gts.ai.sdlc-master"
        marker = cache_parent / ".complete"
        if marker.is_file() and catalog_root.is_dir():
            return catalog_root
        cache_parent.mkdir(parents=True, exist_ok=True)
        total_uncompressed = 0
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            for member in members:
                relative = PurePosixPath(member.filename)
                if (
                    "\\" in member.filename
                    or relative.is_absolute()
                    or ".." in relative.parts
                    or not relative.parts
                    or relative.parts[0] != "gts.ai.sdlc-master"
                    or ((member.external_attr >> 16) & 0o170000) == 0o120000
                ):
                    raise ProgramError("GTS SDLC archive contains an unsafe path")
                total_uncompressed += member.file_size
                if total_uncompressed > 50 * 1024 * 1024:
                    raise ProgramError("GTS SDLC archive exceeds the 50 MiB limit")
            bundle.extractall(cache_parent)
        if not (
            (catalog_root / ".agents/skills").is_dir()
            and (catalog_root / ".github/agents").is_dir()
        ):
            raise ProgramError(
                "GTS SDLC archive does not contain the expected catalog"
            )
        marker.write_text(archive_sha + "\n", encoding="utf-8")
        return catalog_root

    def _fallback_extension_resource(
        self, kind: str, entry: dict[str, Any]
    ) -> dict[str, Any] | None:
        catalog_root = self._gts_catalog_root()
        declared = Path(str(entry["path"]))
        resource_path = (self.root.parent / declared).resolve()
        try:
            resource_path.relative_to(catalog_root)
        except ValueError:
            return None
        if not resource_path.is_file():
            return None
        size = resource_path.stat().st_size
        if size > MAX_EXTENSION_FILE_BYTES:
            return None
        result = {
            "id": entry["id"],
            "path": workspace_relative(resource_path, self.root.parent),
            "sha256": file_digest(resource_path),
            "size_bytes": size,
            "required": True,
            "source": "central-gts-ai-sdlc-fallback",
        }
        if kind == "agents":
            result["role"] = entry["role"]
        return result

    @staticmethod
    def _catalog_id_from_path(path: Path) -> str:
        stem = path.stem
        if stem.lower() == "skill":
            stem = path.parent.name
        sanitized = stem.replace("_", "-").replace(" ", "-").lower()
        return re.sub(r"[^a-z0-9._-]", "-", sanitized)

    def _repository_system(self, repository_id: str) -> str:
        repository = self.repositories.get(repository_id, {})
        configured = str(repository.get("system", "")).strip().lower()
        if configured:
            if not SYSTEM_ID_RE.fullmatch(configured):
                raise ProgramError(
                    f"{repository_id}: system must match {SYSTEM_ID_RE.pattern}"
                )
            return configured
        for legacy in ("p7", "t7"):
            if repository_id.startswith(f"{legacy}-"):
                return legacy
        return "generic"

    def _discover_gts_catalog(
        self, repository_id: str
    ) -> dict[str, list[dict[str, Any]]]:
        root = self._gts_catalog_root()
        skills_root = root / ".agents" / "skills"
        agents_root = root / ".github" / "agents"

        system_key = self._repository_system(repository_id)

        skills: list[dict[str, Any]] = []
        for skill_path in sorted((skills_root / "common").glob("**/SKILL.md")):
            rel = workspace_relative(skill_path, self.root.parent)
            skills.append(
                {
                    "id": f"common-{self._catalog_id_from_path(skill_path)}",
                    "path": rel,
                    "activate_when": {},
                }
            )
        for skill_path in sorted(
            (skills_root / "systems" / system_key).glob("**/SKILL.md")
        ):
            rel = workspace_relative(skill_path, self.root.parent)
            skills.append(
                {
                    "id": f"{system_key}-{self._catalog_id_from_path(skill_path)}",
                    "path": rel,
                    "activate_when": {},
                }
            )

        agents: list[dict[str, Any]] = []
        for agent_path in sorted(agents_root.glob(f"{system_key}-*.agent.md")):
            rel = workspace_relative(agent_path, self.root.parent)
            agent_id = self._catalog_id_from_path(agent_path)
            role = "implementation"
            if "review" in agent_id:
                role = "independent-domain-review"
            elif "test" in agent_id:
                role = "testing"
            elif "build" in agent_id:
                role = "build"
            elif "spec" in agent_id:
                role = "spec-authoring"
            elif "architect" in agent_id:
                role = "architecture"
            elif "planner" in agent_id:
                role = "planning"
            agents.append(
                {
                    "id": agent_id,
                    "path": rel,
                    "role": role,
                    "activate_when": {},
                }
            )
        for agent_path in sorted(agents_root.glob("gts-*.agent.md")):
            rel = workspace_relative(agent_path, self.root.parent)
            agent_id = self._catalog_id_from_path(agent_path)
            agents.append(
                {
                    "id": agent_id,
                    "path": rel,
                    "role": "orchestration-support",
                    "activate_when": {},
                }
            )

        return {"skills": skills, "agents": agents}

    def _fallback_extensions_for_repository(
        self,
        *,
        repository: dict[str, Any],
        mode: str,
        risk_tier: str,
        request: str,
    ) -> dict[str, list[dict[str, Any]]]:
        repository_id = str(repository.get("id", ""))
        discovered_catalog = self._discover_gts_catalog(repository_id)

        selected: dict[str, list[dict[str, Any]]] = {
            kind: [] for kind in EXTENSION_KINDS
        }
        for kind in ("skills", "agents"):
            for entry in discovered_catalog.get(kind, []):
                if extension_is_active(
                    entry,
                    mode=mode,
                    risk_tier=risk_tier,
                    request=request,
                ):
                    resolved = self._fallback_extension_resource(kind, entry)
                    if resolved:
                        selected[kind].append(resolved)
        return selected

    def resolve_repository_extensions(
        self,
        change_id: str,
        repository_id: str,
        worktree: Path,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        repository = self.repositories[repository_id]
        mode = (
            "implementation"
            if repository_id in state["implementation_scope"]
            else "validation"
        )
        configured_manifest = repository.get(
            "extensions_config", ".github/sdlc/extensions.json"
        )
        extension_relative = safe_relative_path(
            configured_manifest, f"{repository_id}.extensions_config"
        )
        extension_path = (worktree / extension_relative).resolve()
        try:
            extension_path.relative_to(worktree.resolve())
        except ValueError as exc:
            raise ProgramError(
                f"{repository_id}: extensions_config escapes the repository"
            ) from exc

        extension: dict[str, Any] = {
            "schema_version": "1.0",
            "repository_id": repository_id,
        }
        manifest_status = "ABSENT"
        manifest_sha256 = None
        if extension_path.is_file():
            extension = read_json(extension_path)
            errors = validate_extension_manifest(extension, repository_id)
            if errors:
                raise ProgramError(
                    f"{repository_id}: invalid repository extension manifest:\n- "
                    + "\n- ".join(errors)
                )
            manifest_status = "PRESENT"
            manifest_sha256 = file_digest(extension_path)
        elif repository.get("extensions_required") is True:
            raise ProgramError(
                f"{repository_id}: required extension manifest is missing: "
                f"{extension_relative.as_posix()}"
            )

        selected: dict[str, list[dict[str, Any]]] = {
            kind: [] for kind in EXTENSION_KINDS
        }
        for kind in EXTENSION_KINDS:
            for entry in extension.get(kind, []):
                if extension_is_active(
                    entry,
                    mode=mode,
                    risk_tier=state["risk_tier"],
                    request=state["request"],
                ):
                    selected[kind].append(
                        self._extension_resource(worktree, kind, entry)
                    )

        used_fallback = False
        if (
            manifest_status == "ABSENT"
            or (
                len(selected["skills"]) == 0
                and len(selected["agents"]) == 0
            )
        ):
            fallback_selected = self._fallback_extensions_for_repository(
                repository={"id": repository_id, **repository},
                mode=mode,
                risk_tier=state["risk_tier"],
                request=state["request"],
            )
            if fallback_selected["skills"] or fallback_selected["agents"]:
                selected["skills"].extend(fallback_selected["skills"])
                selected["agents"].extend(fallback_selected["agents"])
                used_fallback = True

        quality_source = "unconfigured"
        quality_path_value = None
        quality_base = None
        if repository.get("quality_config"):
            quality_source = "program-repository-entry"
            quality_path_value = repository["quality_config"]
            quality_base = worktree
        elif extension.get("quality_config"):
            quality_source = "repository-extension"
            quality_path_value = extension["quality_config"]
            quality_base = worktree
        else:
            default_quality = self.manifest.get("default_quality_configs", {}).get(
                repository["stack"]
            )
            if default_quality:
                quality_source = "central-stack-default"
                quality_path_value = default_quality
                quality_base = self.root

        quality: dict[str, Any] = {"source": quality_source, "configured": False}
        if quality_path_value and quality_base:
            relative_quality = safe_relative_path(
                quality_path_value, f"{repository_id}.quality_config"
            )
            resolved_quality = (quality_base / relative_quality).resolve()
            try:
                resolved_quality.relative_to(quality_base.resolve())
            except ValueError as exc:
                raise ProgramError(
                    f"{repository_id}: quality config escapes its configured base"
                ) from exc
            quality.update(
                {
                    "configured": True,
                    "path": relative_quality.as_posix(),
                    "base": (
                        "repository"
                        if quality_base.resolve() == worktree.resolve()
                        else "control-plane"
                    ),
                    "exists": resolved_quality.is_file(),
                }
            )
            if resolved_quality.is_file():
                quality["sha256"] = file_digest(resolved_quality)

        packet: dict[str, Any] = {
            "schema_version": "1.0",
            "change_id": change_id,
            "repository_id": repository_id,
            "repository_commit": run_command(["git", "rev-parse", "HEAD"], worktree),
            "mode": mode,
            "risk_tier": state["risk_tier"],
            "manifest": {
                "status": manifest_status,
                "path": extension_relative.as_posix(),
                "sha256": manifest_sha256,
            },
            "instructions": selected["instructions"],
            "skills": selected["skills"],
            "agents": selected["agents"],
            "quality_config": quality,
            "selection_policy": (
                "enabled entries must match mode, risk tier, and at least one "
                "configured request term"
            ),
            "selection_source": (
                "central-gts-ai-sdlc-fallback"
                if used_fallback
                else "repository-extension-manifest"
            ),
            "trust_boundary": (
                "repository extensions may add context and controls but cannot "
                "weaken central gates, approve, merge, or write program state"
            ),
        }
        packet["digest"] = digest(packet)
        destination = (
            self.run_dir(change_id)
            / "repository-extensions"
            / f"{repository_id}.json"
        )
        atomic_json(destination, packet)
        return packet

    def persist_repository_extensions(
        self, change_id: str, state: dict[str, Any]
    ) -> str:
        artifact: dict[str, Any] = {
            "schema_version": "1.0",
            "change_id": change_id,
            "repositories": state["repository_extensions"],
        }
        artifact["digest"] = digest(artifact)
        atomic_json(self.run_dir(change_id) / "repository-extensions.json", artifact)
        state["repository_extensions_digest"] = artifact["digest"]
        return artifact["digest"]

    def repository_extension_packet(
        self, change_id: str, repository_id: str
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        packet = state.get("repository_extensions", {}).get(repository_id)
        if not isinstance(packet, dict):
            raise ProgramError(
                f"{repository_id}: repository extensions have not been resolved"
            )
        return packet

    def refresh_repository_extensions(
        self, change_id: str, repository_id: str
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] not in {"WORKSPACES_READY", "EXECUTING"}:
            raise ProgramError(
                "repository extensions may be refreshed only during execution"
            )
        if repository_id not in state.get("checkout_scope", []):
            raise ProgramError(f"{repository_id}: not in the checkout scope")
        vector = state.get("commit_vector", {}).get(repository_id)
        if not isinstance(vector, dict):
            raise ProgramError(f"{repository_id}: workspace is not prepared")
        worktree = Path(vector["worktree"])
        packet = self.resolve_repository_extensions(
            change_id, repository_id, worktree, state
        )
        state["repository_extensions"][repository_id] = packet
        state["commit_vector"][repository_id]["head_sha"] = packet[
            "repository_commit"
        ]
        state["commit_vector"][repository_id][
            "repository_extension_digest"
        ] = packet["digest"]
        extensions_digest = self.persist_repository_extensions(change_id, state)
        vector_digest = self.persist_commit_vector(change_id, state)
        self.append_event(
            change_id,
            state,
            "REPOSITORY_EXTENSIONS_REFRESHED",
            {
                "repository_id": repository_id,
                "repository_extension_digest": packet["digest"],
                "repository_extensions_digest": extensions_digest,
                "commit_vector_digest": vector_digest,
            },
        )
        self.write_state(change_id, state)
        return packet

    def inventory_repository(self, repository_id: str) -> dict[str, Any]:
        repository = self.repositories[repository_id]
        path = self.repository_path(repository_id)
        result: dict[str, Any] = {
            "repository_id": repository_id,
            "path": str(path),
            "expected_remote": repository["url"],
        }
        if not path.exists():
            result["status"] = "MISSING"
            return result
        if not (path / ".git").exists():
            result["status"] = "NOT_GIT"
            return result
        actual_remote = run_command(["git", "remote", "get-url", "origin"], path, check=False)
        result["actual_remote"] = actual_remote
        if normalize_remote(actual_remote) != normalize_remote(repository["url"]):
            result["status"] = "REMOTE_MISMATCH"
            return result
        status = run_command(["git", "status", "--porcelain"], path)
        result["dirty"] = bool(status)
        result["head_sha"] = run_command(["git", "rev-parse", "HEAD"], path)
        result["branch"] = run_command(
            ["git", "branch", "--show-current"], path, check=False
        )
        result["status"] = "DIRTY" if status else "READY"
        return result

    def inventory(self, change_id: str) -> list[dict[str, Any]]:
        state = self.read_state(change_id)
        if "checkout_scope" not in state:
            raise ProgramError("prepare a plan before inventorying repositories")
        return [
            self.inventory_repository(repository_id)
            for repository_id in state["checkout_scope"]
        ]

    def prepare_workspaces(
        self, change_id: str, *, execute: bool, allow_clone: bool
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "PLAN_APPROVED":
            raise ProgramError("workspaces may be prepared only after plan approval")
        inventory = self.inventory(change_id)
        blockers = [
            item
            for item in inventory
            if item["status"] not in ({"READY", "MISSING"} if allow_clone else {"READY"})
        ]
        if blockers:
            detail = ", ".join(
                f"{item['repository_id']}={item['status']}" for item in blockers
            )
            raise ProgramError(f"workspace inventory contains blockers: {detail}")
        if not execute:
            return {"decision": "DRY_RUN", "inventory": inventory}

        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.worktree_root.mkdir(parents=True, exist_ok=True)
        vector: dict[str, Any] = {}
        state["repository_extensions"] = {}
        for repository_id in state["checkout_scope"]:
            repository = self.repositories[repository_id]
            checkout = self.repository_path(repository_id)
            if not checkout.exists():
                if not allow_clone:
                    raise ProgramError(f"{repository_id}: clone is not allowed")
                checkout.parent.mkdir(parents=True, exist_ok=True)
                run_command(["git", "clone", repository["url"], str(checkout)], self.workspace_root)
            current = self.inventory_repository(repository_id)
            if current["status"] != "READY":
                raise ProgramError(
                    f"{repository_id}: repository became unsafe: {current['status']}"
                )
            branch = f"{self.manifest.get('branch_prefix', 'change/')}{change_id}/{repository_id}"
            run_command(
                ["git", "fetch", "--prune", "origin", repository["default_branch"]],
                checkout,
            )
            base_ref = f"origin/{repository['default_branch']}"
            base_sha = run_command(["git", "rev-parse", base_ref], checkout)
            worktree = (self.worktree_root / change_id / repository_id).resolve()
            if worktree.exists():
                actual_branch = run_command(
                    ["git", "branch", "--show-current"], worktree, check=False
                )
                if actual_branch != branch:
                    raise ProgramError(
                        f"{repository_id}: existing worktree uses {actual_branch!r}, expected {branch!r}"
                    )
                if run_command(["git", "status", "--porcelain"], worktree):
                    raise ProgramError(f"{repository_id}: existing worktree is dirty")
            else:
                worktree.parent.mkdir(parents=True, exist_ok=True)
                branch_exists = bool(
                    run_command(
                        ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                        checkout,
                        check=False,
                    )
                )
                args = ["git", "worktree", "add"]
                if not branch_exists:
                    args.extend(["-b", branch])
                args.extend([str(worktree), branch if branch_exists else base_ref])
                run_command(args, checkout)
            vector[repository_id] = {
                "base_sha": base_sha,
                "head_sha": run_command(["git", "rev-parse", "HEAD"], worktree),
                "branch": branch,
                "worktree": str(worktree),
                "mode": (
                    "implementation"
                    if repository_id in state["implementation_scope"]
                    else "validation"
                ),
            }
            packet = self.resolve_repository_extensions(
                change_id, repository_id, worktree, state
            )
            state["repository_extensions"][repository_id] = packet
            vector[repository_id]["repository_extension_digest"] = packet["digest"]

        state["commit_vector"] = vector
        extensions_digest = self.persist_repository_extensions(change_id, state)
        vector_digest = self.persist_commit_vector(change_id, state)
        state["state"] = "WORKSPACES_READY"
        self.append_event(
            change_id,
            state,
            "WORKSPACES_PREPARED",
            {
                "commit_vector_digest": vector_digest,
                "repository_extensions_digest": extensions_digest,
            },
        )
        self.write_state(change_id, state)
        return state

    def record_repository_result(
        self,
        change_id: str,
        repository_id: str,
        decision: str,
        evidence_path: Path,
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] not in {"WORKSPACES_READY", "EXECUTING"}:
            raise ProgramError("repository results are not accepted in the current state")
        if repository_id not in state["validation_scope"]:
            raise ProgramError(f"{repository_id}: not in the validation scope")
        if decision not in DECISIONS:
            raise ProgramError(f"decision must be one of {sorted(DECISIONS)}")
        evidence = read_json(evidence_path.resolve())
        if (
            evidence.get("change_id") != change_id
            or evidence.get("repository_id") != repository_id
            or evidence.get("decision") != decision
        ):
            raise ProgramError("repository evidence does not match the change and decision")
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        actual_sha = run_command(["git", "rev-parse", "HEAD"], worktree)
        if evidence.get("commit_sha") != actual_sha:
            raise ProgramError("repository evidence is stale or bound to another commit")
        if (
            repository_id not in state["implementation_scope"]
            and actual_sha != state["commit_vector"][repository_id]["base_sha"]
        ):
            raise ProgramError(
                f"{repository_id}: unplanned implementation change in a validation-only "
                "repository; prepare a new plan and obtain new human approval"
            )
        packet = state.get("repository_extensions", {}).get(repository_id)
        if not isinstance(packet, dict):
            raise ProgramError("repository extension packet is missing")
        if packet.get("repository_commit") != actual_sha:
            raise ProgramError(
                "repository extension packet is stale; refresh extensions at the current HEAD"
            )
        if evidence.get("repository_extension_digest") != packet.get("digest"):
            raise ProgramError(
                "repository evidence is not bound to the selected extension packet"
            )
        if decision == "PASS":
            validate_pass_gates(
                evidence.get("gates"),
                "repository",
                allow_optional_non_pass=True,
            )
            passed_gate_ids = {
                gate["id"]
                for gate in evidence["gates"]
                if gate.get("status") == "PASS"
            }
            changed_files = {
                path
                for path in run_command(
                    [
                        "git",
                        "diff",
                        "--name-only",
                        state["commit_vector"][repository_id]["base_sha"],
                        actual_sha,
                    ],
                    worktree,
                ).splitlines()
                if path
            }
            coverage = evidence.get("requirement_coverage")
            if not isinstance(coverage, list):
                raise ProgramError(
                    "PASS repository evidence requires requirement_coverage"
                )
            expected_ids = {
                item["id"]
                for item in state.get("requirement_obligations", [])
                if repository_id in item["repositories"]
            }
            observed_ids: set[str] = set()
            for index, item in enumerate(coverage):
                if not isinstance(item, dict):
                    raise ProgramError(
                        f"repository requirement coverage {index} must be an object"
                    )
                requirement_id = item.get("requirement_id")
                if requirement_id not in expected_ids:
                    raise ProgramError(
                        f"{repository_id}: unknown or unassigned requirement coverage "
                        f"{requirement_id!r}"
                    )
                if requirement_id in observed_ids:
                    raise ProgramError(
                        f"{repository_id}: duplicate requirement coverage "
                        f"{requirement_id}"
                    )
                observed_ids.add(requirement_id)
                implementation_files = item.get("implementation_files")
                test_ids = item.get("test_ids")
                evidence_refs = item.get("evidence_refs")
                if (
                    not isinstance(implementation_files, list)
                    or not implementation_files
                    or not all(
                        isinstance(path, str)
                        and safe_relative_path(
                            path,
                            f"{repository_id}.{requirement_id}.implementation_files",
                        )
                        for path in implementation_files
                    )
                    or not isinstance(test_ids, list)
                    or not test_ids
                    or not all(isinstance(test, str) and test.strip() for test in test_ids)
                    or not isinstance(evidence_refs, list)
                    or not evidence_refs
                    or not all(
                        isinstance(reference, str) and reference.strip()
                        for reference in evidence_refs
                    )
                ):
                    raise ProgramError(
                        f"{repository_id}: {requirement_id} requires implementation "
                        "files, test IDs and evidence references"
                    )
                for field in ("acceptance_criteria_ids", "evidence_types"):
                    values = item.get(field)
                    if not isinstance(values, list) or not all(
                        isinstance(value, str) and value.strip() for value in values
                    ):
                        raise ProgramError(
                            f"{repository_id}: {requirement_id} {field} must be a list"
                        )
                obligation = next(
                    obligation
                    for obligation in state["requirement_obligations"]
                    if obligation["id"] == requirement_id
                )
                verification_entries = [
                    entry
                    for entry in obligation["verification"]
                    if entry["scope"] == "repository"
                    and entry["repository"] == repository_id
                ]
                expected_test_ids = {
                    gate_id
                    for entry in verification_entries
                    for gate_id in entry["gate_ids"]
                }
                expected_criteria = {
                    criterion_id
                    for entry in verification_entries
                    for criterion_id in entry["acceptance_criteria_ids"]
                }
                expected_evidence = {
                    evidence_type
                    for entry in verification_entries
                    for evidence_type in entry["evidence_types"]
                }
                if set(test_ids) != expected_test_ids:
                    raise ProgramError(
                        f"{repository_id}: {requirement_id} test IDs do not match "
                        "the approved verification matrix"
                    )
                if not expected_test_ids.issubset(passed_gate_ids):
                    raise ProgramError(
                        f"{repository_id}: {requirement_id} verification gates did "
                        "not all PASS"
                    )
                if set(item["acceptance_criteria_ids"]) != expected_criteria:
                    raise ProgramError(
                        f"{repository_id}: {requirement_id} acceptance criteria do "
                        "not match the approved verification matrix"
                    )
                if set(item["evidence_types"]) != expected_evidence:
                    raise ProgramError(
                        f"{repository_id}: {requirement_id} evidence types do not "
                        "match the approved verification matrix"
                    )
                if not set(implementation_files).issubset(changed_files):
                    raise ProgramError(
                        f"{repository_id}: {requirement_id} implementation files "
                        "are not changed by the tested commit"
                    )
            if observed_ids != expected_ids:
                missing_ids = sorted(expected_ids - observed_ids)
                raise ProgramError(
                    f"{repository_id}: missing requirement coverage: "
                    + ", ".join(missing_ids)
                )
        elif decision == "BLOCKED_SPEC":
            reason = evidence.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ProgramError(
                    "BLOCKED_SPEC repository evidence requires a non-empty reason"
                )
        destination = (
            self.run_dir(change_id)
            / "repository-evidence"
            / repository_id
            / f"attempt-{int(state['remediation_cycles'].get(repository_id, 0)) + 1}.json"
        )
        atomic_json(destination, evidence)
        state["commit_vector"][repository_id]["head_sha"] = actual_sha
        self.persist_commit_vector(change_id, state)
        state["repository_results"][repository_id] = {
            "decision": decision,
            "commit_sha": actual_sha,
            "repository_extension_digest": packet["digest"],
            "evidence_path": destination.relative_to(
                self.run_dir(change_id)
            ).as_posix(),
            "evidence_sha256": file_digest(destination),
            "recorded_at": now(),
        }
        if decision == "BLOCKED_SPEC":
            state["state"] = "BLOCKED_SPEC"
        elif decision != "PASS":
            count = int(state["remediation_cycles"].get(repository_id, 0)) + 1
            state["remediation_cycles"][repository_id] = count
            maximum = int(self.manifest["controls"]["maximum_remediation_cycles"])
            state["state"] = "FAIL" if count >= maximum else "EXECUTING"
        else:
            state["state"] = "EXECUTING"
        self.append_event(
            change_id,
            state,
            "REPOSITORY_RESULT_RECORDED",
            {"repository_id": repository_id, "decision": decision, "commit_sha": actual_sha},
        )
        self.write_state(change_id, state)
        return state

    def record_integration_result(
        self, change_id: str, evidence_path: Path
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "EXECUTING":
            raise ProgramError("integration evidence is not accepted in the current state")
        missing = [
            repository_id
            for repository_id in state["validation_scope"]
            if state["repository_results"].get(repository_id, {}).get("decision") != "PASS"
        ]
        if missing:
            raise ProgramError("repositories without PASS evidence: " + ", ".join(missing))
        current_vector: dict[str, str] = {}
        for repository_id in state["validation_scope"]:
            worktree = Path(state["commit_vector"][repository_id]["worktree"])
            current_head = run_command(["git", "rev-parse", "HEAD"], worktree)
            current_vector[repository_id] = current_head
            tested_head = state["repository_results"][repository_id].get(
                "commit_sha"
            )
            planned_head = state["commit_vector"][repository_id].get("head_sha")
            if current_head != tested_head or current_head != planned_head:
                raise ProgramError(
                    f"{repository_id}: repository HEAD changed after repository "
                    "gates passed; rerun repository gates before integration"
                )
        evidence = read_json(evidence_path.resolve())
        decision = evidence.get("decision")
        if (
            evidence.get("change_id") != change_id
            or decision not in DECISIONS
            or evidence.get("commit_vector") != current_vector
        ):
            raise ProgramError("integration evidence is incomplete or stale")
        if evidence.get("commit_vector_digest") != state.get(
            "commit_vector_digest"
        ):
            raise ProgramError(
                "integration evidence commit-vector digest is missing or stale"
            )
        gates = evidence.get("cross_repository_gates")
        if decision == "PASS":
            validate_pass_gates(
                gates,
                "cross-repository",
                allow_optional_non_pass=False,
            )
        else:
            if not isinstance(gates, list) or not gates:
                raise ProgramError(
                    "non-PASS integration evidence requires gate results"
                )
            seen_gate_ids: set[str] = set()
            for gate in gates:
                if (
                    not isinstance(gate, dict)
                    or not isinstance(gate.get("id"), str)
                    or not GATE_ID_RE.fullmatch(gate["id"])
                    or gate.get("status") not in DECISIONS
                ):
                    raise ProgramError("integration gate result is malformed")
                if gate["id"] in seen_gate_ids:
                    raise ProgramError(
                        f"cross-repository gate IDs must be unique: {gate['id']}"
                    )
                seen_gate_ids.add(gate["id"])
            if all(gate["status"] == "PASS" for gate in gates):
                raise ProgramError(
                    "non-PASS integration decision requires a non-PASS gate"
                )
            if decision == "BLOCKED_SPEC" and (
                not isinstance(evidence.get("reason"), str)
                or not evidence["reason"].strip()
            ):
                raise ProgramError(
                    "BLOCKED_SPEC integration evidence requires a non-empty reason"
                )
        obligation_ids = {
            item["id"] for item in state.get("requirement_obligations", [])
        }
        expected_integration = integration_verification_matrix(
            state.get("requirement_obligations", [])
        )
        observed_integration_gate_ids = {
            gate["id"] for gate in gates
        }
        if observed_integration_gate_ids != set(expected_integration):
            raise ProgramError(
                "cross-repository gate set does not match the approved "
                f"verification matrix; missing="
                f"{sorted(set(expected_integration) - observed_integration_gate_ids)}, "
                f"extra={sorted(observed_integration_gate_ids - set(expected_integration))}"
            )
        for gate in gates:
            if gate.get("commit_vector_digest") != state.get(
                "commit_vector_digest"
            ):
                raise ProgramError(
                    "cross-repository gate commit-vector digest is missing or stale"
                )
            requirement_ids = gate.get("requirement_ids")
            source_refs = gate.get("source_refs")
            if (
                not isinstance(requirement_ids, list)
                or not requirement_ids
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in requirement_ids
                )
                or not isinstance(source_refs, list)
                or not source_refs
                or not all(
                    isinstance(item, str) and item.strip() for item in source_refs
                )
            ):
                raise ProgramError(
                    "cross-repository gate traceability requires non-empty "
                    "requirement_ids and source_refs"
                )
            unknown_requirements = set(requirement_ids) - obligation_ids
            if unknown_requirements:
                raise ProgramError(
                    "cross-repository gate references unknown requirements: "
                    + ", ".join(sorted(unknown_requirements))
                )
            expected_gate = expected_integration[gate["id"]]
            if set(requirement_ids) != expected_gate["requirement_ids"]:
                raise ProgramError(
                    f"cross-repository gate {gate['id']} requirement IDs do not "
                    "match the approved verification matrix"
                )
            for field in ("acceptance_criteria_ids", "evidence_types"):
                values = gate.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value.strip() for value in values
                ):
                    raise ProgramError(
                        f"cross-repository gate {field} must be a list"
                    )
            referenced_obligations = [
                item
                for item in state["requirement_obligations"]
                if item["id"] in requirement_ids
            ]
            allowed_criteria = {
                criterion["id"]
                for item in referenced_obligations
                for criterion in item["acceptance_criteria"]
            }
            allowed_evidence_types = {
                evidence_type
                for item in referenced_obligations
                for evidence_type in item["required_evidence"]
            }
            if set(source_refs) != expected_gate["source_refs"]:
                raise ProgramError(
                    f"cross-repository gate {gate['id']} source refs do not match "
                    "the approved requirements"
                )
            unknown_criteria = set(gate["acceptance_criteria_ids"]) - allowed_criteria
            unknown_evidence_types = (
                set(gate["evidence_types"]) - allowed_evidence_types
            )
            if unknown_criteria:
                raise ProgramError(
                    "cross-repository gate references acceptance criteria outside "
                    "its requirements: "
                    + ", ".join(sorted(unknown_criteria))
                )
            if unknown_evidence_types:
                raise ProgramError(
                    "cross-repository gate references evidence types outside its "
                    "requirements: "
                    + ", ".join(sorted(unknown_evidence_types))
                )
            if (
                set(gate["acceptance_criteria_ids"])
                != expected_gate["acceptance_criteria_ids"]
            ):
                raise ProgramError(
                    f"cross-repository gate {gate['id']} acceptance criteria do "
                    "not match the approved verification matrix"
                )
            if set(gate["evidence_types"]) != expected_gate["evidence_types"]:
                raise ProgramError(
                    f"cross-repository gate {gate['id']} evidence types do not "
                    "match the approved verification matrix"
                )
            evidence_refs = gate.get("evidence_refs")
            if (
                not isinstance(evidence_refs, list)
                or not evidence_refs
                or not all(
                    isinstance(reference, str) and reference.strip()
                    for reference in evidence_refs
                )
            ):
                raise ProgramError(
                    "cross-repository gate requires non-empty evidence_refs"
                )
        if decision != "PASS":
            attempt = int(state.get("integration_remediation_cycles", 0)) + 1
            destination = (
                self.run_dir(change_id)
                / "integration-evidence"
                / f"attempt-{attempt}.json"
            )
            atomic_json(destination, evidence)
            state["integration_result"] = {
                "decision": decision,
                "evidence_path": destination.relative_to(
                    self.run_dir(change_id)
                ).as_posix(),
                "evidence_sha256": file_digest(destination),
                "recorded_at": now(),
            }
            if decision == "BLOCKED_SPEC":
                state["state"] = "BLOCKED_SPEC"
            else:
                state["integration_remediation_cycles"] = attempt
                maximum = int(
                    self.manifest["controls"]["maximum_remediation_cycles"]
                )
                state["state"] = "FAIL" if attempt >= maximum else "EXECUTING"
            self.append_event(
                change_id,
                state,
                "INTEGRATION_RESULT_RECORDED",
                {
                    "decision": decision,
                    "attempt": attempt,
                    "evidence_sha256": state["integration_result"][
                        "evidence_sha256"
                    ],
                },
            )
            self.write_state(change_id, state)
            return state
        destination = self.run_dir(change_id) / "integration-evidence.json"
        atomic_json(destination, evidence)
        for repository_id, head_sha in current_vector.items():
            state["commit_vector"][repository_id]["head_sha"] = head_sha
        self.persist_commit_vector(change_id, state)
        state["state"] = "INTEGRATION_PASSED"
        state["integration_evidence_path"] = destination.relative_to(
            self.run_dir(change_id)
        ).as_posix()
        state["integration_evidence_sha256"] = file_digest(destination)
        self.append_event(
            change_id,
            state,
            "INTEGRATION_PASSED",
            {"evidence_sha256": state["integration_evidence_sha256"]},
        )
        self.write_state(change_id, state)
        return state

    def close_plan(
        self, change_id: str, evidence_path: Path
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "INTEGRATION_PASSED":
            raise ProgramError(
                "plan closure is accepted only after integration passes"
            )
        integrity_errors = self.verify(change_id)
        if integrity_errors:
            raise ProgramError(
                "plan closure cannot use invalid run evidence: "
                + "; ".join(integrity_errors)
            )
        obligations = {
            item["id"]: item for item in state.get("requirement_obligations", [])
        }
        coverage: dict[str, dict[str, Any]] = {
            requirement_id: {
                "repositories": set(),
                "acceptance_criteria_ids": set(),
                "evidence_types": set(),
                "implementation_refs": {},
                "test_ids": set(),
                "evidence_refs": set(),
            }
            for requirement_id in obligations
        }
        for repository_id, repository_result in state["repository_results"].items():
            stored_path = (
                self.run_dir(change_id) / repository_result["evidence_path"]
            )
            repository_evidence = read_json(stored_path)
            for item in repository_evidence.get("requirement_coverage", []):
                requirement_id = item["requirement_id"]
                if requirement_id not in coverage:
                    raise ProgramError(
                        f"repository evidence references unknown requirement "
                        f"{requirement_id}"
                    )
                observed = coverage[requirement_id]
                observed["repositories"].add(repository_id)
                observed["acceptance_criteria_ids"].update(
                    item["acceptance_criteria_ids"]
                )
                observed["evidence_types"].update(item["evidence_types"])
                observed["implementation_refs"][repository_id] = sorted(
                    set(item["implementation_files"])
                )
                observed["test_ids"].update(item["test_ids"])
                observed["evidence_refs"].update(item["evidence_refs"])
        integration_path = self.run_dir(change_id) / state[
            "integration_evidence_path"
        ]
        integration_evidence = read_json(integration_path)
        for gate in integration_evidence["cross_repository_gates"]:
            for requirement_id in gate["requirement_ids"]:
                observed = coverage[requirement_id]
                obligation = obligations[requirement_id]
                expected_criteria = {
                    item["id"] for item in obligation["acceptance_criteria"]
                }
                expected_evidence_types = set(
                    obligation["required_evidence"]
                )
                observed["acceptance_criteria_ids"].update(
                    set(gate["acceptance_criteria_ids"]) & expected_criteria
                )
                observed["evidence_types"].update(
                    set(gate["evidence_types"]) & expected_evidence_types
                )
                observed["test_ids"].add(gate["id"])
                observed["evidence_refs"].update(gate["evidence_refs"])

        missing_messages: list[str] = []
        normalized_coverage: list[dict[str, Any]] = []
        for requirement_id, obligation in obligations.items():
            observed = coverage[requirement_id]
            expected_repositories = set(obligation["repositories"])
            expected_criteria = {
                item["id"] for item in obligation["acceptance_criteria"]
            }
            expected_evidence = set(obligation["required_evidence"])
            unknown_criteria = (
                observed["acceptance_criteria_ids"] - expected_criteria
            )
            unknown_evidence = observed["evidence_types"] - expected_evidence
            if unknown_criteria:
                raise ProgramError(
                    f"{requirement_id}: unknown acceptance criteria in evidence: "
                    + ", ".join(sorted(unknown_criteria))
                )
            if unknown_evidence:
                raise ProgramError(
                    f"{requirement_id}: unknown evidence types: "
                    + ", ".join(sorted(unknown_evidence))
                )
            missing_repositories = (
                expected_repositories - observed["repositories"]
            )
            missing_criteria = (
                expected_criteria - observed["acceptance_criteria_ids"]
            )
            missing_evidence = expected_evidence - observed["evidence_types"]
            if missing_repositories:
                missing_messages.append(
                    f"{requirement_id} repositories="
                    + ",".join(sorted(missing_repositories))
                )
            if missing_criteria:
                missing_messages.append(
                    f"{requirement_id} acceptance_criteria="
                    + ",".join(sorted(missing_criteria))
                )
            if missing_evidence:
                missing_messages.append(
                    f"{requirement_id} evidence_types="
                    + ",".join(sorted(missing_evidence))
                )
            normalized_coverage.append(
                {
                    "requirement_id": requirement_id,
                    "repositories": sorted(observed["repositories"]),
                    "acceptance_criteria_ids": sorted(
                        observed["acceptance_criteria_ids"]
                    ),
                    "evidence_types": sorted(observed["evidence_types"]),
                    "implementation_refs": {
                        key: value
                        for key, value in sorted(
                            observed["implementation_refs"].items()
                        )
                    },
                    "test_ids": sorted(observed["test_ids"]),
                    "evidence_refs": sorted(observed["evidence_refs"]),
                }
            )
        if missing_messages:
            raise ProgramError(
                "plan closure has missing coverage: "
                + "; ".join(missing_messages)
            )

        evidence = read_json(evidence_path.resolve())
        if (
            evidence.get("change_id") != change_id
            or evidence.get("decision") != "PASS"
            or evidence.get("plan_digest") != state["plan_digest"]
            or evidence.get("requirements_digest")
            != state["requirements_digest"]
            or evidence.get("commit_vector_digest")
            != state["commit_vector_digest"]
            or evidence.get("integration_evidence_sha256")
            != state["integration_evidence_sha256"]
        ):
            raise ProgramError(
                "plan-closure evidence is stale or not bound to the approved plan "
                "and tested commit vector"
            )
        if evidence.get("deviations") != []:
            raise ProgramError(
                "PASS plan closure cannot contain unresolved deviations"
            )
        reviews = evidence.get("mandatory_reviews")
        expected_review_types = {
            "independent-verification",
            "adversarial-review",
        }
        if not isinstance(reviews, list):
            raise ProgramError("plan closure requires mandatory independent reviews")
        review_by_type = {
            item.get("type"): item for item in reviews if isinstance(item, dict)
        }
        if set(review_by_type) != expected_review_types:
            raise ProgramError(
                "plan closure requires independent-verification and "
                "adversarial-review"
            )
        review_actors: set[str] = set()
        requester = str(state["requested_by"]).casefold()
        for review_type in sorted(expected_review_types):
            review = review_by_type[review_type]
            actor = review.get("actor")
            if (
                review.get("decision") != "PASS"
                or review.get("independent") is not True
                or not isinstance(actor, str)
                or not actor.strip()
                or actor.casefold() == requester
                or not isinstance(review.get("source_url"), str)
                or not review["source_url"].startswith("https://")
                or review.get("reviewed_plan_digest") != state["plan_digest"]
                or review.get("reviewed_commit_vector_digest")
                != state["commit_vector_digest"]
            ):
                raise ProgramError(
                    f"{review_type}: independent PASS review is missing or stale"
                )
            review_actors.add(actor.casefold())
        if len(review_actors) != len(expected_review_types):
            raise ProgramError(
                "mandatory plan-closure reviews require distinct accountable actors"
            )

        results = evidence.get("requirement_results")
        if not isinstance(results, list):
            raise ProgramError("plan closure requires requirement_results")
        result_by_id = {
            item.get("requirement_id"): item
            for item in results
            if isinstance(item, dict)
        }
        if set(result_by_id) != set(obligations):
            missing = sorted(set(obligations) - set(result_by_id))
            extra = sorted(set(result_by_id) - set(obligations))
            raise ProgramError(
                "plan closure requirement result set mismatch; "
                f"missing={missing}, extra={extra}"
            )
        for requirement_id, obligation in obligations.items():
            item = result_by_id[requirement_id]
            expected_criteria = {
                criterion["id"] for criterion in obligation["acceptance_criteria"]
            }
            criteria_results = item.get("acceptance_criteria")
            evidence_results = item.get("required_evidence")
            if (
                item.get("status") != "PASS"
                or set(item.get("repositories", []))
                != set(obligation["repositories"])
                or not isinstance(criteria_results, list)
                or not isinstance(evidence_results, list)
            ):
                raise ProgramError(
                    f"{requirement_id}: closure result is incomplete or not PASS"
                )
            criteria_by_id = {
                result.get("id"): result
                for result in criteria_results
                if isinstance(result, dict)
            }
            evidence_by_type = {
                result.get("type"): result
                for result in evidence_results
                if isinstance(result, dict)
            }
            if set(criteria_by_id) != expected_criteria:
                raise ProgramError(
                    f"{requirement_id}: acceptance-criterion result set is incomplete"
                )
            if set(evidence_by_type) != set(obligation["required_evidence"]):
                raise ProgramError(
                    f"{requirement_id}: required-evidence result set is incomplete"
                )
            for label, result_items in (
                ("acceptance criterion", criteria_by_id.values()),
                ("required evidence", evidence_by_type.values()),
            ):
                for result_item in result_items:
                    refs = result_item.get("evidence_refs")
                    if (
                        result_item.get("status") != "PASS"
                        or not isinstance(refs, list)
                        or not refs
                        or not all(
                            isinstance(reference, str) and reference.strip()
                            for reference in refs
                        )
                    ):
                        raise ProgramError(
                            f"{requirement_id}: {label} is not proven by PASS evidence"
                        )

        evidence_destination = (
            self.run_dir(change_id) / "plan-closure-evidence.json"
        )
        atomic_json(evidence_destination, evidence)
        artifact = {
            "schema_version": "1.0",
            "change_id": change_id,
            "decision": "PASS",
            "plan_digest": state["plan_digest"],
            "requirements_digest": state["requirements_digest"],
            "commit_vector_digest": state["commit_vector_digest"],
            "integration_evidence_sha256": state[
                "integration_evidence_sha256"
            ],
            "coverage": normalized_coverage,
            "mandatory_reviews": reviews,
            "deviations": [],
            "closure_evidence_sha256": file_digest(evidence_destination),
            "generated_at": now(),
        }
        artifact["digest"] = digest(artifact)
        destination = self.run_dir(change_id) / "plan-closure.json"
        atomic_json(destination, artifact)
        state["plan_closure_digest"] = artifact["digest"]
        state["plan_closure_path"] = "plan-closure.json"
        state["plan_closure_evidence_path"] = "plan-closure-evidence.json"
        state["plan_closure_evidence_sha256"] = artifact[
            "closure_evidence_sha256"
        ]
        state["state"] = "PLAN_CLOSED"
        self.append_event(
            change_id,
            state,
            "PLAN_CLOSED",
            {
                "plan_closure_digest": artifact["digest"],
                "requirements_closed": len(obligations),
            },
        )
        self.write_state(change_id, state)
        return state

    def prepare_pr_set(self, change_id: str, title: str) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "PLAN_CLOSED":
            raise ProgramError(
                "PRs may be prepared only after the plan closure gate passes"
            )
        integrity_errors = self.verify(change_id)
        if integrity_errors:
            raise ProgramError(
                "PR preparation requires valid closure evidence: "
                + "; ".join(integrity_errors)
            )
        for repository_id in state["validation_scope"]:
            worktree = Path(state["commit_vector"][repository_id]["worktree"])
            current_head = run_command(["git", "rev-parse", "HEAD"], worktree)
            if current_head != state["commit_vector"][repository_id]["head_sha"]:
                raise ProgramError(
                    f"{repository_id}: HEAD changed after plan closure; rerun "
                    "verification, integration and closure"
                )
        pull_requests = []
        for repository_id in state["implementation_scope"]:
            repository = self.repositories[repository_id]
            vector = state["commit_vector"][repository_id]
            pull_requests.append(
                {
                    "repository_id": repository_id,
                    "repository_url": repository["url"],
                    "base_branch": repository["default_branch"],
                    "head_branch": vector["branch"],
                    "head_sha": vector["head_sha"],
                    "draft": True,
                    "title": f"{change_id}: {title}",
                    "body": (
                        f"Coordinated change `{change_id}`. Plan `{state['plan_digest']}`; "
                        f"commit vector `{state['commit_vector_digest']}`; "
                        f"plan closure `{state['plan_closure_digest']}`. "
                        "Human approval and all required checks are mandatory."
                    ),
                }
            )
        artifact = {
            "schema_version": "1.0",
            "change_id": change_id,
            "pull_requests": pull_requests,
            "plan_closure_digest": state["plan_closure_digest"],
            "generated_at": now(),
        }
        artifact["digest"] = digest({key: value for key, value in artifact.items() if key != "digest"})
        atomic_json(self.run_dir(change_id) / "pr-set.json", artifact)
        state["pr_set_digest"] = artifact["digest"]
        state["state"] = "PR_SET_READY"
        self.append_event(
            change_id, state, "PR_SET_PREPARED", {"pr_set_digest": artifact["digest"]}
        )
        self.write_state(change_id, state)
        return artifact

    def record_pull_request(
        self,
        change_id: str,
        repository_id: str,
        number: int,
        url: str,
        head_sha: str,
    ) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] not in {"PR_SET_READY", "AWAITING_PR_APPROVAL"}:
            raise ProgramError("pull requests are not expected in the current state")
        if repository_id not in state["implementation_scope"]:
            raise ProgramError(f"{repository_id}: no PR is expected")
        expected_sha = state["commit_vector"][repository_id]["head_sha"]
        if head_sha != expected_sha or not SHA_RE.fullmatch(head_sha):
            raise ProgramError("PR head SHA does not match the tested commit vector")
        if number < 1 or not url.startswith("https://"):
            raise ProgramError("PR number and HTTPS URL are required")
        state["pull_requests"][repository_id] = {
            "number": number,
            "url": url,
            "head_sha": head_sha,
        }
        if set(state["pull_requests"]) == set(state["implementation_scope"]):
            state["state"] = "AWAITING_PR_APPROVAL"
        self.append_event(
            change_id,
            state,
            "PULL_REQUEST_RECORDED",
            {"repository_id": repository_id, "number": number, "head_sha": head_sha},
        )
        self.write_state(change_id, state)
        return state

    def approve_pr_set(self, change_id: str, evidence_path: Path) -> dict[str, Any]:
        state = self.read_state(change_id)
        if state["state"] != "AWAITING_PR_APPROVAL":
            raise ProgramError("PR approval is not expected in the current state")
        evidence = read_json(evidence_path.resolve())
        self._validate_human_evidence(
            state, evidence, "pr-approval", state["pr_set_digest"]
        )
        approved = {
            item.get("repository_id"): item
            for item in evidence.get("approved_pull_requests", [])
            if isinstance(item, dict)
        }
        for repository_id in state["implementation_scope"]:
            expected = state["pull_requests"][repository_id]
            observed = approved.get(repository_id, {})
            reviewers = observed.get("approved_by")
            requester = str(state.get("requested_by", "")).casefold()
            independent_reviewers = (
                isinstance(reviewers, list)
                and bool(reviewers)
                and all(
                    isinstance(reviewer, str) and reviewer.strip()
                    for reviewer in reviewers
                )
                and all(reviewer.casefold() != requester for reviewer in reviewers)
            )
            if (
                observed.get("number") != expected["number"]
                or observed.get("head_sha") != expected["head_sha"]
                or observed.get("required_checks_passed") is not True
                or not independent_reviewers
            ):
                raise ProgramError(
                    f"{repository_id}: missing independent approval and checks for exact PR head"
                )
        destination = self.run_dir(change_id) / "approvals" / "pr-approval.json"
        atomic_json(destination, evidence)
        state["state"] = "PR_APPROVED"
        state["pr_approval"] = {
            "approver": evidence["approver"],
            "source_url": evidence["source_url"],
            "reviewed_artifact_url": evidence["reviewed_artifact_url"],
            "evidence_sha256": file_digest(destination),
        }
        self.append_event(change_id, state, "PR_SET_APPROVED", state["pr_approval"])
        self.write_state(change_id, state)
        return state

    def verify(self, change_id: str) -> list[str]:
        errors: list[str] = []
        state = self.read_state(change_id)
        events_path = self.run_dir(change_id) / "events.jsonl"
        previous = "0" * 64
        count = 0
        try:
            lines = events_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return [f"cannot read event log: {exc}"]
        for count, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"event {count}: invalid JSON: {exc}")
                continue
            claimed = event.pop("hash", None)
            if event.get("sequence") != count:
                errors.append(f"event {count}: invalid sequence")
            if event.get("previous_hash") != previous:
                errors.append(f"event {count}: previous hash mismatch")
            calculated = digest(event)
            if claimed != calculated:
                errors.append(f"event {count}: hash mismatch")
            previous = claimed or calculated
        if count != state.get("event_count"):
            errors.append("run event_count does not match event log")
        if previous != state.get("last_event_hash"):
            errors.append("run last_event_hash does not match event log")
        plan_path = self.run_dir(change_id) / "plan.json"
        if state["state"] not in {"AWAITING_CLARIFICATION", "INTAKE"}:
            if not plan_path.is_file():
                errors.append("plan.json is missing")
            else:
                plan = read_json(plan_path)
                calculated = digest(
                    {key: value for key, value in plan.items() if key != "digest"}
                )
                if (
                    calculated != plan.get("digest")
                    or calculated != state.get("plan_digest")
                ):
                    errors.append("plan digest mismatch")
            requirements_path = self.run_dir(change_id) / "requirements.json"
            if not requirements_path.is_file():
                errors.append("requirements.json is missing")
            else:
                requirements = read_json(requirements_path)
                calculated = digest(
                    {
                        key: value
                        for key, value in requirements.items()
                        if key != "digest"
                    }
                )
                if (
                    calculated != requirements.get("digest")
                    or calculated != state.get("requirements_digest")
                ):
                    errors.append("requirements digest mismatch")
        if state["state"] not in {"AWAITING_CLARIFICATION"}:
            ready_rounds = [
                item
                for item in state.get("clarification_rounds", [])
                if item.get("decision") == "READY"
            ]
            if not ready_rounds:
                errors.append("intake readiness evidence is missing")
        if state["state"] in {
            "AWAITING_PLAN_APPROVAL",
            "PLAN_APPROVED",
            "WORKSPACES_READY",
            "EXECUTING",
            "INTEGRATION_PASSED",
            "PLAN_CLOSED",
            "PR_SET_READY",
            "AWAITING_PR_APPROVAL",
            "PR_APPROVED",
        }:
            try:
                passing_reviews = self._validated_current_plan_reviews(
                    change_id, state
                )
            except ProgramError as exc:
                errors.append(str(exc))
                passing_reviews = []
            if len(passing_reviews) < int(state.get("required_plan_reviews", 1)):
                errors.append("required plan review cycles are incomplete")
        if state["state"] in {
            "WORKSPACES_READY",
            "EXECUTING",
            "INTEGRATION_PASSED",
            "PLAN_CLOSED",
            "PR_SET_READY",
            "AWAITING_PR_APPROVAL",
            "PR_APPROVED",
            "BLOCKED_SPEC",
            "FAIL",
        }:
            missing = set(state.get("checkout_scope", [])) - set(state.get("commit_vector", {}))
            if missing:
                errors.append("commit vector is missing: " + ", ".join(sorted(missing)))
            vector_path = self.run_dir(change_id) / "commit-vector.json"
            if not vector_path.is_file():
                errors.append("commit-vector.json is missing")
            else:
                vector = read_json(vector_path)
                calculated = digest(
                    {key: value for key, value in vector.items() if key != "digest"}
                )
                if (
                    calculated != vector.get("digest")
                    or calculated != state.get("commit_vector_digest")
                    or vector.get("repositories") != state.get("commit_vector")
                ):
                    errors.append("commit vector digest mismatch")
            extensions_path = self.run_dir(change_id) / "repository-extensions.json"
            if not extensions_path.is_file():
                errors.append("repository-extensions.json is missing")
            else:
                extensions = read_json(extensions_path)
                calculated = digest(
                    {
                        key: value
                        for key, value in extensions.items()
                        if key != "digest"
                    }
                )
                if (
                    calculated != extensions.get("digest")
                    or calculated != state.get("repository_extensions_digest")
                    or extensions.get("repositories")
                    != state.get("repository_extensions")
                ):
                    errors.append("repository extension digest mismatch")
                for repository_id, packet in state.get(
                    "repository_extensions", {}
                ).items():
                    packet_calculated = digest(
                        {
                            key: value
                            for key, value in packet.items()
                            if key != "digest"
                        }
                    )
                    if packet_calculated != packet.get("digest"):
                        errors.append(
                            f"{repository_id}: repository extension packet digest mismatch"
                        )
            for repository_id, repository_result in state.get(
                "repository_results", {}
            ).items():
                evidence_path = repository_result.get("evidence_path")
                expected_digest = repository_result.get("evidence_sha256")
                if not isinstance(evidence_path, str) or not evidence_path:
                    errors.append(
                        f"{repository_id}: repository evidence path is missing"
                    )
                    continue
                stored_path = self.run_dir(change_id) / evidence_path
                if not stored_path.is_file():
                    errors.append(
                        f"{repository_id}: repository evidence is missing"
                    )
                elif file_digest(stored_path) != expected_digest:
                    errors.append(
                        f"{repository_id}: repository evidence digest mismatch"
                    )
            integration_path = state.get("integration_evidence_path")
            integration_digest = state.get("integration_evidence_sha256")
            if integration_digest is not None:
                if not isinstance(integration_path, str) or not integration_path:
                    errors.append("integration evidence path is missing")
                else:
                    stored_path = self.run_dir(change_id) / integration_path
                    if not stored_path.is_file():
                        errors.append("integration evidence is missing")
                    elif file_digest(stored_path) != integration_digest:
                        errors.append("integration evidence digest mismatch")
            integration_result = state.get("integration_result")
            if integration_result is not None:
                if not isinstance(integration_result, dict):
                    errors.append("integration result is malformed")
                else:
                    try:
                        attempt_path = safe_relative_path(
                            integration_result.get("evidence_path"),
                            "integration attempt evidence_path",
                        )
                    except ProgramError as exc:
                        errors.append(str(exc))
                    else:
                        stored_path = self.run_dir(change_id) / attempt_path
                        if not stored_path.is_file():
                            errors.append("integration attempt evidence is missing")
                        elif file_digest(stored_path) != integration_result.get(
                            "evidence_sha256"
                        ):
                            errors.append(
                                "integration attempt evidence digest mismatch"
                            )
        if state["state"] in {
            "PLAN_CLOSED",
            "PR_SET_READY",
            "AWAITING_PR_APPROVAL",
            "PR_APPROVED",
        }:
            closure_path = self.run_dir(change_id) / "plan-closure.json"
            if not closure_path.is_file():
                errors.append("plan-closure.json is missing")
            else:
                closure = read_json(closure_path)
                calculated = digest(
                    {
                        key: value
                        for key, value in closure.items()
                        if key != "digest"
                    }
                )
                if (
                    calculated != closure.get("digest")
                    or calculated != state.get("plan_closure_digest")
                    or closure.get("plan_digest") != state.get("plan_digest")
                    or closure.get("requirements_digest")
                    != state.get("requirements_digest")
                    or closure.get("commit_vector_digest")
                    != state.get("commit_vector_digest")
                    or closure.get("integration_evidence_sha256")
                    != state.get("integration_evidence_sha256")
                ):
                    errors.append("plan closure digest or binding mismatch")
            closure_evidence_path = (
                self.run_dir(change_id) / "plan-closure-evidence.json"
            )
            if not closure_evidence_path.is_file():
                errors.append("plan-closure-evidence.json is missing")
            elif (
                file_digest(closure_evidence_path)
                != state.get("plan_closure_evidence_sha256")
            ):
                errors.append("plan closure evidence digest mismatch")
        if state["state"] in {"PR_SET_READY", "AWAITING_PR_APPROVAL", "PR_APPROVED"}:
            pr_set_path = self.run_dir(change_id) / "pr-set.json"
            if not pr_set_path.is_file():
                errors.append("pr-set.json is missing")
            else:
                pr_set = read_json(pr_set_path)
                calculated = digest(
                    {key: value for key, value in pr_set.items() if key != "digest"}
                )
                if calculated != pr_set.get("digest") or calculated != state.get("pr_set_digest"):
                    errors.append("PR-set digest mismatch")
        return errors


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=repository_root())
    result.add_argument("--manifest", type=Path)
    subparsers = result.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--adoption", action="store_true")

    start = subparsers.add_parser("start")
    start.add_argument("--change-id", required=True)
    start.add_argument("--request", required=True)
    start.add_argument("--requested-by", required=True)
    start.add_argument("--risk-tier", default="critical")

    assess_intake = subparsers.add_parser("assess-intake")
    assess_intake.add_argument("--change-id", required=True)
    assess_intake.add_argument("--evidence", type=Path, required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("--change-id", required=True)
    plan.add_argument("--repositories", required=True, help="comma-separated seed repository IDs")
    plan.add_argument("--requirements", type=Path, required=True)

    review_plan = subparsers.add_parser("review-plan")
    review_plan.add_argument("--change-id", required=True)
    review_plan.add_argument("--evidence", type=Path, required=True)

    approve_plan = subparsers.add_parser("approve-plan")
    approve_plan.add_argument("--change-id", required=True)
    approve_plan.add_argument("--evidence", type=Path, required=True)

    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--change-id", required=True)

    prepare = subparsers.add_parser("prepare-workspaces")
    prepare.add_argument("--change-id", required=True)
    prepare.add_argument("--execute", action="store_true")
    prepare.add_argument("--allow-clone", action="store_true")

    extensions = subparsers.add_parser("extensions")
    extensions.add_argument("--change-id", required=True)
    extensions.add_argument("--repository", required=True)

    refresh_extensions = subparsers.add_parser("refresh-extensions")
    refresh_extensions.add_argument("--change-id", required=True)
    refresh_extensions.add_argument("--repository", required=True)

    repository_result = subparsers.add_parser("record-repository-result")
    repository_result.add_argument("--change-id", required=True)
    repository_result.add_argument("--repository", required=True)
    repository_result.add_argument("--decision", choices=sorted(DECISIONS), required=True)
    repository_result.add_argument("--evidence", type=Path, required=True)

    integration = subparsers.add_parser("record-integration-result")
    integration.add_argument("--change-id", required=True)
    integration.add_argument("--evidence", type=Path, required=True)

    close_plan = subparsers.add_parser("close-plan")
    close_plan.add_argument("--change-id", required=True)
    close_plan.add_argument("--evidence", type=Path, required=True)

    pr_set = subparsers.add_parser("prepare-pr-set")
    pr_set.add_argument("--change-id", required=True)
    pr_set.add_argument("--title", required=True)

    record_pr = subparsers.add_parser("record-pr")
    record_pr.add_argument("--change-id", required=True)
    record_pr.add_argument("--repository", required=True)
    record_pr.add_argument("--number", type=int, required=True)
    record_pr.add_argument("--url", required=True)
    record_pr.add_argument("--head-sha", required=True)

    approve_pr = subparsers.add_parser("approve-pr-set")
    approve_pr.add_argument("--change-id", required=True)
    approve_pr.add_argument("--evidence", type=Path, required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--change-id", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--change-id", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    if manifest and not manifest.is_absolute():
        manifest = root / manifest
    try:
        engine = ProgramOrchestrator(root, manifest)
        if args.command == "validate":
            errors = validate_manifest(engine.manifest, adoption=args.adoption)
            if errors:
                print("PROGRAM_MANIFEST_INVALID")
                for error in errors:
                    print(f"- {error}")
                return 1
            print("PROGRAM_MANIFEST_VALID")
            return 0
        if args.command == "start":
            output = engine.start(
                args.change_id, args.request, args.requested_by, args.risk_tier
            )
        elif args.command == "assess-intake":
            output = engine.assess_intake(args.change_id, args.evidence)
        elif args.command == "plan":
            repositories = [item.strip() for item in args.repositories.split(",") if item.strip()]
            output = engine.plan(
                args.change_id, repositories, args.requirements
            )
        elif args.command == "review-plan":
            output = engine.record_plan_review(args.change_id, args.evidence)
        elif args.command == "approve-plan":
            output = engine.approve_plan(args.change_id, args.evidence)
        elif args.command == "inventory":
            output = {"repositories": engine.inventory(args.change_id)}
        elif args.command == "prepare-workspaces":
            output = engine.prepare_workspaces(
                args.change_id, execute=args.execute, allow_clone=args.allow_clone
            )
        elif args.command == "extensions":
            output = engine.repository_extension_packet(
                args.change_id, args.repository
            )
        elif args.command == "refresh-extensions":
            output = engine.refresh_repository_extensions(
                args.change_id, args.repository
            )
        elif args.command == "record-repository-result":
            output = engine.record_repository_result(
                args.change_id, args.repository, args.decision, args.evidence
            )
        elif args.command == "record-integration-result":
            output = engine.record_integration_result(args.change_id, args.evidence)
        elif args.command == "close-plan":
            output = engine.close_plan(args.change_id, args.evidence)
        elif args.command == "prepare-pr-set":
            output = engine.prepare_pr_set(args.change_id, args.title)
        elif args.command == "record-pr":
            output = engine.record_pull_request(
                args.change_id, args.repository, args.number, args.url, args.head_sha
            )
        elif args.command == "approve-pr-set":
            output = engine.approve_pr_set(args.change_id, args.evidence)
        elif args.command == "status":
            output = engine.read_state(args.change_id)
        elif args.command == "verify":
            errors = engine.verify(args.change_id)
            if errors:
                print("PROGRAM_RUN_INVALID")
                for error in errors:
                    print(f"- {error}")
                return 1
            print("PROGRAM_RUN_VALID")
            return 0
        else:
            raise ProgramError(f"unsupported command: {args.command}")
        print(json.dumps(output, indent=2))
        return 0
    except ProgramError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
