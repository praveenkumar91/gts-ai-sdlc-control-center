#!/usr/bin/env python3
"""Create the program's linked draft PRs after explicit execution authorization."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import program_orchestrator


SCP_REMOTE = re.compile(r"^(?:[^@]+@)?([^:]+):(.+)$")


def repository_selector(remote: str) -> str:
    if "://" in remote:
        parsed = urlparse(remote)
        path = parsed.path.strip("/").removesuffix(".git")
        if not parsed.hostname or path.count("/") < 1:
            raise program_orchestrator.ProgramError(f"unsupported GitHub remote: {remote}")
        return f"{parsed.hostname}/{path}"
    match = SCP_REMOTE.fullmatch(remote)
    if match:
        return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"
    raise program_orchestrator.ProgramError(f"unsupported GitHub remote: {remote}")


def planned_actions(
    engine: program_orchestrator.ProgramOrchestrator, change_id: str
) -> list[dict]:
    state = engine.read_state(change_id)
    if state["state"] not in {"PR_SET_READY", "AWAITING_PR_APPROVAL"}:
        raise program_orchestrator.ProgramError(
            "draft PRs may be created only from PR_SET_READY"
        )
    pr_set = program_orchestrator.read_json(engine.run_dir(change_id) / "pr-set.json")
    actions = []
    for spec in pr_set["pull_requests"]:
        repository_id = spec["repository_id"]
        if repository_id in state["pull_requests"]:
            continue
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        actual_head = program_orchestrator.run_command(
            ["git", "rev-parse", "HEAD"], worktree
        )
        if actual_head != spec["head_sha"]:
            raise program_orchestrator.ProgramError(
                f"{repository_id}: worktree HEAD differs from tested PR head"
            )
        if program_orchestrator.run_command(["git", "status", "--porcelain"], worktree):
            raise program_orchestrator.ProgramError(
                f"{repository_id}: worktree is dirty; commit and rerun all affected gates"
            )
        selector = repository_selector(spec["repository_url"])
        actions.append(
            {
                "repository_id": repository_id,
                "worktree": str(worktree),
                "push": [
                    "git",
                    "push",
                    "--set-upstream",
                    "origin",
                    spec["head_branch"],
                ],
                "create": [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    selector,
                    "--base",
                    spec["base_branch"],
                    "--head",
                    spec["head_branch"],
                    "--title",
                    spec["title"],
                    "--body",
                    spec["body"],
                    "--draft",
                ],
                "expected_head_sha": spec["head_sha"],
            }
        )
    return actions


def execute_actions(
    engine: program_orchestrator.ProgramOrchestrator,
    change_id: str,
    actions: list[dict],
) -> dict:
    state = engine.read_state(change_id)
    for action in actions:
        worktree = Path(action["worktree"])
        program_orchestrator.run_command(action["push"], worktree)
        url = program_orchestrator.run_command(action["create"], worktree)
        metadata_text = program_orchestrator.run_command(
            ["gh", "pr", "view", url, "--json", "number,url,headRefOid"],
            worktree,
        )
        try:
            metadata = json.loads(metadata_text)
        except json.JSONDecodeError as exc:
            raise program_orchestrator.ProgramError(
                f"{action['repository_id']}: gh returned invalid PR metadata"
            ) from exc
        if metadata.get("headRefOid") != action["expected_head_sha"]:
            raise program_orchestrator.ProgramError(
                f"{action['repository_id']}: created PR head differs from tested commit"
            )
        state = engine.record_pull_request(
            change_id,
            action["repository_id"],
            int(metadata["number"]),
            metadata["url"],
            metadata["headRefOid"],
        )
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=program_orchestrator.repository_root())
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    if manifest and not manifest.is_absolute():
        manifest = root / manifest
    try:
        engine = program_orchestrator.ProgramOrchestrator(root, manifest)
        actions = planned_actions(engine, args.change_id)
        if not args.execute:
            print(json.dumps({"decision": "DRY_RUN", "actions": actions}, indent=2))
            return 0
        state = execute_actions(engine, args.change_id, actions)
        print(json.dumps(state, indent=2))
        return 0
    except program_orchestrator.ProgramError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
