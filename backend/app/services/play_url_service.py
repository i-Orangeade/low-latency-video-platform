from app.config import settings


def build_http_flv_url(stream_id: str, app: str | None = None) -> str:
    app_name = app or settings.default_app
    host = settings.public_zlm_host
    http_port = settings.public_zlm_http_port
    return f"http://{host}:{http_port}/{app_name}/{stream_id}.live.flv"
