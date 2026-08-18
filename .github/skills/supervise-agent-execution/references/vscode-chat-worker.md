# VS Code Chat worker loop

Use the GTS control-centre checkout and select `gts-orchestrator`.
This is a compatibility mode, not the autonomous default. Set
`worker.mode=vscode-chat` only when an interactive Chat lease is required.

1. Run the supervisor for the approved change:

   ```text
   python .github/scripts/agent_supervisor.py run --change-id <id> --allow-clone
   ```

2. If status is `PAUSED_VSCODE_WORKER`, inspect the active lease:

   ```text
   python .github/scripts/agent_supervisor.py task --change-id <id>
   ```

   Mirror `task_board` and `visible_work_plan` through the VS Code `todo` tool.
   The supervisor also persists `IMPLEMENTATION_PLAN.md` so another chat can
   resume from file-backed state.

3. Read `prompt_path`. Work only in `worktree`. Read relevant selected
   resources using each authoritative `resolved_path`. A
   central GTS resource is outside the managed application repository and is
   read-only. The normal catalog is the control centre's own `.github/agents`
   and `.agents/skills`; external roots and the verified ZIP cache are migration
   compatibility inputs only.
4. Apply every skill entry in `specialist_usage_requirements` and run its exact
   `specialist_usage_commands` receipt. Agent profiles are excluded because a
   shell receipt cannot prove a VS Code subagent actually ran. Use
   `copilot-sdk` mode when independent agent execution is required.
5. Do not commit, push, approve, merge, deploy, edit the task artifact, or edit
   protected policy paths.
6. Leave the worktree ready and invoke the lease's `completion_command`. Add a
   concise `--summary`. Use `blocked-spec` for normative conflicts,
   `inconclusive` for missing tools/evidence, or `failed` when the attempt is
   genuinely unsuccessful.
7. The command verifies task integrity, plan and requirements digests, selected
   extension packet, skill usage receipts, starting HEAD and protected
   paths. It then commits, runs deterministic gates and continues to the next
   lease or gate. `specialist-usage.json` preserves guidance-file IDs and
   hashes; it is never subagent evidence.

Never use a Chat completion message as task evidence. If the IDE closes, rerun
the same change ID; the active lease and hash-chained state remain durable.
