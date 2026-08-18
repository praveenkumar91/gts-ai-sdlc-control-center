#!/usr/bin/env python3
"""Run a deterministic ten-repository, Eurex-style SDLC control evaluation.

The fixture uses public exchange-interface concepts and synthetic data. It tests
the control plane; it is not a certification of Deutsche Boerse software.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import program_orchestrator
import run_integration_gates
import run_repository_gates


REPOSITORIES = [
    ("product-reference-contracts", "contracts", []),
    ("trade-entry-gateway", "cpp", ["product-reference-contracts"]),
    ("pre-trade-risk", "python", ["product-reference-contracts"]),
    (
        "matching-engine",
        "cpp",
        ["product-reference-contracts", "trade-entry-gateway", "pre-trade-risk"],
    ),
    ("trade-capture", "node", ["matching-engine"]),
    ("market-data-publisher", "node", ["matching-engine"]),
    ("clearing-adapter", "python", ["trade-capture"]),
    ("margin-risk", "python", ["clearing-adapter"]),
    (
        "member-portal-ui",
        "vite-typescript",
        ["market-data-publisher", "margin-risk"],
    ),
    (
        "reconciliation-ops",
        "python",
        ["trade-capture", "clearing-adapter", "margin-risk"],
    ),
]

PUBLIC_SOURCES = [
    {
        "title": "T7 Release 13.0 system documentation",
        "url": "https://www.eurex.com/ex-en/support/initiatives/t7-release13",
        "used_for": "ETI, EOBI, market/reference data, GUI and traceability boundaries",
    },
    {
        "title": "T7 system overview",
        "url": "https://www.eurex.com/ex-en/support/technology/t7",
        "used_for": "high-throughput trading-platform context",
    },
    {
        "title": "Eurex Clearing risk",
        "url": "https://www.eurex.com/ec-en/support/risk",
        "used_for": "clearing-risk and intraday-margin context",
    },
    {
        "title": "T7 Release 14.1 ETI manual",
        "url": "https://www.eurex.com/resource/blob/5032534/b34946612a479b4b9018590fc584a49a/data/T7_R.14.1_Enhanced_Trading_Interface_-_Manual_Version_2.pdf",
        "used_for": "session heartbeat, recovery and retransmission behavior",
    },
    {
        "title": "T7 Release 14.1 market and reference data manual",
        "url": "https://www.eurex.com/resource/blob/5055560/c138bd262600e59a7c1018112fdeb252/data/T7_R.14.1_%20EMDI_MDI_RDI_Manual_Version_2.pdf",
        "used_for": "snapshot recovery, sequence handling and RDI/RDF cutover",
    },
    {
        "title": "T7 Release 14.1 EDCI manual",
        "url": "https://www.eurex.com/resource/blob/4978238/9b1a5723d93fd8bb2a4d319eaaf1a9e6/data/T7_R.14.1_Enhanced_Drop_Copy_Interface_-_Manual_Version_1.pdf",
        "used_for": "lean-order coverage and absence of historical catch-up",
    },
    {
        "title": "T7 Release 14.1 functional reference",
        "url": "https://www.eurex.com/resource/blob/5000130/73b31cf8fa62eeb7d9f0421d5ed07ea9/data/T7_Release_14.1_-_Functional_Reference_Version_1.pdf",
        "used_for": "self-match prevention and synthetic matching constraints",
    },
    {
        "title": "T7 Release 14.1 production-start circular",
        "url": "https://www.eurex.com/ex-en/find/circulars/circular-5098798",
        "used_for": "interface migration, key rotation and reference-data restart",
    },
    {
        "title": "T7 matcher and gateway failover guidance",
        "url": "https://www.eurex.com/ex-en/find/circulars/Eurex-Readiness-Newsflash-Incident-Handling-Matching-Engine-and-Gateway-Failover-Failure--5005792",
        "used_for": "market reset and persistent versus non-persistent recovery",
    },
    {
        "title": "T7 Disaster Recovery Concept 2026",
        "url": "https://www.eurex.com/resource/blob/5112638/81542953c69a9f450c08ba44cd0b2c0a/data/T7_Disaster_Recovery_Concept_2026_v_1.1.pdf",
        "used_for": "DR endpoint changes, stream availability and isolation",
    },
    {
        "title": "T7 derivatives participant and user maintenance manual",
        "url": "https://www.eurex.com/resource/blob/5000084/9af4d0c2c09a4de82607115b1f146889/data/T7_R.14.1_Derivatives_Market_-_Participant_and_User_Maintenance_Manual_Version_1.pdf",
        "used_for": "entitlements, transaction limits and re-login semantics",
    },
]


@dataclass
class Result:
    scenario: str
    change_type: str
    repositories: str
    stages: str
    expected: str
    observed: str
    status: str
    evidence: str
    deficiency: str
    correction: str
    specification: str = ""


class Fixture:
    def __init__(self, source_root: Path):
        self.temporary = tempfile.TemporaryDirectory(prefix="eurex-sdlc-eval-")
        self.base = Path(self.temporary.name)
        self.root = self.base / "control-plane"
        self.workspace = self.base / "workspace"
        self.worktrees = self.base / "worktrees"
        self.origins = self.base / "origins"
        self.inputs = self.base / "inputs"
        for path in (
            self.root / ".github/sdlc/stack-adapters",
            self.workspace,
            self.worktrees,
            self.origins,
            self.inputs,
        ):
            path.mkdir(parents=True, exist_ok=True)
        for adapter in (source_root / ".github/sdlc/stack-adapters").glob("*.json"):
            shutil.copy2(adapter, self.root / ".github/sdlc/stack-adapters" / adapter.name)
        (self.root / "integration_check.py").write_text(
            "from __future__ import annotations\n"
            "import json, pathlib, sys\n"
            "failures = pathlib.Path('integration-failures.json')\n"
            "blocked = json.loads(failures.read_text()) if failures.exists() else []\n"
            "raise SystemExit(1 if sys.argv[1] in blocked else 0)\n",
            encoding="utf-8",
        )
        self._write_json(
            self.root / ".github/sdlc/integration-gates.json",
            {
                "schema_version": "1.0",
                "adoption_complete": True,
                "commands": [
                    {
                        "id": gate_id,
                        "enabled": True,
                        "required": True,
                        "args": [sys.executable, "integration_check.py", gate_id],
                        "timeout_seconds": 30,
                    }
                    for gate_id in (
                        "contract-compatibility",
                        "end-to-end-trade-lifecycle",
                        "reconciliation",
                    )
                ],
            },
        )
        self.repository_gate_ids: dict[str, list[str]] = {}
        entries = []
        for repository_id, stack, dependencies in REPOSITORIES:
            origin = self._create_repository(repository_id, stack)
            entries.append(
                {
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
            )
        self.manifest = {
            "schema_version": "1.0",
            "program_id": "synthetic-eurex-style-evaluation",
            "adoption_complete": True,
            "workspace_root": str(self.workspace),
            "worktree_root": str(self.worktrees),
            "runs_directory": str(self.base / "runs"),
            "branch_prefix": "evaluation/",
            "maximum_parallel_repositories": 8,
            "integration_quality_config": ".github/sdlc/integration-gates.json",
            "controls": {
                "human_plan_approval": True,
                "human_pr_approval": True,
                "human_production_approval": True,
                "allow_agent_self_approval": False,
                "maximum_remediation_cycles": 3,
            },
            "repositories": entries,
        }
        self.manifest_path = self.root / ".github/sdlc/program.json"
        self._write_json(self.manifest_path, self.manifest)
        self.engine = program_orchestrator.ProgramOrchestrator(
            self.root, self.manifest_path
        )

    def close(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _git(cwd: Path, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        if check and result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        return result.stdout.strip()

    @staticmethod
    def _write_json(path: Path, value: object) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def input_json(self, name: str, value: object) -> Path:
        return self._write_json(self.inputs / name, value)

    def ready_intake(self, change_id: str) -> None:
        evidence = self.input_json(
            f"{change_id}-intake.json",
            {
                "change_id": change_id,
                "decision": "READY",
                "assessor": "evaluation-requirements-engineer",
                "source_facts": [
                    {
                        "source_id": "official-eurex-reference",
                        "fact": "The synthetic scenario has a frozen evaluated requirement.",
                        "citation": f"evaluation scenario {change_id}",
                    }
                ],
                "open_questions": [],
                "inaccessible_sources": [],
                "unverified_assumptions": [],
                "user_answers": [],
                "evidence_refs": [
                    "https://www.eurex.com/ex-en/support/initiatives/t7release14-1"
                ],
            },
        )
        self.engine.assess_intake(change_id, evidence)

    def complete_plan_reviews(self, change_id: str, plan: dict) -> None:
        for index, review_type in enumerate(
            ("requirements", "architecture", "adversarial"), 1
        ):
            evidence = self.input_json(
                f"{change_id}-plan-review-{index}.json",
                {
                    "change_id": change_id,
                    "gate": "plan-review",
                    "decision": "PASS",
                    "reviewer": f"evaluation-reviewer-{index}",
                    "independent": True,
                    "review_type": review_type,
                    "reviewed_digest": plan["digest"],
                    "findings": [],
                    "source_url": (
                        f"https://github.example/reviews/{change_id}/{index}"
                    ),
                },
            )
            self.engine.record_plan_review(change_id, evidence)

    def _create_repository(self, repository_id: str, stack: str) -> Path:
        seed = self.base / "seeds" / repository_id
        origin = self.origins / f"{repository_id}.git"
        seed.mkdir(parents=True)
        self._git(seed, "init", "-b", "main")
        self._git(seed, "config", "user.email", "evaluation@example.invalid")
        self._git(seed, "config", "user.name", "SDLC Evaluation")
        (seed / ".github/sdlc").mkdir(parents=True)
        (seed / ".github/instructions").mkdir(parents=True)
        (seed / ".github/skills/domain-validation").mkdir(parents=True)
        (seed / ".github/agents").mkdir(parents=True)
        (seed / "README.md").write_text(
            f"# {repository_id}\n\nSynthetic evaluation fixture only.\n",
            encoding="utf-8",
        )
        (seed / "fixture_check.py").write_text(
            "from __future__ import annotations\n"
            "import json, pathlib, sys\n"
            "failures = pathlib.Path('fixture-failures.json')\n"
            "blocked = json.loads(failures.read_text()) if failures.exists() else []\n"
            "raise SystemExit(1 if sys.argv[1] in blocked else 0)\n",
            encoding="utf-8",
        )
        adapter = program_orchestrator.read_json(
            self.root / ".github/sdlc/stack-adapters" / f"{stack}.json"
        )
        self.repository_gate_ids[repository_id] = list(
            adapter["required_capabilities"]
        )
        commands = [
            {
                "id": capability,
                "enabled": True,
                "required": True,
                "args": [sys.executable, "fixture_check.py", capability],
                "timeout_seconds": 30,
            }
            for capability in adapter["required_capabilities"]
        ]
        self._write_json(
            seed / ".github/sdlc/project.json",
            {
                "schema_version": "1.0",
                "project_id": repository_id,
                "adoption_complete": True,
                "commands": commands,
            },
        )
        (seed / ".github/instructions/domain.instructions.md").write_text(
            "Preserve deterministic sequencing, decimal precision, idempotency, "
            "traceability, authorization and reconciliation invariants.\n",
            encoding="utf-8",
        )
        (seed / ".github/skills/domain-validation/SKILL.md").write_text(
            "---\n"
            "name: domain-validation\n"
            "description: Validate repository-specific financial invariants.\n"
            "---\n\n"
            "Run the configured deterministic gates and cite exact evidence.\n",
            encoding="utf-8",
        )
        (seed / ".github/agents/domain-reviewer.agent.md").write_text(
            "---\n"
            "name: Domain Reviewer\n"
            "description: Independently inspect domain behavior and evidence.\n"
            "tools:\n"
            "  - read\n"
            "---\n\n"
            "Review only. Never approve the pull request.\n",
            encoding="utf-8",
        )
        self._write_json(
            seed / ".github/sdlc/extensions.json",
            {
                "schema_version": "1.0",
                "repository_id": repository_id,
                "instructions": [
                    {
                        "id": "domain-invariants",
                        "path": ".github/instructions/domain.instructions.md",
                        "required": True,
                    }
                ],
                "skills": [
                    {
                        "id": "domain-validation",
                        "path": ".github/skills/domain-validation/SKILL.md",
                        "required": True,
                    }
                ],
                "agents": [
                    {
                        "id": "domain-reviewer",
                        "path": ".github/agents/domain-reviewer.agent.md",
                        "role": "independent-domain-review",
                        "required": True,
                    }
                ],
            },
        )
        self._git(seed, "add", ".")
        self._git(seed, "commit", "-m", "Create synthetic repository fixture")
        self._git(self.origins, "init", "--bare", str(origin))
        self._git(seed, "remote", "add", "origin", str(origin))
        self._git(seed, "push", "-u", "origin", "main")
        clone = self.workspace / repository_id
        self._git(
            self.workspace, "clone", "--branch", "main", str(origin), str(clone)
        )
        self._git(clone, "config", "user.email", "evaluation@example.invalid")
        self._git(clone, "config", "user.name", "SDLC Evaluation")
        return origin

    def bootstrap(
        self,
        change_id: str,
        seeds: list[str],
        request: str,
        integration_gate_ids: list[str] | None = None,
    ) -> dict:
        selected_integration_gates = integration_gate_ids or [
            "contract-compatibility",
            "end-to-end-trade-lifecycle",
            "reconciliation",
        ]
        self._write_json(
            self.root / ".github/sdlc/integration-gates.json",
            {
                "schema_version": "1.0",
                "adoption_complete": True,
                "commands": [
                    {
                        "id": gate_id,
                        "enabled": True,
                        "required": True,
                        "args": [sys.executable, "integration_check.py", gate_id],
                        "timeout_seconds": 30,
                    }
                    for gate_id in selected_integration_gates
                ],
            },
        )
        self.engine.start(change_id, request, "feature-requester", "critical")
        self.ready_intake(change_id)
        numeric_id = int("".join(character for character in change_id if character.isdigit()))
        source_set = [
            {
                "source_id": "official-eurex-reference",
                "version": "evaluated",
                "content_sha256": "sha256:" + ("b" * 64),
                "locator": "https://www.eurex.com/ex-en/support/initiatives/t7release14-1",
            }
        ]
        requirements = self.input_json(
            f"{change_id}-requirements.json",
            {
                "change_id": change_id,
                "source_set_digest": "sha256:" + program_orchestrator.digest(source_set),
                "source_set": source_set,
                "requirements": [
                    {
                        "id": f"EVALREQ-{numeric_id:03d}-{index:03d}",
                        "statement": (
                            f"{repository_id} implements and proves its approved "
                            f"slice of {request}."
                        ),
                        "type": "functional",
                        "criticality": "critical",
                        "sources": [
                            {
                                "source_id": "official-eurex-reference",
                                "version": "evaluated",
                                "section": change_id,
                            }
                        ],
                        "repositories": [repository_id],
                        "acceptance_criteria": [
                            {
                                "id": f"EVALREQ-{numeric_id:03d}-{index:03d}-AC-001",
                                "statement": (
                                    "The exact changed commit satisfies the approved "
                                    "behavior."
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
                                "repository": repository_id,
                                "gate_ids": self.repository_gate_ids[repository_id],
                                "acceptance_criteria_ids": [],
                                "evidence_types": ["repository-test"],
                            },
                            *[
                                {
                                    "scope": "integration",
                                    "gate_ids": [gate_id],
                                    "acceptance_criteria_ids": [
                                        f"EVALREQ-{numeric_id:03d}-{index:03d}-AC-001"
                                    ],
                                    "evidence_types": ["integration-test"],
                                }
                                for gate_id in selected_integration_gates
                            ],
                        ],
                    }
                    for index, repository_id in enumerate(sorted(seeds), 1)
                ],
            },
        )
        plan = self.engine.plan(change_id, seeds, requirements)
        self.complete_plan_reviews(change_id, plan)
        approval = self.input_json(
            f"{change_id}-plan-approval.json",
            {
                "change_id": change_id,
                "gate": "plan-approval",
                "decision": "APPROVED",
                "approver": "architecture-owner",
                "independent": True,
                "reviewed_digest": plan["digest"],
                "reviewed_artifact_url": (
                    f"https://github.example/evidence/{change_id}/plan"
                ),
                "source_url": f"https://github.example/actions/{change_id}/plan",
            },
        )
        self.engine.approve_plan(change_id, approval)
        return self.engine.prepare_workspaces(
            change_id, execute=True, allow_clone=False
        )

    def commit_change(self, change_id: str, repository_id: str, content: str) -> str:
        state = self.engine.read_state(change_id)
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        (worktree / f"{change_id}.change").write_text(content + "\n", encoding="utf-8")
        self._git(worktree, "add", f"{change_id}.change")
        self._git(worktree, "commit", "-m", f"{change_id}: synthetic evaluated change")
        self.engine.refresh_repository_extensions(change_id, repository_id)
        return self._git(worktree, "rev-parse", "HEAD")

    def repository_evidence(
        self,
        change_id: str,
        repository_id: str,
        *,
        decision: str = "PASS",
        gates: list[dict] | None = None,
        extension_digest: str | None = None,
        reason: str | None = None,
    ) -> Path:
        state = self.engine.read_state(change_id)
        worktree = Path(state["commit_vector"][repository_id]["worktree"])
        packet = state["repository_extensions"][repository_id]
        assigned_obligations = [
            obligation
            for obligation in state["requirement_obligations"]
            if repository_id in obligation["repositories"]
        ]
        planned_gate_ids = sorted(
            {
                gate_id
                for obligation in assigned_obligations
                for entry in obligation["verification"]
                if entry["scope"] == "repository"
                and entry["repository"] == repository_id
                for gate_id in entry["gate_ids"]
            }
        )
        evidence = {
            "schema_version": "1.0",
            "change_id": change_id,
            "repository_id": repository_id,
            "decision": decision,
            "commit_sha": self._git(worktree, "rev-parse", "HEAD"),
            "repository_extension_digest": extension_digest or packet["digest"],
            "gates": gates
            if gates is not None
            else [
                {"id": gate_id, "status": "PASS", "required": True}
                for gate_id in (planned_gate_ids or ["unit-tests"])
            ],
        }
        if decision == "PASS":
            evidence["requirement_coverage"] = [
                {
                    "requirement_id": obligation["id"],
                    "implementation_files": [f"{change_id}.change"],
                    "test_ids": sorted(
                        {
                            gate_id
                            for entry in obligation["verification"]
                            if entry["scope"] == "repository"
                            and entry["repository"] == repository_id
                            for gate_id in entry["gate_ids"]
                        }
                    ),
                    "acceptance_criteria_ids": sorted(
                        {
                            criterion_id
                            for entry in obligation["verification"]
                            if entry["scope"] == "repository"
                            and entry["repository"] == repository_id
                            for criterion_id in entry["acceptance_criteria_ids"]
                        }
                    ),
                    "evidence_types": sorted(
                        {
                            evidence_type
                            for entry in obligation["verification"]
                            if entry["scope"] == "repository"
                            and entry["repository"] == repository_id
                            for evidence_type in entry["evidence_types"]
                        }
                    ),
                    "evidence_refs": [
                        f"https://github.example/evidence/{change_id}/"
                        f"{repository_id}"
                    ],
                }
                for obligation in assigned_obligations
            ]
        if reason is not None:
            evidence["reason"] = reason
        return self.input_json(
            f"{change_id}-{repository_id}-{decision}.json",
            evidence,
        )

    def record_all_pass(self, change_id: str) -> dict:
        state = self.engine.read_state(change_id)
        for repository_id in state["implementation_scope"]:
            vector = state["commit_vector"][repository_id]
            current_head = self._git(Path(vector["worktree"]), "rev-parse", "HEAD")
            if current_head == vector["base_sha"]:
                self.commit_change(
                    change_id,
                    repository_id,
                    "evaluated implementation change",
                )
        state = self.engine.read_state(change_id)
        for repository_id in state["validation_scope"]:
            evidence = self.repository_evidence(change_id, repository_id)
            state = self.engine.record_repository_result(
                change_id, repository_id, "PASS", evidence
            )
        return state

    def integration(self, change_id: str, gates: list[dict] | None = None) -> dict:
        state = self.engine.read_state(change_id)
        if gates is None:
            evidence, evidence_path = run_integration_gates.generate(
                self.engine, change_id
            )
            if evidence["decision"] != "PASS":
                raise AssertionError(
                    f"integration runner returned {evidence['decision']}: "
                    f"{evidence.get('reason', '')}"
                )
            return self.engine.record_integration_result(change_id, evidence_path)
        vector = {
            repository_id: state["commit_vector"][repository_id]["head_sha"]
            for repository_id in state["validation_scope"]
        }
        configured_gates = gates
        enriched_gates = []
        for gate in configured_gates:
            enriched = dict(gate)
            mapped = [
                (obligation, entry)
                for obligation in state["requirement_obligations"]
                for entry in obligation["verification"]
                if entry["scope"] == "integration"
                and enriched["id"] in entry["gate_ids"]
            ]
            enriched.setdefault(
                "requirement_ids",
                sorted({obligation["id"] for obligation, _ in mapped}),
            )
            enriched.setdefault(
                "source_refs",
                sorted(
                    {
                        source["source_id"]
                        for obligation, _ in mapped
                        for source in obligation["sources"]
                    }
                ),
            )
            enriched.setdefault(
                "commit_vector_digest", state["commit_vector_digest"]
            )
            enriched.setdefault(
                "acceptance_criteria_ids",
                sorted(
                    {
                        criterion_id
                        for _, entry in mapped
                        for criterion_id in entry["acceptance_criteria_ids"]
                    }
                ),
            )
            enriched.setdefault(
                "evidence_types",
                sorted(
                    {
                        evidence_type
                        for _, entry in mapped
                        for evidence_type in entry["evidence_types"]
                    }
                ),
            )
            enriched.setdefault(
                "evidence_refs",
                [
                    f"https://github.example/evidence/{change_id}/"
                    f"{enriched['id']}"
                ],
            )
            enriched_gates.append(enriched)
        evidence = self.input_json(
            f"{change_id}-integration.json",
            {
                "schema_version": "1.0",
                "change_id": change_id,
                "decision": "PASS",
                "commit_vector": vector,
                "commit_vector_digest": state["commit_vector_digest"],
                "cross_repository_gates": enriched_gates,
            },
        )
        return self.engine.record_integration_result(change_id, evidence)

    def close_plan(self, change_id: str) -> dict:
        state = self.engine.read_state(change_id)
        evidence = self.input_json(
            f"{change_id}-plan-closure.json",
            {
                "change_id": change_id,
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
                                    f"https://github.example/evidence/{change_id}/"
                                    "criterion"
                                ],
                            }
                            for criterion in obligation["acceptance_criteria"]
                        ],
                        "required_evidence": [
                            {
                                "type": evidence_type,
                                "status": "PASS",
                                "evidence_refs": [
                                    f"https://github.example/evidence/{change_id}/"
                                    "type"
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
                        "source_url": (
                            f"https://github.example/reviews/{change_id}/verification"
                        ),
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
                        "source_url": (
                            f"https://github.example/reviews/{change_id}/adversarial"
                        ),
                        "reviewed_plan_digest": state["plan_digest"],
                        "reviewed_commit_vector_digest": state[
                            "commit_vector_digest"
                        ],
                    },
                ],
                "deviations": [],
            },
        )
        return self.engine.close_plan(change_id, evidence)

    def approve_prs(self, change_id: str, title: str) -> dict:
        self.close_plan(change_id)
        artifact = self.engine.prepare_pr_set(change_id, title)
        state = self.engine.read_state(change_id)
        approved = []
        for index, item in enumerate(artifact["pull_requests"], 1):
            repository_id = item["repository_id"]
            head = state["commit_vector"][repository_id]["head_sha"]
            self.engine.record_pull_request(
                change_id,
                repository_id,
                1000 + index,
                f"https://github.example/{repository_id}/pull/{1000 + index}",
                head,
            )
            approved.append(
                {
                    "repository_id": repository_id,
                    "number": 1000 + index,
                    "head_sha": head,
                    "required_checks_passed": True,
                    "approved_by": [f"{repository_id}-codeowner"],
                }
            )
        state = self.engine.read_state(change_id)
        approval = self.input_json(
            f"{change_id}-pr-approval.json",
            {
                "change_id": change_id,
                "gate": "pr-approval",
                "decision": "APPROVED",
                "approver": "release-owner",
                "independent": True,
                "reviewed_digest": state["pr_set_digest"],
                "reviewed_artifact_url": (
                    f"https://github.example/evidence/{change_id}/pr-set"
                ),
                "source_url": f"https://github.example/actions/{change_id}/pr",
                "approved_pull_requests": approved,
            },
        )
        return self.engine.approve_pr_set(change_id, approval)


SHARED_FIXTURE: Fixture | None = None


def fixture_for(source_root: Path) -> Fixture:
    return SHARED_FIXTURE if SHARED_FIXTURE is not None else Fixture(source_root)


def close_fixture(fixture: Fixture) -> None:
    if fixture is not SHARED_FIXTURE:
        fixture.close()


def result(
    scenario: str,
    change_type: str,
    repositories: str,
    stages: str,
    expected: str,
    observed: str,
    passed: bool,
    evidence: str,
    deficiency: str = "",
    correction: str = "",
    specification: str = "",
) -> Result:
    return Result(
        scenario,
        change_type,
        repositories,
        stages,
        expected,
        observed,
        "PASS" if passed else "FAIL",
        evidence,
        deficiency,
        correction,
        specification,
    )


def expect_error(action: Callable[[], object], phrase: str) -> tuple[bool, str]:
    try:
        action()
    except program_orchestrator.ProgramError as exc:
        return phrase.casefold() in str(exc).casefold(), str(exc)
    return False, "unsafe input was accepted"


def scenario_01(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-01"
        ids = [item[0] for item in REPOSITORIES]
        state = fixture.bootstrap(
            change_id,
            ids,
            "Add a client order correlation attribute across the full trade lifecycle",
        )
        for repository_id in ids:
            fixture.commit_change(change_id, repository_id, "feature: correlation-id")
        for repository_id in state["validation_scope"]:
            evidence, evidence_path = run_repository_gates.generate(
                fixture.engine, change_id, repository_id
            )
            if evidence["decision"] != "PASS":
                raise AssertionError(f"{repository_id}: {evidence['decision']}")
            fixture.engine.record_repository_result(
                change_id, repository_id, "PASS", evidence_path
            )
        fixture.integration(change_id)
        state = fixture.approve_prs(change_id, "Client order correlation")
        errors = fixture.engine.verify(change_id)
        passed = state["state"] == "PR_APPROVED" and not errors
        return result(
            "E01",
            "Full feature",
            "10/10",
            "INTAKE -> plan gate -> build/test -> integration -> plan closure -> PR gate",
            "PR_APPROVED with exact-SHA evidence for ten changed repositories",
            state["state"],
            passed,
            "10 unmodified runner-generated gate packets, integration vector, plan closure and 10-PR approval set",
        )
    finally:
        close_fixture(fixture)


def scenario_02(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-02"
        state = fixture.bootstrap(
            change_id,
            ["pre-trade-risk"],
            "Fix incorrect rejection at an inclusive member exposure limit",
        )
        fixture.commit_change(change_id, "pre-trade-risk", "bugfix: inclusive limit")
        fixture.record_all_pass(change_id)
        fixture.integration(change_id)
        state = fixture.approve_prs(change_id, "Inclusive risk limit")
        return result(
            "E02",
            "Bug fix",
            f"1 changed / {len(state['validation_scope'])} validated",
            "impact graph -> repository gates -> integration -> PR gate",
            "PR_APPROVED; downstream consumers validated",
            state["state"],
            state["state"] == "PR_APPROVED",
            "Dependency closure and single changed-repository PR",
        )
    finally:
        close_fixture(fixture)


def scenario_03(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-03"
        fixture.bootstrap(
            change_id,
            ["margin-risk"],
            "Fix decimal rounding drift in intraday margin aggregation",
        )
        failed = fixture.repository_evidence(
            change_id,
            "margin-risk",
            decision="FAIL",
            gates=[
                {
                    "id": "property-tests",
                    "status": "FAIL",
                    "required": True,
                }
            ],
        )
        state = fixture.engine.record_repository_result(
            change_id, "margin-risk", "FAIL", failed
        )
        fixture.commit_change(change_id, "margin-risk", "bugfix: decimal quantization")
        passed_evidence = fixture.repository_evidence(change_id, "margin-risk")
        state = fixture.engine.record_repository_result(
            change_id, "margin-risk", "PASS", passed_evidence
        )
        for repository_id in state["validation_scope"]:
            if repository_id != "margin-risk":
                evidence = fixture.repository_evidence(change_id, repository_id)
                state = fixture.engine.record_repository_result(
                    change_id, repository_id, "PASS", evidence
                )
        fixture.integration(change_id)
        state = fixture.approve_prs(change_id, "Margin decimal precision")
        return result(
            "E03",
            "Bug remediation loop",
            "margin-risk plus downstream UI/ops",
            "FAIL -> remediation -> PASS -> integration -> PR gate",
            "One bounded remediation cycle then PR_APPROVED",
            f"{state['state']}; cycles=1",
            state["state"] == "PR_APPROVED"
            and state["remediation_cycles"]["margin-risk"] == 1,
            "Failed property gate retained before corrected exact-SHA evidence",
        )
    finally:
        close_fixture(fixture)


def scenario_04(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-04"
        fixture.bootstrap(
            change_id,
            ["trade-capture"],
            "Fix duplicate trade capture during replay",
        )
        evidence = fixture.repository_evidence(
            change_id,
            "trade-capture",
            decision="PASS",
            gates=[
                {
                    "id": "idempotency-tests",
                    "status": "FAIL",
                    "required": True,
                }
            ],
        )
        passed, observed = expect_error(
            lambda: fixture.engine.record_repository_result(
                change_id, "trade-capture", "PASS", evidence
            ),
            "required repository gate",
        )
        return result(
            "E04",
            "Adversarial evidence",
            "trade-capture",
            "repository verification",
            "Reject PASS envelope containing a failed required gate",
            observed,
            passed,
            "Top-level PASS with required idempotency-tests=FAIL",
            "Repository PASS envelope could conceal failed gates" if not passed else "",
            "Validate repository ID and every required gate before accepting PASS",
        )
    finally:
        close_fixture(fixture)


def scenario_05(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-05"
        fixture.bootstrap(
            change_id,
            ["product-reference-contracts"],
            "Introduce a compatible trade event schema field",
            integration_gate_ids=["consumer-contracts"],
        )
        fixture.record_all_pass(change_id)
        passed, observed = expect_error(
            lambda: fixture.integration(
                change_id,
                [{"id": "consumer-contracts", "status": "FAIL"}],
            ),
            "cross-repository gate",
        )
        return result(
            "E05",
            "Breaking-contract negative control",
            "10 validation repositories",
            "cross-repository integration",
            "Reject PASS envelope containing a failed integration gate",
            observed,
            passed,
            "Exact commit vector with consumer-contracts=FAIL",
            "Integration PASS envelope could conceal a failed cross-repository gate"
            if not passed
            else "",
            "Require all cross-repository gates to report PASS",
        )
    finally:
        close_fixture(fixture)


def scenario_06(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-06"
        fixture.bootstrap(
            change_id,
            ["market-data-publisher"],
            "Repair sequence-gap recovery after packet loss and replay",
            integration_gate_ids=[
                "sequence-continuity",
                "snapshot-replay-convergence",
            ],
        )
        failure = fixture.repository_evidence(
            change_id,
            "market-data-publisher",
            decision="FAIL",
            gates=[
                {"id": "replay-tests", "status": "FAIL", "required": True}
            ],
        )
        fixture.engine.record_repository_result(
            change_id, "market-data-publisher", "FAIL", failure
        )
        fixture.commit_change(
            change_id, "market-data-publisher", "bugfix: replay sequence reset"
        )
        fixture.record_all_pass(change_id)
        fixture.integration(
            change_id,
            [
                {"id": "sequence-continuity", "status": "PASS"},
                {"id": "snapshot-replay-convergence", "status": "PASS"},
            ],
        )
        state = fixture.approve_prs(change_id, "Sequence recovery")
        return result(
            "E06",
            "Resilience bug",
            "market-data-publisher plus member-portal-ui",
            "FAIL -> remediation -> recovery integration -> PR gate",
            "Recovery and convergence evidence reaches PR_APPROVED",
            state["state"],
            state["state"] == "PR_APPROVED",
            "Sequence-continuity and snapshot-replay-convergence gates",
        )
    finally:
        close_fixture(fixture)


def scenario_07(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-07"
        fixture.bootstrap(
            change_id,
            ["trade-capture"],
            "Validate end-to-end trade/clearing reconciliation",
            integration_gate_ids=["trade-clearing-reconciliation"],
        )
        fixture.record_all_pass(change_id)
        passed, observed = expect_error(
            lambda: fixture.integration(
                change_id,
                [{"id": "trade-clearing-reconciliation", "status": "INCONCLUSIVE"}],
            ),
            "cross-repository gate",
        )
        return result(
            "E07",
            "Reconciliation negative control",
            "trade capture, clearing, margin, UI and operations",
            "cross-repository integration",
            "Reject INCONCLUSIVE reconciliation inside PASS envelope",
            observed,
            passed,
            "Exact commit vector with reconciliation=INCONCLUSIVE",
            "Integration PASS envelope could conceal an inconclusive reconciliation"
            if not passed
            else "",
            "Require all cross-repository gates to report PASS",
        )
    finally:
        close_fixture(fixture)


def scenario_08(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-08"
        fixture.bootstrap(
            change_id,
            ["member-portal-ui"],
            "Build a new margin-call screen from prose without an approved visual baseline",
        )
        evidence = fixture.repository_evidence(
            change_id,
            "member-portal-ui",
            decision="BLOCKED_SPEC",
            gates=[],
            reason="No approved normative visual design or reference baseline",
        )
        try:
            state = fixture.engine.record_repository_result(
                change_id, "member-portal-ui", "BLOCKED_SPEC", evidence
            )
            observed = state["state"]
            passed = observed == "BLOCKED_SPEC"
        except program_orchestrator.ProgramError as exc:
            observed = str(exc)
            passed = False
        return result(
            "E08",
            "GUI feature with missing design",
            "member-portal-ui",
            "requirements/GUI evidence",
            "BLOCKED_SPEC before implementation or snapshot invention",
            observed,
            passed,
            "Prose requirement; no approved design or reference image",
            "Program-level state machine did not support BLOCKED_SPEC" if not passed else "",
            "Add terminal BLOCKED_SPEC program decision/state",
        )
    finally:
        close_fixture(fixture)


def scenario_09(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-09"
        fixture.engine.start(
            change_id, "Change risk limits", "feature-requester", "critical"
        )
        fixture.ready_intake(change_id)
        source_set = [
            {
                "source_id": "approved-spec",
                "version": "1.0",
                "content_sha256": "sha256:" + ("c" * 64),
                "locator": "https://github.example/specs/risk-limits/1.0",
            }
        ]
        requirements = fixture.input_json(
            "EVAL-09-requirements.json",
            {
                "change_id": change_id,
                "source_set_digest": "sha256:" + program_orchestrator.digest(source_set),
                "source_set": source_set,
                "requirements": [
                    {
                        "id": "EVALREQ-009-001",
                        "statement": "Pre-trade risk limits follow the approved specification.",
                        "type": "functional",
                        "criticality": "critical",
                        "sources": [
                            {
                                "source_id": "approved-spec",
                                "version": "1.0",
                                "section": "risk-limits",
                            }
                        ],
                        "repositories": ["pre-trade-risk"],
                        "acceptance_criteria": [
                            {
                                "id": "EVALREQ-009-001-AC-001",
                                "statement": "Configured limits are enforced.",
                            }
                        ],
                        "required_evidence": ["repository-test"],
                        "verification": [
                            {
                                "scope": "repository",
                                "repository": "pre-trade-risk",
                                "gate_ids": fixture.repository_gate_ids[
                                    "pre-trade-risk"
                                ],
                                "acceptance_criteria_ids": [
                                    "EVALREQ-009-001-AC-001"
                                ],
                                "evidence_types": ["repository-test"],
                            },
                            {
                                "scope": "integration",
                                "gate_ids": ["contract-compatibility"],
                                "acceptance_criteria_ids": [],
                                "evidence_types": [],
                            },
                        ],
                    }
                ],
            },
        )
        plan = fixture.engine.plan(
            change_id, ["pre-trade-risk"], requirements
        )
        fixture.complete_plan_reviews(change_id, plan)
        approval = fixture.input_json(
            "EVAL-09-approval.json",
            {
                "change_id": change_id,
                "gate": "plan-approval",
                "decision": "APPROVED",
                "approver": "architecture-owner",
                "independent": True,
                "reviewed_digest": plan["digest"],
                "reviewed_artifact_url": "https://github.example/evidence/EVAL-09/plan",
                "source_url": "https://github.example/actions/EVAL-09",
            },
        )
        fixture.engine.approve_plan(change_id, approval)
        dirty = fixture.workspace / "pre-trade-risk" / "untracked.txt"
        dirty.write_text("dirty\n", encoding="utf-8")
        passed, observed = expect_error(
            lambda: fixture.engine.prepare_workspaces(
                change_id, execute=True, allow_clone=False
            ),
            "dirty",
        )
        dirty.unlink()
        return result(
            "E09",
            "Workspace safety",
            "pre-trade-risk checkout",
            "workspace preparation",
            "Dirty checkout blocks before execution",
            observed,
            passed,
            "Untracked file in managed clone",
        )
    finally:
        close_fixture(fixture)


def scenario_10(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-10"
        checkout = fixture.workspace / "trade-entry-gateway"
        expected_remote = next(
            item["url"]
            for item in fixture.manifest["repositories"]
            if item["id"] == "trade-entry-gateway"
        )
        fixture._git(checkout, "remote", "set-url", "origin", str(fixture.origins / "wrong.git"))
        fixture.engine.start(
            change_id, "Fix session recovery", "feature-requester", "critical"
        )
        fixture.ready_intake(change_id)
        source_set = [
            {
                "source_id": "approved-spec",
                "version": "1.0",
                "content_sha256": "sha256:" + ("d" * 64),
                "locator": "https://github.example/specs/session-recovery/1.0",
            }
        ]
        requirements = fixture.input_json(
            "EVAL-10-requirements.json",
            {
                "change_id": change_id,
                "source_set_digest": "sha256:" + program_orchestrator.digest(source_set),
                "source_set": source_set,
                "requirements": [
                    {
                        "id": "EVALREQ-010-001",
                        "statement": "The session gateway recovers according to the approved specification.",
                        "type": "functional",
                        "criticality": "critical",
                        "sources": [
                            {
                                "source_id": "approved-spec",
                                "version": "1.0",
                                "section": "session-recovery",
                            }
                        ],
                        "repositories": ["trade-entry-gateway"],
                        "acceptance_criteria": [
                            {
                                "id": "EVALREQ-010-001-AC-001",
                                "statement": "Session recovery is deterministic.",
                            }
                        ],
                        "required_evidence": ["repository-test"],
                        "verification": [
                            {
                                "scope": "repository",
                                "repository": "trade-entry-gateway",
                                "gate_ids": fixture.repository_gate_ids[
                                    "trade-entry-gateway"
                                ],
                                "acceptance_criteria_ids": [
                                    "EVALREQ-010-001-AC-001"
                                ],
                                "evidence_types": ["repository-test"],
                            },
                            {
                                "scope": "integration",
                                "gate_ids": ["contract-compatibility"],
                                "acceptance_criteria_ids": [],
                                "evidence_types": [],
                            },
                        ],
                    }
                ],
            },
        )
        plan = fixture.engine.plan(
            change_id, ["trade-entry-gateway"], requirements
        )
        fixture.complete_plan_reviews(change_id, plan)
        approval = fixture.input_json(
            "EVAL-10-approval.json",
            {
                "change_id": change_id,
                "gate": "plan-approval",
                "decision": "APPROVED",
                "approver": "architecture-owner",
                "independent": True,
                "reviewed_digest": plan["digest"],
                "reviewed_artifact_url": "https://github.example/evidence/EVAL-10/plan",
                "source_url": "https://github.example/actions/EVAL-10",
            },
        )
        fixture.engine.approve_plan(change_id, approval)
        passed, observed = expect_error(
            lambda: fixture.engine.prepare_workspaces(
                change_id, execute=True, allow_clone=False
            ),
            "remote",
        )
        fixture._git(checkout, "remote", "set-url", "origin", expected_remote)
        return result(
            "E10",
            "Supply-chain/workspace safety",
            "trade-entry-gateway checkout",
            "workspace preparation",
            "Wrong Git remote blocks checkout use",
            observed,
            passed,
            "Origin URL differs from program manifest",
        )
    finally:
        close_fixture(fixture)


def scenario_11(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-11"
        manifest = json.loads(json.dumps(fixture.manifest))
        for item in manifest["repositories"]:
            if item["id"] == "clearing-adapter":
                item["extensions_required"] = True
                item["extensions_config"] = ".github/sdlc/required-but-missing.json"
        fixture._write_json(fixture.manifest_path, manifest)
        fixture.engine = program_orchestrator.ProgramOrchestrator(
            fixture.root, fixture.manifest_path
        )
        try:
            fixture.bootstrap(
                change_id,
                ["clearing-adapter"],
                "Change clearing allocation behavior",
            )
            observed = "required extension was ignored"
            passed = False
        except program_orchestrator.ProgramError as exc:
            observed = str(exc)
            passed = "required extension manifest is missing" in observed
        fixture._write_json(fixture.manifest_path, fixture.manifest)
        fixture.engine = program_orchestrator.ProgramOrchestrator(
            fixture.root, fixture.manifest_path
        )
        return result(
            "E11",
            "Repository governance",
            "clearing-adapter",
            "extension resolution",
            "Missing required local policy blocks execution",
            observed,
            passed,
            "extensions_required=true with absent manifest",
        )
    finally:
        close_fixture(fixture)


def scenario_12(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-12"
        checkout = fixture.workspace / "matching-engine"
        extension_path = checkout / ".github/sdlc/extensions.json"
        original_extension = json.loads(extension_path.read_text(encoding="utf-8"))
        extension = json.loads(json.dumps(original_extension))
        extension["skills"][0]["path"] = "../outside/SKILL.md"
        fixture._write_json(extension_path, extension)
        fixture._git(checkout, "add", ".github/sdlc/extensions.json")
        fixture._git(checkout, "commit", "-m", "Inject traversal for negative test")
        fixture._git(checkout, "push", "origin", "main")
        try:
            fixture.bootstrap(
                change_id,
                ["matching-engine"],
                "Change matching priority",
            )
            observed = "path traversal was accepted"
            passed = False
        except program_orchestrator.ProgramError as exc:
            observed = str(exc)
            passed = "safe relative path" in observed or "escapes" in observed
        fixture._write_json(extension_path, original_extension)
        fixture._git(checkout, "add", ".github/sdlc/extensions.json")
        fixture._git(checkout, "commit", "-m", "Restore valid extension after negative test")
        fixture._git(checkout, "push", "origin", "main")
        return result(
            "E12",
            "Extension supply-chain safety",
            "matching-engine",
            "extension resolution",
            "Path traversal is rejected",
            observed,
            passed,
            "Local skill path ../outside/SKILL.md",
        )
    finally:
        close_fixture(fixture)


def scenario_13(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-13"
        state = fixture.bootstrap(
            change_id,
            ["pre-trade-risk"],
            "Change risk validation",
        )
        evidence = fixture.repository_evidence(
            change_id,
            "pre-trade-risk",
            extension_digest="0" * 64,
        )
        passed, observed = expect_error(
            lambda: fixture.engine.record_repository_result(
                change_id, "pre-trade-risk", "PASS", evidence
            ),
            "selected extension packet",
        )
        return result(
            "E13",
            "Evidence freshness",
            "pre-trade-risk",
            "repository evidence ingestion",
            "Stale/wrong extension digest rejected",
            observed,
            passed,
            f"Expected digest {state['repository_extensions']['pre-trade-risk']['digest'][:12]}...",
        )
    finally:
        close_fixture(fixture)


def scenario_14(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-14"
        state = fixture.bootstrap(
            change_id,
            ["trade-entry-gateway"],
            "Change gateway validation only",
        )
        downstream = "matching-engine"
        fixture.commit_change(change_id, downstream, "unplanned code modification")
        evidence = fixture.repository_evidence(change_id, downstream)
        passed, observed = expect_error(
            lambda: fixture.engine.record_repository_result(
                change_id, downstream, "PASS", evidence
            ),
            "unplanned implementation change",
        )
        return result(
            "E14",
            "Scope-integrity negative control",
            f"{downstream} (validation-only)",
            "repository evidence -> PR planning",
            "Reject changed validation-only repo; require replanning and new human approval",
            observed,
            passed,
            (
                f"base={state['commit_vector'][downstream]['base_sha'][:12]}..., "
                "HEAD changed"
            ),
            "Changed validation-only repository could be omitted from the PR set"
            if not passed
            else "",
            "Reject unplanned implementation changes before accepting evidence",
        )
    finally:
        close_fixture(fixture)


def scenario_15(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-15"
        fixture.bootstrap(
            change_id,
            ["reconciliation-ops"],
            "Fix end-of-day reconciliation diagnostics",
        )
        fixture.commit_change(change_id, "reconciliation-ops", "bugfix: diagnostic")
        fixture.record_all_pass(change_id)
        fixture.integration(change_id)
        fixture.close_plan(change_id)
        artifact = fixture.engine.prepare_pr_set(change_id, "Reconciliation diagnostic")
        state = fixture.engine.read_state(change_id)
        head = state["commit_vector"]["reconciliation-ops"]["head_sha"]
        stale = "0" * 40
        stale_ok, stale_observed = expect_error(
            lambda: fixture.engine.record_pull_request(
                change_id,
                "reconciliation-ops",
                1500,
                "https://github.example/reconciliation-ops/pull/1500",
                stale,
            ),
            "head SHA",
        )
        fixture.engine.record_pull_request(
            change_id,
            "reconciliation-ops",
            1500,
            "https://github.example/reconciliation-ops/pull/1500",
            head,
        )
        state = fixture.engine.read_state(change_id)
        approval = fixture.input_json(
            "EVAL-15-self-approval.json",
            {
                "change_id": change_id,
                "gate": "pr-approval",
                "decision": "APPROVED",
                "approver": "feature-requester",
                "independent": True,
                "reviewed_digest": state["pr_set_digest"],
                "reviewed_artifact_url": "https://github.example/evidence/EVAL-15/pr-set",
                "source_url": "https://github.example/actions/EVAL-15",
                "approved_pull_requests": [
                    {
                        "repository_id": "reconciliation-ops",
                        "number": 1500,
                        "head_sha": head,
                        "required_checks_passed": True,
                        "approved_by": ["feature-requester"],
                    }
                ],
            },
        )
        approval_ok, approval_observed = expect_error(
            lambda: fixture.engine.approve_pr_set(change_id, approval),
            "independent",
        )
        passed = stale_ok and approval_ok and len(artifact["pull_requests"]) == 1
        return result(
            "E15",
            "PR integrity",
            "reconciliation-ops",
            "PR set -> human gate 2",
            "Reject stale PR head and requester self-approval",
            f"stale: {stale_observed}; approval: {approval_observed}",
            passed,
            "Exact tested head and independent approval policy",
        )
    finally:
        close_fixture(fixture)


def scenario_16(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-16"
        fixture.bootstrap(
            change_id,
            ["trade-entry-gateway"],
            "Recover ETI session liveness after missed heartbeats and reconnect safely",
            integration_gate_ids=[
                "eti-heartbeat-liveness",
                "reconnect-before-retransmission",
            ],
        )
        failure = fixture.repository_evidence(
            change_id,
            "trade-entry-gateway",
            decision="FAIL",
            gates=[
                {
                    "id": "eti-heartbeat-timeout",
                    "status": "FAIL",
                    "required": True,
                }
            ],
            reason="Client did not disconnect and recover after the heartbeat deadline",
        )
        fixture.engine.record_repository_result(
            change_id, "trade-entry-gateway", "FAIL", failure
        )
        fixture.commit_change(
            change_id,
            "trade-entry-gateway",
            "bugfix: heartbeat watchdog and reconnect state machine",
        )
        fixture.record_all_pass(change_id)
        fixture.integration(
            change_id,
            [
                {"id": "eti-heartbeat-liveness", "status": "PASS"},
                {"id": "reconnect-before-retransmission", "status": "PASS"},
            ],
        )
        state = fixture.approve_prs(change_id, "ETI heartbeat recovery")
        return result(
            "E16",
            "ETI session resilience",
            "trade-entry gateway and downstream lifecycle",
            "FAIL -> remediation -> reconnect/retransmission -> PR gate",
            "Missed-heartbeat recovery reaches PR_APPROVED",
            state["state"],
            state["state"] == "PR_APPROVED",
            "Heartbeat watchdog, disconnect, reconnect and recovery gates",
            specification=(
                "[ETI 14.1 sections 6.4 and 6.10]"
                "(https://www.eurex.com/resource/blob/5032534/"
                "b34946612a479b4b9018590fc584a49a/data/"
                "T7_R.14.1_Enhanced_Trading_Interface_-_Manual_Version_2.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_17(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-17"
        state = fixture.bootstrap(
            change_id,
            ["trade-entry-gateway"],
            "Handle partial ETI retransmission ranges per partition and broadcast type",
        )
        state = fixture.record_all_pass(change_id)
        vector = {
            repository_id: state["commit_vector"][repository_id]["head_sha"]
            for repository_id in state["validation_scope"]
        }
        evidence = fixture.input_json(
            "EVAL-17-unbound-integration.json",
            {
                "change_id": change_id,
                "decision": "PASS",
                "commit_vector": vector,
                "cross_repository_gates": [
                    {
                        "id": "partial-retransmission-range",
                        "status": "PASS",
                        "requirement_ids": ["ETI-6.10-RANGE"],
                        "source_refs": [
                            "T7_R14.1_ETI_Manual_6.10"
                        ],
                    }
                ],
            },
        )
        passed, observed = expect_error(
            lambda: fixture.engine.record_integration_result(change_id, evidence),
            "commit-vector digest",
        )
        return result(
            "E17",
            "Adversarial integration evidence",
            "ETI gateway plus downstream consumers",
            "cross-repository evidence ingestion",
            "Reject integration evidence not bound to the persisted commit-vector digest",
            observed,
            passed,
            "Exact SHAs were present but the immutable vector artifact digest was omitted",
            "Integration evidence was not bound to the persisted commit-vector artifact"
            if not passed
            else "",
            "Require the exact commit_vector_digest in integration evidence and gates",
            (
                "[ETI retransmission ranges]"
                "(https://www.eurex.com/resource/blob/5032534/"
                "b34946612a479b4b9018590fc584a49a/data/"
                "T7_R.14.1_Enhanced_Trading_Interface_-_Manual_Version_2.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_18(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-18"
        fixture.bootstrap(
            change_id,
            ["market-data-publisher"],
            "Rebuild a consistent book after an MDI sequence gap and snapshot",
            integration_gate_ids=[
                "snapshot-cycle-completeness",
                "sender-change-restart",
                "stale-incremental-discard",
            ],
        )
        failure = fixture.repository_evidence(
            change_id,
            "market-data-publisher",
            decision="FAIL",
            gates=[
                {
                    "id": "discard-covered-incrementals",
                    "status": "FAIL",
                    "required": True,
                }
            ],
            reason="Incremental sequence 8 was applied after snapshot sequence 9",
        )
        fixture.engine.record_repository_result(
            change_id, "market-data-publisher", "FAIL", failure
        )
        fixture.commit_change(
            change_id,
            "market-data-publisher",
            "bugfix: snapshot watermark and stale incremental discard",
        )
        fixture.record_all_pass(change_id)
        fixture.integration(
            change_id,
            [
                {"id": "snapshot-cycle-completeness", "status": "PASS"},
                {"id": "sender-change-restart", "status": "PASS"},
                {"id": "stale-incremental-discard", "status": "PASS"},
            ],
        )
        state = fixture.approve_prs(change_id, "MDI snapshot recovery")
        return result(
            "E18",
            "Market-data recovery",
            "market-data publisher and member UI",
            "sequence gap -> snapshot recovery -> integration -> PR gate",
            "Recovered order book converges and reaches PR_APPROVED",
            state["state"],
            state["state"] == "PR_APPROVED",
            "Snapshot completeness, sender change and stale-message gates",
            specification=(
                "[Market and Reference Data Manual section 7.4.2]"
                "(https://www.eurex.com/resource/blob/5055560/"
                "c138bd262600e59a7c1018112fdeb252/data/"
                "T7_R.14.1_%20EMDI_MDI_RDI_Manual_Version_2.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_19(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-19"
        fixture.bootstrap(
            change_id,
            ["product-reference-contracts"],
            "Apply start-of-day and intraday reference data before market data",
        )
        state = fixture.record_all_pass(change_id)
        repository_id = "product-reference-contracts"
        evidence_path = (
            fixture.engine.run_dir(change_id)
            / "repository-evidence"
            / repository_id
            / "attempt-1.json"
        )
        accepted = json.loads(evidence_path.read_text(encoding="utf-8"))
        accepted["gates"][0]["status"] = "FAIL"
        accepted["tampered_after_acceptance"] = True
        fixture._write_json(evidence_path, accepted)
        errors = fixture.engine.verify(change_id)
        passed = any(
            "repository evidence digest mismatch" in item for item in errors
        )
        observed = "; ".join(errors) if errors else "tampering was not detected"
        return result(
            "E19",
            "Post-acceptance evidence tampering",
            "reference contracts within the 10-repository vector",
            "durable-run verification",
            "Verify detects changed repository evidence after it was accepted",
            observed,
            passed,
            "Accepted gate result was changed from PASS to FAIL on disk",
            "Run verification did not re-hash repository evidence" if not passed else "",
            "Persist evidence paths and verify every stored evidence digest",
            (
                "[Reference-data start-up and intraday files]"
                "(https://www.eurex.com/resource/blob/5055560/"
                "c138bd262600e59a7c1018112fdeb252/data/"
                "T7_R.14.1_%20EMDI_MDI_RDI_Manual_Version_2.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_20(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-20"
        state = fixture.bootstrap(
            change_id,
            ["product-reference-contracts", "trade-entry-gateway"],
            "Migrate mandatory ETI order layouts and non-backward-compatible market data",
            integration_gate_ids=["release-14.1-interface-migration"],
        )
        state = fixture.record_all_pass(change_id)
        vector = {
            repository_id: state["commit_vector"][repository_id]["head_sha"]
            for repository_id in state["validation_scope"]
        }
        evidence = fixture.input_json(
            "EVAL-20-untraceable-integration.json",
            {
                "change_id": change_id,
                "decision": "PASS",
                "commit_vector": vector,
                "commit_vector_digest": state["commit_vector_digest"],
                "cross_repository_gates": [
                    {
                        "id": "release-14.1-interface-migration",
                        "status": "PASS",
                        "commit_vector_digest": state["commit_vector_digest"],
                    }
                ],
            },
        )
        passed, observed = expect_error(
            lambda: fixture.engine.record_integration_result(change_id, evidence),
            "traceability",
        )
        return result(
            "E20",
            "Release migration traceability",
            "contracts, ETI gateway and all market-data consumers",
            "cross-repository evidence ingestion",
            "Reject a migration PASS gate without requirement IDs and source references",
            observed,
            passed,
            "Gate had exact commit-vector binding but no normative source linkage",
            "Integration PASS gates could be untraceable to authoritative specifications"
            if not passed
            else "",
            "Require requirement_ids and source_refs on every integration gate",
            (
                "[T7 14.1 production-start requirements]"
                "(https://www.eurex.com/ex-en/find/circulars/circular-5098798)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_21(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-21"
        fixture.bootstrap(
            change_id,
            ["trade-capture", "reconciliation-ops"],
            "Use EDCI for a complete lean-order inventory including pre-connect history",
        )
        evidence = fixture.repository_evidence(
            change_id,
            "trade-capture",
            decision="BLOCKED_SPEC",
            gates=[],
        )
        passed, observed = expect_error(
            lambda: fixture.engine.record_repository_result(
                change_id, "trade-capture", "BLOCKED_SPEC", evidence
            ),
            "reason",
        )
        return result(
            "E21",
            "Unresolved EDCI completeness requirement",
            "trade capture and reconciliation operations",
            "repository decision ingestion",
            "Reject BLOCKED_SPEC evidence that does not explain the normative blocker",
            observed,
            passed,
            "EDCI includes lean orders but provides no history from before connection",
            "BLOCKED_SPEC could be recorded without an accountable reason"
            if not passed
            else "",
            "Require a non-empty reason for BLOCKED_SPEC",
            (
                "[EDCI 14.1 purpose and history boundary]"
                "(https://www.eurex.com/resource/blob/4978238/"
                "9b1a5723d93fd8bb2a4d319eaaf1a9e6/data/"
                "T7_R.14.1_Enhanced_Drop_Copy_Interface_-_Manual_Version_1.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_22(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-22"
        fixture.bootstrap(
            change_id,
            ["matching-engine", "pre-trade-risk"],
            "Implement Eurex SMP type A without masking synthetic cross-instrument matches",
            integration_gate_ids=[
                "same-business-unit-smp",
                "auction-smp-boundary",
                "synthetic-cross-instrument-path",
            ],
        )
        fixture.commit_change(
            change_id,
            "matching-engine",
            "feature: same-instrument SMP and synthetic-path exception",
        )
        fixture.commit_change(
            change_id,
            "pre-trade-risk",
            "feature: SMP-aware exposure and audit events",
        )
        fixture.record_all_pass(change_id)
        fixture.integration(
            change_id,
            [
                {"id": "same-business-unit-smp", "status": "PASS"},
                {"id": "auction-smp-boundary", "status": "PASS"},
                {"id": "synthetic-cross-instrument-path", "status": "PASS"},
            ],
        )
        state = fixture.approve_prs(change_id, "SMP behavior")
        return result(
            "E22",
            "Matching/risk feature",
            "matching engine, pre-trade risk and downstream lifecycle",
            "implementation -> business invariants -> integration -> PR gate",
            "SMP boundary and synthetic exception reach PR_APPROVED",
            state["state"],
            state["state"] == "PR_APPROVED",
            "Same-owner, auction and synthetic cross-instrument behavior",
            specification=(
                "[Functional Reference section 7.6]"
                "(https://www.eurex.com/resource/blob/5000130/"
                "73b31cf8fa62eeb7d9f0421d5ed07ea9/data/"
                "T7_Release_14.1_-_Functional_Reference_Version_1.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_23(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-23"
        fixture.bootstrap(
            change_id,
            ["trade-entry-gateway", "matching-engine"],
            "Recover correctly after combined partition gateway and matcher failover",
            integration_gate_ids=[
                "market-reset-observed",
                "persistent-orders-restored",
                "non-persistent-orders-purged",
                "primary-then-backup-reconnect",
            ],
        )
        failure = fixture.repository_evidence(
            change_id,
            "matching-engine",
            decision="FAIL",
            gates=[
                {
                    "id": "non-persistent-order-purge",
                    "status": "FAIL",
                    "required": True,
                }
            ],
            reason="Non-persistent orders survived the simulated Market Reset",
        )
        fixture.engine.record_repository_result(
            change_id, "matching-engine", "FAIL", failure
        )
        fixture.commit_change(
            change_id,
            "matching-engine",
            "bugfix: restore persistent state and purge transient state",
        )
        fixture.commit_change(
            change_id,
            "trade-entry-gateway",
            "bugfix: reconnect primary then backup and wait for service status",
        )
        fixture.record_all_pass(change_id)
        fixture.integration(
            change_id,
            [
                {"id": "market-reset-observed", "status": "PASS"},
                {"id": "persistent-orders-restored", "status": "PASS"},
                {"id": "non-persistent-orders-purged", "status": "PASS"},
                {"id": "primary-then-backup-reconnect", "status": "PASS"},
            ],
        )
        state = fixture.approve_prs(change_id, "Matcher failover recovery")
        return result(
            "E23",
            "Matcher/gateway failover",
            "gateway, matcher and all downstream trade consumers",
            "failure -> bounded remediation -> recovery integration -> PR gate",
            "Market Reset semantics reach PR_APPROVED",
            state["state"],
            state["state"] == "PR_APPROVED",
            "Persistent restore, transient purge and ordered reconnect gates",
            specification=(
                "[Eurex matcher/gateway failover guidance]"
                "(https://www.eurex.com/ex-en/find/circulars/"
                "Eurex-Readiness-Newsflash-Incident-Handling-"
                "Matching-Engine-and-Gateway-Failover-Failure--5005792)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_24(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-24"
        fixture.bootstrap(
            change_id,
            [
                "trade-entry-gateway",
                "market-data-publisher",
                "reconciliation-ops",
            ],
            "Exercise T7 disaster recovery without leaking test data to production",
            integration_gate_ids=[
                "dr-endpoint-switch",
                "eobi-single-stream-mode",
                "test-data-production-fence",
                "production-reconnect",
            ],
        )
        fixture.commit_change(
            change_id,
            "reconciliation-ops",
            "feature: DR environment fencing and production reconnect",
        )
        fixture.record_all_pass(change_id)
        fixture.integration(
            change_id,
            [
                {"id": "dr-endpoint-switch", "status": "PASS"},
                {"id": "eobi-single-stream-mode", "status": "PASS"},
                {"id": "test-data-production-fence", "status": "PASS"},
                {"id": "production-reconnect", "status": "PASS"},
            ],
        )
        state = fixture.approve_prs(change_id, "T7 DR isolation")
        return result(
            "E24",
            "Disaster recovery",
            "gateway, market data, operations and affected consumers",
            "DR topology -> isolation -> reconnect -> PR gate",
            "DR single-stream and environment-fencing flow reaches PR_APPROVED",
            state["state"],
            state["state"] == "PR_APPROVED",
            "DR endpoints, absent EOBI Stream B, data fence and reconnect gates",
            specification=(
                "[T7 Disaster Recovery Concept 2026]"
                "(https://www.eurex.com/resource/blob/5112638/"
                "81542953c69a9f450c08ba44cd0b2c0a/data/"
                "T7_Disaster_Recovery_Concept_2026_v_1.1.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


def scenario_25(source_root: Path) -> Result:
    fixture = fixture_for(source_root)
    try:
        change_id = "EVAL-25"
        fixture.bootstrap(
            change_id,
            ["member-portal-ui"],
            "Apply immediate entitlement and transaction-limit changes after re-login",
            integration_gate_ids=[
                "entitlement-change-immediate",
                "forced-relogin",
                "transaction-size-limit",
            ],
        )
        fixture.commit_change(
            change_id,
            "member-portal-ui",
            "feature: entitlement refresh and forced re-login",
        )
        fixture.record_all_pass(change_id)
        fixture.integration(
            change_id,
            [
                {"id": "entitlement-change-immediate", "status": "PASS"},
                {"id": "forced-relogin", "status": "PASS"},
                {"id": "transaction-size-limit", "status": "PASS"},
            ],
        )
        fixture.close_plan(change_id)
        artifact = fixture.engine.prepare_pr_set(change_id, "Entitlement refresh")
        state = fixture.engine.read_state(change_id)
        head = state["commit_vector"]["member-portal-ui"]["head_sha"]
        fixture.engine.record_pull_request(
            change_id,
            "member-portal-ui",
            2500,
            "https://github.example/member-portal-ui/pull/2500",
            head,
        )
        state = fixture.engine.read_state(change_id)
        approval = fixture.input_json(
            "EVAL-25-case-variant-self-approval.json",
            {
                "change_id": change_id,
                "gate": "pr-approval",
                "decision": "APPROVED",
                "approver": "release-owner",
                "independent": True,
                "reviewed_digest": state["pr_set_digest"],
                "reviewed_artifact_url": (
                    "https://github.example/evidence/EVAL-25/pr-set"
                ),
                "source_url": "https://github.example/actions/EVAL-25",
                "approved_pull_requests": [
                    {
                        "repository_id": "member-portal-ui",
                        "number": 2500,
                        "head_sha": head,
                        "required_checks_passed": True,
                        "approved_by": ["Feature-Requester"],
                    }
                ],
            },
        )
        passed, observed = expect_error(
            lambda: fixture.engine.approve_pr_set(change_id, approval),
            "independent approval",
        )
        return result(
            "E25",
            "Case-variant self-approval",
            "member portal UI",
            "Human Gate 2",
            "Reject requester identity even when reviewer casing differs",
            observed,
            passed and len(artifact["pull_requests"]) == 1,
            "requested_by=feature-requester; approved_by=Feature-Requester",
            "PR reviewer separation-of-duties comparison was case-sensitive"
            if not passed
            else "",
            "Compare requester and every reviewer using casefolded identities",
            (
                "[T7 participant and user maintenance]"
                "(https://www.eurex.com/resource/blob/5000084/"
                "9af4d0c2c09a4de82607115b1f146889/data/"
                "T7_R.14.1_Derivatives_Market_-_Participant_and_"
                "User_Maintenance_Manual_Version_1.pdf)"
            ),
        )
    finally:
        close_fixture(fixture)


SCENARIOS = [
    scenario_01,
    scenario_02,
    scenario_03,
    scenario_04,
    scenario_05,
    scenario_06,
    scenario_07,
    scenario_08,
    scenario_09,
    scenario_10,
    scenario_11,
    scenario_12,
    scenario_13,
    scenario_14,
    scenario_15,
    scenario_16,
    scenario_17,
    scenario_18,
    scenario_19,
    scenario_20,
    scenario_21,
    scenario_22,
    scenario_23,
    scenario_24,
    scenario_25,
]


def load_baselines(paths: list[Path | None]) -> dict | None:
    results: list[dict] = []
    for path in paths:
        if path and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            results.extend(payload.get("results", []))
    return {"results": results} if results else None


def render_report(payload: dict, baseline: dict | None) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    rows = payload["results"]
    baseline_by_id = {
        item["scenario"]: item for item in (baseline or {}).get("results", [])
    }
    lines = [
        "# 25-scenario, ten-repository Eurex-style SDLC evaluation",
        "",
        f"- Evaluation time: `{payload['generated_at']}`",
        f"- Starting Git revision: `{payload['control_plane_revision']}`",
        f"- Evaluated program orchestrator SHA-256: `{payload['evaluated_control_sha256']}`",
        f"- Scenarios: `{payload['summary']['total']}`",
        f"- Final pass: `{payload['summary']['passed']}`",
        f"- Final fail: `{payload['summary']['failed']}`",
        "- Fixture: deterministic local Git origins/worktrees and synthetic test data",
        "- Scope: control-plane behavior, not certification of Deutsche Boerse or Eurex production software",
        "",
        "## Repository model",
        "",
        "| Repository | Stack | Depends on |",
        "|---|---|---|",
    ]
    for repository_id, stack, dependencies in REPOSITORIES:
        lines.append(
            f"| `{repository_id}` | `{stack}` | "
            + (", ".join(f"`{item}`" for item in dependencies) or "none")
            + " |"
        )
    lines.extend(
        [
            "",
            "## Scenario results",
            "",
            "| ID | Change / control | Repository scope | Stage(s) | Expected | Official basis | Baseline | Final | Evidence / observed result |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in rows:
        baseline_status = baseline_by_id.get(item["scenario"], {}).get(
            "status", "not captured"
        )
        observed = item["evidence"] if item["status"] == "PASS" else item["observed"]
        lines.append(
            "| {scenario} | {change_type} | {repositories} | {stages} | {expected} | "
            "{official_basis} | {baseline} | **{status}** | {display_result} |".format(
                baseline=baseline_status,
                display_result=cell(observed),
                official_basis=cell(
                    item.get("specification") or "Existing control-plane assurance"
                ),
                **item,
            )
        )
    deficiencies = [
        item
        for item in rows
        if item.get("deficiency") or baseline_by_id.get(item["scenario"], {}).get("status") == "FAIL"
    ]
    lines.extend(
        [
            "",
            "## Confirmed deficiencies and corrections",
            "",
            "| Scenario | Baseline deficiency | Correction | Final result |",
            "|---|---|---|---|",
        ]
    )
    for item in deficiencies:
        baseline_item = baseline_by_id.get(item["scenario"], {})
        deficiency = (
            baseline_item.get("deficiency")
            or item.get("deficiency")
            or baseline_item.get("observed", "Baseline expectation failed")
        )
        lines.append(
            f"| {item['scenario']} | {cell(deficiency)} | "
            f"{cell(item.get('correction') or 'Regression retained; no core change required')} | "
            f"{item['status']} |"
        )
    lines.extend(
        [
            "",
            "## Stage assurance",
            "",
            "| Stage | What this evaluation demonstrated | Remaining production requirement |",
            "|---|---|---|",
            "| Intake and impact | Dependency closure and execution waves across ten repositories | Curated, complete real repository graph and authoritative DFS/FSD links |",
            "| Human Gate 1 | Digest-bound independent plan approval is mandatory | Real GitHub environment reviewers and accountable architecture/risk owners |",
            "| Workspace | Clean checkout, expected remote, isolated branch/worktree and extension integrity | Enterprise credentials, network controls and repository onboarding |",
            "| Repository verification | The frozen per-change matrix selects reusable gate IDs; unmodified runner evidence is exact-commit, changed-file and extension-packet bound | Native C++/Python/Node/Vite commands, approved test data and real performance environments |",
            "| Integration | The executed cross-repository gate set and requirement/criterion/evidence mappings exactly match the approved matrix and ten-repository commit vector | Market/member simulators, contract fixtures, replay, latency, capacity and reconciliation environments |",
            "| Plan closure | Every frozen requirement, owning repository, acceptance criterion and required evidence type must be covered; distinct independent and adversarial reviews are mandatory | Authoritative DFS/FSD completeness, accountable reviewers and approved real evidence mappings |",
            "| GUI | Missing normative visual baseline stops at BLOCKED_SPEC | Approved design system/screens, Playwright baselines, browser matrix and accessibility owners |",
            "| Human Gate 2 | Exact PR heads, required checks and independent reviewers are mandatory | Real CODEOWNERS, protected branches and separation-of-duties policy |",
            "| Production | Not exercised by this local evaluation | Pre-production, migration/rollback rehearsal, business validation, production approval, canary, monitoring and post-deploy reconciliation |",
            "",
            "## Public basis and limitations",
            "",
            "The repository names and flows are an illustrative decomposition based only on public interface concepts. They are not a statement of Deutsche Boerse's internal architecture.",
            "",
        ]
    )
    for source in PUBLIC_SOURCES:
        lines.append(
            f"- [{source['title']}]({source['url']}): {source['used_for']}."
        )
    lines.extend(
        [
            "",
            "Synthetic fixtures are intentionally used only to make orchestration failures deterministic. A PASS proves that the configured controls behaved as tested; it does not prove that unspecified requirements are correct or that production software is defect-free.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    global SHARED_FIXTURE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--baseline-json", type=Path)
    parser.add_argument("--additional-baseline-json", type=Path)
    parser.add_argument(
        "--scenario-ids",
        help="comma-separated scenario IDs to execute, for example E16,E17",
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="render --output-report from the existing --output-json",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if args.render_only:
        if not args.output_report or not args.output_json.is_file():
            parser.error(
                "--render-only requires an existing --output-json and --output-report"
            )
        payload = json.loads(args.output_json.read_text(encoding="utf-8"))
        payload["evaluated_control_sha256"] = program_orchestrator.file_digest(
            root / ".github/scripts/program_orchestrator.py"
        )
        payload["evaluation_harness_sha256"] = program_orchestrator.file_digest(
            root / ".github/scripts/evaluate_eurex_ten_repo.py"
        )
        args.output_json.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        baseline = load_baselines(
            [args.baseline_json, args.additional_baseline_json]
        )
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(
            render_report(payload, baseline), encoding="utf-8"
        )
        print(json.dumps(payload["summary"], indent=2))
        return 0 if payload["summary"]["failed"] == 0 else 1
    selected_scenarios = SCENARIOS
    if args.scenario_ids:
        requested_ids = {
            item.strip().upper()
            for item in args.scenario_ids.split(",")
            if item.strip()
        }
        known = {
            scenario.__name__.replace("scenario_", "E"): scenario
            for scenario in SCENARIOS
        }
        unknown = sorted(requested_ids - set(known))
        if unknown:
            parser.error(f"unknown scenario IDs: {', '.join(unknown)}")
        selected_scenarios = [
            scenario
            for scenario_id, scenario in known.items()
            if scenario_id in requested_ids
        ]
    results = []
    SHARED_FIXTURE = Fixture(root)
    try:
        for scenario in selected_scenarios:
            try:
                observed = scenario(root)
            except Exception as exc:  # preserve every scenario result
                observed = result(
                    scenario.__name__.replace("scenario_", "E"),
                    "Harness execution",
                    "10-repository fixture",
                    "unknown",
                    "Scenario completes deterministically",
                    f"{type(exc).__name__}: {exc}",
                    False,
                    "Unhandled evaluation exception",
                    "Evaluation harness or control path raised unexpectedly",
                )
            results.append(asdict(observed))
            print(
                f"{observed.scenario}: {observed.status} - {observed.observed}",
                flush=True,
            )
    finally:
        SHARED_FIXTURE.close()
        SHARED_FIXTURE = None
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    payload = {
        "schema_version": "1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "control_plane_revision": revision or "unavailable",
        "evaluated_control_sha256": program_orchestrator.file_digest(
            root / ".github/scripts/program_orchestrator.py"
        ),
        "evaluation_harness_sha256": program_orchestrator.file_digest(
            root / ".github/scripts/evaluate_eurex_ten_repo.py"
        ),
        "fixture_kind": "synthetic-local-git",
        "repository_count": len(REPOSITORIES),
        "scenario_count": len(selected_scenarios),
        "public_sources": PUBLIC_SOURCES,
        "results": results,
        "summary": {
            "total": len(results),
            "passed": sum(item["status"] == "PASS" for item in results),
            "failed": sum(item["status"] == "FAIL" for item in results),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.output_report:
        baseline = load_baselines(
            [args.baseline_json, args.additional_baseline_json]
        )
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(
            render_report(payload, baseline), encoding="utf-8"
        )
    print(json.dumps(payload["summary"], indent=2))
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
