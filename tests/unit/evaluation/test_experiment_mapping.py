import unittest

from app.modules.evaluation.domain.mapping import normalize_experiment_mapping


class ExperimentMappingTest(unittest.TestCase):
    def test_defaults_to_input_expected_output_and_target_output(self) -> None:
        mapping = normalize_experiment_mapping(
            fields=["input", "expectedOutput"],
            target_field_mapping={},
            evaluator_field_mapping={},
            item_concurrency=0,
            item_retry_count=-1,
        )

        self.assertEqual(mapping.target_field_mapping, {"userMessage": "input"})
        self.assertEqual(mapping.evaluator_field_mapping, {
            "expectedOutput": "expectedOutput",
            "actualOutput": "__target.output",
        })
        self.assertEqual(mapping.item_concurrency, 1)
        self.assertEqual(mapping.item_retry_count, 0)

    def test_rejects_unknown_dataset_field_references(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown Eval Set field"):
            normalize_experiment_mapping(
                fields=["input", "expectedOutput"],
                target_field_mapping={"userMessage": "missing_field"},
                evaluator_field_mapping={"expectedOutput": "expectedOutput"},
                item_concurrency=1,
                item_retry_count=0,
            )


if __name__ == "__main__":
    unittest.main()
