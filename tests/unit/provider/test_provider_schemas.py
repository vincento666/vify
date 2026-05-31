import unittest

from app.modules.provider.web.schemas import ProviderCreateRequest


class ProviderSchemaTest(unittest.TestCase):
    def test_create_request_accepts_frontend_camel_case(self) -> None:
        request = ProviderCreateRequest.model_validate(
            {
                "name": "Unit Provider",
                "type": "OPENAI",
                "baseUrl": "https://api.example.com/v1",
                "authConfig": {"api_key": "sk-test"},
            }
        )

        self.assertEqual(request.base_url, "https://api.example.com/v1")
        self.assertEqual(request.auth_config, {"api_key": "sk-test"})


if __name__ == "__main__":
    unittest.main()
