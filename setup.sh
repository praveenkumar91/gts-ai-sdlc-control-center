#!/usr/bin/env bash
# setup.sh — Install gts.ai.sdlc agents and skills into a VS Code workspace.
#
# Usage:
#   ./setup.sh [WORKSPACE_DIR]
#
# If WORKSPACE_DIR is omitted the script uses the current working directory.
# The script creates symlinks under:
#   <workspace>/.github/agents/   — all agent files (Tier 1, Tier 2, Tier 3)
#   <workspace>/.github/skills/   — all skill folders (common + system)

set -euo pipefail

# ── Resolve paths ────────────────────────────────────────────────────────────

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${1:-$PWD}"

# If called from inside the repo itself, default to the parent directory.
if [[ "$WORKSPACE_DIR" == "$REPO_DIR" ]]; then
  WORKSPACE_DIR="$(dirname "$REPO_DIR")"
fi

AGENTS_DIR="$WORKSPACE_DIR/.github/agents"
SKILLS_DIR="$WORKSPACE_DIR/.github/skills"

echo "Repository : $REPO_DIR"
echo "Workspace  : $WORKSPACE_DIR"
echo ""

# ── Helpers ──────────────────────────────────────────────────────────────────

make_link() {
  local target="$1"   # absolute path to the source file/dir in the repo
  local link="$2"     # absolute path where the symlink should be created

  if [[ -L "$link" ]]; then
    echo "  [skip]   $link  (symlink already exists)"
    return
  fi
  if [[ -e "$link" ]]; then
    echo "  [skip]   $link  (real file already exists — remove it manually to replace)"
    return
  fi

  # Compute a relative target path so the symlink works even after moves.
  local link_dir
  link_dir="$(dirname "$link")"
  local rel_target
  rel_target="$(realpath --relative-to="$link_dir" "$target")"

  ln -s "$rel_target" "$link"
  echo "  [link]   $link  →  $rel_target"
}

# ── Create destination directories ───────────────────────────────────────────

mkdir -p "$AGENTS_DIR"
mkdir -p "$SKILLS_DIR"

# ── Tier 1: Generic orchestrator ─────────────────────────────────────────────

echo "=== Tier 1: Generic Orchestrator ==="
make_link \
  "$REPO_DIR/agents/orchestrator/agent.md" \
  "$AGENTS_DIR/gts-orchestrator.agent.md"
echo ""

# ── Tier 2 + Tier 3: System subagents and pipeline agents ────────────────────

echo "=== Tier 2 & 3: System Subagents and Pipeline Agents ==="
for system_dir in "$REPO_DIR/subagents"/*/; do
  system="$(basename "$system_dir")"

  # Skip the _template folder
  [[ "$system" == _* ]] && continue

  # Tier 2: system orchestrator  (subagents/{system}/agent.md)
  if [[ -f "$system_dir/agent.md" ]]; then
    make_link \
      "$system_dir/agent.md" \
      "$AGENTS_DIR/${system}-orchestrator.agent.md"
  fi

  # Tier 3: pipeline agents  (subagents/{system}/agents/*.agent.md)
  if [[ -d "$system_dir/agents" ]]; then
    for agent_file in "$system_dir/agents"/*.agent.md; do
      [[ -f "$agent_file" ]] || continue
      agent_name="$(basename "$agent_file" .agent.md)"
      make_link \
        "$agent_file" \
        "$AGENTS_DIR/${system}-${agent_name}.agent.md"
    done
  fi
done
echo ""

# ── Skills: common ───────────────────────────────────────────────────────────

echo "=== Common Skills ==="
for skill_dir in "$REPO_DIR/skills/common"/*/; do
  [[ -d "$skill_dir" ]] || continue
  skill_name="$(basename "$skill_dir")"
  make_link "$skill_dir" "$SKILLS_DIR/$skill_name"
done
echo ""

# ── Skills: system-scoped ────────────────────────────────────────────────────

echo "=== System Skills ==="
for system_dir in "$REPO_DIR/skills/systems"/*/; do
  [[ -d "$system_dir" ]] || continue
  for skill_dir in "$system_dir"*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_name="$(basename "$skill_dir")"
    make_link "$skill_dir" "$SKILLS_DIR/$skill_name"
  done
done
echo ""

# ── Done ─────────────────────────────────────────────────────────────────────

echo "Setup complete."
echo ""
echo "Next step: reload VS Code (Ctrl+Shift+P → 'Developer: Reload Window')"
echo "Agents will appear in Copilot Chat as @gts-orchestrator, @p7-orchestrator, @t7-orchestrator, etc."
