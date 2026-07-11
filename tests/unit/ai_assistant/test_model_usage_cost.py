import unittest
from decimal import Decimal


class ModelUsageCostResolverTest(unittest.TestCase):
    def test_provider_actual_cost_wins_over_configured_price(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import (
            ModelPrice,
            VersionedCostResolver,
            normalize_model_usage,
        )

        resolver = VersionedCostResolver(
            version="prices-2026-07",
            prices={
                ("openrouter", "qwen/test"): ModelPrice(
                    input_usd_per_million=Decimal("1"),
                    output_usd_per_million=Decimal("2"),
                )
            },
        )
        result = resolver.resolve(
            "openrouter",
            "qwen/test",
            normalize_model_usage(
                {"prompt_tokens": 100, "completion_tokens": 20, "cost": "0.0042"}
            ),
        )

        self.assertEqual(result.effective_cost_usd, Decimal("0.0042000000"))
        self.assertEqual(result.cost_source, "provider")
        self.assertIsNone(result.pricing_version)

    def test_versioned_estimate_prices_cache_as_input_subset_and_reasoning_as_output_subset(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import (
            ModelPrice,
            VersionedCostResolver,
            normalize_model_usage,
        )

        resolver = VersionedCostResolver(
            version="prices-2026-07",
            prices={
                ("openrouter", "qwen/test"): ModelPrice(
                    input_usd_per_million=Decimal("1"),
                    output_usd_per_million=Decimal("2"),
                    cache_read_usd_per_million=Decimal("0.1"),
                )
            },
        )
        result = resolver.resolve(
            "openrouter",
            "qwen/test",
            normalize_model_usage(
                {
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                    "total_tokens": 1500,
                    "cache_read_tokens": 400,
                    "reasoning_tokens": 300,
                }
            ),
        )

        self.assertEqual(result.effective_cost_usd, Decimal("0.0016400000"))
        self.assertEqual(result.cost_source, "price_table")
        self.assertEqual(result.pricing_version, "prices-2026-07")

    def test_missing_price_is_unknown_null_not_zero(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import (
            VersionedCostResolver,
            normalize_model_usage,
        )

        result = VersionedCostResolver(version="empty", prices={}).resolve(
            "unknown",
            "missing",
            normalize_model_usage({"total_tokens": 10}),
        )

        self.assertIsNone(result.effective_cost_usd)
        self.assertEqual(result.cost_source, "unknown")

    def test_total_only_usage_cannot_be_estimated_as_zero(self) -> None:
        from app.modules.ai_assistant.domain.model_usage import (
            ModelPrice,
            VersionedCostResolver,
            normalize_model_usage,
        )

        result = VersionedCostResolver(
            version="v1",
            prices={
                ("openrouter", "qwen/total-only"): ModelPrice(
                    input_usd_per_million=Decimal("1"),
                    output_usd_per_million=Decimal("2"),
                )
            },
        ).resolve(
            "openrouter",
            "qwen/total-only",
            normalize_model_usage({"total_tokens": 10}),
        )

        self.assertIsNone(result.effective_cost_usd)
        self.assertEqual(result.cost_source, "unknown")

    def test_provider_actual_cost_does_not_parse_broken_price_configuration(self) -> None:
        import os
        from unittest.mock import patch

        from app.modules.ai_assistant.domain.model_usage import (
            normalize_model_usage,
            resolve_configured_model_cost,
        )

        with patch.dict(os.environ, {"HIFY_AI_ASSISTANT_MODEL_PRICES_JSON": "not-json"}):
            result = resolve_configured_model_cost(
                "openrouter",
                "qwen/actual",
                normalize_model_usage({"total_tokens": 10, "cost": "0.001"}),
            )

        self.assertEqual(result.cost_source, "provider")
        self.assertEqual(result.effective_cost_usd, Decimal("0.0010000000"))


if __name__ == "__main__":
    unittest.main()
