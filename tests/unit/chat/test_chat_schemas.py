import unittest

try:
    from app.modules.chat.web.schemas import ChatSessionCreateRequest
except ModuleNotFoundError:
    ChatSessionCreateRequest = None  # type: ignore[assignment]


class ChatSchemaTest(unittest.TestCase):
    def test_session_create_request_accepts_frontend_camel_case(self) -> None:
        self.assertIsNotNone(ChatSessionCreateRequest)
        request = ChatSessionCreateRequest.model_validate({"agentId": 7})

        self.assertEqual(request.agent_id, 7)


if __name__ == "__main__":
    unittest.main()
