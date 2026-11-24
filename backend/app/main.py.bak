from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, auth, brands, health, products
from app.core.config import get_settings
from app.db import models  # noqa: F401  (importing registers the tables on Base)
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development and tests build tables directly. Production uses `alembic upgrade head`.
    if get_settings().app_env != "production":
        Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AdBanao", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,  # the sign-in cookie
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(brands.router)
    app.include_router(products.router)
    return app


app = create_app()
