import unittest
from unittest.mock import patch

from app.core.config import Settings
from app.core.database_url_policy import DEFAULT_MYSQL8_DATABASE_URL


class SettingsTest(unittest.TestCase):
    def test_defaults_keep_local_development_runnable(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.app_name, "Hify")
        self.assertEqual(settings.api_prefix, "/api/v1")
        self.assertEqual(settings.database_url, DEFAULT_MYSQL8_DATABASE_URL)
        self.assertIsNone(settings.redis_url)
        self.assertEqual(settings.deployment_environment, "local")
        self.assertEqual(settings.host_identity_mode, "local_headers")
        self.assertTrue(settings.runtime_v2_request_thread_completion_enabled)
        self.assertEqual(settings.runtime_lab_sop_runtime_invocation_mode, "async")
        self.assertEqual(settings.customer_assistant_sop_runtime_invocation_mode, "async")

    def test_production_requires_trusted_host_identity_mode(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "production deployment requires host_identity_mode=trusted_state",
        ):
            Settings(
                _env_file=None,
                deployment_environment="production",
                host_identity_mode="local_headers",
            )


if __name__ == "__main__":
    unittest.main()
