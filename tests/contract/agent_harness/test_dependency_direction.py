import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
AGENT_HARNESS_ROOT = REPOSITORY_ROOT / "app/modules/agent_harness"
CUSTOMER_ASSISTANT_ROOT = REPOSITORY_ROOT / "app/modules/customer_assistant"


def test_agent_harness_dependency_direction_is_product_neutral() -> None:
    harness_imports = _module_imports(AGENT_HARNESS_ROOT)
    customer_imports = _module_imports(CUSTOMER_ASSISTANT_ROOT)

    assert not any(
        imported.startswith(
            (
                "app.modules.ai_assistant",
                "app.modules.customer_assistant",
                "app.modules.workflow",
                "app.web",
            )
        )
        for imported in harness_imports
    )
    assert not any(imported.startswith("app.modules.ai_assistant") for imported in customer_imports)
    assert "app.modules.agent_harness" in customer_imports


def _module_imports(root: Path) -> set[str]:
    imports: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    return imports
