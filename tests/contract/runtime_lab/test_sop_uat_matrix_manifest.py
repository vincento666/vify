import json
import unittest
from pathlib import Path


MATRIX_PATH = Path("frontend/e2e/fixtures/sop-matrix/runtime-v2-12-case-matrix.json")


class SopUatMatrixManifestContractTest(unittest.TestCase):
    def test_runtime_v2_sop_matrix_defines_12_cases_and_four_evidence_dimensions(self) -> None:
        self.assertTrue(MATRIX_PATH.exists(), f"missing SOP UAT matrix manifest: {MATRIX_PATH}")

        matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        cases = matrix.get("cases")
        self.assertIsInstance(cases, list)
        self.assertEqual(len(cases), 12)

        expected_dimensions = {"apiResponse", "eventStream", "taskPanel", "refreshRecovery"}
        case_ids = set()
        for case in cases:
            with self.subTest(case=case.get("id")):
                case_ids.add(case["id"])
                self.assertTrue(case.get("title"))
                self.assertTrue(case.get("acceptance"))
                self.assertEqual(set(case.get("evidenceDimensions") or []), expected_dimensions)

        self.assertEqual(
            case_ids,
            {
                "strong-intent-start",
                "active-sop-continue",
                "interruptible-switch",
                "resume-offer-after-new-sop-complete",
                "resume-original-child-run",
                "non-interruptible-switch-rejected",
                "explicit-resume-signal",
                "clarify-does-not-create-run",
                "faq-rag-no-state-pollution",
                "agent-fallback-no-state-replacement",
                "handoff-preserves-runtime-refs",
                "multiple-child-runs-aggregate-only",
            },
        )


if __name__ == "__main__":
    unittest.main()
