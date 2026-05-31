import unittest

try:
    from app.modules.chat.domain.mode import ChatModeRouter
except ModuleNotFoundError:
    ChatModeRouter = None  # type: ignore[assignment]


class ChatModeRouterTest(unittest.TestCase):
    def test_workflow_binding_takes_priority_over_rag_binding(self) -> None:
        self.assertIsNotNone(ChatModeRouter)
        router = ChatModeRouter()

        self.assertEqual(router.resolve({"knowledge_base_id": 1, "workflow_id": 2}), "workflow")
        self.assertEqual(router.resolve({"knowledge_base_id": 1, "workflow_id": None}), "rag")
        self.assertEqual(router.resolve({"knowledge_base_id": None, "workflow_id": None}), "direct")


if __name__ == "__main__":
    unittest.main()
