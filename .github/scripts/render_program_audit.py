#!/usr/bin/env python3
"""Render a visual audit summary for a control-plane program change.

Outputs a markdown report based on program-run artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path
import subprocess
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json(path)


def short_sha(value: str | None) -> str:
    if not value:
        return "-"
    return value[:8]


def git_head(path: Path) -> str | None:
    if not path.exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_changed_files(path: Path, base_sha: str, head_sha: str) -> list[str]:
    if not path.exists() or not base_sha or not head_sha:
        return []
    if base_sha == head_sha:
        return []
    result = subprocess.run(
        ["git", "-C", str(path), "diff", "--name-only", f"{base_sha}..{head_sha}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def collect_changed_files(run: dict[str, Any], run_dir: Path) -> dict[str, dict[str, Any]]:
    commit_vector = run.get("commit_vector") if isinstance(run.get("commit_vector"), dict) else {}
    repository_results = run.get("repository_results") if isinstance(run.get("repository_results"), dict) else {}

    changed: dict[str, dict[str, Any]] = {}
    for repo_id, info in commit_vector.items():
        if not isinstance(info, dict):
            continue
        base_sha = str(info.get("base_sha", ""))
        head_sha = str(info.get("head_sha", ""))
        mode = str(info.get("mode", "-"))
        worktree = Path(str(info.get("worktree", "")))
        git_files = git_changed_files(worktree, base_sha, head_sha)

        evidence_files: list[str] = []
        result = repository_results.get(repo_id)
        if isinstance(result, dict):
            evidence_rel = result.get("evidence_path")
            if isinstance(evidence_rel, str) and evidence_rel:
                evidence_path = run_dir / evidence_rel
                if evidence_path.exists():
                    try:
                        evidence_payload = read_json(evidence_path)
                        coverage = evidence_payload.get("requirement_coverage")
                        if isinstance(coverage, list):
                            for item in coverage:
                                if not isinstance(item, dict):
                                    continue
                                impl_files = item.get("implementation_files")
                                if isinstance(impl_files, list):
                                    for file_item in impl_files:
                                        if isinstance(file_item, str) and file_item.strip():
                                            evidence_files.append(file_item.strip())
                    except Exception:
                        pass

        changed[repo_id] = {
            "mode": mode,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "git_files": sorted(set(git_files)),
            "evidence_files": sorted(set(evidence_files)),
        }
    return changed


def verify_chain(events: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not events:
        return False, ["No events found"]
    expected_prev = "0" * 64
    for event in sorted(events, key=lambda item: int(item.get("sequence", 0))):
        seq = event.get("sequence")
        prev_hash = event.get("previous_hash")
        ev_hash = event.get("hash")
        if prev_hash != expected_prev:
            issues.append(
                f"sequence {seq}: previous_hash mismatch (expected {expected_prev[:8]}..., got {str(prev_hash)[:8]}...)"
            )
        if not isinstance(ev_hash, str) or len(ev_hash) != 64:
            issues.append(f"sequence {seq}: invalid event hash format")
            expected_prev = expected_prev
        else:
            expected_prev = ev_hash
    return len(issues) == 0, issues


def to_markdown(
    change_id: str,
    run: dict[str, Any],
    plan: dict[str, Any] | None,
    plan_approval_evidence: dict[str, Any] | None,
    changed_files: dict[str, dict[str, Any]],
    events: list[dict[str, Any]],
    chain_ok: bool,
    chain_issues: list[str],
    scorecard: dict[str, Any] | None,
) -> str:
    state = str(run.get("state", "UNKNOWN"))
    risk = str(run.get("risk_tier", "unknown"))
    created = str(run.get("created_at", "-"))
    updated = str(run.get("updated_at", "-"))
    event_count = int(run.get("event_count", len(events)))
    commit_vector = run.get("commit_vector", {}) if isinstance(run.get("commit_vector"), dict) else {}

    required_events = [
        "PROGRAM_CHANGE_STARTED",
        "PLAN_PREPARED",
        "PLAN_APPROVED",
        "WORKSPACES_PREPARED",
        "REPOSITORY_RESULT_RECORDED",
        "INTEGRATION_PASSED",
        "PLAN_CLOSED",
        "PR_SET_PREPARED",
        "PULL_REQUEST_RECORDED",
        "PR_SET_APPROVED",
    ]
    seen_types = {str(event.get("type")) for event in events}

    lines: list[str] = []
    lines.append(f"# Program Audit Summary: {change_id}")
    lines.append("")
    lines.append(f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Snapshot")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| State | {state} |")
    lines.append(f"| Risk Tier | {risk} |")
    lines.append(f"| Created | {created} |")
    lines.append(f"| Updated | {updated} |")
    lines.append(f"| Events Recorded | {event_count} |")
    lines.append(f"| Event Chain Integrity | {'PASS' if chain_ok else 'FAIL'} |")
    lines.append("")

    lines.append("## Proposed Plan")
    lines.append("")
    if isinstance(plan, dict):
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Plan Digest | {plan.get('digest', '-')} |")
        lines.append(f"| Implementation Scope | {', '.join(plan.get('implementation_scope', [])) if isinstance(plan.get('implementation_scope'), list) else '-'} |")
        lines.append(f"| Validation Scope | {', '.join(plan.get('validation_scope', [])) if isinstance(plan.get('validation_scope'), list) else '-'} |")
        lines.append(f"| Checkout Scope | {', '.join(plan.get('checkout_scope', [])) if isinstance(plan.get('checkout_scope'), list) else '-'} |")
        waves = plan.get("execution_waves")
        if isinstance(waves, list):
            rendered_waves = []
            for idx, wave in enumerate(waves, 1):
                if isinstance(wave, list):
                    rendered_waves.append(f"wave-{idx}:" + ",".join(str(x) for x in wave))
            lines.append(f"| Execution Waves | {'; '.join(rendered_waves) if rendered_waves else '-'} |")
        obligations = plan.get("requirement_obligations")
        if isinstance(obligations, list) and obligations:
            lines.append("")
            lines.append("Requirement obligations:")
            for req in obligations:
                if not isinstance(req, dict):
                    continue
                req_id = str(req.get("id", "-"))
                repos = req.get("repositories")
                evidence = req.get("required_evidence")
                lines.append(
                    f"- {req_id}: repos={','.join(repos) if isinstance(repos, list) else '-'}; evidence={','.join(evidence) if isinstance(evidence, list) else '-'}"
                )
    else:
        lines.append("- plan.json not found")
    lines.append("")

    lines.append("## Plan Approval")
    lines.append("")
    plan_approval = run.get("plan_approval")
    if isinstance(plan_approval, dict):
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Approver | {plan_approval.get('approver', '-')} |")
        lines.append(f"| Source URL | {plan_approval.get('source_url', '-')} |")
        lines.append(f"| Reviewed Artifact URL | {plan_approval.get('reviewed_artifact_url', '-')} |")
        lines.append(f"| Evidence SHA256 | {plan_approval.get('evidence_sha256', '-')} |")
        if isinstance(plan_approval_evidence, dict):
            lines.append(f"| Gate | {plan_approval_evidence.get('gate', '-')} |")
            lines.append(f"| Decision | {plan_approval_evidence.get('decision', '-')} |")
            lines.append(f"| Independent | {plan_approval_evidence.get('independent', '-')} |")
            lines.append(f"| Reviewed Digest | {plan_approval_evidence.get('reviewed_digest', '-')} |")
    else:
        lines.append("- Plan approval evidence missing")
    lines.append("")

    lines.append("## Gate Progress")
    lines.append("")
    for gate in required_events:
        mark = "[x]" if gate in seen_types else "[ ]"
        lines.append(f"- {mark} {gate}")
    lines.append("")

    if not chain_ok:
        lines.append("## Chain Issues")
        lines.append("")
        for issue in chain_issues:
            lines.append(f"- {issue}")
        lines.append("")

    lines.append("## Repository Drift Check")
    lines.append("")
    lines.append("| Repository | Mode | Base | Recorded Head | Current Worktree Head | Drift |")
    lines.append("|---|---:|---:|---:|---:|---|")

    for repo_id in sorted(commit_vector):
        info = commit_vector.get(repo_id, {})
        if not isinstance(info, dict):
            continue
        mode = str(info.get("mode", "-"))
        base_sha = str(info.get("base_sha", ""))
        recorded_head = str(info.get("head_sha", ""))
        worktree = Path(str(info.get("worktree", "")))
        current_head = git_head(worktree)
        if current_head is None:
            drift = "UNKNOWN (worktree missing or not git)"
        elif current_head == recorded_head:
            drift = "NO"
        else:
            drift = "YES"
        lines.append(
            f"| {repo_id} | {mode} | {short_sha(base_sha)} | {short_sha(recorded_head)} | {short_sha(current_head)} | {drift} |"
        )
    lines.append("")

    lines.append("## Event Timeline")
    lines.append("")
    lines.append("| Seq | Timestamp | Type | Hash |")
    lines.append("|---:|---|---|---|")
    for event in sorted(events, key=lambda item: int(item.get("sequence", 0))):
        seq = event.get("sequence", "-")
        ts = str(event.get("timestamp", "-"))
        typ = str(event.get("type", "-"))
        ev_hash = short_sha(str(event.get("hash", "")))
        lines.append(f"| {seq} | {ts} | {typ} | {ev_hash} |")
    lines.append("")

    lines.append("## Changed Files")
    lines.append("")
    lines.append("| Repository | Mode | Base | Head | Files (git diff) | Files (evidence) |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for repo_id in sorted(changed_files):
        item = changed_files[repo_id]
        git_files = item.get("git_files", []) if isinstance(item, dict) else []
        evidence_files = item.get("evidence_files", []) if isinstance(item, dict) else []
        lines.append(
            f"| {repo_id} | {item.get('mode', '-')} | {short_sha(item.get('base_sha'))} | {short_sha(item.get('head_sha'))} | {len(git_files)} | {len(evidence_files)} |"
        )
        if isinstance(git_files, list) and git_files:
            lines.append(f"- {repo_id} git diff: " + ", ".join(git_files))
        if isinstance(evidence_files, list) and evidence_files:
            lines.append(f"- {repo_id} evidence: " + ", ".join(evidence_files))
    if not changed_files:
        lines.append("- No repository changes recorded")
    lines.append("")

    lines.append("## Evidence Files")
    lines.append("")
    lines.append("- run.json")
    lines.append("- plan.json")
    lines.append("- requirements.json")
    lines.append("- commit-vector.json")
    lines.append("- events.jsonl")
    lines.append("- approvals/")

    if isinstance(scorecard, dict):
        scores = scorecard.get("scores", {}) if isinstance(scorecard.get("scores"), dict) else {}
        cp = scores.get("control_plane", {}) if isinstance(scores.get("control_plane"), dict) else {}
        sdlc = scores.get("gts_ai_sdlc", {}) if isinstance(scores.get("gts_ai_sdlc"), dict) else {}
        chain = scores.get("chain", {}) if isinstance(scores.get("chain"), dict) else {}

        lines.append("")
        lines.append("## Agent Chain Scorecard")
        lines.append("")
        lines.append("| Score | Value |")
        lines.append("|---|---:|")
        lines.append(f"| Control Plane | {cp.get('score', 0)}/{cp.get('max', 0)} |")
        lines.append(f"| gts.ai.sdlc | {sdlc.get('score', 0)}/{sdlc.get('max', 0)} |")
        lines.append(f"| Chain | {chain.get('score', 0)}/{chain.get('max', 0)} |")
        lines.append(
            f"| Hard Gates | {'PASS' if chain.get('hard_gates_pass') else 'FAIL'} |"
        )

        hard_gates = scorecard.get("hard_gates")
        if isinstance(hard_gates, list) and hard_gates:
            lines.append("")
            lines.append("### Hard Gate Details")
            lines.append("")
            for gate in hard_gates:
                if not isinstance(gate, dict):
                    continue
                passed = gate.get("pass") is True
                gate_id = str(gate.get("id", "-"))
                lines.append(f"- {'PASS' if passed else 'FAIL'}: {gate_id}")
                reasons = gate.get("reasons")
                if isinstance(reasons, list):
                    for reason in reasons:
                        lines.append(f"  - {reason}")

        pipeline = scorecard.get("pipeline_coverage")
        if isinstance(pipeline, dict):
            summary = pipeline.get("summary") if isinstance(pipeline.get("summary"), dict) else {}
            stages = pipeline.get("stages") if isinstance(pipeline.get("stages"), dict) else {}
            lines.append("")
            lines.append("### Pipeline Coverage")
            lines.append("")
            lines.append("| Stage | Status | Used By | Used Paths | Rating |")
            lines.append("|---|---|---|---|---:|")
            for stage_key in [
                "user_request",
                "control_plane_orchestration",
                "ingest_sources",
                "plan_and_human_gate_1",
                "prepare_workspaces",
                "load_repository_extensions",
                "gts_ai_sdlc_skills_agents",
                "implement_verify_integrate",
                "plan_closure_and_pr_set",
                "human_gate_2_and_release_evidence",
            ]:
                item = stages.get(stage_key, {}) if isinstance(stages, dict) else {}
                participants = item.get("participants", []) if isinstance(item, dict) else []
                used_by: list[str] = []
                used_paths: list[str] = []
                ratings: list[str] = []
                if isinstance(participants, list):
                    for participant in participants:
                        if not isinstance(participant, dict):
                            continue
                        used_by.append(str(participant.get("id", "unknown")))
                        path_value = str(participant.get("path", "")).strip()
                        used_paths.append(path_value if path_value else "-")
                        ratings.append(
                            f"{int(participant.get('rating', 0))}/{int(participant.get('max_rating', 5))}"
                        )
                lines.append(
                    f"| {stage_key} | {item.get('status', 'PENDING')} | "
                    f"{', '.join(used_by) if used_by else '-'} | "
                    f"{', '.join(used_paths) if used_paths else '-'} | "
                    f"{', '.join(ratings) if ratings else '-'} |"
                )
            lines.append("")
            lines.append(
                f"Pipeline summary: pass={summary.get('pass', 0)}, "
                f"partial={summary.get('partial', 0)}, "
                f"pending={summary.get('pending', 0)}, "
                f"total={summary.get('total', 0)}"
            )

    return "\n".join(lines) + "\n"


def to_html(
    change_id: str,
    run: dict[str, Any],
    plan: dict[str, Any] | None,
    plan_approval_evidence: dict[str, Any] | None,
    changed_files: dict[str, dict[str, Any]],
    events: list[dict[str, Any]],
    chain_ok: bool,
    chain_issues: list[str],
    scorecard: dict[str, Any] | None,
) -> str:
    state = str(run.get("state", "UNKNOWN"))
    risk = str(run.get("risk_tier", "unknown"))
    created = str(run.get("created_at", "-"))
    updated = str(run.get("updated_at", "-"))
    event_count = int(run.get("event_count", len(events)))
    commit_vector = run.get("commit_vector", {}) if isinstance(run.get("commit_vector"), dict) else {}

    required_events = [
        "PROGRAM_CHANGE_STARTED",
        "PLAN_PREPARED",
        "PLAN_APPROVED",
        "WORKSPACES_PREPARED",
        "REPOSITORY_RESULT_RECORDED",
        "INTEGRATION_PASSED",
        "PLAN_CLOSED",
        "PR_SET_PREPARED",
        "PULL_REQUEST_RECORDED",
        "PR_SET_APPROVED",
    ]
    seen_types = {str(event.get("type")) for event in events}

    sections: list[str] = []
    sections.append(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Program Audit Summary</title>
  <style>
    :root {
      --bg: #f7f9fc;
      --card: #ffffff;
      --text: #12263a;
      --muted: #52677d;
      --line: #d8e1ea;
      --pass: #1f9d55;
      --fail: #c53030;
      --warn: #b7791f;
      --accent: #0f5ea8;
    }
    body {
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
      background: linear-gradient(180deg, #eef4fb 0%, var(--bg) 30%);
      color: var(--text);
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 24px; }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 18px;
      margin-bottom: 16px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    h1, h2, h3 { margin: 0 0 12px 0; }
    h1 { font-size: 24px; }
    h2 { font-size: 18px; color: var(--accent); }
    h3 { font-size: 16px; }
    p.meta { margin: 4px 0 0 0; color: var(--muted); }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th, td { border-bottom: 1px solid var(--line); text-align: left; padding: 8px 10px; vertical-align: top; }
    th { color: var(--muted); font-weight: 600; }
    .status-pass { color: var(--pass); font-weight: 700; }
    .status-fail { color: var(--fail); font-weight: 700; }
    .status-pending { color: var(--warn); font-weight: 700; }
    ul { margin: 8px 0 0 20px; padding: 0; }
    li { margin: 4px 0; }
    code { background: #f2f6fa; border: 1px solid var(--line); border-radius: 4px; padding: 1px 4px; }
    .small { color: var(--muted); font-size: 13px; }
  </style>
</head>
<body>
<div class="wrap">
"""
    )

    sections.append(
        f"<div class=\"card\"><h1>Program Audit Summary: {html.escape(change_id)}</h1>"
        f"<p class=\"meta\">Generated: {html.escape(dt.datetime.now(dt.timezone.utc).isoformat())}</p></div>"
    )

    chain_css = "status-pass" if chain_ok else "status-fail"
    chain_text = "PASS" if chain_ok else "FAIL"
    sections.append("<div class=\"card\"><h2>Snapshot</h2><table><tbody>")
    for key, value in [
        ("State", state),
        ("Risk Tier", risk),
        ("Created", created),
        ("Updated", updated),
        ("Events Recorded", str(event_count)),
    ]:
        sections.append(
            f"<tr><th>{html.escape(key)}</th><td>{html.escape(value)}</td></tr>"
        )
    sections.append(
        f"<tr><th>Event Chain Integrity</th><td><span class=\"{chain_css}\">{chain_text}</span></td></tr>"
    )
    sections.append("</tbody></table></div>")

    sections.append("<div class=\"card\"><h2>Proposed Plan</h2>")
    if isinstance(plan, dict):
        sections.append("<table><tbody>")
        sections.append(f"<tr><th>Plan Digest</th><td><code>{html.escape(str(plan.get('digest', '-')))}</code></td></tr>")
        for key, label in (
            ("implementation_scope", "Implementation Scope"),
            ("validation_scope", "Validation Scope"),
            ("checkout_scope", "Checkout Scope"),
        ):
            values = plan.get(key)
            value = ", ".join(str(v) for v in values) if isinstance(values, list) else "-"
            sections.append(f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>")
        waves = plan.get("execution_waves")
        wave_text = "-"
        if isinstance(waves, list):
            rendered = []
            for idx, wave in enumerate(waves, 1):
                if isinstance(wave, list):
                    rendered.append(f"wave-{idx}:" + ",".join(str(x) for x in wave))
            wave_text = "; ".join(rendered) if rendered else "-"
        sections.append(f"<tr><th>Execution Waves</th><td>{html.escape(wave_text)}</td></tr>")
        sections.append("</tbody></table>")

        obligations = plan.get("requirement_obligations")
        if isinstance(obligations, list) and obligations:
            sections.append("<h3>Requirement Obligations</h3><ul>")
            for req in obligations:
                if not isinstance(req, dict):
                    continue
                req_id = str(req.get("id", "-"))
                repos = req.get("repositories")
                evidence = req.get("required_evidence")
                sections.append(
                    f"<li><code>{html.escape(req_id)}</code>: repos={html.escape(','.join(repos) if isinstance(repos, list) else '-')}; evidence={html.escape(','.join(evidence) if isinstance(evidence, list) else '-')}</li>"
                )
            sections.append("</ul>")
    else:
        sections.append("<p class=\"small\">plan.json not found</p>")
    sections.append("</div>")

    sections.append("<div class=\"card\"><h2>Plan Approval</h2>")
    plan_approval = run.get("plan_approval")
    if isinstance(plan_approval, dict):
        sections.append("<table><tbody>")
        sections.append(f"<tr><th>Approver</th><td>{html.escape(str(plan_approval.get('approver', '-')))}</td></tr>")
        sections.append(f"<tr><th>Source URL</th><td>{html.escape(str(plan_approval.get('source_url', '-')))}</td></tr>")
        sections.append(f"<tr><th>Reviewed Artifact URL</th><td>{html.escape(str(plan_approval.get('reviewed_artifact_url', '-')))}</td></tr>")
        sections.append(f"<tr><th>Evidence SHA256</th><td><code>{html.escape(str(plan_approval.get('evidence_sha256', '-')))}</code></td></tr>")
        if isinstance(plan_approval_evidence, dict):
            sections.append(f"<tr><th>Gate</th><td>{html.escape(str(plan_approval_evidence.get('gate', '-')))}</td></tr>")
            sections.append(f"<tr><th>Decision</th><td>{html.escape(str(plan_approval_evidence.get('decision', '-')))}</td></tr>")
            sections.append(f"<tr><th>Independent</th><td>{html.escape(str(plan_approval_evidence.get('independent', '-')))}</td></tr>")
            sections.append(f"<tr><th>Reviewed Digest</th><td><code>{html.escape(str(plan_approval_evidence.get('reviewed_digest', '-')))}</code></td></tr>")
        sections.append("</tbody></table>")
    else:
        sections.append("<p class=\"small\">Plan approval evidence missing</p>")
    sections.append("</div>")

    sections.append("<div class=\"card\"><h2>Gate Progress</h2><ul>")
    for gate in required_events:
        present = gate in seen_types
        css = "status-pass" if present else "status-pending"
        label = "PASS" if present else "PENDING"
        sections.append(
            f"<li><span class=\"{css}\">{label}</span> - {html.escape(gate)}</li>"
        )
    sections.append("</ul></div>")

    if not chain_ok:
        sections.append("<div class=\"card\"><h2>Chain Issues</h2><ul>")
        for issue in chain_issues:
            sections.append(f"<li>{html.escape(issue)}</li>")
        sections.append("</ul></div>")

    sections.append(
        "<div class=\"card\"><h2>Repository Drift Check</h2>"
        "<table><thead><tr><th>Repository</th><th>Mode</th><th>Base</th><th>Recorded Head</th><th>Current Worktree Head</th><th>Drift</th></tr></thead><tbody>"
    )
    for repo_id in sorted(commit_vector):
        info = commit_vector.get(repo_id, {})
        if not isinstance(info, dict):
            continue
        mode = str(info.get("mode", "-"))
        base_sha = str(info.get("base_sha", ""))
        recorded_head = str(info.get("head_sha", ""))
        worktree = Path(str(info.get("worktree", "")))
        current_head = git_head(worktree)
        if current_head is None:
            drift = "UNKNOWN"
            css = "status-pending"
        elif current_head == recorded_head:
            drift = "NO"
            css = "status-pass"
        else:
            drift = "YES"
            css = "status-fail"
        sections.append(
            "<tr>"
            f"<td>{html.escape(repo_id)}</td>"
            f"<td>{html.escape(mode)}</td>"
            f"<td><code>{html.escape(short_sha(base_sha))}</code></td>"
            f"<td><code>{html.escape(short_sha(recorded_head))}</code></td>"
            f"<td><code>{html.escape(short_sha(current_head))}</code></td>"
            f"<td><span class=\"{css}\">{html.escape(drift)}</span></td>"
            "</tr>"
        )
    sections.append("</tbody></table></div>")

    sections.append(
        "<div class=\"card\"><h2>Changed Files</h2>"
        "<table><thead><tr><th>Repository</th><th>Mode</th><th>Base</th><th>Head</th><th>Files (git diff)</th><th>Files (evidence)</th></tr></thead><tbody>"
    )
    for repo_id in sorted(changed_files):
        item = changed_files[repo_id]
        git_files = item.get("git_files", []) if isinstance(item, dict) else []
        evidence_files = item.get("evidence_files", []) if isinstance(item, dict) else []
        sections.append(
            "<tr>"
            f"<td>{html.escape(repo_id)}</td>"
            f"<td>{html.escape(str(item.get('mode', '-')))}</td>"
            f"<td><code>{html.escape(short_sha(str(item.get('base_sha', ''))))}</code></td>"
            f"<td><code>{html.escape(short_sha(str(item.get('head_sha', ''))))}</code></td>"
            f"<td>{len(git_files)}</td>"
            f"<td>{len(evidence_files)}</td>"
            "</tr>"
        )
        if isinstance(git_files, list) and git_files:
            sections.append(
                f"<tr><td colspan=\"6\" class=\"small\"><strong>{html.escape(repo_id)} git diff:</strong> {html.escape(', '.join(git_files))}</td></tr>"
            )
        if isinstance(evidence_files, list) and evidence_files:
            sections.append(
                f"<tr><td colspan=\"6\" class=\"small\"><strong>{html.escape(repo_id)} evidence:</strong> {html.escape(', '.join(evidence_files))}</td></tr>"
            )
    if not changed_files:
        sections.append("<tr><td colspan=\"6\" class=\"small\">No repository changes recorded</td></tr>")
    sections.append("</tbody></table></div>")

    sections.append(
        "<div class=\"card\"><h2>Event Timeline</h2>"
        "<table><thead><tr><th>Seq</th><th>Timestamp</th><th>Type</th><th>Hash</th></tr></thead><tbody>"
    )
    for event in sorted(events, key=lambda item: int(item.get("sequence", 0))):
        seq = str(event.get("sequence", "-"))
        ts = str(event.get("timestamp", "-"))
        typ = str(event.get("type", "-"))
        ev_hash = short_sha(str(event.get("hash", "")))
        sections.append(
            "<tr>"
            f"<td>{html.escape(seq)}</td>"
            f"<td>{html.escape(ts)}</td>"
            f"<td>{html.escape(typ)}</td>"
            f"<td><code>{html.escape(ev_hash)}</code></td>"
            "</tr>"
        )
    sections.append("</tbody></table></div>")

    if isinstance(scorecard, dict):
        scores = scorecard.get("scores", {}) if isinstance(scorecard.get("scores"), dict) else {}
        cp = scores.get("control_plane", {}) if isinstance(scores.get("control_plane"), dict) else {}
        sdlc = scores.get("gts_ai_sdlc", {}) if isinstance(scores.get("gts_ai_sdlc"), dict) else {}
        chain = scores.get("chain", {}) if isinstance(scores.get("chain"), dict) else {}
        hard_pass = chain.get("hard_gates_pass") is True

        sections.append(
            "<div class=\"card\"><h2>Agent Chain Scorecard</h2>"
            "<table><thead><tr><th>Score</th><th>Value</th></tr></thead><tbody>"
            f"<tr><td>Control Plane</td><td>{int(cp.get('score', 0))}/{int(cp.get('max', 0))}</td></tr>"
            f"<tr><td>gts.ai.sdlc</td><td>{int(sdlc.get('score', 0))}/{int(sdlc.get('max', 0))}</td></tr>"
            f"<tr><td>Chain</td><td>{int(chain.get('score', 0))}/{int(chain.get('max', 0))}</td></tr>"
            f"<tr><td>Hard Gates</td><td><span class=\"{'status-pass' if hard_pass else 'status-fail'}\">{'PASS' if hard_pass else 'FAIL'}</span></td></tr>"
            "</tbody></table>"
        )

        hard_gates = scorecard.get("hard_gates")
        if isinstance(hard_gates, list) and hard_gates:
            sections.append("<h3>Hard Gate Details</h3><ul>")
            for gate in hard_gates:
                if not isinstance(gate, dict):
                    continue
                passed = gate.get("pass") is True
                gate_id = str(gate.get("id", "-"))
                sections.append(
                    f"<li><span class=\"{'status-pass' if passed else 'status-fail'}\">{'PASS' if passed else 'FAIL'}</span> - {html.escape(gate_id)}"
                )
                reasons = gate.get("reasons")
                if isinstance(reasons, list) and reasons:
                    sections.append("<ul>")
                    for reason in reasons:
                        sections.append(f"<li class=\"small\">{html.escape(str(reason))}</li>")
                    sections.append("</ul>")
                sections.append("</li>")
            sections.append("</ul>")

        pipeline = scorecard.get("pipeline_coverage")
        if isinstance(pipeline, dict):
            summary = pipeline.get("summary") if isinstance(pipeline.get("summary"), dict) else {}
            stages = pipeline.get("stages") if isinstance(pipeline.get("stages"), dict) else {}
            sections.append(
                "<h3>Pipeline Coverage</h3>"
                "<table><thead><tr><th>Stage</th><th>Status</th><th>Used By</th><th>Used Paths</th><th>Rating</th></tr></thead><tbody>"
            )
            for stage_key in [
                "user_request",
                "control_plane_orchestration",
                "ingest_sources",
                "plan_and_human_gate_1",
                "prepare_workspaces",
                "load_repository_extensions",
                "gts_ai_sdlc_skills_agents",
                "implement_verify_integrate",
                "plan_closure_and_pr_set",
                "human_gate_2_and_release_evidence",
            ]:
                item = stages.get(stage_key, {}) if isinstance(stages, dict) else {}
                participants = item.get("participants", []) if isinstance(item, dict) else []
                used_by: list[str] = []
                used_paths: list[str] = []
                ratings: list[str] = []
                if isinstance(participants, list):
                    for part in participants:
                        if not isinstance(part, dict):
                            continue
                        used_by.append(str(part.get("id", "unknown")))
                        path_value = str(part.get("path", "")).strip()
                        used_paths.append(path_value if path_value else "-")
                        ratings.append(
                            f"{int(part.get('rating', 0))}/{int(part.get('max_rating', 5))}"
                        )
                status = str(item.get("status", "PENDING"))
                status_css = "status-pass" if status == "PASS" else ("status-pending" if status == "PARTIAL" else "status-fail")
                sections.append(
                    "<tr>"
                    f"<td>{html.escape(stage_key)}</td>"
                    f"<td><span class=\"{status_css}\">{html.escape(status)}</span></td>"
                    f"<td>{html.escape(', '.join(used_by) if used_by else '-')}</td>"
                    f"<td>{html.escape(', '.join(used_paths) if used_paths else '-')}</td>"
                    f"<td>{html.escape(', '.join(ratings) if ratings else '-')}</td>"
                    "</tr>"
                )
            sections.append("</tbody></table>")
            sections.append(
                f"<p class=\"small\">Pipeline summary: pass={int(summary.get('pass', 0))}, partial={int(summary.get('partial', 0))}, pending={int(summary.get('pending', 0))}, total={int(summary.get('total', 0))}</p>"
            )

        sections.append("</div>")

    sections.append("</div></body></html>")
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render markdown and HTML audit summaries for a program change.")
    parser.add_argument("--change-id", required=True, help="Program change ID, e.g. P7-3420")
    parser.add_argument("--write", action="store_true", help="Write summary to program-run folder")
    args = parser.parse_args()

    root = repo_root()
    run_dir = root / ".github" / "sdlc" / "program-runs" / args.change_id

    run = read_json(run_dir / "run.json")
    events = read_events(run_dir / "events.jsonl")
    chain_ok, chain_issues = verify_chain(events)

    if args.write:
        score_result = subprocess.run(
            [
                "python",
                str(root / ".github" / "scripts" / "score_program_agents.py"),
                "--change-id",
                args.change_id,
                "--write",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if score_result.returncode != 0:
            stderr = score_result.stderr.strip()
            stdout = score_result.stdout.strip()
            details = stderr or stdout or "unknown scoring failure"
            raise RuntimeError(f"score_program_agents.py failed: {details}")

    scorecard = read_optional_json(run_dir / "agent-scorecard.json")
    plan = read_optional_json(run_dir / "plan.json")
    plan_approval_evidence = read_optional_json(run_dir / "approvals" / "plan-approval.json")
    changed_files = collect_changed_files(run, run_dir)

    report = to_markdown(
        args.change_id,
        run,
        plan,
        plan_approval_evidence,
        changed_files,
        events,
        chain_ok,
        chain_issues,
        scorecard,
    )
    report_html = to_html(
        args.change_id,
        run,
        plan,
        plan_approval_evidence,
        changed_files,
        events,
        chain_ok,
        chain_issues,
        scorecard,
    )

    if args.write:
        output_md_path = run_dir / "audit-summary.md"
        output_html_path = run_dir / "audit-summary.html"
        output_md_path.write_text(report, encoding="utf-8")
        output_html_path.write_text(report_html, encoding="utf-8")
        print(str(output_md_path))
        print(str(output_html_path))
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
