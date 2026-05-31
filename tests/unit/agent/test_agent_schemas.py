import unittest

from app.modules.agent.web.schemas import AgentCreateRequest


class AgentSchemaTest(unittest.TestCase):
    def test_create_request_accepts_frontend_camel_case(self) -> None:
        request = AgentCreateRequest.model_validate(
            {
                "name": "Unit Agent",
                "systemPrompt": "You are helpful.",
                "modelConfigId": 1,
                "temperature": 0.7,
                "maxTokens": 2048,
                "maxContextTurns": 10,
                "toolIds": [],
            }
        )

        self.assertEqual(request.system_prompt, "You are helpful.")
        self.assertEqual(request.model_config_id, 1)
        self.assertEqual(request.max_context_turns, 10)

    def test_create_request_accepts_nullable_binding_ids(self) -> None:
        request = AgentCreateRequest.model_validate(
            {
                "name": "Bound Agent",
                "modelConfigId": 1,
                "knowledgeBaseId": None,
                "workflowId": 9,
            }
        )

        self.assertIsNone(getattr(request, "knowledge_base_id", "missing"))
        self.assertEqual(getattr(request, "workflow_id", "missing"), 9)


if __name__ == "__main__":
    unittest.main()
