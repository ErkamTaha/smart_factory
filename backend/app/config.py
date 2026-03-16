"""
Configuration settings for Smart Factory Backend
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from datetime import timedelta


class Settings(BaseSettings):

    # Application
    APP_NAME: str = "Smart Factory"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database (no default — must be provided via .env or environment)
    DATABASE_URL: str

    # MQTT/EMQX Configuration
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_DEFAULT_QOS: int = 1
    MQTT_TOPIC_PREFIX: str = "sf"
    MQTT_TLS_ENABLED: bool = False
    MQTT_CA_CERTS: str = "/app/certs/ca.crt"
    MQTT_USERNAME: str
    MQTT_PASSWORD: str

    # EMQX HTTP API Configuration
    EMQX_API_URL: str = "http://localhost:18083"
    EMQX_API_KEY: str
    EMQX_API_SECRET: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Security (no defaults for secrets — must be provided)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def ACCESS_TOKEN_EXPIRE(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if v in ("your-secret-key-change-in-production", "changeme", "secret"):
            raise ValueError(
                "SECRET_KEY must be changed from the placeholder value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        return v

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
