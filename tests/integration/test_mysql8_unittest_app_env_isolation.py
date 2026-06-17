import os
import unittest

from app.core.config import get_settings
from tests.support.mysql import mysql8_unittest_database


MYSQL8_TEST_DATABASE_URL = os.getenv("HIFY_MYSQL8_TEST_DATABASE_URL")


@unittest.skipUnless(MYSQL8_TEST_DATABASE_URL, "set HIFY_MYSQL8_TEST_DATABASE_URL for MySQL8 integration")
class Mysql8UnittestAppEnvIsolationTest(unittest.TestCase):
    def test_unittest_database_sets_disposable_database_url_and_restores_it(self) -> None:
        previous_url = os.environ.get("HIFY_DATABASE_URL")

        database = mysql8_unittest_database(self, "mysql8_unittest_app_env_isolation")

        self.assertEqual(os.environ.get("HIFY_DATABASE_URL"), database.database_url)
        self.assertEqual(get_settings().database_url, database.database_url)

        self.doCleanups()

        self.assertEqual(os.environ.get("HIFY_DATABASE_URL"), previous_url)
        self.assertNotEqual(get_settings().database_url, database.database_url)


if __name__ == "__main__":
    unittest.main()
