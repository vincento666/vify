import unittest


class AiAssistantToolSchedulerTest(unittest.TestCase):
    def test_read_only_tools_share_one_parallel_batch(self) -> None:
        from app.modules.ai_assistant.domain.scheduler import ScheduledToolInvocation, ToolScheduler
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        scheduler = ToolScheduler(ToolRegistry.with_builtin_tools())

        plan = scheduler.plan(
            [
                ScheduledToolInvocation("echo_context", {"message": "first"}),
                ScheduledToolInvocation("echo_context", {"message": "second"}),
            ],
            context={"session_id": 7},
        )

        self.assertEqual(len(plan.batches), 1)
        self.assertEqual(plan.batches[0].execution_mode, "READ_PARALLEL")
        self.assertEqual([item.tool_name for item in plan.batches[0].items], ["echo_context", "echo_context"])
        self.assertEqual(plan.batches[0].read_resources, ["session:7"])
        self.assertEqual(plan.batches[0].write_resources, [])
        self.assertEqual(plan.batches[0].lock_mode, "READ")
        self.assertTrue(plan.batches[0].parallel_eligible)
        self.assertEqual(
            [metadata["schedulerPosition"] for metadata in plan.batches[0].item_metadata],
            [1, 2],
        )

    def test_write_tools_are_serialized_by_resource_key(self) -> None:
        from app.modules.ai_assistant.domain.scheduler import ScheduledToolInvocation, ToolScheduler
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        scheduler = ToolScheduler(ToolRegistry.with_builtin_tools())

        plan = scheduler.plan(
            [
                ScheduledToolInvocation("update_customer_profile", {"customerId": "C-1", "field": "tier"}),
                ScheduledToolInvocation("update_customer_profile", {"customerId": "C-1", "field": "phone"}),
            ],
            context={"session_id": 7},
        )

        self.assertEqual(len(plan.batches), 2)
        self.assertEqual([batch.execution_mode for batch in plan.batches], ["WRITE_EXCLUSIVE", "WRITE_EXCLUSIVE"])
        self.assertEqual([batch.lock_mode for batch in plan.batches], ["WRITE", "WRITE"])
        self.assertEqual([batch.write_resources for batch in plan.batches], [["customer:C-1"], ["customer:C-1"]])
        self.assertEqual([batch.batch_id for batch in plan.batches], [1, 2])

    def test_unresolved_write_resources_fall_back_to_serial_lock(self) -> None:
        from app.modules.ai_assistant.domain.scheduler import ScheduledToolInvocation, ToolScheduler
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        scheduler = ToolScheduler(ToolRegistry.with_builtin_tools())

        plan = scheduler.plan(
            [ScheduledToolInvocation("update_customer_profile", {"field": "tier"})],
            context={"session_id": 7},
        )

        self.assertEqual(plan.batches[0].execution_mode, "SERIAL")
        self.assertEqual(plan.batches[0].lock_mode, "SERIAL")
        self.assertEqual(plan.batches[0].write_resources, ["customer:{customerId}"])
        self.assertEqual(plan.batches[0].resource_lock_reason, "unresolved_resource_template")
        self.assertFalse(plan.batches[0].parallel_eligible)


if __name__ == "__main__":
    unittest.main()
