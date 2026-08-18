from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATH = ROOT / ".github" / "scripts" / "copilot_runtime.py"


def load_runtime_module():
    spec = importlib.util.spec_from_file_location("copilot_runtime", RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["copilot_runtime"] = module
    spec.loader.exec_module(module)
    return module


runtime = load_runtime_module()


class CopilotRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def profile(self, name: str, description: str = "specialist") -> Path:
        path = self.root / f"{name}.agent.md"
        path.write_text(
            "---\n"
            f"name: {name}\n"
            f'description: "{description}"\n'
            "tools: [read, search]\n"
            "user-invocable: false\n"
            "---\n\n"
            f"Operate as {name}.\n",
            encoding="utf-8",
        )
        return path

    def packet_item(self, path: Path, role: str) -> dict:
        return {
            "id": path.name.removesuffix(".md"),
            "resolved_path": str(path),
            "sha256": runtime.sha256_file(path),
            "role": role,
        }

    def test_catalog_uses_frontmatter_name_and_prefers_developer(self):
        architect = self.profile("p7-sdlc-architect")
        builder = self.profile("p7-sdlc-builder")
        developer = self.profile("p7-sdlc-developer")
        tester = self.profile("p7-sdlc-tester")
        reviewer = self.profile("p7-sdlc-reviewer")
        packet = {
            "agents": [
                self.packet_item(architect, "implementation"),
                self.packet_item(builder, "implementation"),
                self.packet_item(developer, "implementation"),
                self.packet_item(tester, "testing"),
                self.packet_item(reviewer, "independent-domain-review"),
            ]
        }
        catalog, roles = runtime.build_agent_catalog(packet)
        selected = runtime.select_required_agents(
            catalog,
            roles,
            ["implementation", "build", "testing", "independent-domain-review"],
        )
        self.assertEqual(selected["implementation"], "p7-sdlc-developer")
        self.assertEqual(selected["build"], "p7-sdlc-builder")
        self.assertEqual(selected["testing"], "p7-sdlc-tester")
        self.assertEqual(
            selected["independent-domain-review"], "p7-sdlc-reviewer"
        )
        self.assertNotIn("p7-sdlc-developer.agent", selected.values())

    def test_multiline_frontmatter_tools_remain_scoped(self):
        path = self.root / "build-verifier.agent.md"
        path.write_text(
            "---\n"
            "name: build-verifier\n"
            "description: Build only\n"
            "tools:\n"
            "  - read\n"
            "  - execute\n"
            "user-invocable: false\n"
            "---\n\nRun the build.\n",
            encoding="utf-8",
        )
        self.assertEqual(runtime.read_agent_profile(path)["tools"], ["read", "execute"])

    @staticmethod
    def execution_events(agent: str, instance: str, call: str) -> list[dict]:
        return [
            {
                "id": call + "-start",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "agent_id": instance,
                "type": "subagent.started",
                "data": {"agent_name": agent, "tool_call_id": call},
            },
            {
                "id": call + "-message",
                "timestamp": "2026-01-01T00:00:01+00:00",
                "agent_id": instance,
                "type": "assistant.message",
                "data": {
                    "content": (
                        f"{agent} result\nSDLC_SPECIALIST_RESULT "
                        '{"decision":"PASS","summary":"complete",'
                        '"evidence":["test command passed"],"findings":[]}'
                    )
                },
            },
            {
                "id": call + "-complete",
                "timestamp": "2026-01-01T00:00:02+00:00",
                "agent_id": None,
                "type": "subagent.completed",
                "data": {"agent_name": agent, "tool_call_id": call},
            },
        ]

    def test_final_state_assurance_requires_real_lifecycle_messages(self):
        required = {
            "implementation": "developer",
            "build": "builder",
            "testing": "tester",
            "independent-domain-review": "reviewer",
        }
        events = []
        for index, name in enumerate(required.values(), start=1):
            events.extend(self.execution_events(name, f"instance-{index}", f"call-{index}"))
        executions = runtime.summarize_executions(events)
        missing, failed, inconclusive = runtime.validate_required_executions(
            executions, required
        )
        self.assertEqual(failed, [])
        self.assertEqual(inconclusive, [])
        self.assertEqual(missing, [])
        self.assertTrue(all(item["output_message_count"] == 1 for item in executions))
        self.assertTrue(
            all(item["result_contract"]["decision"] == "PASS" for item in executions)
        )

    def test_validation_before_implementation_is_stale(self):
        required = {
            "implementation": "developer",
            "build": "builder",
            "testing": "tester",
            "independent-domain-review": "reviewer",
        }
        events = []
        for index, name in enumerate(("tester", "reviewer", "builder", "developer"), start=1):
            events.extend(self.execution_events(name, f"instance-{index}", f"call-{index}"))
        executions = runtime.summarize_executions(events)
        missing, failed, inconclusive = runtime.validate_required_executions(
            executions, required
        )
        self.assertEqual(failed, [])
        self.assertEqual(inconclusive, [])
        self.assertIn(
            "tester (no final-state execution after implementation)", missing
        )
        self.assertIn(
            "reviewer (no final-state execution after implementation)", missing
        )

    def test_digest_mismatch_rejects_selected_agent(self):
        profile = self.profile("risk-reviewer")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            runtime.build_agent_catalog(
                {
                    "agents": [
                        {
                            "id": "risk-reviewer.agent",
                            "resolved_path": str(profile),
                            "sha256": "0" * 64,
                            "role": "independent-domain-review",
                        }
                    ]
                }
            )

    def test_missing_specialist_contract_fails_closed(self):
        events = self.execution_events("developer", "instance", "call")
        events[1]["data"]["content"] = "looks good"
        executions = runtime.summarize_executions(events)
        missing, failed, inconclusive = runtime.validate_required_executions(
            executions, {"implementation": "developer"}
        )
        self.assertEqual(failed, [])
        self.assertEqual(inconclusive, [])
        self.assertEqual(missing, ["developer"])

    def test_inconclusive_specialist_is_not_misreported_as_failure(self):
        events = self.execution_events("developer", "instance", "call")
        events[1]["data"]["content"] = (
            'SDLC_SPECIALIST_RESULT {"decision":"INCONCLUSIVE",'
            '"summary":"missing approved rate source",'
            '"evidence":["DFS section is absent"],'
            '"findings":["Need authoritative rate source"]}'
        )
        executions = runtime.summarize_executions(events)
        missing, failed, inconclusive = runtime.validate_required_executions(
            executions, {"implementation": "developer"}
        )
        self.assertEqual(failed, [])
        self.assertEqual(inconclusive, ["developer"])
        self.assertEqual(missing, ["developer"])

    def test_skill_catalog_is_digest_bound_and_mapped_to_agent(self):
        skill = self.root / "common" / "coding-guidelines" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Coding guidelines\n", encoding="utf-8")
        available, roots = runtime.build_skill_catalog(
            {
                "skills": [
                    {
                        "resolved_path": str(skill),
                        "sha256": runtime.sha256_file(skill),
                    }
                ]
            }
        )
        agent = {
            "metadata": {"skills_common": ["coding-guidelines", "missing"]}
        }
        self.assertEqual(list(available), ["coding-guidelines"])
        self.assertEqual(roots, [str(skill.parent.parent)])
        self.assertEqual(
            runtime.skills_for_agent(agent, "implementation", available),
            ["coding-guidelines"],
        )

    def test_model_display_label_is_normalized_for_sdk(self):
        self.assertEqual(
            runtime.sdk_model_id("Claude Sonnet 4.6 (copilot)"),
            "claude-sonnet-4.6",
        )

    def test_vscode_tool_aliases_are_translated_for_sdk(self):
        self.assertEqual(
            runtime.sdk_tool_names(["read", "search", "edit", "execute"]),
            ["view", "grep", "glob", "edit", "bash"],
        )


if __name__ == "__main__":
    unittest.main()
