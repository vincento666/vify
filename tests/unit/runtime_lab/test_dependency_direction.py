from pathlib import Path

from app.modules.runtime_lab.domain.dependency_guard import find_runtime_lab_imports


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_workflow_modules_do_not_import_runtime_lab() -> None:
    offenders = find_runtime_lab_imports(REPO_ROOT / "app/modules/workflow")

    assert offenders == []


def test_import_scan_detects_runtime_lab_imports(tmp_path: Path) -> None:
    bad_module = tmp_path / "bad_workflow.py"
    bad_module.write_text(
        "from app.modules.runtime_lab.domain.service import RuntimeLabService\n",
        encoding="utf-8",
    )

    offenders = find_runtime_lab_imports(tmp_path)

    assert offenders == [str(bad_module)]
