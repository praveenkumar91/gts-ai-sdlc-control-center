from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "policy_kernel.py"
SPEC = importlib.util.spec_from_file_location("policy_kernel", SCRIPT)
assert SPEC and SPEC.loader
policy_kernel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy_kernel)
PolicyError = policy_kernel.PolicyError
PolicyKernel = policy_kernel.PolicyKernel


class PolicyKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.sdlc = self.root / ".github" / "sdlc"
        (self.sdlc / "repositories.d").mkdir(parents=True)
        (self.sdlc / "schemas").mkdir()
        self._write_json(
            self.sdlc / "program.json",
            {
                "schemaVersion": "1.0",
                "programId": "test-program",
                "catalogGlobs": [".github/sdlc/repositories.d/*.json"],
                "repositoryLocalDescriptor": ".github/sdlc/repository.json",
                "workspaceSearchRoots": ["."],
                "worktreeRoot": "workspace/worktrees",
                "runRoot": ".github/sdlc/runs",
                "auditRoot": ".github/sdlc/audit",
                "defaults": {
                    "riskTier": "high",
                    "maxCatalogRepositories": 100,
                    "maxActiveRepositories": 100,
                    "maxParallelWorkers": 4,
                    "maxNodeAttempts": 3,
                    "maxPlanReviewCycles": 3,
                    "requireGate1": True,
                    "requireGate2": True,
                },
                "protectedBranches": ["main", "master", "develop"],
                "automationIdentities": ["agent", "copilot", "github-actions", "jenkins"],
            },
        )
        self.add_repositories(100)
        self.kernel = PolicyKernel(self.root)
        self.evidence_counter = 0

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def add_repositories(self, count: int) -> None:
        for index in range(1, count + 1):
            repository_id = f"repo-{index:03d}"
            path = self.sdlc / "repositories.d" / f"{repository_id}.json"
            if path.exists():
                continue
            self._write_json(
                path,
                {
                    "schemaVersion": "1.0",
                    "repositoryId": repository_id,
                    "displayName": repository_id,
                    "system": "P7" if index % 2 else "T7",
                    "orchestrator": "p7-orchestrator" if index % 2 else "t7-orchestrator",
                    "checkout": {
                        "mode": "existing-or-clone",
                        "localCandidates": [f"workspace/repositories/{repository_id}"],
                        "remote": f"ssh://example.invalid/{repository_id}.git",
                        "defaultBranch": "main",
                    },
                    "ownership": {"components": [f"component-{index}"], "paths": ["src/**"]},
                    "capabilities": {
                        "provides": [f"capability-{index}"],
                        "consumes": [],
                        "contractsProduced": [],
                        "contractsConsumed": [],
                        "gui": index % 10 == 0,
                    },
                    "dependencies": [],
                    "sharedResources": [],
                    "customizations": {
                        "instructions": ["AGENTS.md"],
                        "agents": [".github/agents"],
                        "skills": [".agents/skills"],
                    },
                    "commands": {
                        "bootstrap": [],
                        "unit": ["test"],
                        "integration": [],
                        "lint": [],
                        "build": ["build"],
                        "security": [],
                    },
                },
            )

    @staticmethod
    def _digest(character: str) -> str:
        return "sha256:" + character * 64

    def make_graph(
        self,
        repository_ids: list[str],
        *,
        dependencies: dict[str, list[str]] | None = None,
        revision: int = 1,
        change_id: str = "change-001",
    ) -> dict:
        dependencies = dependencies or {repository_id: [] for repository_id in repository_ids}
        active_repositories = [
            {
                "repositoryId": repository_id,
                "disposition": "IMPLEMENTATION",
                "baseRevision": f"abcdef{index:034d}",
                "worktree": f"workspace/worktrees/{change_id}/{repository_id}",
                "dependsOn": dependencies.get(repository_id, []),
                "sharedResources": [],
            }
            for index, repository_id in enumerate(repository_ids, start=1)
        ]
        active_ids = set(repository_ids)
        repositories = active_repositories + [
            {
                "repositoryId": f"repo-{index:03d}",
                "disposition": "NOT_IMPACTED",
                "baseRevision": "not-applicable",
                "dependsOn": [],
                "sharedResources": [],
            }
            for index in range(1, 101)
            if f"repo-{index:03d}" not in active_ids
        ]
        nodes = [
            self.node("requirements", "REQUIREMENTS", [], "Freeze requirements", ["REQ-001"], ["PLAN-001"]),
            self.node("impact", "IMPACT", ["requirements"], "Select repository impact", ["REQ-001"], ["PLAN-001"]),
            self.node("plan", "PLAN", ["impact"], "Create architecture and plan", ["REQ-001"], ["PLAN-001"]),
            self.node("plan-review", "PLAN_REVIEW", ["plan"], "Independently review plan", ["REQ-001"], ["PLAN-001"]),
            self.node("gate-1", "HUMAN_GATE_1", ["plan-review"], "Human approves plan", ["REQ-001"], ["PLAN-001"]),
        ]
        next(node for node in nodes if node["id"] == "plan-review")["evidenceTypes"] = [
            "system-architecture-review",
            "program-plan-review",
        ]
        for repository_id in repository_ids:
            nodes.append(
                self.node(
                    f"checkout-{repository_id}",
                    "CHECKOUT",
                    ["gate-1"],
                    f"Prepare {repository_id}",
                    ["REQ-001"],
                    [f"PLAN-{repository_id}"],
                    repository_id,
                )
            )
            upstream_verification = [f"verify-{item}" for item in dependencies.get(repository_id, [])]
            nodes.append(
                self.node(
                    f"implement-{repository_id}",
                    "IMPLEMENT",
                    [f"checkout-{repository_id}", *upstream_verification],
                    f"Implement in {repository_id}",
                    ["REQ-001"],
                    [f"PLAN-{repository_id}"],
                    repository_id,
                    budget=2,
                )
            )
            nodes.append(
                self.node(
                    f"verify-{repository_id}",
                    "VERIFY",
                    [f"implement-{repository_id}"],
                    f"Verify {repository_id}",
                    ["REQ-001"],
                    [f"PLAN-{repository_id}"],
                    repository_id,
                )
            )
        verify_nodes = [f"verify-{repository_id}" for repository_id in repository_ids]
        nodes.append(self.node("integrate", "INTEGRATE", verify_nodes, "Run integration checks", ["REQ-001"], ["PLAN-INT"]))
        nodes.append(self.node("closure", "CLOSURE", ["integrate"], "Verify plan closure", ["REQ-001"], ["PLAN-INT"]))
        for repository_id in repository_ids:
            nodes.append(
                self.node(
                    f"pr-{repository_id}",
                    "PR_DRAFT",
                    ["closure"],
                    f"Prepare draft PR for {repository_id}",
                    ["REQ-001"],
                    [f"PLAN-{repository_id}"],
                    repository_id,
                )
            )
        nodes.append(
            self.node(
                "gate-2",
                "HUMAN_GATE_2",
                ["closure", *[f"pr-{repository_id}" for repository_id in repository_ids]],
                "Human approves PR set",
                ["REQ-001"],
                ["PLAN-INT"],
            )
        )
        return {
            "schemaVersion": "1.0",
            "changeId": change_id,
            "graphRevision": revision,
            "requirementsDigest": self._digest("a"),
            "impactDigest": self._digest("b"),
            "planDigest": self._digest("c"),
            "repositories": repositories,
            "nodes": nodes,
        }

    @staticmethod
    def node(
        node_id: str,
        node_type: str,
        dependencies: list[str],
        task: str,
        requirements: list[str],
        plan_tasks: list[str],
        repository_id: str | None = None,
        budget: int = 2,
    ) -> dict:
        value = {
            "id": node_id,
            "type": node_type,
            "dependsOn": dependencies,
            "task": task,
            "attemptBudget": budget,
            "evidenceTypes": ["test-output"],
            "requirementIds": requirements,
            "planTaskIds": plan_tasks,
            "sharedResources": [],
        }
        if repository_id:
            value["repositoryId"] = repository_id
        return value

    def init_and_register(self, graph: dict) -> str:
        change_id = graph["changeId"]
        self.kernel.init_run(change_id, "Test change", "human-user", "high")
        path = self.root / "inputs" / f"graph-{graph['graphRevision']}.json"
        self._write_json(path, graph)
        self.kernel.register_graph(change_id, path)
        return change_id

    def evidence(self, label: str = "evidence") -> Path:
        self.evidence_counter += 1
        path = self.root / "evidence" / f"{self.evidence_counter:03d}-{label}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"verified {label}\n", encoding="utf-8")
        return path

    def pass_node(self, change_id: str, node_id: str) -> None:
        evidence = [self.evidence(node_id)]
        if node_id == "plan-review":
            evidence.append(self.evidence("plan-review-independent-lane"))
        self.kernel.record(change_id, node_id, "PASS", "test-worker", evidence)

    def approve(self, change_id: str, gate: str, graph_digest: str, approver: str = "alice") -> Path:
        path = self.root / "approvals" / f"{change_id}-{gate}-{approver.replace(':', '_')}.json"
        self._write_json(
            path,
            {
                "schemaVersion": "1.0",
                "changeId": change_id,
                "gate": gate,
                "graphDigest": graph_digest,
                "decision": "APPROVE",
                "approver": approver,
                "approvedAt": "2026-08-19T08:00:00Z",
                "statement": f"I approve {gate} for this exact graph digest.",
                "evidenceRef": "VS Code chat session test-session",
            },
        )
        return path

    def pass_pre_gate(self, change_id: str) -> str:
        for node_id in ("requirements", "impact", "plan", "plan-review"):
            self.pass_node(change_id, node_id)
        ready = self.kernel.ready(change_id)
        self.assertEqual(["gate-1"], [item["id"] for item in ready["awaitingHumanApproval"]])
        graph_digest = ready["graphDigest"]
        self.kernel.approve(change_id, self.approve(change_id, "gate-1", graph_digest))
        return graph_digest

    def finish_run(self, change_id: str) -> None:
        while True:
            ready = self.kernel.ready(change_id)
            if ready["awaitingHumanApproval"]:
                self.assertEqual("gate-2", ready["awaitingHumanApproval"][0]["id"])
                self.kernel.approve(
                    change_id,
                    self.approve(change_id, "gate-2", ready["graphDigest"], approver="bob"),
                )
                return
            self.assertTrue(ready["scheduledWave"], "Run stalled before Gate 2")
            for node in ready["scheduledWave"]:
                self.pass_node(change_id, node["id"])

    def test_01_validates_100_repository_catalog(self) -> None:
        result = self.kernel.validate()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(100, result["catalogRepositories"])
        artifact = self.evidence("digest")
        digest = self.kernel.digest_artifact(artifact)
        self.assertRegex(digest["sha256"], r"^sha256:[a-f0-9]{64}$")

    def test_02_three_repository_dependency_graph_is_accepted(self) -> None:
        graph = self.make_graph(
            ["repo-001", "repo-002", "repo-003"],
            dependencies={"repo-001": [], "repo-002": ["repo-001"], "repo-003": ["repo-001"]},
        )
        result = self.kernel.validate_graph(graph)
        self.assertEqual(3, result["activeRepositories"])
        self.assertGreater(result["nodes"], 13)

    def test_03_eight_independent_repositories_respect_parallel_limit(self) -> None:
        graph = self.make_graph([f"repo-{index:03d}" for index in range(1, 9)])
        change_id = self.init_and_register(graph)
        self.pass_pre_gate(change_id)
        ready = self.kernel.ready(change_id)
        self.assertEqual(8, len(ready["readyNodes"]))
        self.assertEqual(4, len(ready["scheduledWave"]))
        calls = [
            (node["id"], self.evidence(f"parallel-{node['id']}"))
            for node in ready["scheduledWave"]
        ]
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(self.root),
                    "record",
                    "--change-id",
                    change_id,
                    "--node",
                    node_id,
                    "--outcome",
                    "PASS",
                    "--actor",
                    "parallel-worker",
                    "--evidence",
                    str(evidence),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for node_id, evidence in calls
        ]
        results = [process.communicate(timeout=30) for process in processes]
        for process, (stdout, stderr) in zip(processes, results):
            self.assertEqual(0, process.returncode, stderr)
            self.assertEqual("PASS", json.loads(stdout)["status"])
        state = json.loads((self.sdlc / "runs" / change_id / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(all(state["nodes"][node_id]["status"] == "PASS" for node_id, _ in calls))

    def test_04_one_hundred_active_repositories_are_supported(self) -> None:
        graph = self.make_graph([f"repo-{index:03d}" for index in range(1, 101)])
        result = self.kernel.validate_graph(graph)
        self.assertEqual(100, result["activeRepositories"])

    def test_05_configured_active_repository_limit_fails_closed(self) -> None:
        self.kernel.config["defaults"]["maxActiveRepositories"] = 60
        graph = self.make_graph([f"repo-{index:03d}" for index in range(1, 62)])
        with self.assertRaisesRegex(PolicyError, "maximum is 60"):
            self.kernel.validate_graph(graph)

    def test_06_cycle_is_rejected(self) -> None:
        graph = self.make_graph(["repo-001"])
        next(node for node in graph["nodes"] if node["id"] == "requirements")["dependsOn"] = ["gate-2"]
        with self.assertRaisesRegex(PolicyError, "cycle"):
            self.kernel.validate_graph(graph)

    def test_07_all_thirteen_stage_types_are_required(self) -> None:
        graph = self.make_graph(["repo-001"])
        graph["nodes"] = [node for node in graph["nodes"] if node["id"] != "integrate"]
        next(node for node in graph["nodes"] if node["id"] == "closure")["dependsOn"] = ["verify-repo-001"]
        with self.assertRaisesRegex(PolicyError, "all 13 stages"):
            self.kernel.validate_graph(graph)
        review_graph = self.make_graph(["repo-001"], change_id="change-review-evidence")
        next(node for node in review_graph["nodes"] if node["id"] == "plan-review")["evidenceTypes"] = [
            "one-review-only"
        ]
        self.kernel.init_run("change-review-evidence", "Review evidence test", "human-user", "high")
        review_path = self.root / "inputs" / "graph-review-evidence.json"
        self._write_json(review_path, review_graph)
        with self.assertRaisesRegex(PolicyError, "two independent PLAN_REVIEW"):
            self.kernel.register_graph("change-review-evidence", review_path)

    def test_08_bounded_failure_exhausts_attempt_budget(self) -> None:
        graph = self.make_graph(["repo-001"])
        change_id = self.init_and_register(graph)
        first_evidence = self.evidence("first")
        first = self.kernel.record(change_id, "requirements", "FAIL", "tester", [first_evidence])
        second = self.kernel.record(change_id, "requirements", "FAIL", "tester", [self.evidence("second")])
        self.assertEqual("PENDING", first["status"])
        self.assertEqual("FAIL", second["status"])
        self.assertEqual("FAIL", second["runStatus"])
        first_evidence.write_text("tampered retry evidence\n", encoding="utf-8")
        integrity = self.kernel.verify(change_id)
        self.assertTrue(any("Historical evidence digest mismatch" in error for error in integrity["errors"]))

    def test_09_automation_identity_cannot_approve_gate(self) -> None:
        change_id = self.init_and_register(self.make_graph(["repo-001"]))
        digest = self.kernel.ready(change_id)["graphDigest"]
        for node_id in ("requirements", "impact", "plan", "plan-review"):
            self.pass_node(change_id, node_id)
        with self.assertRaisesRegex(PolicyError, "Automation identities"):
            self.kernel.approve(change_id, self.approve(change_id, "gate-1", digest, approver="agent"))

    def test_10_digest_mismatched_approval_is_rejected(self) -> None:
        change_id = self.init_and_register(self.make_graph(["repo-001"]))
        for node_id in ("requirements", "impact", "plan", "plan-review"):
            self.pass_node(change_id, node_id)
        with self.assertRaisesRegex(PolicyError, "does not match the current graph"):
            self.kernel.approve(change_id, self.approve(change_id, "gate-1", self._digest("f")))

    def test_11_graph_revision_invalidates_gate_and_results(self) -> None:
        graph = self.make_graph(["repo-001"])
        change_id = self.init_and_register(graph)
        self.pass_pre_gate(change_id)
        revised = self.make_graph(["repo-001", "repo-002"], revision=2)
        revised_path = self.root / "inputs" / "graph-2.json"
        self._write_json(revised_path, revised)
        result = self.kernel.register_graph(change_id, revised_path)
        self.assertEqual("GRAPH_REVISED", result["status"])
        state = json.loads((self.sdlc / "runs" / change_id / "state.json").read_text(encoding="utf-8"))
        self.assertEqual({}, state["approvals"])
        self.assertTrue(all(node["status"] == "PENDING" for node in state["nodes"].values()))

    def test_12_evidence_tampering_is_detected(self) -> None:
        change_id = self.init_and_register(self.make_graph(["repo-001"]))
        evidence = self.evidence("requirements")
        self.kernel.record(change_id, "requirements", "PASS", "tester", [evidence])
        evidence.write_text("tampered\n", encoding="utf-8")
        result = self.kernel.verify(change_id)
        self.assertEqual("FAIL", result["integrity"])
        self.assertTrue(any("Evidence digest mismatch" in error for error in result["errors"]))

    def test_13_complete_run_verifies_pass(self) -> None:
        change_id = self.init_and_register(self.make_graph(["repo-001", "repo-002", "repo-003"]))
        self.pass_pre_gate(change_id)
        self.finish_run(change_id)
        result = self.kernel.verify(change_id)
        self.assertEqual("PASS", result["integrity"])
        self.assertEqual("PASS", result["result"])

    def test_14_hooks_deny_force_push_and_ask_for_protected_push(self) -> None:
        denied = self.kernel.handle_hook(
            {
                "hook_event_name": "PreToolUse",
                "session_id": "test",
                "tool_name": "runInTerminal",
                "tool_input": {"command": "git push --force-with-lease origin feature"},
            }
        )
        asked = self.kernel.handle_hook(
            {
                "hook_event_name": "PreToolUse",
                "session_id": "test",
                "tool_name": "runInTerminal",
                "tool_input": {"command": "git push origin HEAD:main"},
            }
        )
        self.assertEqual("deny", denied["hookSpecificOutput"]["permissionDecision"])
        self.assertEqual("ask", asked["hookSpecificOutput"]["permissionDecision"])

    def test_15_generated_workspace_contains_only_active_graph_repositories(self) -> None:
        graph = self.make_graph(["repo-001", "repo-002", "repo-003"])
        change_id = self.init_and_register(graph)
        output = self.root / "generated.code-workspace"
        with self.assertRaisesRegex(PolicyError, "Active worktree does not exist"):
            self.kernel.generate_workspace(change_id, output)
        for repository in graph["repositories"]:
            if repository["disposition"] != "NOT_IMPACTED":
                (self.root / repository["worktree"]).mkdir(parents=True)
        result = self.kernel.generate_workspace(change_id, output)
        workspace = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(4, result["folders"])
        self.assertEqual(4, len(workspace["folders"]))
        self.assertFalse(workspace["settings"]["chat.subagents.useRichRendering"])


if __name__ == "__main__":
    unittest.main()
