import json
import unittest

try:
    from app.modules.chat.domain.sse import SseEventEncoder
except ModuleNotFoundError:
    SseEventEncoder = None  # type: ignore[assignment]


class SseEventEncoderTest(unittest.TestCase):
    def test_encode_event_as_sse_data_line(self) -> None:
        self.assertIsNotNone(SseEventEncoder)
        line = SseEventEncoder().encode({"type": "delta", "content": "hi"})

        self.assertTrue(line.startswith("data: "))
        self.assertTrue(line.endswith("\n\n"))
        self.assertEqual(json.loads(line.removeprefix("data: ").strip()), {"type": "delta", "content": "hi"})


if __name__ == "__main__":
    unittest.main()
