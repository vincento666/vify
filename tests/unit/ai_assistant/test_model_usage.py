import unittest


class ModelUsageNormalizationTest(unittest.TestCase):
    def test_missing_provider_usage_remains_unknown_instead_of_provider_zero(self) -> None:
        from app.modules.ai_assistant.domain.live_model import _usage
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage

        raw = _usage({"choices": []})
        usage = normalize_model_usage(raw)

        self.assertEqual(raw, {})
        self.assertEqual(usage.usage_source, "unknown")
        self.assertEqual(usage.total_tokens, 0)

    def test_provider_usage_preserves_optional_breakouts_without_double_counting_total(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage

        usage = normalize_model_usage(
            {
                "prompt_tokens": 100,
                "completion_tokens": 40,
                "total_tokens": 140,
                "prompt_tokens_details": {"cached_tokens": 60},
                "completion_tokens_details": {"reasoning_tokens": 25},
            }
        )

        self.assertEqual(usage.input_tokens, 100)
        self.assertEqual(usage.output_tokens, 40)
        self.assertEqual(usage.cache_read_tokens, 60)
        self.assertIsNone(usage.cache_write_tokens)
        self.assertEqual(usage.reasoning_tokens, 25)
        self.assertEqual(usage.total_tokens, 140)
        self.assertEqual(usage.usage_source, "provider")

    def test_missing_total_uses_only_input_plus_output_and_keeps_unknown_optional_null(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage

        usage = normalize_model_usage({"input_tokens": 7, "output_tokens": 3})

        self.assertEqual(usage.total_tokens, 10)
        self.assertIsNone(usage.cache_read_tokens)
        self.assertIsNone(usage.cache_write_tokens)
        self.assertIsNone(usage.reasoning_tokens)

    def test_negative_provider_tokens_are_rejected(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage

        with self.assertRaisesRegex(ValueError, "non-negative"):
            normalize_model_usage({"prompt_tokens": -1, "completion_tokens": 2})

    def test_boolean_and_fractional_tokens_are_rejected_instead_of_coerced(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage

        for invalid in (True, 1.5, "1.5"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "integers"):
                    normalize_model_usage({"prompt_tokens": invalid})

    def test_non_finite_provider_cost_is_rejected(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage

        for invalid in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "finite"):
                    normalize_model_usage({"cost": invalid})


if __name__ == "__main__":
    unittest.main()
