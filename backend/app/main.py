from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import devices, streams
from app.config import settings
from app.database import init_db


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    app.include_router(devices.router, prefix="/api")
    app.include_router(streams.router, prefix="/api")
    return app


app = create_app()
