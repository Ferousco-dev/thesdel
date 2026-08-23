from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.announcements.router import router as announcements_router
from app.auth.router import router as auth_router
from app.classes.router import router as classes_router
from app.litheral.study.router import router as litheral_study_router
from app.shared import db, redis_client
from app.timetable.router import router as timetable_router
from app.usage.router import router as usage_router
from app.shared.config import get_settings
from app.shared.errors import AppError
from app.shared.logging import configure_logging, get_logger
from app.shared.middleware import request_context_middleware
from app.users.router import router as users_router

configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("app.startup")
    await db.ensure_indexes()
    yield
    logger.info("app.shutdown")
    await db.close_client()
    await redis_client.close_redis()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Thesdel API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_local else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_context_middleware)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # Internal detail never reaches the client — only error_code + safe
        # message, per docs/API.md §4. Full detail already went to logs via
        # the request-context middleware's exception logging.
        request_id = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "request_id": request_id,
                "details": exc.details,
            },
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        mongo_ok = await db.ping()
        redis_ok = await redis_client.ping()
        ok = mongo_ok and redis_ok
        return JSONResponse(
            status_code=200 if ok else 503,
            content={"mongo": mongo_ok, "redis": redis_ok},
        )

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(classes_router)
    app.include_router(timetable_router)
    app.include_router(announcements_router)
    app.include_router(usage_router)
    app.include_router(litheral_study_router)

    return app


app = create_app()
