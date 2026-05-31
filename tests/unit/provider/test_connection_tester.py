import unittest

from app.modules.provider.domain.connection import ProviderConnectionTester


class ProviderConnectionTesterTest(unittest.TestCase):
    def test_mock_success_returns_latency_and_model_count(self) -> None:
        result = ProviderConnectionTester().test(
            provider_type="OPENAI",
            base_url="mock://success",
            auth_config={"api_key": "sk-test"},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.model_count, 2)
        self.assertIsNotNone(result.latency_ms)

    def test_mock_failure_maps_to_error_result(self) -> None:
        result = ProviderConnectionTester().test(
            provider_type="OPENAI",
            base_url="mock://failure",
            auth_config={"api_key": "sk-test"},
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "mock connection failure")


if __name__ == "__main__":
    unittest.main()
