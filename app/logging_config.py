"""Logging setup.

Each HTTP request gets a short random id. It is stored in a context variable,
added to every log line written while handling that request, and returned to
the client in the X-Request-ID header and in error bodies. That lets you match
a user's error report to the exact log lines.
"""
import contextvars
import logging

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"
        )
    )
    root = logging.getLogger("inventory")
    root.handlers = [handler]
    root.setLevel(level.upper())
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """All app loggers live under the 'inventory' namespace."""
    return logging.getLogger(f"inventory.{name}")
