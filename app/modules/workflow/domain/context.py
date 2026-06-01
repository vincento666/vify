from __future__ import annotations

import re
from typing import Any


_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\.([A-Za-z0-9_.-]+)\s*\}\}")


class ExecutionContext:
    def __init__(self) -> None:
        self._outputs: dict[str, dict[str, Any]] = {}

    def set_output(self, node_key: str, values: dict[str, Any]) -> None:
        self._outputs[node_key] = dict(values)

    def get_output(self, node_key: str) -> dict[str, Any]:
        return dict(self._outputs.get(node_key, {}))

    def find_value(self, variable_name: str) -> Any:
        for values in reversed(self._outputs.values()):
            if variable_name in values:
                return values[variable_name]
        return None

    def render(self, template: str) -> str:
        return _TEMPLATE_PATTERN.sub(self._replace_match, template)

    def _replace_match(self, match: re.Match[str]) -> str:
        node_key, variable_name = match.group(1), match.group(2)
        value = self._outputs.get(node_key, {}).get(variable_name)
        if value is None:
            flat_key = f"{node_key}.{variable_name}"
            for values in reversed(self._outputs.values()):
                value = values.get(flat_key)
                if value is not None:
                    break
        if value is None:
            for values in reversed(self._outputs.values()):
                nested = values.get(node_key)
                if isinstance(nested, dict) and variable_name in nested:
                    value = nested[variable_name]
                    break
        if value is None:
            return ""
        return str(value)
