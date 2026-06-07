import ast
from pathlib import Path


RUNTIME_LAB_IMPORT_PREFIX = "app.modules.runtime_lab"


def find_runtime_lab_imports(root: Path) -> list[str]:
    offenders: list[str] = []
    if not root.exists():
        return offenders
    for path in sorted(root.rglob("*.py")):
        if _imports_runtime_lab(path):
            offenders.append(str(path))
    return offenders


def _imports_runtime_lab(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(_is_runtime_lab_import(alias.name) for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom):
            if node.module and _is_runtime_lab_import(node.module):
                return True
    return False


def _is_runtime_lab_import(module: str) -> bool:
    return module == RUNTIME_LAB_IMPORT_PREFIX or module.startswith(f"{RUNTIME_LAB_IMPORT_PREFIX}.")
