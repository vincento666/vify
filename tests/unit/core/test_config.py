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


if __name__ == "__main__":
    unittest.main()
