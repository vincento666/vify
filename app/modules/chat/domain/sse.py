import json
from typing import Any


class SseEventEncoder:
    def encode(self, event: dict[str, Any]) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
