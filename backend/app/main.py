from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, streams, video_sources
from app.config import settings
from app.database import init_db, run_migrations
from app.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    run_migrations()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.auth_service = AuthService()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        # 管理会话通过前端同源 /api 代理发送，不允许跨域请求携带 Cookie。
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    app.include_router(video_sources.router, prefix="/api")
    app.include_router(streams.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    return app


app = create_app()
