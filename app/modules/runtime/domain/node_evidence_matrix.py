from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


EVIDENCE_STATUSES = {"covered", "partial", "automated-only", "not-applicable", "missing"}
FOLLOW_UP_REQUIRED_STATUSES = {"partial", "automated-only", "missing"}


@dataclass(frozen=True)
class NodeEvidenceMatrixRow:
    node_type: str
    workflow_evidence: str
    chatflow_evidence: str
    closure_owner: str


def parse_node_evidence_matrix(markdown: str) -> dict[str, NodeEvidenceMatrixRow]:
    rows: dict[str, NodeEvidenceMatrixRow] = {}
    lines = markdown.splitlines()
    header_index = -1
    for index, line in enumerate(lines):
        cells = _split_markdown_row(line)
        if cells[:4] == ["Node type", "Workflow evidence", "Chatflow evidence", "Closure owner"]:
            header_index = index
            break
    if header_index < 0:
        return rows
    for line in lines[header_index + 1 :]:
        cells = _split_markdown_row(line)
        if not cells:
            if rows:
                break
            continue
        if _is_separator_row(cells):
            continue
        if len(cells) < 4:
            break
        node_type = cells[0].strip()
        if not node_type:
            continue
        rows[node_type] = NodeEvidenceMatrixRow(
            node_type=node_type,
            workflow_evidence=_normalize_status(cells[1]),
            chatflow_evidence=_normalize_status(cells[2]),
            closure_owner=cells[3].strip(),
        )
    return rows


def validate_node_evidence_matrix(
    rows: dict[str, NodeEvidenceMatrixRow],
    *,
    expected_node_types: Iterable[str],
) -> list[str]:
    errors: list[str] = []
    expected = tuple(expected_node_types)
    row_keys = set(rows)
    for node_type in expected:
        row = rows.get(node_type)
        if row is None:
            errors.append(f"{node_type} evidence row is missing")
            continue
        _append_status_errors(errors, node_type, "workflow", row.workflow_evidence)
        _append_status_errors(errors, node_type, "chatflow", row.chatflow_evidence)
        if (
            row.workflow_evidence in FOLLOW_UP_REQUIRED_STATUSES
            or row.chatflow_evidence in FOLLOW_UP_REQUIRED_STATUSES
        ) and not _has_markdown_link(row.closure_owner):
            errors.append(f"{node_type} closure owner must link to owning follow-up")
    for node_type in sorted(row_keys - set(expected)):
        errors.append(f"{node_type} evidence row is not a first-class node")
    return errors


def _append_status_errors(errors: list[str], node_type: str, flow: str, status: str) -> None:
    if not status:
        errors.append(f"{node_type} {flow} evidence status is missing")
        return
    if status not in EVIDENCE_STATUSES:
        errors.append(f"{node_type} {flow} evidence status is invalid: {status}")


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(set(cell.replace(" ", "")) <= {"-", ":"} and "-" in cell for cell in cells)


def _normalize_status(value: str) -> str:
    return value.strip().strip("`").lower()


def _has_markdown_link(value: str) -> bool:
    return "](" in value and value.strip().startswith("[")
