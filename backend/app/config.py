from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Smart Factory API"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_topic_prefix: str = "sf"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()