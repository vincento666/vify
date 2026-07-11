from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable
from zoneinfo import ZoneInfo


def validate_usage_range(
    from_date: date | None,
    to_date: date | None,
    *,
    today: date,
    default_days: int,
    max_days: int = 366,
) -> tuple[date, date]:
    end = to_date or today
    start = from_date or (end - timedelta(days=default_days - 1))
    if start > end:
        raise ValueError("usage range start must not exceed end")
    if (end - start).days + 1 > max_days:
        raise ValueError("usage range cannot exceed 366 days")
    return start, end


def rows_in_local_range(
    rows: Iterable[dict[str, Any]],
    *,
    timezone_name: str,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    zone = ZoneInfo(timezone_name)
    return [row for row in rows if start <= _local_date(row, zone) <= end]


def usage_utc_bounds(
    *,
    timezone_name: str,
    start: date,
    end: date,
) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_start = datetime.combine(start, datetime.min.time(), tzinfo=zone)
    local_end = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return (
        local_start.astimezone(timezone.utc).replace(tzinfo=None),
        local_end.astimezone(timezone.utc).replace(tzinfo=None),
    )


def usage_session_detail(
    rows: list[dict[str, Any]],
    *,
    session_id: int,
    title: str,
) -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "title": title,
        **usage_totals(rows),
        "calls": [_call_payload(row) for row in rows],
    }


def usage_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_tokens = sum(int(row.get("total_tokens") or 0) for row in rows)
    known_costs = [Decimal(row["effective_cost_usd"]) for row in rows if row.get("effective_cost_usd") is not None]
    unknown = [row for row in rows if row.get("effective_cost_usd") is None]
    known_cost = sum(known_costs, Decimal(0))
    if not rows or not unknown:
        cost_state = "complete"
    elif known_costs:
        cost_state = "partial"
    else:
        cost_state = "unknown"
    return {
        "totalTokens": total_tokens,
        "costUsd": _cost_text(known_cost) if known_costs or not rows else None,
        "costState": cost_state,
        "unknownCostCount": len(unknown),
        "unknownCostTokens": sum(int(row.get("total_tokens") or 0) for row in unknown),
        "sessionCount": len({int(row["session_id"]) for row in rows}),
        "callCount": len(rows),
    }


def usage_totals_from_aggregate(values: dict[str, Any]) -> dict[str, Any]:
    call_count = int(values.get("call_count") or 0)
    unknown_count = int(values.get("unknown_cost_count") or 0)
    known_count = call_count - unknown_count
    if call_count == 0 or unknown_count == 0:
        cost_state = "complete"
    elif known_count > 0:
        cost_state = "partial"
    else:
        cost_state = "unknown"
    known_cost = Decimal(values.get("known_cost_usd") or 0)
    return {
        "totalTokens": int(values.get("total_tokens") or 0),
        "costUsd": _cost_text(known_cost) if known_count > 0 or call_count == 0 else None,
        "costState": cost_state,
        "unknownCostCount": unknown_count,
        "unknownCostTokens": int(values.get("unknown_cost_tokens") or 0),
        "sessionCount": int(values.get("session_count") or 0),
        "callCount": call_count,
    }


def _call_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "runId": int(row["run_id"]),
        "callId": str(row["call_id"]),
        "callKind": str(row["call_kind"]),
        "provider": str(row["provider"]),
        "model": str(row["model"]),
        "inputTokens": row.get("input_tokens"),
        "outputTokens": row.get("output_tokens"),
        "cacheReadTokens": row.get("cache_read_tokens"),
        "cacheWriteTokens": row.get("cache_write_tokens"),
        "reasoningTokens": row.get("reasoning_tokens"),
        "totalTokens": row.get("total_tokens"),
        "costUsd": _cost_text(Decimal(row["effective_cost_usd"])) if row.get("effective_cost_usd") is not None else None,
        "costSource": str(row["cost_source"]),
        "pricingVersion": row.get("pricing_version"),
        "startedAt": row["started_at"].isoformat(),
        "completedAt": row["completed_at"].isoformat() if row.get("completed_at") else None,
    }


def _local_date(row: dict[str, Any], zone: ZoneInfo) -> date:
    started = row["started_at"]
    if not isinstance(started, datetime):
        raise ValueError("usage row started_at must be a datetime")
    aware = started.replace(tzinfo=timezone.utc) if started.tzinfo is None else started.astimezone(timezone.utc)
    return aware.astimezone(zone).date()


def _cost_text(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0000000001")))
