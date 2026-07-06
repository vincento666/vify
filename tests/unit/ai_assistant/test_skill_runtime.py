import tempfile
import unittest
from pathlib import Path


class AiAssistantSkillRuntimeTest(unittest.TestCase):
    def test_discovers_metadata_without_loading_skill_body_then_loads_on_trigger(self) -> None:
        from app.modules.ai_assistant.domain import skills

        tmp = tempfile.TemporaryDirectory()
        root = _make_skill_root(Path(tmp.name))
        try:
            self.assertTrue(hasattr(skills, "SkillRuntime"), "SkillRuntime must be a first-class runtime")
            runtime = skills.SkillRuntime(root_paths=[root])
            registry = runtime.discover()

            manifest = registry.get_manifest("tdd")
            self.assertEqual(manifest.name, "tdd")
            self.assertEqual(manifest.description, "Use red-green-refactor workflow.")
            self.assertEqual(manifest.path, str((root / "tdd").resolve()))
            self.assertEqual(manifest.version, "1.2.3")
            self.assertEqual(manifest.risk_level, "READ")
            self.assertTrue(manifest.checksum.startswith("sha256:"))
            self.assertFalse(manifest.content_loaded)
            self.assertNotIn("BODY_SECRET", registry.prompt_index())

            loaded = runtime.load_skill("tdd", reason="trigger:tdd", session_id=7, run_id=11)
            self.assertEqual(loaded.manifest.name, "tdd")
            self.assertIn("BODY_SECRET", loaded.content)
            self.assertTrue(loaded.manifest.content_loaded)
            self.assertEqual(
                [event["type"] for event in loaded.audit_events],
                ["skill.load_started", "skill.loaded"],
            )
            self.assertEqual(loaded.audit_events[-1]["payload"]["checksum"], manifest.checksum)
        finally:
            tmp.cleanup()

    def test_reads_references_scripts_and_assets_on_demand_only(self) -> None:
        from app.modules.ai_assistant.domain import skills

        tmp = tempfile.TemporaryDirectory()
        root = _make_skill_root(Path(tmp.name))
        try:
            runtime = skills.SkillRuntime(root_paths=[root])
            runtime.discover()

            reference = runtime.read_resource(
                "tdd",
                "references/checklist.md",
                session_id=7,
                run_id=11,
            )
            script = runtime.read_resource("tdd", "scripts/verify.js", session_id=7, run_id=11)
            asset = runtime.read_resource("tdd", "assets/template.txt", session_id=7, run_id=11)

            self.assertEqual(reference.kind, "reference")
            self.assertIn("RED then GREEN", reference.content)
            self.assertEqual(script.kind, "script")
            self.assertIn("console.log", script.content)
            self.assertEqual(asset.kind, "asset")
            self.assertIn("template asset", asset.content)
            self.assertTrue(
                all(event["type"] == "skill.resource_read" for event in reference.audit_events + script.audit_events + asset.audit_events)
            )

            with self.assertRaises(skills.SkillRuntimeError):
                runtime.read_resource("tdd", "../outside.txt", session_id=7, run_id=11)
        finally:
            tmp.cleanup()


class AiAssistantSkillPromptAssemblerTest(unittest.TestCase):
    def test_prompt_uses_metadata_index_before_trigger_and_skill_body_after_trigger(self) -> None:
        from app.modules.ai_assistant.domain import skills
        from app.modules.ai_assistant.domain.prompt import PromptAssembler
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        tmp = tempfile.TemporaryDirectory()
        root = _make_skill_root(Path(tmp.name))
        try:
            runtime = skills.SkillRuntime(root_paths=[root])
            registry = runtime.discover()

            plain_prompt = PromptAssembler(
                base_instruction="You are Hify AI Assistant.",
                tool_registry=ToolRegistry.with_builtin_tools(),
                skill_registry=registry,
            ).assemble(user_message="Say hello.", run_state={"status": "RUNNING"})

            self.assertIn("tdd", plain_prompt.text)
            self.assertIn("Use red-green-refactor workflow.", plain_prompt.text)
            self.assertNotIn("BODY_SECRET", plain_prompt.text)

            triggered_prompt = PromptAssembler(
                base_instruction="You are Hify AI Assistant.",
                tool_registry=ToolRegistry.with_builtin_tools(),
                skill_registry=registry,
            ).assemble(user_message="Use tdd for this slice.", run_state={"status": "RUNNING"})

            self.assertIn("skill:tdd", [layer["name"] for layer in triggered_prompt.layers])
            self.assertIn("BODY_SECRET", triggered_prompt.text)
        finally:
            tmp.cleanup()


def _make_skill_root(root: Path) -> Path:
    skill_dir = root / "tdd"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "assets").mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: tdd
description: Use red-green-refactor workflow.
version: 1.2.3
risk: READ
triggers:
  - tdd
  - red green refactor
---
# TDD Skill

BODY_SECRET: load this only after trigger match.
""",
        encoding="utf-8",
    )
    (skill_dir / "references" / "checklist.md").write_text("RED then GREEN then REFACTOR.\n", encoding="utf-8")
    (skill_dir / "scripts" / "verify.js").write_text("console.log('verify');\n", encoding="utf-8")
    (skill_dir / "assets" / "template.txt").write_text("template asset\n", encoding="utf-8")
    return root


if __name__ == "__main__":
    unittest.main()
