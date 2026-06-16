from __future__ import annotations

import re
from typing import Any


_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\.([A-Za-z0-9_.-]+)\s*\}\}")
_LOCAL_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class ExecutionContext:
    def __init__(self) -> None:
        self._outputs: dict[str, dict[str, Any]] = {}
        self._scopes: dict[str, dict[str, Any]] = {
            "input": {},
            "external": {},
            "flow": {},
            "global": {},
            "conversation": {},
            "user": {},
            "channel": {},
            "sys": {},
        }
        self._local_values: dict[str, Any] = {}

    def set_output(self, node_key: str, values: dict[str, Any]) -> None:
        self._outputs[node_key] = dict(values)

    def set_scope_value(self, scope: str, variable_name: str, value: Any, write_mode: str = "set") -> Any:
        normalized_scope = scope.strip().lower()
        if normalized_scope not in self._scopes:
            raise ValueError(f"Unsupported variable scope: {scope}")
        values = self._scopes[normalized_scope]
        if write_mode == "clear":
            values.pop(variable_name, None)
            return None
        if write_mode == "append":
            current = values.get(variable_name)
            if isinstance(current, list):
                current.append(value)
                values[variable_name] = current
                return current
            if current is None:
                values[variable_name] = [value]
                return values[variable_name]
            values[variable_name] = f"{current}{value}"
            return values[variable_name]
        values[variable_name] = value
        return value

    def get_output(self, node_key: str) -> dict[str, Any]:
        return dict(self._outputs.get(node_key, {}))

    def outputs_snapshot(self) -> dict[str, dict[str, Any]]:
        return {node_key: dict(values) for node_key, values in self._outputs.items()}

    def get_scope(self, scope: str) -> dict[str, Any]:
        return dict(self._scopes.get(scope.strip().lower(), {}))

    def load_scopes(self, scopes: dict[str, Any]) -> None:
        for scope, values in scopes.items():
            normalized_scope = str(scope).strip().lower()
            if normalized_scope not in self._scopes or not isinstance(values, dict):
                continue
            self._scopes[normalized_scope] = dict(values)

    def set_local_values(self, values: dict[str, Any]) -> None:
        self._local_values = dict(values)

    def clear_local_values(self) -> None:
        self._local_values = {}

    def scopes_snapshot(self) -> dict[str, dict[str, Any]]:
        return {scope: dict(values) for scope, values in self._scopes.items()}

    def find_value(self, variable_name: str) -> Any:
        for values in reversed(self._outputs.values()):
            if variable_name in values:
                return values[variable_name]
        return None

    def render(self, template: str) -> str:
        with_local_values = _LOCAL_TEMPLATE_PATTERN.sub(self._replace_local_match, template)
        return _TEMPLATE_PATTERN.sub(self._replace_match, with_local_values)

    def _replace_local_match(self, match: re.Match[str]) -> str:
        variable_name = match.group(1)
        if variable_name not in self._local_values:
            return match.group(0)
        value = self._local_values.get(variable_name)
        if value is None:
            return ""
        return str(value)

    def _replace_match(self, match: re.Match[str]) -> str:
        node_key, variable_name = match.group(1), match.group(2)
        if node_key in self._scopes:
            value = self._scopes[node_key].get(variable_name)
            if value is not None:
                return str(value)
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
