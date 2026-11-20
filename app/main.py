"""Application factory: builds and wires the FastAPI app.

Run with:  uvicorn --factory app.main:create_app

`create_app` takes its collaborators as arguments (settings, notifier) instead
of reading globals. Production passes nothing and gets the real ones; tests
pass an in-memory database and a fake notifier.
"""
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.database import init_db, make_engine, make_session_factory
from app.errors import error_response, register_error_handlers
from app.logging_config import configure_logging, get_logger, request_id_var
from app.notifications import Notifier, build_notifier
from app.routes import auth, health, items, movements

logger = get_logger("http")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(settings: Settings | None = None, notifier: Notifier | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Shop Inventory")
    app.state.settings = settings
    app.state.notifier = notifier or build_notifier(settings)

    engine = make_engine(settings.database_url)
    init_db(engine)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)

    register_error_handlers(app)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Last line of defence: log the full traceback, but never leak
            # internals to the client.
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            response = error_response(500, "internal_error", "Something went wrong")
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.0f ms)",
            request.method, request.url.path, response.status_code, elapsed_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(items.router)
    app.include_router(movements.router)

    # The web UI. Mounted last so the /api routes above take priority.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
