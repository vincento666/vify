import unittest

from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables
from tests.support.mysql import mysql8_session


class AiAssistantToolSchedulerMetadataIntegrationTest(unittest.TestCase):
    def test_scheduler_metadata_round_trips_through_mysql8_tool_calls_and_events(self) -> None:
        with mysql8_session(
            "ai_assistant_scheduler_metadata",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        ) as session:
            repository = AiAssistantRepository(session)
            service = AiAssistantHarnessService(repository)
            assistant_session = service.create_session(title="Scheduler metadata")

            result = service.run_message(
                int(assistant_session["id"]),
                "run scheduler metadata",
                idempotency_key="scheduler-metadata-1",
                tool_calls=[
                    {"toolName": "echo_context", "toolInput": {"message": "alpha"}},
                    {"toolName": "echo_context", "toolInput": {"message": "beta"}},
                ],
            )
            tool_calls = repository.list_run_tool_calls(int(result.run["id"]))
            events = repository.list_run_events(int(result.run["id"]))

        scheduler_payload = dict(tool_calls[0]["input_payload"]["_scheduler"])
        started_payloads = [event["payload"] for event in events if event["type"] == "tool.call_started"]
        batch_events = [event for event in events if event["type"] == "scheduler.batch_started"]

        self.assertEqual(scheduler_payload["lockMode"], "READ")
        self.assertEqual(scheduler_payload["schedulerBatchId"], 1)
        self.assertEqual(scheduler_payload["readResourceKeys"], ["session:{}".format(assistant_session["id"])])
        self.assertEqual(started_payloads[0]["scheduler"]["parallelEligible"], True)
        self.assertEqual(batch_events[0]["payload"]["executionMode"], "READ_PARALLEL")


if __name__ == "__main__":
    unittest.main()
