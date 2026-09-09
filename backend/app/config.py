from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLVP_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "low-latency-video-platform"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    database_url: str = "sqlite:///./llvp.db"

    zlm_base_url: str = "http://127.0.0.1:8080"
    zlm_secret: str = "change-me-via-LLVP_ZLM_SECRET"
    public_zlm_host: str = "127.0.0.1"
    public_zlm_http_port: int = 8080
    public_zlm_rtmp_port: int = 1935

    default_app: str = "live"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
