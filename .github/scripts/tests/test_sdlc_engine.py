from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ENGINE_PATH = ROOT / ".github" / "scripts" / "sdlc_engine.py"
OPERATION_PATH = ROOT / ".github" / "scripts" / "run_operation.py"
APPROVAL_PATH = ROOT / ".github" / "scripts" / "emit_approval_evidence.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("sdlc_engine", ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["sdlc_engine"] = module
    spec.loader.exec_module(module)
    return module


sdlc_engine = load_engine_module()


class SdlcEngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        policy_dir = self.root / ".github" / "sdlc" / "policies"
        policy_dir.mkdir(parents=True)
        shutil.copy(
            ROOT / ".github/sdlc/policies/state-machine.json",
            policy_dir / "state-machine.json",
        )
        shutil.copy(
            ROOT / ".github/sdlc/policies/risk-tiers.json",
            policy_dir / "risk-tiers.json",
        )
        shutil.copy(
            ROOT / ".github/sdlc/policies/artifact-contracts.json",
            policy_dir / "artifact-contracts.json",
        )
        (self.root / ".github/sdlc/runs").mkdir()
        (self.root / "specs").mkdir()
        (self.root / "specs/ledger.md").write_text(
            "# Ledger\nDebits must equal credits.\n", encoding="utf-8"
        )
        (self.root / ".github/sdlc/sources.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "sources": [
                        {
                            "id": "ledger-spec",
                            "type": "repository",
                            "location": "specs",
                            "authority": "normative",
                            "version": "1.0",
                            "owner": "finance",
                            "required": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (self.root / ".gitignore").write_text(".github/sdlc/runs/\n", encoding="utf-8")
        self.git("init")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "SDLC Test")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")
        self.engine = sdlc_engine.Engine(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def start(self, change_id: str = "CHG-100"):
        return self.engine.start(change_id, "Add settlement validation", "high")

    def record_required(self, change_id: str, decision: str = "PASS"):
        state = self.engine.read_state(change_id)
        transition = self.engine.transition(state["state"])
        assert transition is not None
        for name in transition["required_artifacts"]:
            if name in state["artifacts"]:
                continue
            producer = self.engine.policy["artifact_producers"][name]
            self.engine.record_artifact(
                change_id,
                name,
                producer,
                decision,
                self.valid_payload(name, state["target_commit"]),
            )
        return transition

    def valid_payload(self, name: str, commit: str) -> dict:
        payloads = {
            "preproduction-report.json": {
                "all_tests_passed": True,
                "evidence_refs": ["run:100"],
            },
            "migration-rehearsal.json": {
                "rehearsal_passed": True,
                "rollback_tested": True,
            },
            "disaster-recovery-test.json": {
                "recovery_objectives_met": True,
                "failover_and_restore_tested": True,
            },
            "business-invariant-report.json": {
                "all_invariants_passed": True,
                "requirement_ids": ["REQ-1"],
                "checks": ["debits-equal-credits"],
            },
            "reconciliation-baseline.json": {
                "baseline_id": "BASE-1",
                "captured_at": "2026-07-28T12:00:00Z",
                "tolerances": {"unexplained_breaks": 0},
            },
            "human-approval-attestation.json": {
                "source": "github-environment",
                "approval_id": "APP-1",
                "approver": "accountable-owner",
                "approved_at": "2026-07-28T12:30:00Z",
                "environment": "production",
                "approved_commit": commit,
                "workflow_run_url": "https://github.com/example/project/actions/runs/100",
            },
            "change-window.json": {
                "window_id": "WINDOW-1",
                "starts_at": "2026-07-28T13:00:00Z",
                "ends_at": "2026-07-28T14:00:00Z",
                "runbook_url": "https://example.invalid/runbook",
            },
            "deployment-record.json": {
                "deployed_commit": commit,
                "artifact_digest": "a" * 64,
                "environment": "production",
                "strategy": "canary",
                "workflow_run_url": "https://github.com/example/project/actions/runs/101",
            },
            "canary-observations.json": {
                "guardrails_passed": True,
                "observations": [{"metric": "error-rate", "value": 0}],
            },
            "monitoring-report.json": {
                "guardrails_passed": True,
                "signals": [{"metric": "availability", "value": 1}],
            },
            "reconciliation-report.json": {
                "balanced": True,
                "unexplained_breaks": 0,
                "records_checked": 100,
            },
            "rollback-decision.json": {
                "action": "KEEP",
                "reason": "all approved guardrails and reconciliations passed",
            },
        }
        return payloads.get(name, {"requirement_ids": ["REQ-1"], "evidence": "test"})

    def advance_until(self, change_id: str, target_state: str):
        while self.engine.read_state(change_id)["state"] != target_state:
            state = self.engine.read_state(change_id)
            if state["state"] == "INTAKE":
                self.engine.snapshot_sources(change_id)
            if state["state"] == "DESIGN_READY":
                self.engine.bind_commit(change_id, "implementation", None)
            transition = self.engine.transition(self.engine.read_state(change_id)["state"])
            assert transition is not None
            self.record_required(change_id)
            self.engine.advance(change_id, transition["owner"])
        return self.engine.read_state(change_id)

    def test_start_snapshot_and_advance_preserve_valid_hash_chain(self):
        state = self.start()
        self.assertEqual(state["state"], "INTAKE")
        snapshot = self.engine.snapshot_sources("CHG-100")
        self.assertEqual(snapshot["decision"], "PASS")
        self.record_required("CHG-100")
        state = self.engine.advance("CHG-100", "spec-ingestion")
        self.assertEqual(state["state"], "KNOWLEDGE_READY")
        self.assertEqual(self.engine.verify("CHG-100"), [])

    def test_source_fingerprint_alone_does_not_claim_knowledge_ready(self):
        self.start()
        self.engine.snapshot_sources("CHG-100")
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "missing artifact context-pack"):
            self.engine.advance("CHG-100", "spec-ingestion")

    def test_dirty_worktree_cannot_start_evidence_run(self):
        (self.root / "uncommitted.txt").write_text("not reviewed", encoding="utf-8")
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "worktree must be clean"):
            self.start()

    def test_missing_artifacts_and_wrong_actor_fail_closed(self):
        self.start()
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "owned by spec-ingestion"):
            self.engine.advance("CHG-100", "implementation")
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "missing artifact"):
            self.engine.advance("CHG-100", "spec-ingestion")

    def test_non_pass_artifact_cannot_advance(self):
        self.start()
        self.engine.snapshot_sources("CHG-100")
        self.record_required("CHG-100")
        payload = {"errors": ["contradictory normative requirements"]}
        self.engine.record_artifact(
            "CHG-100",
            "context-pack.json",
            "spec-ingestion",
            "BLOCKED_SPEC",
            payload,
        )
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "artifact is not PASS"):
            self.engine.advance("CHG-100", "spec-ingestion")

    def test_implementation_commit_binding_rejects_non_head(self):
        self.start()
        self.engine.snapshot_sources("CHG-100")
        self.record_required("CHG-100")
        self.engine.advance("CHG-100", "spec-ingestion")
        for actor in ("requirements-engineer", "solution-architect"):
            transition = self.record_required("CHG-100")
            self.engine.advance("CHG-100", actor)
        self.assertEqual(
            self.engine.read_state("CHG-100")["state"],
            "DESIGN_READY",
        )
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "must equal the repository HEAD"):
            self.engine.bind_commit("CHG-100", "implementation", "a" * 40)

    def test_three_failures_stop_remediation(self):
        self.start()
        for cycle in range(3):
            state = self.engine.failure("CHG-100", "spec-ingestion", f"failure {cycle}")
        self.assertEqual(state["state"], "FAIL")
        self.assertEqual(state["remediation_cycles"], 3)
        self.assertEqual(self.engine.verify("CHG-100"), [])

    def test_complete_lifecycle_reaches_production_validated(self):
        self.start()
        state = self.advance_until("CHG-100", "PRODUCTION_VALIDATED")
        self.assertEqual(state["state"], "PRODUCTION_VALIDATED")
        self.assertIn("completed_at", state)
        self.assertEqual(self.engine.verify("CHG-100"), [])

    def test_post_implementation_failure_resets_and_invalidates_evidence(self):
        self.start()
        self.advance_until("CHG-100", "IMPLEMENTED")
        before = self.engine.read_state("CHG-100")
        self.assertIn("implementation-summary.json", before["artifacts"])
        state = self.engine.failure("CHG-100", "verification", "property test found a counterexample")
        self.assertEqual(state["state"], "DESIGN_READY")
        self.assertEqual(state["remediation_cycles"], 1)
        self.assertNotIn("implementation-summary.json", state["artifacts"])
        self.assertEqual(self.engine.verify("CHG-100"), [])

    def test_rollback_requires_authorized_actor_and_pass_evidence(self):
        self.start()
        self.advance_until("CHG-100", "PRODUCTION_APPROVED")
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "must be recorded by"):
            self.engine.rollback("CHG-100", "implementation", "canary breach")
        self.engine.record_artifact(
            "CHG-100",
            "rollback-execution.json",
            "deployment-controller",
            "PASS",
            {
                "restored": True,
                "reconciliation_passed": True,
                "restored_version": "previous-release",
            },
        )
        state = self.engine.rollback(
            "CHG-100", "deployment-controller", "canary reconciliation breach"
        )
        self.assertEqual(state["state"], "ROLLED_BACK")
        self.assertEqual(self.engine.verify("CHG-100"), [])

    def test_unauthorized_terminal_decision_is_rejected(self):
        self.start()
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "cannot terminate"):
            self.engine.terminate(
                "CHG-100",
                "implementation",
                "BLOCKED_SPEC",
                "attempted unauthorized decision",
            )

    def test_meaningless_pass_payload_is_rejected_by_contract(self):
        self.start()
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "all_invariants_passed"):
            self.engine.record_artifact(
                "CHG-100",
                "business-invariant-report.json",
                "business-invariant-validator",
                "PASS",
                {"claim": "looks good"},
            )

    def test_tampered_event_log_is_detected(self):
        self.start()
        events = self.engine.run_dir("CHG-100") / "events.jsonl"
        text = events.read_text(encoding="utf-8")
        events.write_text(text.replace("RUN_STARTED", "RUN_FORGED"), encoding="utf-8")
        errors = self.engine.verify("CHG-100")
        self.assertTrue(any("hash mismatch" in error for error in errors))

    def test_missing_required_source_is_inconclusive(self):
        sources = self.root / ".github/sdlc/sources.json"
        config = json.loads(sources.read_text(encoding="utf-8"))
        config["sources"][0]["location"] = "missing-specs"
        sources.write_text(json.dumps(config), encoding="utf-8")
        self.git("add", ".github/sdlc/sources.json")
        self.git("commit", "-m", "missing source fixture")
        self.start()
        result = self.engine.snapshot_sources("CHG-100")
        self.assertEqual(result["decision"], "INCONCLUSIVE")
        with self.assertRaisesRegex(sdlc_engine.SdlcError, "artifact is not PASS"):
            self.engine.advance("CHG-100", "spec-ingestion")

    def test_artifact_payload_tampering_is_detected(self):
        self.start()
        self.engine.snapshot_sources("CHG-100")
        state = self.engine.read_state("CHG-100")
        metadata = state["artifacts"]["source-snapshot.json"]
        path = self.engine.run_dir("CHG-100") / metadata["path"]
        envelope = json.loads(path.read_text(encoding="utf-8"))
        envelope["payload"]["forged"] = True
        path.write_text(json.dumps(envelope), encoding="utf-8")
        errors = self.engine.verify("CHG-100")
        self.assertTrue(any("artifact digest mismatch" in error for error in errors))

    def test_configured_operation_runs_exact_commit_without_shell(self):
        scripts = self.root / ".github/scripts"
        scripts.mkdir()
        shutil.copy(OPERATION_PATH, scripts / "run_operation.py")
        project = {
            "adoption_complete": True,
            "operations": {
                "enabled": True,
                "commands": [
                    {
                        "id": "preproduction-validation",
                        "enabled": True,
                        "timeout_seconds": 30,
                        "args": [sys.executable, "-c", "print('operation-ok')"],
                    }
                ],
            },
        }
        (self.root / ".github/sdlc/project.json").write_text(
            json.dumps(project), encoding="utf-8"
        )
        self.git("add", ".github/scripts/run_operation.py", ".github/sdlc/project.json")
        self.git("commit", "-m", "configured operation")
        commit = self.git("rev-parse", "HEAD")
        result = subprocess.run(
            [
                sys.executable,
                str(scripts / "run_operation.py"),
                "--operation",
                "preproduction-validation",
                "--change-id",
                "CHG-100",
                "--expected-commit",
                commit,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = json.loads(
            (
                self.root
                / ".github/sdlc/evidence/CHG-100/operations/preproduction-validation.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["commit_sha"], commit)

    def test_approval_evidence_does_not_claim_requester_is_approver(self):
        scripts = self.root / ".github/scripts"
        scripts.mkdir()
        shutil.copy(APPROVAL_PATH, scripts / "emit_approval_evidence.py")
        self.git("add", ".github/scripts/emit_approval_evidence.py")
        self.git("commit", "-m", "approval evidence helper")
        commit = self.git("rev-parse", "HEAD")
        environment = {
            **dict(os.environ),
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": "example/project",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_ACTOR": "requester",
        }
        result = subprocess.run(
            [
                sys.executable,
                str(scripts / "emit_approval_evidence.py"),
                "--change-id",
                "CHG-100",
                "--expected-commit",
                commit,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = json.loads(
            (
                self.root
                / ".github/sdlc/evidence/CHG-100/operations/production-approval-evidence.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["requested_by"], "requester")
        self.assertNotIn("approver", evidence)


if __name__ == "__main__":
    unittest.main()
