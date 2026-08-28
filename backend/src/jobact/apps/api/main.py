"""The first FastAPI app in this codebase.

`create_app()` builds and returns the app so tests can construct fresh
instances (and apply `dependency_overrides`) without importing the
process-wide `app` singleton below.
"""

from fastapi import FastAPI

from jobact.apps.api.error_handlers import register_error_handlers
from jobact.apps.api.middleware.correlation import CorrelationIdMiddleware
from jobact.apps.api.middleware.idempotency import IdempotencyMiddleware
from jobact.apps.api.routers.auth import router as auth_router
from jobact.apps.api.routers.customers import router as customers_router
from jobact.apps.api.routers.media import router as media_router
from jobact.apps.api.routers.reports import router as reports_router
from jobact.apps.api.routers.visits import router as visits_router


def create_app() -> FastAPI:
    app = FastAPI(title="JobAct API", version="1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(customers_router, prefix="/api/v1")
    app.include_router(visits_router, prefix="/api/v1")
    app.include_router(media_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.add_middleware(IdempotencyMiddleware)
    # Added last so it runs first: everything downstream, including the
    # error handlers, sees the correlation id.
    app.add_middleware(CorrelationIdMiddleware)
    register_error_handlers(app)
    return app


app = create_app()
