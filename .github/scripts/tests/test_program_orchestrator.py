from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROGRAM_PATH = ROOT / ".github" / "scripts" / "program_orchestrator.py"
EMIT_APPROVAL_PATH = ROOT / ".github" / "scripts" / "emit_program_approval.py"
CREATE_PRS_PATH = ROOT / ".github" / "scripts" / "create_draft_prs.py"
REPOSITORY_GATES_PATH = ROOT / ".github" / "scripts" / "run_repository_gates.py"
INTEGRATION_GATES_PATH = ROOT / ".github" / "scripts" / "run_integration_gates.py"


def load_program_module():
    spec = importlib.util.spec_from_file_location("program_orchestrator", PROGRAM_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["program_orchestrator"] = module
    spec.loader.exec_module(module)
    return module


program = load_program_module()


def load_utility_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


emit_approval = load_utility_module("emit_program_approval", EMIT_APPROVAL_PATH)
create_prs = load_utility_module("create_draft_prs", CREATE_PRS_PATH)
repository_gates = load_utility_module(
    "run_repository_gates", REPOSITORY_GATES_PATH
)
integration_gates = load_utility_module(
    "run_integration_gates", INTEGRATION_GATES_PATH
)


class ProgramUtilityTests(unittest.TestCase):
    def test_environment_approval_selects_independent_human(self):
        history = [
            {
                "state": "approved",
                "environments": [{"name": "sdlc-plan-approval"}],
                "user": {"login": "requester"},
            },
            {
                "state": "approved",
                "environments": [{"name": "sdlc-plan-approval"}],
                "user": {"login": "architecture-owner"},
            },
        ]
        self.assertEqual(
            emit_approval.independent_approver(
                history, "sdlc-plan-approval", "requester"
            ),
            "architecture-owner",
        )

    def test_environment_approval_rejects_wrong_gate(self):
        history = [
            {
                "state": "approved",
                "environments": [{"name": "production"}],
                "user": {"login": "architecture-owner"},
            }
        ]
        self.assertIsNone(
            emit_approval.independent_approver(
                history, "sdlc-plan-approval", "requester"
            )
        )

    def test_github_remote_selector_supports_cloud_and_enterprise(self):
        self.assertEqual(
            create_prs.repository_selector("https://github.com/acme/risk-api.git"),
            "github.com/acme/risk-api",
        )
        self.assertEqual(
            create_prs.repository_selector("git@github.example:acme/risk-api.git"),
            "github.example/acme/risk-api",
        )


class ProgramOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / "control-plane"
        self.workspace = self.base / "workspace"
        self.worktrees = self.base / "worktrees"
        self.origins = self.base / "origins"
        (self.root / ".github/sdlc").mkdir(parents=True)
        self.workspace.mkdir()
        self.origins.mkdir()
        (self.root / "integration_check.py").write_text(
            "raise SystemExit(0)\n", encoding="utf-8"
        )
        (self.root / ".github/sdlc/integration-gates.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "adoption_complete": True,
                    "commands": [
                        {
                            "id": "end-to-end",
                            "enabled": True,
                            "required": True,
                            "timeout_seconds": 30,
                            "args": [sys.executable, "integration_check.py"],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        contracts = self.create_repository("contracts")
        api = self.create_repository("risk-api")
        ui = self.create_repository("trading-ui")
        manifest = {
            "schema_version": "1.0",
            "program_id": "test-program",
            "adoption_complete": True,
            "workspace_root": str(self.workspace),
            "worktree_root": str(self.worktrees),
            "runs_directory": str(self.base / "runs"),
            "branch_prefix": "change/",
            "maximum_parallel_repositories": 4,
            "integration_quality_config": ".github/sdlc/integration-gates.json",
            "controls": {
                "human_plan_approval": True,
                "human_pr_approval": True,
                "human_production_approval": True,
                "allow_agent_self_approval": False,
                "maximum_remediation_cycles": 3,
            },
            "repositories": [
                self.repository_entry("contracts", contracts, []),
                self.repository_entry("risk-api", api, ["contracts"]),
                self.repository_entry("trading-ui", ui, ["risk-api"], "vite-typescript"),
            ],
        }
        self.manifest_path = self.root / ".github/sdlc/program.json"
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.engine = program.ProgramOrchestrator(self.root, self.manifest_path)

    def tearDown(self):
        self.temporary.cleanup()

    def test_gts_catalog_is_safely_loaded_from_sibling_sdlc_zip(self):
        archive_dir = self.base / "sdlc"
        archive_dir.mkdir()
        archive = archive_dir / "sdlc-master.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr(
                "gts.ai.sdlc-master/.agents/skills/common/ralph-loop/SKILL.md",
                "---\nname: ralph-loop\n---\n# Ralph loop\n",
            )
            bundle.writestr(
                "gts.ai.sdlc-master/.github/agents/p7-sdlc-developer.agent.md",
                "---\nname: p7-sdlc-developer\n---\n",
            )
        catalog = self.engine._gts_catalog_root()
        self.assertTrue(
            (catalog / ".agents/skills/common/ralph-loop/SKILL.md").is_file()
        )
        self.assertTrue((catalog.parent / ".complete").is_file())
        discovered = self.engine._discover_gts_catalog("p7-risk-api")
        self.assertIn("common-ralph-loop", {item["id"] for item in discovered["skills"]})
        self.assertIn(
            "p7-sdlc-developer.agent",
            {item["id"] for item in discovered["agents"]},
        )

    def test_gts_catalog_prefers_in_repository_source_and_explicit_system(self):
        common = self.root / ".agents/skills/common/ralph-loop/SKILL.md"
        system = self.root / ".agents/skills/systems/p7/p7-code/SKILL.md"
        developer = self.root / ".github/agents/p7-sdlc-developer.agent.md"
        router = self.root / ".github/agents/gts-prompt-clarifier.agent.md"
        for path, content in (
            (common, "---\nname: ralph-loop\n---\n# Ralph loop\n"),
            (system, "---\nname: p7-code\n---\n# P7 code\n"),
            (developer, "---\nname: p7-sdlc-developer\n---\n"),
            (router, "---\nname: gts-prompt-clarifier\n---\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.engine.repositories["risk-api"]["system"] = "p7"

        self.assertEqual(self.engine._gts_catalog_root(), self.root.resolve())
        discovered = self.engine._discover_gts_catalog("risk-api")
        self.assertIn(
            "common-ralph-loop", {item["id"] for item in discovered["skills"]}
        )
        self.assertIn("p7-p7-code", {item["id"] for item in discovered["skills"]})
        self.assertIn(
            "p7-sdlc-developer.agent",
            {item["id"] for item in discovered["agents"]},
        )
        self.assertIn(
            "gts-prompt-clarifier.agent",
            {item["id"] for item in discovered["agents"]},
        )

    def test_gts_catalog_rejects_zip_path_escape(self):
        archive_dir = self.base / "sdlc"
        archive_dir.mkdir()
        archive = archive_dir / "sdlc-master.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("gts.ai.sdlc-master/../escape.txt", "unsafe")
        with self.assertRaisesRegex(program.ProgramError, "unsafe path"):
            self.engine._gts_catalog_root()

    def test_dependency_graph_scales_to_one_hundred_repositories(self):
        repositories = {}
        for layer in range(10):
            for column in range(10):
                repository_id = f"repo-{layer:02d}-{column:02d}"
                dependencies = (
                    [] if layer == 0 else [f"repo-{layer - 1:02d}-{column:02d}"]
                )
                repositories[repository_id] = {
                    "id": repository_id,
                    "system": "p7" if column < 5 else "t7",
                    "depends_on": dependencies,
                }
        self.engine.repositories = repositories
        seeds = {f"repo-00-{column:02d}" for column in range(10)}

        validation_scope = self.engine.downstream_closure(seeds)
        checkout_scope = self.engine.upstream_closure(validation_scope)
        waves = self.engine.waves(validation_scope)

        self.assertEqual(len(validation_scope), 100)
        self.assertEqual(checkout_scope, validation_scope)
        self.assertEqual(len(waves), 10)
        self.assertTrue(all(len(wave) == 10 for wave in waves))

    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        return result.stdout.strip()

    def create_repository(self, name: str) -> Path:
        seed = self.base / f"{name}-seed"
        origin = self.origins / f"{name}.git"
        seed.mkdir()
        self.git(seed, "init", "-b", "main")
        self.git(seed, "config", "user.email", "test@example.invalid")
        self.git(seed, "config", "user.name", "Test User")
        (seed / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        self.git(seed, "add", "README.md")
        self.git(seed, "commit", "-m", "initial")
        self.git(self.origins, "init", "--bare", str(origin))
        self.git(seed, "remote", "add", "origin", str(origin))
        self.git(seed, "push", "-u", "origin", "main")
        clone = self.workspace / name
        self.git(self.workspace, "clone", "--branch", "main", str(origin), str(clone))
        return origin

    @staticmethod
    def repository_entry(
        repository_id: str, origin: Path, dependencies: list[str], stack: str = "python"
    ) -> dict:
        return {
            "id": repository_id,
            "enabled": True,
            "url": str(origin),
            "local_path": repository_id,
            "default_branch": "main",
            "stack": stack,
            "criticality": "critical",
            "quality_config": ".github/sdlc/project.json",
            "depends_on": dependencies,
        }

    def write_json(self, name: str, value: dict) -> Path:
        path = self.base / name
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        return path

    def install_extensions(self, repository_id: str) -> None:
        checkout = self.workspace / repository_id
        self.git(checkout, "config", "user.email", "test@example.invalid")
        self.git(checkout, "config", "user.name", "Test User")
        (checkout / ".github/instructions").mkdir(parents=True)
        (checkout / ".github/skills/validate-risk-model").mkdir(parents=True)
        (checkout / ".github/agents").mkdir(parents=True)
        (checkout / ".github/sdlc").mkdir(parents=True, exist_ok=True)
        (checkout / ".github/instructions/risk.instructions.md").write_text(
            "Preserve decimal precision and reconciliation.\n", encoding="utf-8"
        )
        (checkout / ".github/skills/validate-risk-model/SKILL.md").write_text(
            "---\n"
            "name: validate-risk-model\n"
            "description: Validate risk-model changes and their financial invariants.\n"
            "---\n\n"
            "Validate precision, limits, replay, and reconciliation.\n",
            encoding="utf-8",
        )
        (checkout / ".github/agents/risk-reviewer.agent.md").write_text(
            "---\n"
            "name: Risk Reviewer\n"
            "description: Independently review risk-domain behavior and evidence.\n"
            "tools:\n"
            "  - read\n"
            "---\n\n"
            "Review the assigned repository without approving the PR.\n",
            encoding="utf-8",
        )
        extension = {
            "schema_version": "1.0",
            "repository_id": repository_id,
            "instructions": [
                {
                    "id": "risk-rules",
                    "path": ".github/instructions/risk.instructions.md",
                    "required": True,
                }
            ],
            "skills": [
                {
                    "id": "validate-risk-model",
                    "path": ".github/skills/validate-risk-model/SKILL.md",
                    "required": True,
                    "activate_when": {
                        "modes": ["implementation"],
                        "request_terms": ["risk"],
                    },
                }
            ],
            "agents": [
                {
                    "id": "risk-reviewer",
                    "path": ".github/agents/risk-reviewer.agent.md",
                    "role": "independent-domain-review",
                    "required": True,
                    "activate_when": {"risk_tiers": ["critical"]},
                }
            ],
        }
        (checkout / ".github/sdlc/extensions.json").write_text(
            json.dumps(extension, indent=2), encoding="utf-8"
        )
        self.git(checkout, "add", ".github")
        self.git(checkout, "commit", "-m", "add repository extensions")
        self.git(checkout, "push", "origin", "main")

    def approve_plan(self, change_id: str, plan: dict) -> None:
        evidence = self.write_json(
            "plan-approval.json",
            {
                "change_id": change_id,
                "gate": "plan-approval",
                "decision": "APPROVED",
                "approver": "architecture-owner",
                "independent": True,
                "reviewed_digest": plan["digest"],
                "reviewed_artifact_url": "https://github.example/artifacts/plan",
                "source_url": "https://github.example/actions/runs/100",
            },
        )
        self.engine.approve_plan(change_id, evidence)

    def ready_intake(self, change_id: str) -> None:
        evidence = self.write_json(
            f"{change_id}-intake-ready.json",
            {
                "change_id": change_id,
                "decision": "READY",
                "assessor": "requirements-engineer",
                "source_facts": [
                    {
                        "source_id": "approved-risk-spec",
                        "fact": "The risk behavior and validation scope are specified.",
                        "citation": "approved-risk-spec section 1",
                    }
                ],
                "open_questions": [],
                "inaccessible_sources": [],
                "unverified_assumptions": [],
                "user_answers": [],
                "evidence_refs": [
                    "https://github.example/specs/risk/1.0"
                ],
            },
        )
        self.engine.assess_intake(change_id, evidence)

    def complete_plan_reviews(self, change_id: str, plan: dict) -> None:
        review_types = ["requirements", "architecture", "adversarial"]
        for index in range(3):
            evidence = self.write_json(
                f"{change_id}-plan-review-{index + 1}.json",
                {
                    "change_id": change_id,
                    "gate": "plan-review",
                    "decision": "PASS",
                    "reviewer": f"independent-reviewer-{index + 1}",
                    "independent": True,
                    "review_type": review_types[index],
                    "reviewed_digest": plan["digest"],
                    "findings": [],
                    "source_url": (
                        f"https://github.example/reviews/{change_id}/{index + 1}"
                    ),
                },
            )
            self.engine.record_plan_review(change_id, evidence)

    def start_and_plan(
        self, change_id: str = "CHG-100", *, complete_reviews: bool = True
    ) -> dict:
        self.engine.start(
            change_id,
            "Change the risk API and validate its consumers",
            "change-requester",
            "critical",
        )
        self.ready_intake(change_id)
        source_set = [
            {
                "source_id": "approved-risk-spec",
                "version": "1.0",
                "content_sha256": "sha256:" + ("d" * 64),
                "locator": "https://github.example/specs/risk/1.0",
            }
        ]
        requirements = self.write_json(
            f"{change_id}-requirements.json",
            {
                "change_id": change_id,
                "source_set_digest": "sha256:" + program.digest(source_set),
                "source_set": source_set,
                "requirements": [
                    {
                        "id": "RISK-100",
                        "statement": (
                            "Risk API changes preserve validated exposure behavior."
                        ),
                        "type": "functional",
                        "criticality": "critical",
                        "sources": [
                            {
                                "source_id": "approved-risk-spec",
                                "version": "1.0",
                                "section": "1",
                            }
                        ],
                        "repositories": ["risk-api"],
                        "acceptance_criteria": [
                            {
                                "id": "RISK-100-AC-001",
                                "statement": (
                                    "The exact changed commit passes risk behavior checks."
                                ),
                            }
                        ],
                        "required_evidence": [
                            "integration-test",
                            "repository-test",
                        ],
                        "verification": [
                            {
                                "scope": "repository",
                                "repository": "risk-api",
                                "gate_ids": ["unit-tests"],
                                "acceptance_criteria_ids": [],
                                "evidence_types": ["repository-test"],
                            },
                            {
                                "scope": "integration",
                                "gate_ids": ["end-to-end"],
                                "acceptance_criteria_ids": ["RISK-100-AC-001"],
                                "evidence_types": ["integration-test"],
                            },
                        ],
                    }
                ],
            },
        )
        plan = self.engine.plan(change_id, ["risk-api"], requirements)
        if complete_reviews:
            self.complete_plan_reviews(change_id, plan)
        return plan

    def prepare_all_repository_passes(self) -> dict:
        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        state = self.engine.prepare_workspaces(
            "CHG-100", execute=True, allow_clone=False
        )
        implementation_worktree = Path(
            state["commit_vector"]["risk-api"]["worktree"]
        )
        self.git(implementation_worktree, "config", "user.email", "test@example.invalid")
        self.git(implementation_worktree, "config", "user.name", "Test User")
        (implementation_worktree / "README.md").write_text(
            "# risk-api\n\nValidated risk behavior.\n", encoding="utf-8"
        )
        self.git(implementation_worktree, "add", "README.md")
        self.git(implementation_worktree, "commit", "-m", "implement risk behavior")
        self.engine.refresh_repository_extensions("CHG-100", "risk-api")
        state = self.engine.read_state("CHG-100")
        for repository_id in state["validation_scope"]:
            worktree = Path(state["commit_vector"][repository_id]["worktree"])
            coverage = [
                {
                    "requirement_id": obligation["id"],
                    "implementation_files": ["README.md"],
                    "test_ids": ["unit-tests"],
                    "acceptance_criteria_ids": [],
                    "evidence_types": ["repository-test"],
                    "evidence_refs": [
                        f"https://github.example/evidence/{repository_id}"
                    ],
                }
                for obligation in state["requirement_obligations"]
                if repository_id in obligation["repositories"]
            ]
            evidence = self.write_json(
                f"{repository_id}-quality.json",
                {
                    "change_id": "CHG-100",
                    "repository_id": repository_id,
                    "decision": "PASS",
                    "commit_sha": self.git(worktree, "rev-parse", "HEAD"),
                    "repository_extension_digest": state[
                        "repository_extensions"
                    ][repository_id]["digest"],
                    "gates": [{"id": "unit-tests", "status": "PASS"}],
                    "requirement_coverage": coverage,
                },
            )
            state = self.engine.record_repository_result(
                "CHG-100", repository_id, "PASS", evidence
            )
        return state

    def valid_integration_evidence(self, state: dict, name: str = "integration.json") -> Path:
        vector = {
            repository_id: state["commit_vector"][repository_id]["head_sha"]
            for repository_id in state["validation_scope"]
        }
        return self.write_json(
            name,
            {
                "change_id": "CHG-100",
                "decision": "PASS",
                "commit_vector": vector,
                "commit_vector_digest": state["commit_vector_digest"],
                "cross_repository_gates": [
                    {
                        "id": "end-to-end",
                        "status": "PASS",
                        "commit_vector_digest": state["commit_vector_digest"],
                        "requirement_ids": [
                            item["id"]
                            for item in state["requirement_obligations"]
                        ],
                        "source_refs": ["approved-risk-spec"],
                        "acceptance_criteria_ids": [
                            criterion["id"]
                            for item in state["requirement_obligations"]
                            for criterion in item["acceptance_criteria"]
                        ],
                        "evidence_types": ["integration-test"],
                        "evidence_refs": [
                            "https://github.example/evidence/integration"
                        ],
                    }
                ],
            },
        )

    def valid_plan_closure_evidence(
        self, state: dict, name: str = "plan-closure.json"
    ) -> Path:
        return self.write_json(
            name,
            {
                "change_id": "CHG-100",
                "decision": "PASS",
                "plan_digest": state["plan_digest"],
                "requirements_digest": state["requirements_digest"],
                "commit_vector_digest": state["commit_vector_digest"],
                "integration_evidence_sha256": state[
                    "integration_evidence_sha256"
                ],
                "requirement_results": [
                    {
                        "requirement_id": obligation["id"],
                        "status": "PASS",
                        "repositories": obligation["repositories"],
                        "acceptance_criteria": [
                            {
                                "id": criterion["id"],
                                "status": "PASS",
                                "evidence_refs": [
                                    "https://github.example/evidence/criterion"
                                ],
                            }
                            for criterion in obligation["acceptance_criteria"]
                        ],
                        "required_evidence": [
                            {
                                "type": evidence_type,
                                "status": "PASS",
                                "evidence_refs": [
                                    "https://github.example/evidence/type"
                                ],
                            }
                            for evidence_type in obligation["required_evidence"]
                        ],
                    }
                    for obligation in state["requirement_obligations"]
                ],
                "mandatory_reviews": [
                    {
                        "type": "independent-verification",
                        "decision": "PASS",
                        "actor": "verification-owner",
                        "independent": True,
                        "source_url": "https://github.example/reviews/verification",
                        "reviewed_plan_digest": state["plan_digest"],
                        "reviewed_commit_vector_digest": state[
                            "commit_vector_digest"
                        ],
                    },
                    {
                        "type": "adversarial-review",
                        "decision": "PASS",
                        "actor": "adversarial-owner",
                        "independent": True,
                        "source_url": "https://github.example/reviews/adversarial",
                        "reviewed_plan_digest": state["plan_digest"],
                        "reviewed_commit_vector_digest": state[
                            "commit_vector_digest"
                        ],
                    },
                ],
                "deviations": [],
            },
        )

    def test_manifest_rejects_dependency_cycle_and_self_approval(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["repositories"][0]["depends_on"] = ["trading-ui"]
        manifest["controls"]["allow_agent_self_approval"] = True
        manifest["branch_prefix"] = "--unsafe"
        errors = program.validate_manifest(manifest, adoption=True)
        self.assertTrue(any("dependency cycle" in error for error in errors))
        self.assertTrue(any("allow_agent_self_approval" in error for error in errors))
        self.assertTrue(any("branch_prefix" in error for error in errors))

    def test_extension_manifest_rejects_path_escape(self):
        errors = program.validate_extension_manifest(
            {
                "schema_version": "1.0",
                "repository_id": "risk-api",
                "skills": [
                    {
                        "id": "unsafe-skill",
                        "path": "../outside/SKILL.md",
                    }
                ],
            },
            "risk-api",
        )
        self.assertTrue(any("safe relative path" in error for error in errors))

    def test_plan_calculates_downstream_and_upstream_scope(self):
        plan = self.start_and_plan()
        self.assertEqual(plan["implementation_scope"], ["risk-api"])
        self.assertEqual(plan["validation_scope"], ["risk-api", "trading-ui"])
        self.assertEqual(
            plan["checkout_scope"], ["contracts", "risk-api", "trading-ui"]
        )
        self.assertEqual(plan["execution_waves"], [["risk-api"], ["trading-ui"]])
        impact = {
            item["repository_id"]: item["disposition"]
            for item in plan["repository_impact"]
        }
        self.assertEqual(
            impact,
            {
                "contracts": "CONTEXT_ONLY",
                "risk-api": "IMPLEMENTATION",
                "trading-ui": "VALIDATION_ONLY",
            },
        )
        self.assertEqual(
            self.engine.read_state("CHG-100")["state"], "AWAITING_PLAN_APPROVAL"
        )

    def test_intake_questions_block_planning_and_visible_steps_are_durable(self):
        change_id = "CHG-300"
        state = self.engine.start(
            change_id,
            "Fix an unspecified frontend layout problem",
            "change-requester",
            "high",
        )
        self.assertEqual(state["state"], "AWAITING_CLARIFICATION")
        visible = self.engine.run_dir(change_id) / "VISIBLE_STEPS.md"
        self.assertTrue(visible.is_file())
        self.assertIn("Clarify request", visible.read_text(encoding="utf-8"))

        needs_answers = self.write_json(
            "CHG-300-intake-needs-answers.json",
            {
                "change_id": change_id,
                "decision": "NEEDS_CLARIFICATION",
                "assessor": "requirements-engineer",
                "source_facts": [],
                "open_questions": [
                    "Which screens and viewports exhibit the layout defect?"
                ],
                "inaccessible_sources": ["Jira P7-2751"],
                "unverified_assumptions": [],
                "user_answers": [],
                "evidence_refs": [],
            },
        )
        state = self.engine.assess_intake(change_id, needs_answers)
        self.assertEqual(state["state"], "AWAITING_CLARIFICATION")
        self.assertEqual(
            state["clarification_rounds"][0]["open_questions"],
            ["Which screens and viewports exhibit the layout defect?"],
        )

        ready = self.write_json(
            "CHG-300-intake-ready.json",
            {
                "change_id": change_id,
                "decision": "READY",
                "assessor": "requirements-engineer",
                "source_facts": [
                    {
                        "source_id": "user-clarification",
                        "fact": "The defect affects the products table at desktop and mobile widths.",
                        "citation": "Chat answer 1",
                    }
                ],
                "open_questions": [],
                "inaccessible_sources": [],
                "unverified_assumptions": [],
                "user_answers": [
                    {
                        "question": "Which screens and viewports exhibit the layout defect?",
                        "answer": "Products table at desktop and mobile widths.",
                        "answered_by": "change-requester",
                    }
                ],
                "evidence_refs": ["https://github.example/audit/chat/300"],
            },
        )
        self.assertEqual(
            self.engine.assess_intake(change_id, ready)["state"], "INTAKE"
        )

    def test_plan_change_requires_revision_and_restarts_all_reviews(self):
        change_id = "CHG-301"
        plan = self.start_and_plan(change_id, complete_reviews=False)
        review = self.write_json(
            "CHG-301-plan-changes.json",
            {
                "change_id": change_id,
                "gate": "plan-review",
                "decision": "CHANGES_REQUIRED",
                "reviewer": "requirements-owner",
                "independent": True,
                "review_type": "requirements",
                "reviewed_digest": plan["digest"],
                "findings": ["Add an explicit failure-path acceptance criterion."],
                "source_url": "https://github.example/reviews/CHG-301/1",
            },
        )
        state = self.engine.record_plan_review(change_id, review)
        self.assertEqual(state["plan_review_status"], "CHANGES_REQUIRED")
        with self.assertRaisesRegex(program.ProgramError, "must be revised"):
            self.engine.record_plan_review(change_id, review)

        revised = self.engine.plan(
            change_id,
            ["risk-api"],
            self.base / f"{change_id}-requirements.json",
        )
        self.assertNotEqual(revised["digest"], plan["digest"])
        state = self.engine.read_state(change_id)
        self.assertEqual(state["plan_revision"], 2)
        self.assertEqual(state["plan_reviews"], [])
        self.complete_plan_reviews(change_id, revised)
        self.assertEqual(
            self.engine.read_state(change_id)["state"], "AWAITING_PLAN_APPROVAL"
        )

    def test_placeholder_human_approval_is_rejected(self):
        plan = self.start_and_plan()
        evidence = self.write_json(
            "placeholder-plan-approval.json",
            {
                "change_id": "CHG-100",
                "gate": "plan-approval",
                "decision": "APPROVED",
                "approver": "REPLACE_WITH_INDEPENDENT_HUMAN",
                "independent": True,
                "reviewed_digest": plan["digest"],
                "reviewed_artifact_url": (
                    "https://REPLACE_WITH_IMMUTABLE_PLAN_ARTIFACT"
                ),
                "source_url": "https://REPLACE_WITH_AUDITABLE_APPROVAL_RECORD",
            },
        )
        with self.assertRaisesRegex(program.ProgramError, "placeholder"):
            self.engine.approve_plan("CHG-100", evidence)

    def test_gui_requirement_without_approved_baseline_returns_to_clarification(self):
        change_id = "CHG-304"
        self.engine.start(
            change_id,
            "Reduce search bar width without supplied screenshots",
            "change-requester",
            "high",
        )
        self.ready_intake(change_id)
        source_set = [
            {
                "source_id": "jira-layout-request",
                "version": "1.0",
                "content_sha256": "sha256:" + ("a" * 64),
                "locator": "https://github.example/issues/304",
            }
        ]
        requirements = self.write_json(
            "CHG-304-requirements.json",
            {
                "change_id": change_id,
                "source_set_digest": "sha256:" + program.digest(source_set),
                "source_set": source_set,
                "requirements": [
                    {
                        "id": "UIREQ-304",
                        "statement": "The search bar uses an approved responsive layout.",
                        "type": "functional",
                        "criticality": "high",
                        "sources": [
                            {
                                "source_id": "jira-layout-request",
                                "version": "1.0",
                                "section": "summary",
                            }
                        ],
                        "repositories": ["trading-ui"],
                        "acceptance_criteria": [
                            {
                                "id": "UIREQ-304-AC-001",
                                "statement": "The approved layout matches at every required viewport.",
                            }
                        ],
                        "required_evidence": ["gui-validation"],
                        "verification": [
                            {
                                "scope": "repository",
                                "repository": "trading-ui",
                                "gate_ids": ["visual-regression"],
                                "acceptance_criteria_ids": ["UIREQ-304-AC-001"],
                                "evidence_types": ["gui-validation"],
                            },
                            {
                                "scope": "integration",
                                "gate_ids": ["end-to-end"],
                                "acceptance_criteria_ids": [],
                                "evidence_types": [],
                            },
                        ],
                    }
                ],
            },
        )
        with self.assertRaisesRegex(program.ProgramError, "gui_contract"):
            self.engine.plan(change_id, ["trading-ui"], requirements)
        payload = json.loads(requirements.read_text(encoding="utf-8"))
        payload["requirements"][0]["gui_contract"] = {
            "affected_views": ["Products table"],
            "user_journeys": ["Search products"],
            "viewports": ["1440x900", "390x844"],
            "states": ["default", "filtered", "empty", "error"],
            "baseline_refs": ["screenshots/products-approved.png"],
            "approval_ref": "https://github.example/design/304/approval",
        }
        requirements.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        plan = self.engine.plan(change_id, ["trading-ui"], requirements)
        self.assertEqual(
            plan["requirement_obligations"][0]["gui_contract"]["affected_views"],
            ["Products table"],
        )

    def test_plan_rejects_requirement_without_verification_matrix(self):
        change_id = "CHG-200"
        self.engine.start(
            change_id,
            "Change risk behavior without a verification plan",
            "change-requester",
            "critical",
        )
        self.ready_intake(change_id)
        source_set = [
            {
                "source_id": "risk-spec",
                "version": "1.0",
                "content_sha256": "sha256:" + ("e" * 64),
                "locator": "https://github.example/specs/risk/2",
            }
        ]
        requirements = self.write_json(
            "missing-verification.json",
            {
                "change_id": change_id,
                "source_set_digest": "sha256:" + program.digest(source_set),
                "source_set": source_set,
                "requirements": [
                    {
                        "id": "RISK-200",
                        "statement": "Risk behavior follows the approved specification.",
                        "type": "functional",
                        "criticality": "critical",
                        "sources": [
                            {
                                "source_id": "risk-spec",
                                "version": "1.0",
                                "section": "2",
                            }
                        ],
                        "repositories": ["risk-api"],
                        "acceptance_criteria": ["The behavior is deterministic."],
                        "required_evidence": ["repository-test"],
                    }
                ],
            },
        )
        with self.assertRaisesRegex(program.ProgramError, "verification matrix"):
            self.engine.plan(change_id, ["risk-api"], requirements)

    def test_plan_rejects_unsafe_verification_gate_id(self):
        source_set = [
            {
                "source_id": "risk-spec",
                "version": "1.0",
                "content_sha256": "sha256:" + ("f" * 64),
                "locator": "https://github.example/specs/risk/3",
            }
        ]
        payload = {
            "change_id": "CHG-300",
            "source_set_digest": "sha256:" + program.digest(source_set),
            "source_set": source_set,
            "requirements": [
                {
                    "id": "RISK-300",
                    "statement": "Risk behavior remains deterministic and auditable.",
                    "type": "functional",
                    "criticality": "critical",
                    "sources": [
                        {
                            "source_id": "risk-spec",
                            "version": "1.0",
                            "section": "3",
                        }
                    ],
                    "repositories": ["risk-api"],
                    "acceptance_criteria": [
                        {
                            "id": "RISK-300-AC-001",
                            "statement": "The result is deterministic.",
                        }
                    ],
                    "required_evidence": ["repository-test"],
                    "verification": [
                        {
                            "scope": "repository",
                            "repository": "risk-api",
                            "gate_ids": ["../escape"],
                            "acceptance_criteria_ids": [],
                            "evidence_types": ["repository-test"],
                        },
                        {
                            "scope": "integration",
                            "gate_ids": ["end-to-end"],
                            "acceptance_criteria_ids": ["RISK-300-AC-001"],
                            "evidence_types": [],
                        },
                    ],
                }
            ],
        }
        with self.assertRaisesRegex(program.ProgramError, "verification gate_ids"):
            program.normalize_requirement_obligations(
                payload, "CHG-300", {"risk-api"}
            )

    def test_plan_rejects_source_set_digest_not_matching_inventory(self):
        payload = json.loads(
            (ROOT / ".github/sdlc/examples/requirements.example.json").read_text(
                encoding="utf-8"
            )
        )
        payload["change_id"] = "CHG-400"
        payload["source_set_digest"] = "sha256:" + ("0" * 64)
        with self.assertRaisesRegex(program.ProgramError, "frozen source_set"):
            program.normalize_requirement_obligations(
                payload, "CHG-400", {"risk-api"}
            )

    def test_repository_evidence_rejects_unchanged_implementation_file(self):
        change_id = "CHG-201"
        plan = self.start_and_plan(change_id)
        self.approve_plan(change_id, plan)
        state = self.engine.prepare_workspaces(
            change_id, execute=True, allow_clone=False
        )
        worktree = Path(state["commit_vector"]["risk-api"]["worktree"])
        self.git(worktree, "config", "user.email", "test@example.invalid")
        self.git(worktree, "config", "user.name", "Test User")
        (worktree / "risk.py").write_text("LIMIT = 10\n", encoding="utf-8")
        self.git(worktree, "add", "risk.py")
        self.git(worktree, "commit", "-m", "implement risk change")
        packet = self.engine.refresh_repository_extensions(change_id, "risk-api")
        evidence = self.write_json(
            "fabricated-file-coverage.json",
            {
                "change_id": change_id,
                "repository_id": "risk-api",
                "decision": "PASS",
                "commit_sha": self.git(worktree, "rev-parse", "HEAD"),
                "repository_extension_digest": packet["digest"],
                "gates": [{"id": "unit-tests", "status": "PASS"}],
                "requirement_coverage": [
                    {
                        "requirement_id": "RISK-100",
                        "implementation_files": ["README.md"],
                        "test_ids": ["unit-tests"],
                        "acceptance_criteria_ids": [],
                        "evidence_types": ["repository-test"],
                        "evidence_refs": [
                            "https://github.example/evidence/unit-tests"
                        ],
                    }
                ],
            },
        )
        with self.assertRaisesRegex(program.ProgramError, "not changed"):
            self.engine.record_repository_result(
                change_id, "risk-api", "PASS", evidence
            )

    def test_requester_cannot_approve_plan(self):
        plan = self.start_and_plan()
        evidence = self.write_json(
            "bad-plan-approval.json",
            {
                "change_id": "CHG-100",
                "gate": "plan-approval",
                "decision": "APPROVED",
                "approver": "change-requester",
                "independent": True,
                "reviewed_digest": plan["digest"],
                "reviewed_artifact_url": "https://github.example/artifacts/plan",
                "source_url": "https://github.example/actions/runs/100",
            },
        )
        with self.assertRaisesRegex(program.ProgramError, "independent"):
            self.engine.approve_plan("CHG-100", evidence)

    def test_dirty_existing_repository_blocks_workspace_preparation(self):
        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        (self.workspace / "risk-api" / "dirty.txt").write_text("dirty", encoding="utf-8")
        with self.assertRaisesRegex(program.ProgramError, "DIRTY"):
            self.engine.prepare_workspaces(
                "CHG-100", execute=True, allow_clone=False
            )

    def test_repository_extensions_are_selected_hashed_and_bound(self):
        self.install_extensions("risk-api")
        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        state = self.engine.prepare_workspaces(
            "CHG-100", execute=True, allow_clone=False
        )
        packet = state["repository_extensions"]["risk-api"]
        self.assertEqual(packet["manifest"]["status"], "PRESENT")
        self.assertEqual(
            [item["id"] for item in packet["instructions"]], ["risk-rules"]
        )
        self.assertEqual(
            [item["id"] for item in packet["skills"]], ["validate-risk-model"]
        )
        self.assertEqual(
            [item["id"] for item in packet["agents"]], ["risk-reviewer"]
        )
        self.assertEqual(
            state["commit_vector"]["risk-api"]["repository_extension_digest"],
            packet["digest"],
        )
        artifact = json.loads(
            (
                self.engine.run_dir("CHG-100") / "repository-extensions.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            artifact["repositories"]["risk-api"]["digest"], packet["digest"]
        )

        worktree = Path(state["commit_vector"]["risk-api"]["worktree"])
        head = self.git(worktree, "rev-parse", "HEAD")
        bad_evidence = self.write_json(
            "bad-extension-evidence.json",
            {
                "change_id": "CHG-100",
                "repository_id": "risk-api",
                "decision": "PASS",
                "commit_sha": head,
                "repository_extension_digest": "0" * 64,
                "gates": [{"id": "unit-tests", "status": "PASS"}],
            },
        )
        with self.assertRaisesRegex(
            program.ProgramError, "selected extension packet"
        ):
            self.engine.record_repository_result(
                "CHG-100", "risk-api", "PASS", bad_evidence
            )

    def test_repository_can_inherit_central_stack_quality_config(self):
        central_quality = self.root / ".github/sdlc/default-python.json"
        central_quality.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "project_id": "central-python-default",
                    "adoption_complete": True,
                    "commands": [],
                }
            ),
            encoding="utf-8",
        )
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["default_quality_configs"] = {
            "python": ".github/sdlc/default-python.json"
        }
        for repository in manifest["repositories"]:
            if repository["id"] == "risk-api":
                repository.pop("quality_config")
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        self.engine = program.ProgramOrchestrator(self.root, self.manifest_path)

        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        state = self.engine.prepare_workspaces(
            "CHG-100", execute=True, allow_clone=False
        )
        quality = state["repository_extensions"]["risk-api"]["quality_config"]
        self.assertEqual(quality["source"], "central-stack-default")
        self.assertEqual(quality["base"], "control-plane")
        self.assertTrue(quality["exists"])

    def test_complete_program_flow_reaches_independent_pr_approval(self):
        state = self.prepare_all_repository_passes()
        state = self.engine.record_integration_result(
            "CHG-100", self.valid_integration_evidence(state)
        )
        self.assertEqual(state["state"], "INTEGRATION_PASSED")
        with self.assertRaisesRegex(program.ProgramError, "closure gate"):
            self.engine.prepare_pr_set("CHG-100", "Risk validation")
        state = self.engine.close_plan(
            "CHG-100", self.valid_plan_closure_evidence(state)
        )
        self.assertEqual(state["state"], "PLAN_CLOSED")

        pr_set = self.engine.prepare_pr_set("CHG-100", "Risk validation")
        self.assertEqual(len(pr_set["pull_requests"]), 1)
        head = state["commit_vector"]["risk-api"]["head_sha"]
        state = self.engine.record_pull_request(
            "CHG-100",
            "risk-api",
            42,
            "https://github.example/organisation/risk-api/pull/42",
            head,
        )
        self.assertEqual(state["state"], "AWAITING_PR_APPROVAL")

        approval = self.write_json(
            "pr-approval.json",
            {
                "change_id": "CHG-100",
                "gate": "pr-approval",
                "decision": "APPROVED",
                "approver": "release-owner",
                "independent": True,
                "reviewed_digest": state["pr_set_digest"],
                "reviewed_artifact_url": "https://github.example/artifacts/pr-set",
                "source_url": "https://github.example/actions/runs/200",
                "approved_pull_requests": [
                    {
                        "repository_id": "risk-api",
                        "number": 42,
                        "head_sha": head,
                        "required_checks_passed": True,
                        "approved_by": ["risk-code-owner"],
                    }
                ],
            },
        )
        state = self.engine.approve_pr_set("CHG-100", approval)
        self.assertEqual(state["state"], "PR_APPROVED")
        self.assertEqual(self.engine.verify("CHG-100"), [])

    def test_integration_runner_executes_frozen_gate_matrix(self):
        state = self.prepare_all_repository_passes()
        evidence, evidence_path = integration_gates.generate(
            self.engine, "CHG-100"
        )
        self.assertEqual(evidence["decision"], "PASS")
        self.assertEqual(
            [gate["id"] for gate in evidence["cross_repository_gates"]],
            ["end-to-end"],
        )
        self.assertEqual(
            evidence["cross_repository_gates"][0]["source_refs"],
            ["approved-risk-spec"],
        )
        state = self.engine.record_integration_result(
            "CHG-100", evidence_path
        )
        self.assertEqual(state["state"], "INTEGRATION_PASSED")

    def test_integration_rejects_head_changed_after_repository_gates(self):
        state = self.prepare_all_repository_passes()
        worktree = Path(state["commit_vector"]["risk-api"]["worktree"])
        (worktree / "late-change.txt").write_text(
            "not covered by repository gates\n", encoding="utf-8"
        )
        self.git(worktree, "add", "late-change.txt")
        self.git(worktree, "commit", "-m", "change after repository gates")
        _evidence, evidence_path = integration_gates.generate(
            self.engine, "CHG-100"
        )
        with self.assertRaisesRegex(
            program.ProgramError,
            "repository HEAD changed after repository gates passed",
        ):
            self.engine.record_integration_result("CHG-100", evidence_path)

    def test_integration_runner_preserves_failed_command(self):
        self.prepare_all_repository_passes()
        (self.root / "integration_check.py").write_text(
            "raise SystemExit(1)\n", encoding="utf-8"
        )
        for attempt in range(1, 4):
            evidence, evidence_path = integration_gates.generate(
                self.engine, "CHG-100"
            )
            self.assertEqual(evidence["decision"], "FAIL")
            self.assertEqual(
                evidence["cross_repository_gates"][0]["status"], "FAIL"
            )
            state = self.engine.record_integration_result(
                "CHG-100", evidence_path
            )
            self.assertEqual(state["integration_remediation_cycles"], attempt)
            self.assertEqual(
                state["state"], "FAIL" if attempt == 3 else "EXECUTING"
            )
        stored_attempt = (
            self.engine.run_dir("CHG-100")
            / state["integration_result"]["evidence_path"]
        )
        stored_attempt.write_text("{}\n", encoding="utf-8")
        self.assertIn(
            "integration attempt evidence digest mismatch",
            self.engine.verify("CHG-100"),
        )

    def test_integration_runner_classifies_unavailable_gate_as_inconclusive(self):
        self.prepare_all_repository_passes()
        config_path = self.root / ".github/sdlc/integration-gates.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["adoption_complete"] = False
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        evidence, evidence_path = integration_gates.generate(
            self.engine, "CHG-100"
        )
        self.assertEqual(evidence["decision"], "INCONCLUSIVE")
        self.assertEqual(
            evidence["cross_repository_gates"][0]["status"],
            "INCONCLUSIVE",
        )
        state = self.engine.record_integration_result(
            "CHG-100", evidence_path
        )
        self.assertEqual(state["state"], "EXECUTING")
        self.assertEqual(state["integration_remediation_cycles"], 1)

    def test_pass_repository_evidence_rejects_failed_required_gate(self):
        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        state = self.engine.prepare_workspaces(
            "CHG-100", execute=True, allow_clone=False
        )
        repository_id = "risk-api"
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        evidence = self.write_json(
            "concealed-repository-failure.json",
            {
                "change_id": "CHG-100",
                "repository_id": repository_id,
                "decision": "PASS",
                "commit_sha": self.git(worktree, "rev-parse", "HEAD"),
                "repository_extension_digest": state["repository_extensions"][
                    repository_id
                ]["digest"],
                "gates": [
                    {
                        "id": "idempotency-tests",
                        "status": "FAIL",
                        "required": True,
                    }
                ],
            },
        )
        with self.assertRaisesRegex(
            program.ProgramError, "required repository gate"
        ):
            self.engine.record_repository_result(
                "CHG-100", repository_id, "PASS", evidence
            )

    def test_pass_integration_evidence_rejects_non_pass_gate(self):
        state = self.prepare_all_repository_passes()
        vector = {
            repository_id: state["commit_vector"][repository_id]["head_sha"]
            for repository_id in state["validation_scope"]
        }
        integration = self.write_json(
            "concealed-integration-failure.json",
            {
                "change_id": "CHG-100",
                "decision": "PASS",
                "commit_vector": vector,
                "commit_vector_digest": state["commit_vector_digest"],
                "cross_repository_gates": [
                    {
                        "id": "reconciliation",
                        "status": "INCONCLUSIVE",
                        "commit_vector_digest": state["commit_vector_digest"],
                        "requirement_ids": ["RISK-100"],
                        "source_refs": ["approved-risk-spec"],
                        "acceptance_criteria_ids": ["RISK-100-AC-001"],
                        "evidence_types": ["integration-test"],
                        "evidence_refs": [
                            "https://github.example/evidence/reconciliation"
                        ],
                    }
                ],
            },
        )
        with self.assertRaisesRegex(
            program.ProgramError, "required cross-repository gate"
        ):
            self.engine.record_integration_result("CHG-100", integration)

    def test_blocked_spec_is_a_terminal_program_result(self):
        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        state = self.engine.prepare_workspaces(
            "CHG-100", execute=True, allow_clone=False
        )
        repository_id = "risk-api"
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        evidence = self.write_json(
            "blocked-spec.json",
            {
                "change_id": "CHG-100",
                "repository_id": repository_id,
                "decision": "BLOCKED_SPEC",
                "commit_sha": self.git(worktree, "rev-parse", "HEAD"),
                "repository_extension_digest": state["repository_extensions"][
                    repository_id
                ]["digest"],
                "gates": [],
                "reason": "Normative calculation rule is ambiguous",
            },
        )
        state = self.engine.record_repository_result(
            "CHG-100", repository_id, "BLOCKED_SPEC", evidence
        )
        self.assertEqual(state["state"], "BLOCKED_SPEC")
        self.assertEqual(self.engine.verify("CHG-100"), [])

    def test_validation_only_repository_change_requires_replanning(self):
        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        state = self.engine.prepare_workspaces(
            "CHG-100", execute=True, allow_clone=False
        )
        repository_id = "trading-ui"
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        self.git(worktree, "config", "user.email", "test@example.invalid")
        self.git(worktree, "config", "user.name", "Test User")
        (worktree / "unplanned.txt").write_text("changed\n", encoding="utf-8")
        self.git(worktree, "add", "unplanned.txt")
        self.git(worktree, "commit", "-m", "unplanned downstream change")
        packet = self.engine.refresh_repository_extensions(
            "CHG-100", repository_id
        )
        evidence = self.write_json(
            "unplanned-change.json",
            {
                "change_id": "CHG-100",
                "repository_id": repository_id,
                "decision": "PASS",
                "commit_sha": self.git(worktree, "rev-parse", "HEAD"),
                "repository_extension_digest": packet["digest"],
                "gates": [{"id": "unit-tests", "status": "PASS"}],
            },
        )
        with self.assertRaisesRegex(
            program.ProgramError, "unplanned implementation change"
        ):
            self.engine.record_repository_result(
                "CHG-100", repository_id, "PASS", evidence
            )

    def test_integration_requires_persisted_commit_vector_digest(self):
        state = self.prepare_all_repository_passes()
        evidence = json.loads(
            self.valid_integration_evidence(state).read_text(encoding="utf-8")
        )
        evidence.pop("commit_vector_digest")
        path = self.write_json("unbound-integration.json", evidence)
        with self.assertRaisesRegex(program.ProgramError, "commit-vector digest"):
            self.engine.record_integration_result("CHG-100", path)

    def test_integration_gate_requires_normative_traceability(self):
        state = self.prepare_all_repository_passes()
        evidence = json.loads(
            self.valid_integration_evidence(state).read_text(encoding="utf-8")
        )
        evidence["cross_repository_gates"][0].pop("requirement_ids")
        evidence["cross_repository_gates"][0].pop("source_refs")
        path = self.write_json("untraceable-integration.json", evidence)
        with self.assertRaisesRegex(program.ProgramError, "traceability"):
            self.engine.record_integration_result("CHG-100", path)

    def test_integration_rejects_missing_mapped_acceptance_criterion(self):
        state = self.prepare_all_repository_passes()
        integration = json.loads(
            self.valid_integration_evidence(state).read_text(encoding="utf-8")
        )
        integration["cross_repository_gates"][0][
            "acceptance_criteria_ids"
        ] = []
        with self.assertRaisesRegex(
            program.ProgramError, "acceptance criteria.*verification matrix"
        ):
            self.engine.record_integration_result(
                "CHG-100",
                self.write_json("missing-criterion-integration.json", integration),
            )

    def test_integration_rejects_missing_mapped_evidence_type(self):
        state = self.prepare_all_repository_passes()
        integration = json.loads(
            self.valid_integration_evidence(state).read_text(encoding="utf-8")
        )
        integration["cross_repository_gates"][0]["evidence_types"] = []
        with self.assertRaisesRegex(
            program.ProgramError, "evidence types.*verification matrix"
        ):
            self.engine.record_integration_result(
                "CHG-100",
                self.write_json("missing-evidence-type-integration.json", integration),
            )

    def test_plan_closure_rejects_omitted_requirement_result(self):
        state = self.prepare_all_repository_passes()
        state = self.engine.record_integration_result(
            "CHG-100", self.valid_integration_evidence(state)
        )
        closure = json.loads(
            self.valid_plan_closure_evidence(state).read_text(encoding="utf-8")
        )
        closure["requirement_results"] = []
        with self.assertRaisesRegex(program.ProgramError, "result set mismatch"):
            self.engine.close_plan(
                "CHG-100",
                self.write_json("omitted-requirement-closure.json", closure),
            )

    def test_plan_closure_requires_distinct_independent_reviewers(self):
        state = self.prepare_all_repository_passes()
        state = self.engine.record_integration_result(
            "CHG-100", self.valid_integration_evidence(state)
        )
        closure = json.loads(
            self.valid_plan_closure_evidence(state).read_text(encoding="utf-8")
        )
        closure["mandatory_reviews"][1]["actor"] = "verification-owner"
        with self.assertRaisesRegex(program.ProgramError, "distinct accountable"):
            self.engine.close_plan(
                "CHG-100",
                self.write_json("same-reviewer-closure.json", closure),
            )

    def test_verify_detects_plan_closure_tampering(self):
        state = self.prepare_all_repository_passes()
        state = self.engine.record_integration_result(
            "CHG-100", self.valid_integration_evidence(state)
        )
        self.engine.close_plan(
            "CHG-100", self.valid_plan_closure_evidence(state)
        )
        closure_path = self.engine.run_dir("CHG-100") / "plan-closure.json"
        closure = json.loads(closure_path.read_text(encoding="utf-8"))
        closure["coverage"][0]["test_ids"] = []
        closure_path.write_text(json.dumps(closure, indent=2), encoding="utf-8")
        self.assertTrue(
            any(
                "plan closure digest or binding mismatch" in error
                for error in self.engine.verify("CHG-100")
            )
        )

    def test_pr_preparation_rejects_head_changed_after_plan_closure(self):
        state = self.prepare_all_repository_passes()
        state = self.engine.record_integration_result(
            "CHG-100", self.valid_integration_evidence(state)
        )
        self.engine.close_plan(
            "CHG-100", self.valid_plan_closure_evidence(state)
        )
        worktree = Path(state["commit_vector"]["risk-api"]["worktree"])
        self.git(worktree, "config", "user.email", "test@example.invalid")
        self.git(worktree, "config", "user.name", "Test User")
        (worktree / "post-closure.txt").write_text("changed\n", encoding="utf-8")
        self.git(worktree, "add", "post-closure.txt")
        self.git(worktree, "commit", "-m", "change after closure")
        with self.assertRaisesRegex(program.ProgramError, "HEAD changed"):
            self.engine.prepare_pr_set("CHG-100", "Risk validation")

    def test_verify_detects_repository_evidence_tampering(self):
        state = self.prepare_all_repository_passes()
        stored = (
            self.engine.run_dir("CHG-100")
            / state["repository_results"]["risk-api"]["evidence_path"]
        )
        evidence = json.loads(stored.read_text(encoding="utf-8"))
        evidence["gates"][0]["status"] = "FAIL"
        stored.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        self.assertTrue(
            any(
                "risk-api: repository evidence digest mismatch" in error
                for error in self.engine.verify("CHG-100")
            )
        )

    def test_blocked_spec_requires_accountable_reason(self):
        plan = self.start_and_plan()
        self.approve_plan("CHG-100", plan)
        state = self.engine.prepare_workspaces(
            "CHG-100", execute=True, allow_clone=False
        )
        repository_id = "risk-api"
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        evidence = self.write_json(
            "blocked-spec-without-reason.json",
            {
                "change_id": "CHG-100",
                "repository_id": repository_id,
                "decision": "BLOCKED_SPEC",
                "commit_sha": self.git(worktree, "rev-parse", "HEAD"),
                "repository_extension_digest": state["repository_extensions"][
                    repository_id
                ]["digest"],
                "gates": [],
            },
        )
        with self.assertRaisesRegex(program.ProgramError, "non-empty reason"):
            self.engine.record_repository_result(
                "CHG-100", repository_id, "BLOCKED_SPEC", evidence
            )

    def test_pr_approval_rejects_case_variant_requester_identity(self):
        state = self.prepare_all_repository_passes()
        state = self.engine.record_integration_result(
            "CHG-100", self.valid_integration_evidence(state)
        )
        state = self.engine.close_plan(
            "CHG-100", self.valid_plan_closure_evidence(state)
        )
        self.engine.prepare_pr_set("CHG-100", "Risk validation")
        head = state["commit_vector"]["risk-api"]["head_sha"]
        state = self.engine.record_pull_request(
            "CHG-100",
            "risk-api",
            42,
            "https://github.example/organisation/risk-api/pull/42",
            head,
        )
        approval = self.write_json(
            "case-variant-self-approval.json",
            {
                "change_id": "CHG-100",
                "gate": "pr-approval",
                "decision": "APPROVED",
                "approver": "release-owner",
                "independent": True,
                "reviewed_digest": state["pr_set_digest"],
                "reviewed_artifact_url": "https://github.example/artifacts/pr-set",
                "source_url": "https://github.example/actions/runs/200",
                "approved_pull_requests": [
                    {
                        "repository_id": "risk-api",
                        "number": 42,
                        "head_sha": head,
                        "required_checks_passed": True,
                        "approved_by": ["Change-Requester"],
                    }
                ],
            },
        )
        with self.assertRaisesRegex(program.ProgramError, "independent approval"):
            self.engine.approve_pr_set("CHG-100", approval)

    def test_event_tampering_is_detected(self):
        self.start_and_plan()
        event_path = self.engine.run_dir("CHG-100") / "events.jsonl"
        event_path.write_text(
            event_path.read_text(encoding="utf-8").replace(
                "PLAN_PREPARED", "PLAN_FORGED"
            ),
            encoding="utf-8",
        )
        self.assertTrue(
            any("hash mismatch" in error for error in self.engine.verify("CHG-100"))
        )


if __name__ == "__main__":
    unittest.main()
