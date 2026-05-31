from typing import Any


def success(data: Any, message: str = "success") -> dict[str, Any]:
    return {
        "code": 200,
        "message": message,
        "data": data,
    }


def failure(code: int, message: str, data: Any = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
    }
