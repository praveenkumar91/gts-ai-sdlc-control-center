from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / ".github" / "scripts"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard_tool = load_module("guard_tool")
validate_control_plane = load_module("validate_control_plane")
validate_evidence = load_module("validate_evidence")


class ControlPlaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected_policy = json.loads(
            (ROOT / ".github/sdlc/policies/protected-paths.json").read_text(encoding="utf-8")
        )
        cls.risk_policy = json.loads(
            (ROOT / ".github/sdlc/policies/risk-tiers.json").read_text(encoding="utf-8")
        )

    def test_repository_structure_is_valid_in_template_mode(self):
        self.assertEqual(validate_control_plane.validate(ROOT), [])

    def test_force_push_is_denied(self):
        result = guard_tool.evaluate_tool(
            {"toolName": "bash", "toolArgs": {"command": "git push origin main --force"}},
            self.protected_policy,
        )
        self.assertEqual(result["permissionDecision"], "deny")

    def test_protected_policy_edit_is_denied(self):
        result = guard_tool.evaluate_tool(
            {
                "toolName": "edit",
                "toolArgs": {
                    "path": ".github/sdlc/policies/risk-tiers.json",
                    "content": "{}",
                },
            },
            self.protected_policy,
        )
        self.assertEqual(result["permissionDecision"], "deny")

    def test_normal_test_command_is_allowed(self):
        result = guard_tool.evaluate_tool(
            {"toolName": "bash", "toolArgs": {"command": "python -m unittest"}},
            self.protected_policy,
        )
        self.assertEqual(result["permissionDecision"], "allow")

    def test_complete_low_risk_manifest_passes(self):
        commit = "a" * 40
        manifest = {
            "change_id": "CHG-1",
            "commit_sha": commit,
            "risk_tier": "low",
            "requirements": [
                {
                    "id": "REQ-100",
                    "status": "PASS",
                    "source_refs": ["S:1"],
                    "design_refs": ["ADR-1"],
                    "code_refs": ["src/a"],
                    "test_refs": ["test-a"],
                    "result_refs": ["result-a"],
                }
            ],
            "gates": [
                {"id": gate, "status": "PASS", "commit_sha": commit}
                for gate in ("control-plane", "build", "unit-tests", "static-analysis")
            ],
            "independent_reviews": [
                {
                    "reviewer": "independent-1",
                    "independent": True,
                    "status": "PASS",
                    "commit_sha": commit,
                }
            ],
            "open_findings": [],
            "decision": "PASS",
        }
        errors = validate_evidence.evaluate_manifest(manifest, self.risk_policy, commit)
        self.assertEqual(errors, [])

    def test_missing_gate_is_inconclusive(self):
        commit = "b" * 40
        manifest = {
            "change_id": "CHG-2",
            "commit_sha": commit,
            "risk_tier": "low",
            "requirements": [
                {
                    "id": "REQ-101",
                    "status": "PASS",
                    "source_refs": ["S:1"],
                    "design_refs": ["ADR-1"],
                    "code_refs": ["src/a"],
                    "test_refs": ["test-a"],
                    "result_refs": ["result-a"],
                }
            ],
            "gates": [],
            "independent_reviews": [],
            "open_findings": [],
            "decision": "PASS",
        }
        errors = validate_evidence.evaluate_manifest(manifest, self.risk_policy, commit)
        self.assertTrue(any("missing required gate" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
