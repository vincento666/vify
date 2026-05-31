import unittest

try:
    from app.modules.knowledge.web.schemas import KnowledgeBaseCreateRequest, KnowledgeBaseUpdateRequest
except ImportError:
    KnowledgeBaseCreateRequest = None  # type: ignore[assignment]
    KnowledgeBaseUpdateRequest = None  # type: ignore[assignment]


class KnowledgeSchemaTest(unittest.TestCase):
    def test_create_and_update_requests_accept_frontend_fields(self) -> None:
        self.assertIsNotNone(KnowledgeBaseCreateRequest)
        self.assertIsNotNone(KnowledgeBaseUpdateRequest)
        create_request = KnowledgeBaseCreateRequest.model_validate(
            {"name": "KB", "description": "docs"}
        )
        update_request = KnowledgeBaseUpdateRequest.model_validate(
            {"name": "KB2", "description": "docs2", "enabled": 0}
        )

        self.assertEqual(create_request.name, "KB")
        self.assertEqual(update_request.enabled, 0)


if __name__ == "__main__":
    unittest.main()
