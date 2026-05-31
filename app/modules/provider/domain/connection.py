from dataclasses import dataclass
from time import monotonic
from typing import Any

import httpx


@dataclass(frozen=True)
class ConnectionTestResult:
    success: bool
    latency_ms: int | None
    model_count: int | None
    error_message: str | None

    def to_response(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "latencyMs": self.latency_ms,
            "modelCount": self.model_count,
            "errorMessage": self.error_message,
        }


class ProviderConnectionTester:
    def test(
        self,
        provider_type: str,
        base_url: str,
        auth_config: dict[str, Any],
    ) -> ConnectionTestResult:
        start = monotonic()
        if base_url == "mock://success":
            return ConnectionTestResult(True, self._elapsed_ms(start), 2, None)
        if base_url == "mock://failure":
            return ConnectionTestResult(False, self._elapsed_ms(start), None, "mock connection failure")

        try:
            response = httpx.get(
                f"{base_url.rstrip('/')}/models",
                headers=self._auth_headers(provider_type, auth_config),
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
            model_count = len(payload.get("data", [])) if isinstance(payload, dict) else None
            return ConnectionTestResult(True, self._elapsed_ms(start), model_count, None)
        except Exception as exc:
            return ConnectionTestResult(False, self._elapsed_ms(start), None, str(exc))

    def _auth_headers(self, provider_type: str, auth_config: dict[str, Any]) -> dict[str, str]:
        api_key = str(auth_config.get("api_key") or auth_config.get("apiKey") or "")
        if provider_type == "ANTHROPIC":
            return {"x-api-key": api_key} if api_key else {}
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def _elapsed_ms(self, start: float) -> int:
        return max(0, int((monotonic() - start) * 1000))
