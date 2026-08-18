#!/usr/bin/env python3
"""Run one durable repository lease through the GitHub Copilot SDK.

The SDK owns the model-driven observe/plan/delegate/verify loop. This adapter
registers the selected repository/GTS agents, records immutable subagent
lifecycle evidence, and fails closed when required independent roles did not
actually execute.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


EXIT_INCONCLUSIVE = 21
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
SAFE_AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _scalar(text: str) -> Any:
    text = text.strip()
    if not text:
        return ""
    if text in {"true", "false"}:
        return text == "true"
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("'\"") for item in inner.split(",")]
    return text.strip("'\"")


def read_agent_profile(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"agent profile has no YAML frontmatter: {path}")
    metadata: dict[str, Any] = {}
    list_key: str | None = None
    for raw in match.group(1).splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if list_key and stripped.startswith("- "):
            metadata[list_key].append(_scalar(stripped[2:]))
            continue
        list_key = None
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        if value.strip():
            metadata[key] = _scalar(value)
        else:
            metadata[key] = []
            list_key = key
    name = str(metadata.get("name", ""))
    if not SAFE_AGENT_NAME_RE.fullmatch(name):
        raise ValueError(f"agent profile has invalid name: {path}")
    description = str(metadata.get("description", "")).strip()
    if not description:
        raise ValueError(f"agent profile has no description: {path}")
    return {
        "name": name,
        "display_name": name,
        "description": description,
        "prompt": match.group(2).strip(),
        "tools": metadata.get("tools") or None,
        "model": metadata.get("model") or None,
        "metadata": metadata,
    }


def build_agent_catalog(packet: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    agents: list[dict[str, Any]] = []
    roles: dict[str, str] = {}
    names: set[str] = set()
    for item in packet.get("agents", []):
        path = Path(str(item.get("resolved_path", "")))
        if not path.is_file():
            raise ValueError(f"selected agent is unavailable: {path}")
        expected = item.get("sha256")
        if expected and sha256_file(path) != expected:
            raise ValueError(f"selected agent digest mismatch: {path}")
        profile = read_agent_profile(path)
        if profile["name"] in names:
            raise ValueError(f"duplicate selected agent name: {profile['name']}")
        names.add(profile["name"])
        role = str(item.get("role") or "specialist")
        roles[profile["name"]] = role
        profile["source_id"] = item.get("id")
        profile["source_sha256"] = expected
        agents.append(profile)
    return agents, roles


def build_skill_catalog(packet: dict[str, Any]) -> tuple[dict[str, Path], list[str]]:
    """Return digest-verified skill names and SDK discovery directories."""
    skills: dict[str, Path] = {}
    roots: set[str] = set()
    for item in packet.get("skills", []):
        path = Path(str(item.get("resolved_path", "")))
        if not path.is_file() or path.name != "SKILL.md":
            raise ValueError(f"selected skill is unavailable: {path}")
        expected = item.get("sha256")
        if expected and sha256_file(path) != expected:
            raise ValueError(f"selected skill digest mismatch: {path}")
        name = path.parent.name
        if name in skills and skills[name] != path:
            raise ValueError(f"duplicate selected skill name: {name}")
        skills[name] = path
        roots.add(str(path.parent.parent))
    return skills, sorted(roots)


def skills_for_agent(
    agent: dict[str, Any], role: str, available: dict[str, Path]
) -> list[str]:
    requested: list[str] = []
    for key, value in agent.get("metadata", {}).items():
        if not key.startswith("skills") or not isinstance(value, list):
            continue
        requested.extend(Path(str(item)).name for item in value)
    defaults = {
        "implementation": ("coding-guidelines", "requirement-conformance", "p7-code"),
        "build": ("build-failure-lens", "sdlc-verification", "p7-verification"),
        "testing": ("sdlc-verification", "requirement-conformance", "p7-verification"),
        "independent-domain-review": (
            "code-review",
            "code-review-lens",
            "requirement-conformance",
            "p7-code-review",
        ),
    }
    requested.extend(defaults.get(role, ()))
    return list(dict.fromkeys(name for name in requested if name in available))


def sdk_model_id(value: Any) -> str | None:
    """Convert common VS Code display labels into SDK model identifiers."""
    if not value:
        return None
    original = str(value).strip()
    lowered = original.lower()
    lowered = re.sub(r"\s*\(copilot\)\s*$", "", lowered)
    normalized = re.sub(r"[^a-z0-9._-]+", "-", lowered).strip("-")
    return normalized if SAFE_MODEL_ID_RE.fullmatch(normalized) else None


def sdk_tool_names(values: Any) -> list[str] | None:
    """Translate VS Code agent tool aliases to Copilot CLI builtin names."""
    if not isinstance(values, list):
        return None
    aliases = {
        "read": ("view",),
        "search": ("grep", "glob"),
        "execute": ("bash",),
        "agent": ("task",),
    }
    result: list[str] = []
    for value in values:
        name = str(value).strip()
        result.extend(aliases.get(name, (name,)))
    return list(dict.fromkeys(item for item in result if item))


def select_required_agents(
    catalog: list[dict[str, Any]], roles: dict[str, str], required_roles: list[str]
) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    priorities = {
        "implementation": ("developer", "implementer"),
        "build": ("builder", "build"),
        "testing": ("tester", "testing"),
        "independent-domain-review": ("reviewer", "review"),
    }
    for role in required_roles:
        candidates = [agent["name"] for agent in catalog if roles[agent["name"]] == role]
        candidates = [name for name in candidates if name not in used]
        if not candidates:
            tokens = priorities.get(role, (role,))
            candidates = [
                agent["name"]
                for agent in catalog
                if agent["name"] not in used
                if any(token in agent["name"].lower() for token in tokens)
            ]
        if not candidates:
            raise ValueError(f"no selected custom agent satisfies required role: {role}")
        tokens = priorities.get(role, (role,))
        candidates.sort(
            key=lambda name: (
                next((index for index, token in enumerate(tokens) if token in name.lower()), 99),
                name,
            )
        )
        result[role] = candidates[0]
        used.add(candidates[0])
    return result


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "value"):
        return _plain(value.value)
    if hasattr(value, "__dict__"):
        return {key: _plain(item) for key, item in vars(value).items() if not key.startswith("_")}
    return str(value)


def normalized_event(event: Any) -> dict[str, Any]:
    raw_type = getattr(event, "type", "unknown")
    event_type = str(getattr(raw_type, "value", raw_type)).lower().replace("_", ".")
    return {
        "id": getattr(event, "id", None),
        "timestamp": str(getattr(event, "timestamp", utc_now())),
        "parent_id": getattr(event, "parent_id", None),
        "agent_id": getattr(event, "agent_id", None),
        "type": event_type,
        "data": _plain(getattr(event, "data", {})),
    }


def event_agent_name(event: dict[str, Any]) -> str | None:
    data = event.get("data") or {}
    for key in ("agent_name", "agentName", "name"):
        value = data.get(key)
        if value:
            return str(value)
    return None


def specialist_contract(messages: list[str]) -> dict[str, Any] | None:
    """Extract the required machine-readable verdict from specialist output."""
    marker = "SDLC_SPECIALIST_RESULT"
    decoder = json.JSONDecoder()
    for message in reversed(messages):
        offset = message.rfind(marker)
        if offset < 0:
            continue
        candidate = message[offset + len(marker) :].lstrip(" :\n\r\t`")
        try:
            value, _end = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        decision = value.get("decision")
        evidence = value.get("evidence")
        findings = value.get("findings")
        summary = value.get("summary")
        if (
            decision in {"PASS", "FAIL", "INCONCLUSIVE"}
            and isinstance(summary, str)
            and bool(summary.strip())
            and isinstance(evidence, list)
            and bool(evidence)
            and all(isinstance(item, str) and item.strip() for item in evidence)
            and isinstance(findings, list)
            and all(isinstance(item, str) for item in findings)
        ):
            return {
                "decision": decision,
                "summary": summary.strip(),
                "evidence": evidence,
                "findings": findings,
            }
    return None


def write_activity_board(
    path: Path,
    events: list[dict[str, Any]],
    required: dict[str, str],
    *,
    change_id: str,
    repository_id: str,
) -> None:
    executions = summarize_executions(events)
    latest_intent = next(
        (
            str((event.get("data") or {}).get("intent"))
            for event in reversed(events)
            if "assistant.intent" in event.get("type", "")
            and (event.get("data") or {}).get("intent")
        ),
        "Orienting to the repository lease",
    )
    lines = [
        f"# Runtime task board: {change_id} / {repository_id}",
        "",
        f"Last updated: `{utc_now()}`",
        f"Current intent: {latest_intent}",
        "",
        "## Required assurance coverage",
        "",
    ]
    for role, name in required.items():
        matches = [item for item in executions if item.get("agent_name") == name]
        status = matches[-1]["status"] if matches else "pending"
        lines.append(f"- [{ 'x' if status == 'completed' else ' ' }] {role}: `{name}` ({status})")
    lines.extend(["", "## Dynamic specialist executions", ""])
    if not executions:
        lines.append("- No subagent has started.")
    for item in executions:
        contract = item.get("result_contract") or {}
        decision = contract.get("decision", "NO_CONTRACT")
        lines.append(
            f"- `{item['agent_name']}` - {item['status']} / {decision} - "
            f"call `{item['tool_call_id']}`"
        )
    lines.extend(
        [
            "",
            "The parent model may add, split, reorder or repeat work. This board is",
            "rendered from runtime events; it is not a completion claim.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def summarize_executions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    executions: dict[str, dict[str, Any]] = {}
    by_instance: dict[str, str] = {}
    for sequence, event in enumerate(events, start=1):
        kind = event["type"]
        if "subagent.started" in kind:
            name = event_agent_name(event)
            call_id = str((event.get("data") or {}).get("tool_call_id") or (event.get("data") or {}).get("toolCallId") or event.get("id"))
            if name:
                by_instance[str(event.get("agent_id") or call_id)] = call_id
                executions[call_id] = {
                    "tool_call_id": call_id,
                    "agent_name": name,
                    "status": "running",
                    "started_at": event.get("timestamp"),
                    "started_sequence": sequence,
                    "messages": [],
                }
        elif "subagent.completed" in kind or "subagent.failed" in kind:
            data = event.get("data") or {}
            call_id = str(data.get("tool_call_id") or data.get("toolCallId") or event.get("id"))
            name = event_agent_name(event)
            target = executions.get(call_id)
            if target is None and name:
                target = next((item for item in reversed(list(executions.values())) if item["agent_name"] == name and item["status"] == "running"), None)
            if target is not None:
                target["status"] = "failed" if "failed" in kind else "completed"
                target["completed_at"] = event.get("timestamp")
                target["completed_sequence"] = sequence
                if "failed" in kind:
                    target["error"] = data.get("error")
        elif event.get("agent_id") and "assistant.message" in kind and "delta" not in kind:
            call_id = by_instance.get(str(event["agent_id"]))
            if call_id and call_id in executions:
                content = (event.get("data") or {}).get("content")
                if content:
                    executions[call_id]["messages"].append(str(content))
    for execution in executions.values():
        messages = execution.pop("messages")
        execution["output_message_count"] = len(messages)
        execution["output_sha256"] = stable_digest(messages)
        execution["result_contract"] = specialist_contract(messages)
    return list(executions.values())


def validate_required_executions(
    executions: list[dict[str, Any]], required: dict[str, str]
) -> tuple[list[str], list[str], list[str]]:
    failed = sorted(
        {
            item["agent_name"]
            for item in executions
            if item.get("status") == "failed"
        }
    )
    completed = [
        item
        for item in executions
        if item.get("status") == "completed"
        and item.get("output_message_count", 0) > 0
        and isinstance(item.get("result_contract"), dict)
        and item["result_contract"].get("decision") == "PASS"
    ]
    contract_failed = sorted(
        {
            item["agent_name"]
            for item in executions
            if item.get("status") == "completed"
            and isinstance(item.get("result_contract"), dict)
            and item["result_contract"].get("decision") == "FAIL"
        }
    )
    failed.extend(contract_failed)
    inconclusive = sorted(
        {
            item["agent_name"]
            for item in executions
            if item.get("status") == "completed"
            and isinstance(item.get("result_contract"), dict)
            and item["result_contract"].get("decision") == "INCONCLUSIVE"
        }
    )
    missing = sorted(
        name
        for name in set(required.values())
        if not any(item.get("agent_name") == name for item in completed)
    )
    implementation_name = required.get("implementation")
    implementation_end = max(
        (
            int(item.get("completed_sequence", 0))
            for item in completed
            if item.get("agent_name") == implementation_name
        ),
        default=0,
    )
    for role in ("build", "testing", "independent-domain-review"):
        name = required.get(role)
        if not name or name in missing:
            continue
        if not any(
            item.get("agent_name") == name
            and int(item.get("started_sequence", 0)) > implementation_end
            for item in completed
        ):
            missing.append(f"{name} (no final-state execution after implementation)")
    return sorted(missing), sorted(set(failed)), inconclusive


def orchestration_prompt(
    prompt: str, required: dict[str, str], result_path: Path
) -> str:
    required_text = "\n".join(f"- {role}: `{name}`" for role, name in required.items())
    return f"""You are the durable parent execution agent for a regulated software lease.

Operate as an adaptive loop: inspect state, create a visible task graph, choose the next
ready task, delegate isolated work to the most relevant registered custom agent, inspect
its result, update the graph, and repeat. Split or add tasks when evidence or failures
require it. Do not use a prewritten fixed chain and do not ask the user questions in this
unattended implementation phase. Exit inconclusive if authoritative information is
missing. Never push, approve, merge, deploy, or modify protected policy files.

Minimum independent capability coverage before completion:
{required_text}

Invoke those exact custom-agent names as subagents. Other registered specialists may be
used whenever the task graph warrants them. Testing and review must examine the final
worktree state. Resolve every material finding or report failure/inconclusive. The outer
supervisor will independently commit and run deterministic gates; do not claim that your
own judgment replaces them. Each specialist must finish with the exact one-line contract
required by its custom-agent prompt. A missing, malformed, FAIL or INCONCLUSIVE contract
does not satisfy the task. Runtime evidence is written to `{result_path}` by the host, not
by you.

LEASE PROMPT
============
{prompt}
"""


async def execute(args: argparse.Namespace) -> int:
    prompt_path = Path(args.prompt_file).resolve()
    packet_path = Path(args.extension_packet).resolve()
    result_path = Path(args.result).resolve()
    events_path = Path(args.events).resolve()
    board_path = Path(args.board).resolve()
    worktree = Path(args.worktree).resolve()
    base = {
        "schema_version": "1.0",
        "change_id": args.change_id,
        "repository_id": args.repository_id,
        "attempt": args.attempt,
        "phase": args.phase,
        "session_id": args.session_id,
        "model": args.model,
        "worktree": str(worktree),
        "start_head_sha": args.start_head_sha,
        "prompt_sha256": sha256_file(prompt_path),
        "extension_packet_sha256": sha256_file(packet_path),
        "task_board_path": str(board_path),
        "started_at": utc_now(),
    }
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        catalog, roles = build_agent_catalog(packet)
        skill_catalog, skill_directories = build_skill_catalog(packet)
        required = select_required_agents(catalog, roles, args.required_role)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {**base, "decision": "INCONCLUSIVE", "reason": str(exc), "executions": []}
        result["digest"] = stable_digest(result)
        atomic_json(result_path, result)
        print(f"COPILOT_RUNTIME_INCONCLUSIVE: {exc}")
        return EXIT_INCONCLUSIVE

    try:
        from copilot import CopilotClient, PermissionHandler
    except ImportError:
        reason = "github-copilot-sdk is not installed; install the pinned runtime requirements"
        result = {**base, "decision": "INCONCLUSIVE", "reason": reason, "required_agents": required, "executions": []}
        result["digest"] = stable_digest(result)
        atomic_json(result_path, result)
        print(f"COPILOT_RUNTIME_INCONCLUSIVE: {reason}")
        return EXIT_INCONCLUSIVE

    events: list[dict[str, Any]] = []
    resume_existing = events_path.is_file() and events_path.stat().st_size > 0
    if resume_existing:
        try:
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except json.JSONDecodeError as exc:
            reason = f"existing Copilot event stream is invalid: {exc}"
            result = {
                **base,
                "decision": "INCONCLUSIVE",
                "reason": reason,
                "required_agents": required,
                "executions": [],
            }
            result["digest"] = stable_digest(result)
            atomic_json(result_path, result)
            print(f"COPILOT_RUNTIME_INCONCLUSIVE: {reason}")
            return EXIT_INCONCLUSIVE
    events_path.parent.mkdir(parents=True, exist_ok=True)
    event_stream = events_path.open("a", encoding="utf-8")

    def handle(event: Any) -> None:
        normalized = normalized_event(event)
        events.append(normalized)
        event_stream.write(json.dumps(normalized, sort_keys=True) + "\n")
        event_stream.flush()
        write_activity_board(
            board_path,
            events,
            required,
            change_id=args.change_id,
            repository_id=args.repository_id,
        )

    custom_agents = []
    skill_bindings: dict[str, list[str]] = {}
    model_bindings: dict[str, str] = {}
    for agent in catalog:
        role = next(
            (
                required_role
                for required_role, name in required.items()
                if name == agent["name"]
            ),
            roles[agent["name"]],
        )
        contract_instruction = (
            "\n\n## Runtime result contract\n"
            "Your final response MUST end with exactly one line in this form (valid JSON, "
            "no code fence):\n"
            'SDLC_SPECIALIST_RESULT {"decision":"PASS|FAIL|INCONCLUSIVE",'
            '"summary":"concise result","evidence":["file, command, or observed fact"],'
            '"findings":["unresolved finding, if any"]}\n'
            "Use PASS only when this assigned role is complete against the current worktree. "
            "Use INCONCLUSIVE when authoritative input or executable evidence is unavailable."
        )
        config = {
            "name": agent["name"],
            "display_name": agent["display_name"],
            "description": agent["description"],
            "prompt": agent["prompt"] + contract_instruction,
        }
        configured_tools = sdk_tool_names(agent.get("tools"))
        if configured_tools is not None:
            config["tools"] = configured_tools
        if agent.get("model") and args.honor_agent_models:
            normalized_model = sdk_model_id(agent["model"])
            if normalized_model:
                config["model"] = normalized_model
        selected_skills = skills_for_agent(agent, role, skill_catalog)
        if selected_skills:
            config["skills"] = selected_skills
        skill_bindings[agent["name"]] = selected_skills
        custom_agents.append(config)

    write_activity_board(
        board_path,
        events,
        required,
        change_id=args.change_id,
        repository_id=args.repository_id,
    )

    client = CopilotClient()
    decision = "INCONCLUSIVE"
    reason = "runtime did not reach a terminal result"
    response_text = ""
    available_model_ids: set[str] = {args.model}
    try:
        await client.start()
        try:
            available_model_ids.update(
                str(getattr(model, "id", model))
                for model in await client.list_models()
            )
        except Exception:
            # Session creation is the authoritative availability check. An
            # unavailable per-agent preference must not break the whole lease.
            pass
        for config in custom_agents:
            preferred = config.get("model")
            if preferred not in available_model_ids:
                config.pop("model", None)
            model_bindings[config["name"]] = str(config.get("model") or args.model)
        if resume_existing:
            session = await client.resume_session(args.session_id)
        else:
            session = await client.create_session(
                session_id=args.session_id,
                model=args.model,
                streaming=True,
                include_sub_agent_streaming_events=True,
                custom_agents=custom_agents,
                enable_skills=bool(skill_directories),
                skill_directories=skill_directories,
                working_directory=str(worktree),
                on_permission_request=PermissionHandler.approve_all,
            )
        session.on(handle)
        response = await session.send_and_wait(
            orchestration_prompt(prompt_path.read_text(encoding="utf-8"), required, result_path)
        )
        response_text = str(getattr(getattr(response, "data", None), "content", "") or "")
        executions = summarize_executions(events)
        missing, failed, inconclusive = validate_required_executions(
            executions, required
        )
        if failed:
            decision, reason = "FAIL", "subagent failures: " + ", ".join(sorted(set(failed)))
        elif inconclusive:
            decision, reason = (
                "INCONCLUSIVE",
                "subagents require authoritative input or evidence: "
                + ", ".join(inconclusive),
            )
        elif missing:
            decision, reason = "INCONCLUSIVE", "required subagents did not complete: " + ", ".join(missing)
        else:
            decision, reason = "PASS", "required subagent lifecycle evidence completed"
    except Exception as exc:  # SDK/runtime errors must become durable evidence.
        executions = summarize_executions(events)
        reason = f"Copilot SDK execution failed: {type(exc).__name__}: {exc}"
    finally:
        event_stream.close()
        try:
            await client.stop()
        except Exception:
            pass

    result = {
        **base,
        "completed_at": utc_now(),
        "decision": decision,
        "reason": reason,
        "required_agents": required,
        "registered_agents": [agent["name"] for agent in catalog],
        "registered_skills": sorted(skill_catalog),
        "agent_skill_bindings": skill_bindings,
        "available_models": sorted(available_model_ids),
        "agent_model_bindings": model_bindings,
        "executions": executions,
        "events_sha256": sha256_file(events_path),
        "task_board_sha256": sha256_file(board_path),
        "response_sha256": stable_digest(response_text),
    }
    result["digest"] = stable_digest(result)
    atomic_json(result_path, result)
    print(response_text)
    print(f"COPILOT_RUNTIME_{decision}: {reason}")
    if decision == "PASS":
        return 0
    return EXIT_INCONCLUSIVE if decision == "INCONCLUSIVE" else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--prompt-file", required=True)
    result.add_argument("--extension-packet", required=True)
    result.add_argument("--result", required=True)
    result.add_argument("--events", required=True)
    result.add_argument("--board", required=True)
    result.add_argument("--worktree", required=True)
    result.add_argument("--change-id", required=True)
    result.add_argument("--repository-id", required=True)
    result.add_argument("--attempt", type=int, required=True)
    result.add_argument("--phase", required=True)
    result.add_argument("--session-id", required=True)
    result.add_argument("--start-head-sha", required=True)
    result.add_argument("--model", default="auto")
    result.add_argument("--required-role", action="append", default=[])
    result.add_argument("--honor-agent-models", action="store_true")
    return result


def main() -> int:
    return asyncio.run(execute(parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
