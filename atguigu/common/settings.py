from functools import lru_cache
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
    api_host: str = Field("localhost", description="访域名限制")
    api_port: int = Field(8001, description="服务端口")
    cors_origins: list[str] = Field(
        ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
        description="限制请求域白名单")
    conversation_idle_timeout_minutes: int = Field(30, description="AI模式下有效的会话超时时间")
    message_merge_delay_ms: int = Field(800, description="轮次收集消息的固定时间窗口")
    internal_service_token: str = Field("customer-internal-token", description="服务内部访问令牌")

    ai_worker_poll_interval_ms: int = Field(100, description="Woker领取Turn时间")
    ai_timeout_seconds: int = Field(30, description="请求AI Service的http超时时间")
    ai_service_url: str = Field("http://127.0.0.1:8002", description="AI Service服务地址")
    ai_worker_max_attempts: int = Field(3, description="当前轮次重试AI Service调用次数")
    ai_worker_retry_delay_seconds: int = Field(2, description="重试延时")

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache  # ["方法对象","方法返回值"]
def get_settings():
    return Settings()  # type:ignore
