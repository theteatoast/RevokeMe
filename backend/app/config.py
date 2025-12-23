from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    eth_rpc_url: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
