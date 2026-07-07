from __future__ import annotations

import unittest
from pathlib import Path

from app.main import app


class RunsV2AliasRetirementTest(unittest.TestCase):
    """Spec 213.X: physical runtime v2 entrypoint is `/runs`, not `/runs-v2`."""

    def test_backend_route_table_no_longer_exposes_runs_v2_alias(self) -> None:
        route_paths = {getattr(route, "path", "") for route in app.routes}

        self.assertIn("/api/v1/workflows/{workflow_id}/runs", route_paths)
        self.assertIn("/api/v1/chatflows/{chatflow_id}/runs", route_paths)
        self.assertNotIn("/api/v1/workflows/{workflow_id}/runs-v2", route_paths)
        self.assertNotIn("/api/v1/chatflows/{chatflow_id}/runs-v2", route_paths)

    def test_source_and_gate_entrypoints_do_not_reference_runs_v2_url(self) -> None:
        offenders: list[str] = []
        current_file = Path(__file__).resolve()
        for root_name in (
            "app",
            "frontend/src",
            "frontend/e2e",
            "tests/acceptance",
            "tests/contract",
            "tests/integration",
        ):
            root = _repo_root() / root_name
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.resolve() == current_file or path.suffix not in {".py", ".ts", ".vue", ".js", ".mjs"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if "runs-v2" in line:
                        offenders.append(f"{path.relative_to(_repo_root())}:{line_no}: {line.strip()}")

        self.assertEqual(offenders, [])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


if __name__ == "__main__":
    unittest.main()
