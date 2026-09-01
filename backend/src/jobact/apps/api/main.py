"""The JobAct demo API.

Trimmed for the local-demo downgrade: three stateless endpoints
(`/api/v1/demo/*`) are the entire surface. There is no database, no
session, no queue -- see `docs/architecture/overview.md` and
`docs/adr/000X-local-demo-downgrade.md` for what moved to the browser and
why. `create_app()` builds and returns the app so tests can construct
fresh instances without importing the process-wide `app` singleton below.
"""

from fastapi import FastAPI

from jobact.apps.api.error_handlers import register_error_handlers
from jobact.apps.api.middleware.correlation import CorrelationIdMiddleware
from jobact.apps.api.routers.demo import router as demo_router


def create_app() -> FastAPI:
    app = FastAPI(title="JobAct Demo API", version="1")
    app.include_router(demo_router, prefix="/api/v1")
    # Added last so it runs first: everything downstream, including the
    # error handlers, sees the correlation id.
    app.add_middleware(CorrelationIdMiddleware)
    register_error_handlers(app)
    return app


app = create_app()
