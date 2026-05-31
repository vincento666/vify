import unittest

from app.core.config import Settings


class SettingsTest(unittest.TestCase):
    def test_defaults_keep_local_development_runnable(self) -> None:
        settings = Settings()

        self.assertEqual(settings.app_name, "Hify")
        self.assertEqual(settings.api_prefix, "/api/v1")
        self.assertEqual(settings.database_url, "sqlite:///./hify.db")
        self.assertIsNone(settings.redis_url)


if __name__ == "__main__":
    unittest.main()
