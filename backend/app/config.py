# 应用配置中心。
# 所有配置都可以通过 LLVP_<字段名> 环境变量覆盖，例如：
# - LLVP_PORT=8001 覆盖 port；
# - LLVP_DATABASE_URL=sqlite:////data/llvp.db 覆盖 database_url。
# 未设置环境变量时使用这里的默认值，适合直接在本机运行。
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLVP_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Low-Latency Live Video Platform"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    database_url: str = "sqlite:///./llvp.db"

    # zlm_base_url 是 FastAPI 服务访问 ZLM API 的地址。
    # Docker 中该值会被覆盖为 http://zlm，而不是浏览器使用的宿主机地址。
    zlm_base_url: str = "http://127.0.0.1:8080"
    zlm_secret: str = "change-me-via-LLVP_ZLM_SECRET"

    # public_* 用于拼装返回给浏览器的播放地址。
    # 浏览器和后端位于不同网络命名空间时，这两个概念必须分开配置。
    public_zlm_host: str = "127.0.0.1"
    public_zlm_http_port: int = 8080
    public_zlm_rtmp_port: int = 1935

    default_app: str = "live"


@lru_cache
def get_settings() -> Settings:
    # 配置只在进程内读取一次，避免不同模块重复解析环境变量后得到不一致的结果。
    return Settings()


settings = get_settings()
