from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INVENTORY = REPO_ROOT / "artifacts/slices/023-integration-architecture-deepening/023.1/inventory.md"


def test_023_1_inventory_covers_required_shallow_seams() -> None:
    text = INVENTORY.read_text(encoding="utf-8")

    required_sections = [
        "Router RequestContext Construction Sites",
        "Frontend Request And Raw Fetch Sites",
        "Observe Report Debug Projections",
        "FlowGraph Node Fact Spread",
        "Resource Invocation Paths",
        "Persistence Lifecycle Runtime DDL",
        "Anti-Overdesign Checklist",
    ]
    for section in required_sections:
        assert f"## {section}" in text


def test_023_1_inventory_records_deepening_decision_for_each_area() -> None:
    text = INVENTORY.read_text(encoding="utf-8")

    for marker in [
        "Decision: introduce Host Integration Shell",
        "Decision: introduce frontend host request adapter",
        "Decision: introduce Runtime Evidence facade",
        "Decision: introduce FlowGraph Node Catalog",
        "Decision: introduce Unified Resource Invocation",
        "Decision: split persistence lifecycle modes",
    ]:
        assert marker in text
