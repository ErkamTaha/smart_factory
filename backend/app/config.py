"""
Configuration settings for Smart Factory Backend
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from datetime import timedelta


class Settings(BaseSettings):

    # Application
    APP_NAME: str = "Smart Factory"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://smartfactory:password123@localhost:5432/smartfactory",
    )

    # MQTT/EMQX Configuration
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_DEFAULT_QOS: int = 1
    MQTT_TOPIC_PREFIX: str = "sf"
    MQTT_TLS_ENABLED: bool = False
    MQTT_CA_CERTS: str = "/app/certs/ca.crt"
    MQTT_USERNAME: str = "smartfactory"
    MQTT_PASSWORD: str = "mqtt123"

    # EMQX HTTP API Configuration
    EMQX_API_URL: str = os.getenv("EMQX_API_URL", "http://localhost:18083")
    EMQX_API_KEY: str = os.getenv("EMQX_API_KEY", "admin")
    EMQX_API_SECRET: str = os.getenv("EMQX_API_SECRET", "smartfactory_admin_2024")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "redis123")

    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
    ]

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    ACCESS_TOKEN_EXPIRE: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
