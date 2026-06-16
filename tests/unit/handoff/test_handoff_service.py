from datetime import datetime

from app.modules.handoff.domain.service import HandoffService


class FakeRepository:
    def create(self, values):
        return {
            "id": 12,
            "session_id": values["session_id"],
            "conversation_id": values["conversation_id"],
            "user_id": values["user_id"],
            "channel": values["channel"],
            "queue": values["queue"],
            "assignee": values.get("assignee", ""),
            "status": values["status"],
            "reason": values["reason"],
            "priority": values["priority"],
            "sla_due_at": values["sla_due_at"],
            "transcript_snapshot": values["transcript_snapshot"],
            "context_snapshot": values["context_snapshot"],
            "closed_at": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }


def test_handoff_service_creates_queued_ticket_with_sla() -> None:
    ticket = HandoffService(FakeRepository()).create_ticket(
        {
            "session_id": "s-1",
            "conversation_id": "c-1",
            "user_id": "u-1",
            "channel": "web",
            "queue": "vip-support",
            "reason": "user_request",
            "priority": "high",
            "sla_minutes": 15,
            "transcript_snapshot": [{"role": "user", "content": "help"}],
            "context_snapshot": {"nodeKey": "handoff_1"},
        }
    )

    assert ticket["id"] == 12
    assert ticket["status"] == "queued"
    assert ticket["queue"] == "vip-support"
    assert ticket["priority"] == "high"
    assert ticket["slaDueAt"]
    assert ticket["transcriptSnapshot"] == [{"role": "user", "content": "help"}]
