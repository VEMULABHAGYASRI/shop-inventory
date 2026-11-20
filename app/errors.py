"""Application errors and the single, consistent error response format.

Every error the API returns looks like this:

    {"error": {"code": "not_found",
               "message": "Item 42 not found",
               "details": [],
               "request_id": "a1b2c3d4"}}

Services raise the exception classes below. They know nothing about HTTP;
the handlers registered in `register_error_handlers` translate them.
"""
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import get_logger, request_id_var

logger = get_logger("errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class InsufficientStockError(AppError):
    status_code = 409
    code = "insufficient_stock"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"


def error_body(code: str, message: str, details: list | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id_var.get(),
        }
    }


def error_response(status: int, code: str, message: str, details=None, headers=None):
    return JSONResponse(
        status_code=status, content=error_body(code, message, details), headers=headers
    )


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.info("%s: %s", exc.code, exc.message)
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return error_response(exc.status_code, exc.code, exc.message, exc.details, headers)


async def _validation_handler(request: Request, exc: RequestValidationError):
    # Turn Pydantic's verbose errors into a short list of {field, message}.
    details = [
        {
            "field": ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path")),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return error_response(422, "validation_error", "Invalid input", details)


async def _http_error_handler(request: Request, exc: StarletteHTTPException):
    # Covers framework-level errors like unknown URLs (404) or wrong method (405).
    codes = {404: "not_found", 405: "method_not_allowed"}
    return error_response(
        exc.status_code, codes.get(exc.status_code, "http_error"), str(exc.detail)
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    # Unexpected exceptions are caught by the logging middleware in main.py,
    # which logs the traceback and returns a generic 500 in the same format.
