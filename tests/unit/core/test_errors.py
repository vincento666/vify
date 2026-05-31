import unittest

from app.core.errors import BizError, ErrorCode


class ErrorModelTest(unittest.TestCase):
    def test_biz_error_keeps_status_code_and_message(self) -> None:
        error = BizError(ErrorCode.BAD_REQUEST, "invalid provider config")

        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.message, "invalid provider config")


if __name__ == "__main__":
    unittest.main()
