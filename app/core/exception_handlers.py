from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import BizError, ErrorCode
from app.core.responses import failure


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BizError, _handle_biz_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)


async def _handle_biz_error(_request: Request, exc: Exception) -> JSONResponse:
    error = _as_biz_error(exc)
    return JSONResponse(
        status_code=error.status_code,
        content=failure(error.status_code, error.message),
    )


async def _handle_http_error(_request: Request, exc: Exception) -> JSONResponse:
    error = _as_http_error(exc)
    return JSONResponse(
        status_code=error.status_code,
        content=failure(error.status_code, str(error.detail)),
    )


async def _handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=int(ErrorCode.VALIDATION_ERROR),
        content=failure(int(ErrorCode.VALIDATION_ERROR), "Validation Error", _validation_data(exc)),
    )


async def _handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=int(ErrorCode.INTERNAL_ERROR),
        content=failure(int(ErrorCode.INTERNAL_ERROR), "Internal Server Error"),
    )


def _as_biz_error(exc: Exception) -> BizError:
    if isinstance(exc, BizError):
        return exc
    raise TypeError(f"expected BizError, got {type(exc).__name__}")


def _as_http_error(exc: Exception) -> StarletteHTTPException:
    if isinstance(exc, StarletteHTTPException):
        return exc
    raise TypeError(f"expected HTTPException, got {type(exc).__name__}")


def _validation_data(exc: Exception) -> list[dict[str, Any]]:
    if isinstance(exc, RequestValidationError):
        return cast(list[dict[str, Any]], jsonable_encoder(list(exc.errors())))
    return []
