import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import BizError, ErrorCode
from app.core.exception_handlers import register_exception_handlers
from app.main import app


class ErrorEnvelopeContractTest(unittest.TestCase):
    def test_biz_error_returns_stable_error_envelope(self) -> None:
        test_app = FastAPI()
        register_exception_handlers(test_app)

        @test_app.get("/boom")
        def boom() -> None:
            raise BizError(ErrorCode.BAD_REQUEST, "invalid provider config")

        response = TestClient(test_app).get("/boom")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "code": 400,
                "message": "invalid provider config",
                "data": None,
            },
        )

    def test_main_app_404_uses_error_envelope(self) -> None:
        response = TestClient(app).get("/api/v1/not-found")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "code": 404,
                "message": "Not Found",
                "data": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
