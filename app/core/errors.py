from enum import IntEnum


class ErrorCode(IntEnum):
    BAD_REQUEST = 400
    NOT_FOUND = 404
    VALIDATION_ERROR = 422
    INTERNAL_ERROR = 500


class BizError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = int(code)
        self.message = message
