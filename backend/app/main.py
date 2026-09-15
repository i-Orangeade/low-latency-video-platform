# FastAPI 应用入口。
# 该模块负责组装完整后端：创建应用、配置跨域、初始化数据库并注册业务路由。
# 阅读顺序建议是 config.py -> database.py -> models -> schemas -> api -> services。
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import devices, streams
from app.config import settings
from app.database import init_db


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    # 开发环境前端运行在 5173，后端运行在 8000，端口不同会产生浏览器跨域限制。
    # 当前项目统一放开跨域便于学习；真实生产环境应只允许可信前端域名。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 应用开始接收请求前执行 init_db：
    # - 根据 ORM 模型创建缺失的数据表；
    # - 对 SQLite 设置 WAL、超时等运行参数。
    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    # 所有业务接口统一挂载到 /api 前缀。
    # 这样 Vite 开发代理和 Nginx 生产代理都只需要转发一个固定的 URL 前缀。
    app.include_router(devices.router, prefix="/api")
    app.include_router(streams.router, prefix="/api")
    return app


# uvicorn 启动时直接引用 create_app() 生成的实例。
app = create_app()
