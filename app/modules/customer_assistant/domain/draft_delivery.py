from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Any

from app.core.sanitization import sanitize_text


@dataclass(frozen=True)
class MockDraftDeliveryResult:
    adapter_ref: str
    status: str
    delivery: dict[str, Any]
    error: dict[str, Any] | None = None


class MockDraftDeliveryOutbox:
    adapter_ref = "customer_reply_mock_channel"

    def deliver(self, payload: dict[str, Any]) -> MockDraftDeliveryResult:
        draft = _draft_text(payload)
        channel = str(payload.get("channel") or "mock_local")
        now = datetime.now().isoformat()
        delivery = {
            "adapterRef": self.adapter_ref,
            "channel": sanitize_text(channel),
            "status": "SENT",
            "messageId": _message_id(channel, draft),
            "contentHash": hashlib.sha256(draft.encode("utf-8")).hexdigest(),
            "contentExcerpt": sanitize_text(draft[:160]),
            "deliveredAt": now,
        }
        if _force_failure(payload):
            delivery["status"] = "FAILED"
            delivery["messageId"] = None
            delivery["failedAt"] = now
            return MockDraftDeliveryResult(
                adapter_ref=self.adapter_ref,
                status="FAILED",
                delivery=delivery,
                error={
                    "code": "MOCK_DELIVERY_FAILED",
                    "message": "Mock delivery failure requested for local outbox.",
                },
            )
        if not draft.strip():
            delivery["status"] = "FAILED"
            delivery["messageId"] = None
            delivery["failedAt"] = now
            return MockDraftDeliveryResult(
                adapter_ref=self.adapter_ref,
                status="FAILED",
                delivery=delivery,
                error={
                    "code": "EMPTY_DRAFT",
                    "message": "Customer reply draft is required for delivery.",
                },
            )
        return MockDraftDeliveryResult(adapter_ref=self.adapter_ref, status="SENT", delivery=delivery)


def _draft_text(payload: dict[str, Any]) -> str:
    for key in ("draft", "customerReplyDraft", "message", "text"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    return ""


def _force_failure(payload: dict[str, Any]) -> bool:
    config = payload.get("mockDelivery")
    if isinstance(config, dict):
        return bool(config.get("forceFailure"))
    return False


def _message_id(channel: str, draft: str) -> str:
    digest = hashlib.sha256(f"{channel}:{draft}".encode("utf-8")).hexdigest()[:12]
    return f"mock-msg-{digest}"
