from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import test_program_orchestrator as fixture_module


ROOT = Path(__file__).resolve().parents[3]
SUPERVISOR_PATH = ROOT / ".github" / "scripts" / "agent_supervisor.py"


def load_supervisor_module():
    spec = importlib.util.spec_from_file_location("agent_supervisor", SUPERVISOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["agent_supervisor"] = module
    spec.loader.exec_module(module)
    return module


supervisor_module = load_supervisor_module()


class AgentSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.ProgramOrchestratorTests(methodName="runTest")
        self.fixture.setUp()
        self.root = self.fixture.root
        self._install_quality_contract("risk-api")
        self._install_quality_contract("trading-ui")
        adapters = self.root / ".github/sdlc/stack-adapters"
        adapters.mkdir(parents=True)
        adapter = {
            "schema_version": "1.0",
            "required_capabilities": ["unit-tests"],
        }
        for stack in ("python", "vite-typescript"):
            (adapters / f"{stack}.json").write_text(
                json.dumps({"stack": stack, **adapter}, indent=2),
                encoding="utf-8",
            )
        self.worker_script = self.root / "fake_worker.py"
        self.set_worker_behavior("success")
        self.runtime_path = self.root / ".github/sdlc/agent-runtime.json"
        self.runtime_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "adoption_complete": True,
                    "worker": {
                        "enabled": True,
                        "argv": [
                            sys.executable,
                            str(self.worker_script),
                            "{prompt_file}",
                            "{attempt}",
                            "{phase}",
                            "{repository_id}",
                        ],
                        "working_directory": "worktree",
                        "timeout_seconds": 30,
                        "max_output_bytes": 100_000,
                        "max_prompt_bytes": 100_000,
                        "maximum_worker_attempts": 3,
                        "stale_lock_seconds": 60,
                        "blocked_spec_exit_code": 20,
                        "inconclusive_exit_code": 21,
                        "git_author_name": "Test SDLC Worker",
                        "git_author_email": "worker@example.invalid",
                        "environment_allowlist": [
                            "PATH",
                            "PATHEXT",
                            "SYSTEMROOT",
                            "WINDIR",
                            "TEMP",
                            "TMP",
                        ],
                        "protected_paths": [
                            ".github/sdlc/project.json",
                            ".github/sdlc/extensions.json",
                            ".github/workflows/**",
                            ".github/CODEOWNERS",
                            "CODEOWNERS",
                        ],
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self.supervisor = supervisor_module.AgentSupervisor(
            self.root,
            self.fixture.manifest_path,
            self.runtime_path,
        )

    def tearDown(self):
        self.fixture.tearDown()

    def _install_quality_contract(self, repository_id: str) -> None:
        checkout = self.fixture.workspace / repository_id
        self.fixture.git(checkout, "config", "user.email", "test@example.invalid")
        self.fixture.git(checkout, "config", "user.name", "Test User")
        (checkout / ".github/sdlc").mkdir(parents=True)
        (checkout / "quality_check.py").write_text(
            "from pathlib import Path\n"
            "raise SystemExit(1 if Path('fail.marker').exists() else 0)\n",
            encoding="utf-8",
        )
        (checkout / ".github/sdlc/project.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "adoption_complete": True,
                    "commands": [
                        {
                            "id": "unit-tests",
                            "enabled": True,
                            "required": True,
                            "timeout_seconds": 30,
                            "args": [sys.executable, "quality_check.py"],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self.fixture.git(checkout, "add", ".github", "quality_check.py")
        self.fixture.git(checkout, "commit", "-m", "add deterministic quality gate")
        self.fixture.git(checkout, "push", "origin", "main")

    def set_worker_behavior(self, behavior: str) -> None:
        if behavior == "success":
            body = (
                "readme = Path('README.md')\n"
                "readme.write_text(readme.read_text(encoding='utf-8') + "
                "f'\\nimplemented attempt {attempt}\\n', encoding='utf-8')\n"
            )
        elif behavior == "fail-once":
            body = (
                "readme = Path('README.md')\n"
                "readme.write_text(readme.read_text(encoding='utf-8') + "
                "f'\\nremediation attempt {attempt}\\n', encoding='utf-8')\n"
                "marker = Path('fail.marker')\n"
                "marker.write_text('fail\\n', encoding='utf-8') if attempt == 1 "
                "else marker.unlink(missing_ok=True)\n"
            )
        elif behavior == "policy-mutation":
            body = (
                "Path('.github/sdlc/project.json').write_text('{}\\n', "
                "encoding='utf-8')\n"
            )
        elif behavior == "always-fail":
            body = "raise SystemExit(7)\n"
        elif behavior == "blocked-spec":
            body = "print('Normative sections conflict')\nraise SystemExit(20)\n"
        elif behavior == "inconclusive":
            body = "print('Required compiler is unavailable')\nraise SystemExit(21)\n"
        else:
            raise AssertionError(f"unknown behavior: {behavior}")
        self.worker_script.write_text(
            "import sys\n"
            "from pathlib import Path\n"
            "prompt_file, attempt_text, phase, repository_id = sys.argv[1:]\n"
            "attempt = int(attempt_text)\n"
            "assert Path(prompt_file).is_file()\n"
            "assert repository_id == 'risk-api'\n"
            + body,
            encoding="utf-8",
        )

    def plan(self, approve: bool) -> dict:
        plan = self.fixture.start_and_plan()
        if approve:
            self.fixture.approve_plan("CHG-100", plan)
        return plan

    def use_vscode_chat_runtime(self) -> None:
        config = json.loads(self.runtime_path.read_text(encoding="utf-8"))
        config["worker"]["mode"] = "vscode-chat"
        config["worker"]["argv"] = []
        self.runtime_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        self.supervisor = supervisor_module.AgentSupervisor(
            self.root,
            self.fixture.manifest_path,
            self.runtime_path,
        )

    def test_pauses_at_human_gate_one_without_launching_worker(self):
        self.plan(approve=False)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "PAUSED_HUMAN_GATE_1")
        self.assertEqual(state["worker_runs"], [])
        self.assertEqual(
            self.fixture.engine.read_state("CHG-100")["state"],
            "AWAITING_PLAN_APPROVAL",
        )

    def test_pauses_for_user_clarification_before_planning(self):
        self.fixture.engine.start(
            "CHG-302",
            "Fix a frontend screen without supplied acceptance details",
            "change-requester",
            "high",
        )
        state = self.supervisor.run("CHG-302")
        self.assertEqual(state["status"], "PAUSED_CLARIFICATION")
        self.assertIn("user answers", state["reason"])

    def test_pauses_for_plan_review_before_human_gate_one(self):
        self.fixture.start_and_plan("CHG-303", complete_reviews=False)
        state = self.supervisor.run("CHG-303")
        self.assertEqual(state["status"], "PAUSED_PLAN_REVIEW")
        self.assertEqual(
            self.fixture.engine.read_state("CHG-303")["state"],
            "AWAITING_PLAN_REVIEW",
        )

    def test_runs_worker_repository_gates_and_integration_end_to_end(self):
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "PAUSED_PLAN_CLOSURE")
        program_state = self.fixture.engine.read_state("CHG-100")
        self.assertEqual(program_state["state"], "INTEGRATION_PASSED")
        self.assertEqual(
            {
                repository_id: result["decision"]
                for repository_id, result in program_state[
                    "repository_results"
                ].items()
            },
            {"risk-api": "PASS", "trading-ui": "PASS"},
        )
        self.assertEqual(
            [item["repository_id"] for item in state["worker_runs"]],
            ["risk-api"],
        )
        self.assertEqual(self.supervisor.verify("CHG-100"), [])

    def test_failed_gate_is_remediated_by_second_worker_attempt(self):
        self.set_worker_behavior("fail-once")
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "PAUSED_PLAN_CLOSURE")
        self.assertEqual(state["worker_attempts"]["risk-api"], 2)
        program_state = self.fixture.engine.read_state("CHG-100")
        self.assertEqual(program_state["remediation_cycles"]["risk-api"], 1)
        self.assertEqual(
            program_state["repository_results"]["risk-api"]["decision"],
            "PASS",
        )

    def test_step_budget_persists_and_resume_finishes_same_change(self):
        self.plan(approve=True)
        first = self.supervisor.run("CHG-100", max_steps=1)
        self.assertEqual(first["status"], "PAUSED_STEP_BUDGET")
        self.assertEqual(first["worker_runs"], [])
        second = self.supervisor.run("CHG-100")
        self.assertEqual(second["status"], "PAUSED_PLAN_CLOSURE")
        self.assertEqual(second["worker_attempts"]["risk-api"], 1)

    def test_worker_policy_mutation_is_not_committed_or_tested(self):
        self.set_worker_behavior("policy-mutation")
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "PAUSED_POLICY_MUTATION")
        program_state = self.fixture.engine.read_state("CHG-100")
        self.assertNotIn("risk-api", program_state["repository_results"])

    def test_worker_attempt_limit_fails_closed(self):
        self.set_worker_behavior("always-fail")
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "FAILED")
        self.assertEqual(state["worker_attempts"]["risk-api"], 3)

    def test_worker_specification_block_stops_without_gate_evidence(self):
        self.set_worker_behavior("blocked-spec")
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "BLOCKED_SPEC")
        self.assertNotIn(
            "risk-api",
            self.fixture.engine.read_state("CHG-100")["repository_results"],
        )

    def test_worker_missing_tooling_is_inconclusive_not_failed(self):
        self.set_worker_behavior("inconclusive")
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "PAUSED_INCONCLUSIVE")
        self.assertEqual(state["worker_attempts"]["risk-api"], 1)

    def test_integration_failure_triggers_repository_worker_remediation(self):
        counter = self.root / "integration-attempt.txt"
        (self.root / "integration_check.py").write_text(
            "from pathlib import Path\n"
            f"path = Path({str(counter)!r})\n"
            "attempt = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(attempt))\n"
            "raise SystemExit(1 if attempt == 1 else 0)\n",
            encoding="utf-8",
        )
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        self.assertEqual(state["status"], "PAUSED_PLAN_CLOSURE")
        self.assertEqual(state["worker_attempts"]["risk-api"], 2)
        program_state = self.fixture.engine.read_state("CHG-100")
        self.assertEqual(program_state["integration_remediation_cycles"], 1)
        self.assertEqual(program_state["state"], "INTEGRATION_PASSED")

    def test_supervisor_detects_worker_artifact_tampering(self):
        self.plan(approve=True)
        state = self.supervisor.run("CHG-100")
        prompt_path = (
            self.fixture.engine.run_dir("CHG-100")
            / state["worker_runs"][0]["prompt_path"]
        )
        prompt_path.write_text("tampered\n", encoding="utf-8")
        self.assertIn(
            "worker run 1: prompt artifact digest mismatch",
            self.supervisor.verify("CHG-100"),
        )

    def test_vscode_chat_task_is_leased_verified_committed_and_continued(self):
        self.use_vscode_chat_runtime()
        self.fixture.install_extensions("risk-api")
        self.plan(approve=True)
        leased = self.supervisor.run("CHG-100")
        self.assertEqual(leased["status"], "PAUSED_VSCODE_WORKER")
        task = leased["active_task"]
        self.assertEqual(task["repository_id"], "risk-api")
        self.assertTrue(task["repository_extension_digest"])
        self.assertEqual(
            {
                (item["kind"], item["id"])
                for item in task["specialist_usage_requirements"]
            },
            {
                ("skills", "validate-risk-model"),
            },
        )
        self.assertEqual(
            [item["id"] for item in task["visible_work_plan"]],
            [
                "orient",
                "investigate",
                "red",
                "green",
                "verify",
                "expert-review",
                "build",
                "handoff",
            ],
        )
        self.assertEqual(leased["task_board"][0]["status"], "in_progress")
        self.assertTrue(
            (
                self.fixture.engine.run_dir("CHG-100")
                / leased["implementation_plan_path"]
            ).is_file()
        )
        prompt = (
            self.fixture.engine.run_dir("CHG-100") / task["prompt_path"]
        ).read_text(encoding="utf-8")
        self.assertIn("resolved_path", prompt)
        worktree = Path(task["worktree"])
        readme = worktree / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\nimplemented in VS Code Chat\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            supervisor_module.SupervisorError, "usage receipts are missing"
        ):
            self.supervisor.complete_vscode_task(
                "CHG-100",
                task["task_id"],
                "ready",
                "Implemented and ran local checks.",
            )
        for requirement in task["specialist_usage_requirements"]:
            active = self.supervisor.record_specialist_usage(
                "CHG-100",
                task["task_id"],
                requirement["kind"],
                requirement["id"],
            )
        expert = next(
            item for item in active["visible_work_plan"] if item["id"] == "expert-review"
        )
        self.assertEqual(expert["status"], "completed")
        completed = self.supervisor.complete_vscode_task(
            "CHG-100",
            task["task_id"],
            "ready",
            "Implemented and ran local checks.",
        )
        self.assertEqual(completed["status"], "PAUSED_PLAN_CLOSURE")
        self.assertIsNone(completed["active_task"])
        self.assertEqual(completed["worker_runs"][0]["task_id"], task["task_id"])
        self.assertEqual(completed["worker_runs"][0]["specialist_usage_count"], 1)
        self.assertEqual(
            self.fixture.engine.read_state("CHG-100")["state"],
            "INTEGRATION_PASSED",
        )
        self.assertEqual(self.supervisor.verify("CHG-100"), [])
        usage_path = (
            self.fixture.engine.run_dir("CHG-100")
            / completed["worker_runs"][0]["specialist_usage_path"]
        )
        usage_path.write_text("{}\n", encoding="utf-8")
        self.assertIn(
            "worker run 1: specialist usage artifact digest mismatch",
            self.supervisor.verify("CHG-100"),
        )

    def test_vscode_chat_rejects_tampered_task_artifact(self):
        self.use_vscode_chat_runtime()
        self.plan(approve=True)
        leased = self.supervisor.run("CHG-100")
        task = leased["active_task"]
        task_path = self.fixture.engine.run_dir("CHG-100") / task["task_path"]
        task_path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(
            supervisor_module.SupervisorError, "task artifact digest mismatch"
        ):
            self.supervisor.complete_vscode_task(
                "CHG-100", task["task_id"], "ready", "done"
            )

    def test_vscode_chat_rejects_worker_commit(self):
        self.use_vscode_chat_runtime()
        self.plan(approve=True)
        leased = self.supervisor.run("CHG-100")
        task = leased["active_task"]
        worktree = Path(task["worktree"])
        (worktree / "README.md").write_text("worker committed\n", encoding="utf-8")
        self.fixture.git(worktree, "add", "README.md")
        self.fixture.git(worktree, "commit", "-m", "unauthorized worker commit")
        with self.assertRaisesRegex(
            supervisor_module.SupervisorError, "only the supervisor may commit"
        ):
            self.supervisor.complete_vscode_task(
                "CHG-100", task["task_id"], "ready", "done"
            )


class RuntimeConfigTests(unittest.TestCase):
    def test_runtime_packet_materializes_portable_gts_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "control"
            worktree = Path(temporary) / "repo"
            catalog = Path(temporary) / "catalog"
            root.mkdir()
            worktree.mkdir()
            skill = catalog / ".agents/skills/common/code-review/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("# Review\n", encoding="utf-8")

            class Engine:
                @staticmethod
                def _gts_catalog_root():
                    return catalog

            supervisor = object.__new__(supervisor_module.AgentSupervisor)
            supervisor.root = root
            supervisor.engine = Engine()
            supervisor.worker = {"required_specialist_roles": []}
            packet = supervisor._runtime_extension_packet(
                {
                    "skills": [
                        {
                            "id": "common-code-review",
                            "path": "gts.ai.sdlc/.agents/skills/common/code-review/SKILL.md",
                            "sha256": supervisor_module.program_orchestrator.file_digest(
                                skill
                            ),
                            "source": "central-gts-ai-sdlc-fallback",
                        }
                    ],
                    "agents": [],
                },
                worktree,
            )
            self.assertEqual(packet["skills"][0]["resolved_path"], str(skill))

    def test_runtime_rejects_shellless_command_without_prompt_binding(self):
        config = {
            "schema_version": "1.0",
            "adoption_complete": True,
            "worker": {
                "enabled": True,
                "argv": ["copilot"],
                "working_directory": "worktree",
                "timeout_seconds": 10,
                "max_output_bytes": 1024,
                "max_prompt_bytes": 1024,
                "maximum_worker_attempts": 1,
                "stale_lock_seconds": 60,
                "blocked_spec_exit_code": 20,
                "inconclusive_exit_code": 21,
                "git_author_name": "worker",
                "git_author_email": "worker@example.invalid",
                "environment_allowlist": [],
                "protected_paths": [".github/sdlc/project.json"],
            },
        }
        self.assertIn(
            "worker.argv must pass {prompt} or {prompt_file}",
            supervisor_module.validate_runtime_config(config, adoption=True),
        )

    def test_vscode_chat_runtime_does_not_require_cli_argv(self):
        config = {
            "schema_version": "1.0",
            "adoption_complete": True,
            "worker": {
                "enabled": True,
                "mode": "vscode-chat",
                "argv": [],
                "working_directory": "worktree",
                "timeout_seconds": 10,
                "max_output_bytes": 1024,
                "max_prompt_bytes": 1024,
                "maximum_worker_attempts": 1,
                "stale_lock_seconds": 60,
                "blocked_spec_exit_code": 20,
                "inconclusive_exit_code": 21,
                "git_author_name": "worker",
                "git_author_email": "worker@example.invalid",
                "environment_allowlist": [],
                "protected_paths": [".github/sdlc/project.json"],
            },
        }
        self.assertEqual(
            supervisor_module.validate_runtime_config(config, adoption=True), []
        )

    def test_copilot_sdk_runtime_requires_dispatch_contract(self):
        worker = {
            "enabled": True,
            "mode": "copilot-sdk",
            "working_directory": "worktree",
            "timeout_seconds": 10,
            "max_output_bytes": 1024,
            "max_prompt_bytes": 1024,
            "maximum_worker_attempts": 1,
            "stale_lock_seconds": 60,
            "blocked_spec_exit_code": 20,
            "inconclusive_exit_code": 21,
            "git_author_name": "worker",
            "git_author_email": "worker@example.invalid",
            "environment_allowlist": [],
            "protected_paths": [".github/sdlc/project.json"],
        }
        errors = supervisor_module.validate_runtime_config(
            {"schema_version": "1.0", "adoption_complete": True, "worker": worker},
            adoption=True,
        )
        self.assertIn(
            "worker.sdk_runner must be a non-empty path in copilot-sdk mode",
            errors,
        )
        self.assertIn(
            "worker.required_specialist_roles must be a non-empty unique string array in copilot-sdk mode",
            errors,
        )

    def test_agent_receipts_are_rejected_as_execution_proof(self):
        fixture = fixture_module.ProgramOrchestratorTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        runtime_path = fixture.root / ".github/sdlc/agent-runtime.json"
        runtime = {
            "schema_version": "1.0",
            "adoption_complete": True,
            "worker": {
                "enabled": True,
                "mode": "vscode-chat",
                "argv": [],
                "working_directory": "worktree",
                "timeout_seconds": 10,
                "max_output_bytes": 1024,
                "max_prompt_bytes": 100000,
                "maximum_worker_attempts": 1,
                "stale_lock_seconds": 60,
                "blocked_spec_exit_code": 20,
                "inconclusive_exit_code": 21,
                "git_author_name": "worker",
                "git_author_email": "worker@example.invalid",
                "environment_allowlist": [],
                "protected_paths": [".github/sdlc/project.json"],
            },
        }
        runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
        supervisor = supervisor_module.AgentSupervisor(
            fixture.root, fixture.manifest_path, runtime_path
        )
        with self.assertRaisesRegex(
            supervisor_module.SupervisorError,
            "agent receipt cannot prove subagent execution",
        ):
            supervisor.record_specialist_usage("CHG-100", "task", "agents", "fake")
