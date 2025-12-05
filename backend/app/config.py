"""
Configuration settings for Smart Factory Backend
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from datetime import timedelta


class Settings(BaseSettings):
    # Application
    app_name: str = "Smart Factory"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    environment: str = "development"

    # Database
    database_url: str = (
        "postgresql+asyncpg://smartfactory:password123@postgres:5432/smartfactory"
    )

    # MQTT
    mqtt_broker_host: str = "mosquitto"
    mqtt_broker_port: int = 1883
    mqtt_username: str = "smartfactory"
    mqtt_password: str = "mqtt123"
    mqtt_topic_prefix: str = "sf"

    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
    ]

    # Redis (optional)
    redis_url: str = "redis://redis:6379"

    SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-me")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    ACCESS_TOKEN_EXPIRE = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
