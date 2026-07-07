from pathlib import Path
import os
import subprocess
import sys


def test_runtime_job_worker_script_exposes_owner_selection() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "runtime_job_worker.py"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=env,
    )

    assert "--owner" in result.stdout
    assert "workflow" in result.stdout
    assert "chatflow" in result.stdout
    assert "both" in result.stdout
    assert "--job-id" in result.stdout
