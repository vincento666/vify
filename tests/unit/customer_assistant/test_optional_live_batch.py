import tempfile
import unittest
from pathlib import Path

from app.modules.customer_assistant.eval.live_batch import run_optional_live_batch
from app.modules.customer_assistant.eval.synthetic_cases import synthetic_cases


class CustomerAssistantOptionalLiveBatchTest(unittest.TestCase):
    def test_live_batch_skips_without_explicit_env_and_writes_redacted_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_optional_live_batch(
                synthetic_cases()[:2],
                env={},
                output_dir=Path(tmp),
            )

            evidence = Path(tmp) / "live-batch-skipped.md"

            self.assertEqual(result.status, "skipped")
            self.assertEqual(result.live_model_calls, 0)
            self.assertTrue(evidence.exists())
            self.assertIn("skipped", evidence.read_text())
            self.assertNotIn("sk-test", evidence.read_text())


if __name__ == "__main__":
    unittest.main()
