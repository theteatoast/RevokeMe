from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # RPC Configuration
    eth_rpc_url: str = "https://eth.llamarpc.com"  # Free public RPC
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Optional Etherscan API key for enhanced spender analysis
    etherscan_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
