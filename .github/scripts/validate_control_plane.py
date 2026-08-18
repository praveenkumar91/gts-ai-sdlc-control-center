#!/usr/bin/env python3
"""Validate the repository SDLC control plane using only the Python standard library."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


REQUIRED_FILES = [
    ".github/copilot-instructions.md",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/sdlc/project.json",
    ".github/sdlc/program.json",
    ".github/sdlc/agent-runtime.json",
    ".github/sdlc/gts-foundation-lock.json",
    ".github/sdlc/sources.json",
    ".github/sdlc/policies/state-machine.json",
    ".github/sdlc/policies/risk-tiers.json",
    ".github/sdlc/policies/protected-paths.json",
    ".github/sdlc/policies/artifact-contracts.json",
    ".github/sdlc/schemas/requirements.schema.json",
    ".github/sdlc/schemas/evidence-manifest.schema.json",
    ".github/sdlc/schemas/artifact-envelope.schema.json",
    ".github/sdlc/schemas/program.schema.json",
    ".github/sdlc/schemas/agent-runtime.schema.json",
    ".github/sdlc/schemas/repository-extension.schema.json",
    ".github/scripts/sdlc_engine.py",
    ".github/scripts/program_orchestrator.py",
    ".github/scripts/agent_supervisor.py",
    ".github/scripts/generate_readme.py",
    ".github/scripts/run_repository_gates.py",
    ".github/scripts/create_draft_prs.py",
    ".github/scripts/collect_pr_approval.py",
    ".github/scripts/emit_program_approval.py",
    ".github/scripts/run_operation.py",
    ".github/scripts/emit_approval_evidence.py",
    ".github/workflows/controlled-operations.yml",
    ".github/workflows/program-human-gates.yml",
    ".github/prompts/run-sdlc.prompt.md",
    ".github/hooks/guardrails.json",
]

REQUIRED_AGENTS = {
    "sdlc-orchestrator",
    "spec-ingestion",
    "requirements-engineer",
    "solution-architect",
    "implementation",
    "verification",
    "security-reviewer",
    "adversarial-reviewer",
    "release-controller",
    "business-invariant-validator",
    "deployment-controller",
    "operations-validator",
    "program-orchestrator",
    "repository-coordinator",
    "repository-worker",
    "gui-validator",
    "pr-set-coordinator",
}

REQUIRED_GTS_AGENTS = {
    "gts-orchestrator",
    "gts-prompt-clarifier",
    "p7-orchestrator",
    "p7-sdlc-architect",
    "p7-sdlc-builder",
    "p7-sdlc-developer",
    "p7-sdlc-planner",
    "p7-sdlc-pr-author",
    "p7-sdlc-reviewer",
    "p7-sdlc-spec-author",
    "p7-sdlc-tester",
    "t7-orchestrator",
    "t7-sdlc-architect",
    "t7-sdlc-builder",
    "t7-sdlc-developer",
    "t7-sdlc-knowledge",
    "t7-sdlc-planner",
    "t7-sdlc-pr-author",
    "t7-sdlc-reviewer",
    "t7-sdlc-spec-author",
    "t7-sdlc-tester",
}

REQUIRED_GTS_SKILLS = {
    "code-review",
    "code-review-lens",
    "coding-guidelines",
    "confluence",
    "gcp-tools",
    "github",
    "github-pr-miner",
    "jira",
    "p7-brainstorming",
    "p7-code",
    "p7-code-review",
    "p7-debugging",
    "p7-github",
    "p7-verification",
    "ralph-loop",
    "requirement-conformance",
    "sdlc-brainstorming",
    "sdlc-debugging",
    "sdlc-verification",
    "spec-authoring",
    "t7-code",
    "t7-code-review",
    "t7-knowledge-base",
    "t7-spec",
    "teams",
}

GTS_SKILL_FRONTMATTER_KEYS = {
    # Portable Agent Skills fields used by the imported catalog.
    "name",
    "description",
    "argument-hint",
    "user-invocable",
    "disable-model-invocation",
    "context",
    # GTS extension metadata. VS Code discovery does not depend on these keys;
    # the control centre validates them and resolves system scope itself.
    "systems",
    "tools",
    "extends",
}

REQUIRED_SKILLS = {
    "ingest-specifications",
    "compile-requirements",
    "design-change",
    "implement-change",
    "verify-evidence",
    "assess-security",
    "prepare-release",
    "operate-sdlc-run",
    "orchestrate-program-change",
    "validate-gui-change",
    "coordinate-pr-set",
    "use-repository-extensions",
    "supervise-agent-execution",
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path}: top-level value must be an object")
        return {}
    return value


def markdown_frontmatter(path: Path, errors: list[str]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: cannot read: {exc}")
        return ""
    text = text.removeprefix("\ufeff")
    if not text.startswith("---\n"):
        errors.append(f"{path}: missing YAML frontmatter")
        return ""
    marker = text.find("\n---\n", 4)
    if marker < 0:
        errors.append(f"{path}: unterminated YAML frontmatter")
        return ""
    return text[4:marker]


def frontmatter_scalar(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def frontmatter_keys(frontmatter: str) -> list[str]:
    return re.findall(r"(?m)^([A-Za-z][A-Za-z0-9_-]*):", frontmatter)


def inline_list(frontmatter: str, key: str) -> list[str] | None:
    raw = frontmatter_scalar(frontmatter, key)
    if raw is None:
        return None
    if not (raw.startswith("[") and raw.endswith("]")):
        return None
    body = raw[1:-1].strip()
    if not body:
        return []
    return [item.strip().strip("\"'") for item in body.split(",")]


def validate_skills(root: Path, errors: list[str]) -> None:
    skill_root = root / ".github" / "skills"
    actual = {p.name for p in skill_root.iterdir() if p.is_dir()} if skill_root.exists() else set()
    missing = REQUIRED_SKILLS - actual
    if missing:
        errors.append(f"missing skills: {', '.join(sorted(missing))}")
    for name in sorted(actual):
        path = skill_root / name / "SKILL.md"
        if not path.is_file():
            errors.append(f"{path}: missing")
            continue
        frontmatter = markdown_frontmatter(path, errors)
        declared = frontmatter_scalar(frontmatter, "name")
        description = frontmatter_scalar(frontmatter, "description")
        if declared != name:
            errors.append(f"{path}: name must be {name!r}, found {declared!r}")
        if not description or len(description) < 30:
            errors.append(f"{path}: description must explain purpose and trigger")
        if "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"{path}: unresolved TODO")


def validate_agents(root: Path, errors: list[str]) -> None:
    agent_root = root / ".github" / "agents"
    files = list(agent_root.glob("*.agent.md")) if agent_root.exists() else []
    actual = {p.name.removesuffix(".agent.md") for p in files}
    missing = REQUIRED_AGENTS - actual
    if missing:
        errors.append(f"missing agents: {', '.join(sorted(missing))}")
    for path in files:
        frontmatter = markdown_frontmatter(path, errors)
        if not frontmatter_scalar(frontmatter, "name"):
            errors.append(f"{path}: missing name")
        description = frontmatter_scalar(frontmatter, "description")
        if not description or len(description) < 30:
            errors.append(f"{path}: missing meaningful description")
        if not re.search(r"(?m)^tools:\s*(?:\[[^\n]*\])?\s*$", frontmatter):
            errors.append(f"{path}: tools must be explicitly scoped")
        if re.search(r"(?m)^model:\s*\n\s+-", frontmatter):
            errors.append(f"{path}: model must be one string; omit it to inherit the selected model")
        text = path.read_text(encoding="utf-8")
        if re.search(r"REPLACE_WITH_[A-Z0-9_]+|\{SYSTEM\}", text):
            errors.append(f"{path}: unresolved implementation placeholder")


def validate_gts_foundation(root: Path, errors: list[str]) -> None:
    agent_root = root / ".github" / "agents"
    actual_agents = {
        path.name.removesuffix(".agent.md")
        for path in agent_root.glob("*.agent.md")
    }
    missing_agents = REQUIRED_GTS_AGENTS - actual_agents
    if missing_agents:
        errors.append(
            "missing GTS agents: " + ", ".join(sorted(missing_agents))
        )

    skill_root = root / ".agents" / "skills"
    skill_files = list(skill_root.rglob("SKILL.md")) if skill_root.is_dir() else []
    actual_skills = {path.parent.name for path in skill_files}
    missing_skills = REQUIRED_GTS_SKILLS - actual_skills
    if missing_skills:
        errors.append(
            "missing GTS skills: " + ", ".join(sorted(missing_skills))
        )
    for path in sorted(skill_files):
        frontmatter = markdown_frontmatter(path, errors)
        declared = frontmatter_scalar(frontmatter, "name")
        description = frontmatter_scalar(frontmatter, "description")
        keys = frontmatter_keys(frontmatter)
        duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
        unknown_keys = sorted(set(keys) - GTS_SKILL_FRONTMATTER_KEYS)
        if declared != path.parent.name:
            errors.append(
                f"{path}: name must be {path.parent.name!r}, found {declared!r}"
            )
        if declared and not re.fullmatch(r"[a-z0-9-]{1,64}", declared):
            errors.append(f"{path}: name must be a portable Agent Skills identifier")
        if not description or len(description) < 30:
            errors.append(f"{path}: description must explain purpose and trigger")
        elif len(description) > 1024:
            errors.append(f"{path}: description exceeds the 1024 character limit")
        if duplicate_keys:
            errors.append(
                f"{path}: duplicate frontmatter keys: {', '.join(duplicate_keys)}"
            )
        if unknown_keys:
            errors.append(
                f"{path}: unsupported GTS frontmatter keys: {', '.join(unknown_keys)}"
            )

        systems = inline_list(frontmatter, "systems")
        if frontmatter_scalar(frontmatter, "systems") is not None:
            if not systems or any(not re.fullmatch(r"[a-z0-9-]+", item) for item in systems):
                errors.append(f"{path}: systems must be a non-empty inline identifier list")

        tools = inline_list(frontmatter, "tools")
        if frontmatter_scalar(frontmatter, "tools") is not None and not tools:
            errors.append(f"{path}: tools must be a non-empty inline list")

        user_invocable = frontmatter_scalar(frontmatter, "user-invocable")
        if user_invocable is not None and user_invocable not in {"true", "false"}:
            errors.append(f"{path}: user-invocable must be true or false")

        context = frontmatter_scalar(frontmatter, "context")
        if context is not None and context not in {"inline", "fork"}:
            errors.append(f"{path}: context must be inline or fork")

        extends = frontmatter_scalar(frontmatter, "extends")
        if extends is not None:
            if not re.fullmatch(r"skills/(?:common|systems)/[a-z0-9/-]+", extends):
                errors.append(f"{path}: extends must reference a GTS skill path")
            else:
                target = skill_root / extends.removeprefix("skills/") / "SKILL.md"
                if not target.is_file():
                    errors.append(f"{path}: extends target does not exist: {extends}")

    lock_path = root / ".github" / "sdlc" / "gts-foundation-lock.json"
    lock = load_json(lock_path, errors)
    if not re.fullmatch(r"[0-9a-f]{40}", str(lock.get("source_commit", ""))):
        errors.append(f"{lock_path}: source_commit must be a full Git SHA")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(lock.get("source_archive_sha256", ""))
    ):
        errors.append(f"{lock_path}: source_archive_sha256 must be SHA-256")
    if "internal" not in str(lock.get("classification", "")).casefold():
        errors.append(f"{lock_path}: internal classification is required")


def validate_state_machine(root: Path, errors: list[str]) -> None:
    path = root / ".github/sdlc/policies/state-machine.json"
    policy = load_json(path, errors)
    transitions = policy.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        errors.append(f"{path}: transitions must be a non-empty array")
        return
    expected = policy.get("initial_state")
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            errors.append(f"{path}: transition {index} must be an object")
            continue
        if transition.get("from") != expected:
            errors.append(
                f"{path}: transition {index} starts at {transition.get('from')!r}; "
                f"expected {expected!r}"
            )
        expected = transition.get("to")
        owner = transition.get("owner")
        if owner not in REQUIRED_AGENTS:
            errors.append(f"{path}: transition {index} has unknown owner {owner!r}")
        artifacts = transition.get("required_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{path}: transition {index} has no required artifacts")


def validate_adoption(root: Path, errors: list[str]) -> None:
    program_path = root / ".github/sdlc/program.json"
    program = load_json(program_path, errors)
    if program.get("adoption_complete") is not True:
        errors.append(f"{program_path}: adoption_complete must be true")
    program_id = str(program.get("program_id", ""))
    if not program_id or "CHANGE" in program_id.upper() or "REPLACE" in program_id.upper():
        errors.append(f"{program_path}: program_id is still a placeholder")
    repositories = [
        item
        for item in program.get("repositories", [])
        if isinstance(item, dict) and item.get("enabled", True) is True
    ]
    if not repositories:
        errors.append(f"{program_path}: at least one repository must be enabled")

    runtime_relative = program.get("agent_runtime_config")
    if not isinstance(runtime_relative, str) or not runtime_relative.strip():
        errors.append(f"{program_path}: agent_runtime_config is required for adoption")
    else:
        runtime_candidate = Path(runtime_relative)
        if runtime_candidate.is_absolute() or ".." in runtime_candidate.parts:
            errors.append(
                f"{program_path}: agent_runtime_config must be a safe repository-relative path"
            )
        else:
            runtime_path = root / runtime_candidate
            runtime = load_json(runtime_path, errors)
            if runtime.get("adoption_complete") is not True:
                errors.append(f"{runtime_path}: adoption_complete must be true")
            worker = runtime.get("worker")
            if not isinstance(worker, dict) or worker.get("enabled") is not True:
                errors.append(f"{runtime_path}: worker.enabled must be true")
            argv = worker.get("argv") if isinstance(worker, dict) else None
            if not isinstance(argv, list) or not argv or not all(
                isinstance(item, str) and item for item in argv
            ):
                errors.append(f"{runtime_path}: worker.argv must be a non-empty string list")
            elif not any("{prompt}" in item for item in argv):
                errors.append(f"{runtime_path}: worker.argv must bind {{prompt}}")
    for stack, relative in program.get("default_quality_configs", {}).items():
        default_path = root / str(relative)
        if not default_path.is_file():
            errors.append(
                f"{program_path}: central quality default for {stack!r} "
                f"is missing: {relative}"
            )
    for repository in repositories:
        stack = repository.get("stack")
        adapter = root / ".github/sdlc/stack-adapters" / f"{stack}.json"
        if not adapter.is_file():
            errors.append(
                f"{program_path}: enabled repository {repository.get('id')!r} "
                f"has no stack adapter for {stack!r}"
            )

    project_path = root / ".github/sdlc/project.json"
    project = load_json(project_path, errors)
    if project.get("adoption_complete") is not True:
        errors.append(f"{project_path}: adoption_complete must be true")
    project_id = str(project.get("project_id", ""))
    if not project_id or "CHANGE" in project_id.upper() or "REPLACE" in project_id.upper():
        errors.append(f"{project_path}: project_id is still a placeholder")

    sources_path = root / ".github/sdlc/sources.json"
    sources = load_json(sources_path, errors).get("sources", [])
    if not sources:
        errors.append(f"{sources_path}: at least one source is required")
    if "REPLACE_" in sources_path.read_text(encoding="utf-8"):
        errors.append(f"{sources_path}: contains placeholders")

    codeowners = (root / ".github/CODEOWNERS").read_text(encoding="utf-8")
    if "YOUR-ORG" in codeowners:
        errors.append(".github/CODEOWNERS: contains placeholder owners")

    risk_policy = load_json(root / ".github/sdlc/policies/risk-tiers.json", errors)
    tier = project.get("default_risk_tier")
    required = set(
        risk_policy.get("tiers", {}).get(tier, {}).get("required_gates", [])
    )
    commands = {
        item.get("id"): item
        for item in project.get("commands", [])
        if isinstance(item, dict) and item.get("id")
    }
    for gate_id in sorted(required):
        command = commands.get(gate_id)
        if not command:
            errors.append(f"{project_path}: risk tier {tier!r} requires missing gate {gate_id!r}")
        elif command.get("enabled") is not True or command.get("required") is not True:
            errors.append(f"{project_path}: mandatory gate {gate_id!r} must be enabled and required")
        elif any("REPLACE_" in str(arg) for arg in command.get("args", [])):
            errors.append(f"{project_path}: mandatory gate {gate_id!r} contains placeholders")

    operations = project.get("operations", {})
    if not isinstance(operations, dict) or operations.get("enabled") is not True:
        errors.append(f"{project_path}: operations must be configured and enabled")
        return
    for environment in ("preproduction_environment", "production_environment"):
        value = str(operations.get(environment, ""))
        if not value or "REPLACE_" in value:
            errors.append(f"{project_path}: {environment} must name a protected environment")
    required_operations = {
        "preproduction-validation",
        "business-invariant-tests",
        "deploy-canary",
        "canary-health",
        "production-reconciliation",
        "rollback",
    }
    configured_operations = {
        item.get("id"): item
        for item in operations.get("commands", [])
        if isinstance(item, dict) and item.get("id")
    }
    for operation_id in sorted(required_operations):
        operation = configured_operations.get(operation_id)
        if not operation or operation.get("enabled") is not True:
            errors.append(f"{project_path}: required operation {operation_id!r} must be enabled")
        elif (
            not isinstance(operation.get("args"), list)
            or not operation["args"]
            or any("REPLACE_" in str(arg) for arg in operation["args"])
        ):
            errors.append(f"{project_path}: required operation {operation_id!r} is not configured")


def validate(root: Path, adoption: bool = False) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for path in sorted((root / ".github").rglob("*.json")):
        load_json(path, errors)

    hooks = load_json(root / ".github/hooks/guardrails.json", errors)
    if hooks.get("version") != 1 or not isinstance(hooks.get("hooks"), dict):
        errors.append(".github/hooks/guardrails.json: expected version 1 and hooks object")

    validate_skills(root, errors)
    validate_agents(root, errors)
    validate_gts_foundation(root, errors)
    validate_state_machine(root, errors)
    program_module_path = root / ".github/scripts/program_orchestrator.py"
    try:
        spec = importlib.util.spec_from_file_location(
            "program_orchestrator_validation", program_module_path
        )
        if spec is None or spec.loader is None:
            raise ImportError("no module loader")
        program_orchestrator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(program_orchestrator)
        program = load_json(root / ".github/sdlc/program.json", errors)
        errors.extend(program_orchestrator.validate_manifest(program, adoption=adoption))
    except (ImportError, OSError) as exc:
        errors.append(f"program_orchestrator.py could not be imported: {exc}")
    if adoption:
        validate_adoption(root, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adoption", action="store_true", help="require project-specific adoption")
    parser.add_argument("--root", type=Path, default=repository_root())
    args = parser.parse_args()

    errors = validate(args.root.resolve(), adoption=args.adoption)
    if errors:
        print("CONTROL_PLANE_INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("CONTROL_PLANE_VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
