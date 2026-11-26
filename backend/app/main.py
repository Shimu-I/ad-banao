from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, auth, brands, health, products
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.request_context import REQUEST_ID_HEADER
from app.db import models  # noqa: F401  (importing registers the tables on Base)
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development and tests build tables directly. Production uses `alembic upgrade head`.
    if get_settings().app_env != "production":
        Base.metadata.create_all(bind=engine)
    yield


API_PREFIX = "/api/v1"  # change this, never the individual routes, when the API gets a version 2


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    app = FastAPI(title="AdBanao", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        # Dev convenience: the page may be opened as localhost or 127.0.0.1 on any port.
        allow_origin_regex=(
            None
            if settings.app_env == "production"
            else r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
        ),
        allow_credentials=True,  # the sign-in cookie
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],  # so the page can show the id when something fails
    )
    app.add_middleware(RequestIdMiddleware)  # added last = outermost, so even preflight answers carry an id
    install_error_handlers(app)
    app.include_router(health.router)  # /health stays at the root: hosting services and monitors probe it
    for router in (auth.router, admin.router, brands.router, products.router):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
