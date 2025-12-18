from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Yandex Message Queue
    YMQ_ACCESS_KEY_ID: Optional[str] = None
    YMQ_SECRET_ACCESS_KEY: Optional[str] = None
    YMQ_QUEUE_PREFIX: str = "https://message-queue.api.cloud.yandex.net/b1g1qglub2qdq4p5ibol/g6000000a3u94706n1"
    YMQ_QUEUE_DEFAULT: str = "task-tracker-queue"
    YMQ_REGION: str = "ru-central1"
    
    # App settings
    APP_NAME: str = "Virt Backend"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./test.db"
    
    class Config:
        env_file = ".env"

settings = Settings()
