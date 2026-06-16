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

    def test_create_request_accepts_chat_entry_fields(self) -> None:
        request = AgentCreateRequest.model_validate(
            {
                "name": "Entry Agent",
                "modelConfigId": 1,
                "openingMessage": "你好，我可以帮你处理退款。",
                "suggestedQuestions": ["如何退款？", "订单状态是什么？"],
            }
        )

        self.assertEqual(request.opening_message, "你好，我可以帮你处理退款。")
        self.assertEqual(request.suggested_questions, ["如何退款？", "订单状态是什么？"])


if __name__ == "__main__":
    unittest.main()
