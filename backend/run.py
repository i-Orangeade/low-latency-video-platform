import uvicorn

from app.config import settings


if __name__ == "__main__":
    # 开发环境直接执行 python run.py 即可启动。
    # reload=True 时 uvicorn 会在代码变化后自动重启，适合学习调试。
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
