import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
AGENT_EXECUTION_ROOT = REPOSITORY_ROOT / "app/modules/agent_execution"
AGENT_HARNESS_ROOT = REPOSITORY_ROOT / "app/modules/agent_harness"
AI_ASSISTANT_ROOT = REPOSITORY_ROOT / "app/modules/ai_assistant"
CUSTOMER_ASSISTANT_ROOT = REPOSITORY_ROOT / "app/modules/customer_assistant"


def test_agent_harness_dependency_direction_is_product_neutral() -> None:
    execution_imports = _module_imports(AGENT_EXECUTION_ROOT)
    harness_imports = _module_imports(AGENT_HARNESS_ROOT)
    ai_imports = _module_imports(AI_ASSISTANT_ROOT)
    customer_imports = _module_imports(CUSTOMER_ASSISTANT_ROOT)

    for shared_imports in (execution_imports, harness_imports):
        assert not any(
            imported.startswith(
                (
                    "app.modules.ai_assistant",
                    "app.modules.customer_assistant",
                    "app.modules.workflow",
                    "app.web",
                )
            )
            for imported in shared_imports
        )
    assert not any(imported.startswith("app.modules.customer_assistant") for imported in ai_imports)
    assert not any(imported.startswith("app.modules.ai_assistant") for imported in customer_imports)
    assert "app.modules.agent_execution" in ai_imports
    assert "app.modules.agent_execution" in customer_imports
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
