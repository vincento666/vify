import ast
import importlib
from pathlib import Path
from unittest.mock import Mock, patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CORE_ROOTS = (
    REPOSITORY_ROOT / "app/modules/runtime/domain",
    REPOSITORY_ROOT / "app/modules/runtime/infra",
)


def test_runtime_job_core_is_owned_by_product_neutral_runtime_module() -> None:
    repository_module = importlib.import_module("app.modules.runtime.infra.runtime_job_repository")
    worker_module = importlib.import_module("app.modules.runtime.domain.runtime_job_worker")

    assert hasattr(repository_module, "RuntimeJobRepository")
    assert hasattr(worker_module, "RuntimeJobWorker")
    assert not any(
        imported.startswith(
            (
                "app.modules.ai_assistant",
                "app.modules.customer_assistant",
                "app.modules.workflow",
            )
        )
        for imported in set().union(*(_module_imports(root) for root in RUNTIME_CORE_ROOTS))
    )


def test_runtime_job_handler_registry_dispatches_by_owner_type() -> None:
    registry_module = importlib.import_module("app.modules.runtime.domain.runtime_job_registry")
    registry = registry_module.RuntimeJobHandlerRegistry()
    handled: list[int] = []
    registry.register("AI_ASSISTANT", lambda job: handled.append(int(job["run_id"])))

    registry.handle({"owner_type": "AI_ASSISTANT", "run_id": 42})

    assert registry.owner_types == ("AI_ASSISTANT",)
    assert handled == [42]


def test_runtime_composition_registers_all_product_adapters() -> None:
    from app.modules.runtime.composition import build_runtime_job_worker

    with patch(
        "app.modules.runtime.composition.build_registered_runtime_job_worker",
        return_value=Mock(),
    ) as build_worker:
        build_runtime_job_worker(Mock(), owner="all")

    registry = build_worker.call_args.kwargs["registry"]
    assert registry.owner_types == ("AI_ASSISTANT", "CHATFLOW", "WORKFLOW")


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
