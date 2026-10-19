from functools import lru_cache, cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str = Field(
        "postgresql+psycopg://customer_service:customer_service@192.168.200.199:5432/customer_service",
        description="pgsql数据库连接")

    jwt_secret: str = Field("ecommerce-secret", description="jwt加密的秘钥")
    jwt_algorithm: str = Field("HS256", description="jwt加密的算法")
    api_host: str = Field("域名", description="访域名限制")
    api_port: int = Field("端口", description="服务端口")
    cors_origins: list[str] = Field(
        ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
        description="限制请求域白名单")
    conversation_idle_timeout_minutes: int = Field(30, description="AI模式下有效的会话超时时间")
    message_merge_delay_ms: int = Field(800, description="轮次收集消息的固定时间窗口")

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache  # ["方法对象","方法返回值"]
def get_settings():
    return Settings()  # type:ignore
