import unittest


class AiAssistantPlanStateTest(unittest.TestCase):
    def test_default_auto_lightweight_plan_has_recognized_need_and_steps(self) -> None:
        from app.modules.ai_assistant.domain.plan_state import (
            PlanningStrategy,
            create_initial_plan_state,
            normalize_planning_strategy,
        )

        self.assertEqual(normalize_planning_strategy(None), PlanningStrategy.AUTO_LIGHTWEIGHT)

        plan = create_initial_plan_state(
            run_id=42,
            message="读取 AGENTS.md 并总结",
            requested_strategy=None,
            planned_tool_names=["read_workspace_file"],
        )

        self.assertEqual(plan["id"], "plan-42")
        self.assertEqual(plan["planningStrategy"], "auto_lightweight")
        self.assertEqual(plan["recognizedNeeds"], ["读取 AGENTS.md 并总结"])
        self.assertEqual(plan["steps"][0]["status"], "PENDING")
        self.assertEqual(plan["steps"][0]["toolName"], "read_workspace_file")

    def test_plan_only_and_deliberate_are_explicit_strategies(self) -> None:
        from app.modules.ai_assistant.domain.plan_state import (
            PlanningStrategy,
            normalize_planning_strategy,
        )

        self.assertEqual(normalize_planning_strategy("plan_only"), PlanningStrategy.PLAN_ONLY)
        self.assertEqual(normalize_planning_strategy("deliberate"), PlanningStrategy.DELIBERATE)

    def test_blocked_plan_updates_current_step_and_step_list_consistently(self) -> None:
        from app.modules.ai_assistant.domain.plan_state import create_initial_plan_state, mark_plan_blocked

        plan = create_initial_plan_state(
            run_id=7,
            message="写入文件",
            requested_strategy=None,
            planned_tool_names=["write_workspace_file"],
        )

        blocked = mark_plan_blocked(plan, "需要审批")

        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["currentStep"]["status"], "BLOCKED")
        self.assertEqual(blocked["steps"][0]["status"], "BLOCKED")

    def test_plan_only_completion_marks_steps_and_plan_completed(self) -> None:
        from app.modules.ai_assistant.domain.plan_state import complete_plan_without_execution, create_initial_plan_state

        plan = create_initial_plan_state(
            run_id=8,
            message="只规划",
            requested_strategy="plan_only",
            planned_tool_names=["echo_context"],
        )

        completed = complete_plan_without_execution(plan, "已生成计划，未执行工具。")

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["currentStep"]["status"], "COMPLETED")
        self.assertEqual(completed["steps"][0]["status"], "COMPLETED")
        self.assertEqual(completed["finalResult"], "已生成计划，未执行工具。")


if __name__ == "__main__":
    unittest.main()
