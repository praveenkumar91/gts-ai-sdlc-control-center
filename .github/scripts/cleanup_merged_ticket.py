#!/usr/bin/env python3
"""Safely clean up merged ticket branches and optionally their worktrees.

Default mode is preview-only. Use --apply to execute changes.

Examples:
  python .github/scripts/cleanup_merged_ticket.py \
    --repo /path/to/repo \
    --branch change/P7-3420/p7-frontend

    python .github/scripts/cleanup_merged_ticket.py \
    --repo /path/to/repo \
    --branch change/P7-3420/p7-frontend \
        --branch-only \
    --apply --yes
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class CleanupError(RuntimeError):
    pass


@dataclass
class WorktreeInfo:
    path: str
    branch: Optional[str]


def run_git(repo: Path, args: list[str], check: bool = True) -> str:
    cmd = ["git", "-C", str(repo), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise CleanupError(f"Command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def current_branch_name(repo: Path) -> Optional[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    branch = proc.stdout.strip()
    return branch or None


def branch_ref_exists(repo: Path, ref: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", ref],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def parse_worktrees(repo: Path) -> list[WorktreeInfo]:
    out = run_git(repo, ["worktree", "list", "--porcelain"])
    lines = out.splitlines()
    items: list[WorktreeInfo] = []
    current_path: Optional[str] = None
    current_branch: Optional[str] = None

    def flush() -> None:
        nonlocal current_path, current_branch
        if current_path:
            items.append(WorktreeInfo(path=current_path, branch=current_branch))
        current_path = None
        current_branch = None

    for line in lines:
        if not line:
            flush()
            continue
        if line.startswith("worktree "):
            current_path = line.split(" ", 1)[1]
        elif line.startswith("branch refs/heads/"):
            current_branch = line.split("branch refs/heads/", 1)[1]

    flush()
    return items


def find_worktree_for_branch(repo: Path, branch: str) -> Optional[str]:
    for wt in parse_worktrees(repo):
        if wt.branch == branch:
            return wt.path
    return None


def is_merged(repo: Path, branch: str, remote: str, base_branch: str) -> tuple[bool, str, str]:
    base_ref = f"refs/remotes/{remote}/{base_branch}"
    local_ref = f"refs/heads/{branch}"
    remote_ref = f"refs/remotes/{remote}/{branch}"

    if not branch_ref_exists(repo, base_ref):
        raise CleanupError(
            f"Base ref {base_ref} not found. Run fetch first or verify --remote/--base-branch."
        )

    source_ref: Optional[str] = None
    if branch_ref_exists(repo, remote_ref):
        source_ref = remote_ref
    elif branch_ref_exists(repo, local_ref):
        source_ref = local_ref

    if source_ref is None:
        raise CleanupError(
            "Could not verify merge status because neither local nor remote branch ref exists. "
            "Refusing cleanup to keep guardrails."
        )

    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", source_ref, base_ref],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, source_ref, base_ref


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview/apply cleanup for merged ticket branches (with optional worktree removal)."
    )
    parser.add_argument("--repo", required=True, help="Path to repository root.")
    parser.add_argument("--branch", required=True, help="Feature branch to clean.")
    parser.add_argument("--remote", default="origin", help="Remote name (default: origin).")
    parser.add_argument("--base-branch", default="master", help="Base branch name on remote (default: master).")
    parser.add_argument(
        "--worktree-path",
        default=None,
        help="Explicit worktree path to remove. If omitted, branch worktree is auto-detected.",
    )
    parser.add_argument(
        "--branch-only",
        action="store_true",
        help="Branch-only cleanup mode: do not remove worktree, only delete merged branches.",
    )
    parser.add_argument("--apply", action="store_true", help="Execute cleanup. Default is preview only.")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation in apply mode.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        raise CleanupError(f"Not a git repository: {repo}")

    # Keep refs fresh before merge verification.
    run_git(repo, ["fetch", args.remote, "--prune"])

    merged, source_ref, base_ref = is_merged(repo, args.branch, args.remote, args.base_branch)
    worktree_path = None if args.branch_only else (args.worktree_path or find_worktree_for_branch(repo, args.branch))

    remote_ref = f"refs/remotes/{args.remote}/{args.branch}"
    local_ref = f"refs/heads/{args.branch}"
    remote_exists = branch_ref_exists(repo, remote_ref)
    local_exists = branch_ref_exists(repo, local_ref)

    print("Cleanup plan")
    print(f"- repo: {repo}")
    print(f"- branch: {args.branch}")
    print(f"- merge check: {source_ref} is ancestor of {base_ref} -> {merged}")
    print(f"- mode: {'branch-only' if args.branch_only else 'branch+worktree'}")
    print(f"- worktree: {worktree_path or 'not used / not found'}")
    print(f"- local branch exists: {local_exists}")
    print(f"- remote branch exists: {remote_exists}")

    if not merged:
        raise CleanupError("Refusing cleanup: branch is not merged into base branch.")

    if not args.apply:
        print("\nPreview only. Re-run with --apply to execute.")
        return 0

    if not args.yes:
        answer = input("\nProceed with cleanup? Type 'yes' to continue: ").strip().lower()
        if answer != "yes":
            print("Cancelled.")
            return 1

    # Remove worktree first; branch deletion fails if branch is checked out in a worktree.
    if worktree_path:
        current_top = run_git(repo, ["rev-parse", "--show-toplevel"])
        if Path(current_top).resolve() == Path(worktree_path).resolve():
            raise CleanupError(
                "Cannot remove the currently active worktree. Run this command from another checkout."
            )
        run_git(repo, ["worktree", "remove", worktree_path])
        print(f"Removed worktree: {worktree_path}")

    if local_exists:
        checked_out = current_branch_name(repo)
        if checked_out == args.branch:
            raise CleanupError(
                f"Cannot delete currently checked out branch {args.branch!r}. "
                f"Checkout {args.base_branch!r} (or another branch) and retry."
            )
        run_git(repo, ["branch", "-d", args.branch])
        print(f"Deleted local branch: {args.branch}")

    if remote_exists:
        run_git(repo, ["push", args.remote, "--delete", args.branch])
        print(f"Deleted remote branch: {args.remote}/{args.branch}")

    run_git(repo, ["fetch", args.remote, "--prune"])
    print("Pruned remote-tracking refs.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CleanupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
