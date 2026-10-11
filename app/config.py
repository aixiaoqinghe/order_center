from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """应用配置,从 .env 读取"""

    # 数据库配置
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str
    DB_NAME: str = "order_center"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """拼出 SQLAlchemy 用的字符串"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # Redis 配置
    REDIS_HOST: str="localhost"
    REDIS_PORT: int=6379
    REDIS_PASSWORD: str=""

    # RabbitMQ 配置
    RABBITMQ_HOST: str="localhost"
    RABBITMQ_PORT: int=5672
    RABBITMQ_LOGIN: str="guest"
    RABBITMQ_PASSWORD: str="guest"
    RABBITMQ_VHOST: str="/"

    # LLM 配置
    LLM_BASE_URL: str
    LLM_API_KEY: str
    LLM_MODEL: str
    LLM_TIMEOUT_CONNECT: float = 5.0
    LLM_TIMEOUT_READ: float = 30.0
    LLM_TIMEOUT_WRITE: float = 10.0
    LLM_TIMEOUT_POOL: float = 5.0

settings = Settings()        # 全局单例，其他文件 import settings 即可