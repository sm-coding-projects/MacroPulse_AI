"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MacroPulse AI backend configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ABS API
    abs_api_base_url: str = (
        "https://api.data.abs.gov.au/data"
    )

    # Cache
    cache_ttl_hours: int = 24

    # Database
    database_path: str = "/data/macropulse.db"

    # CORS — comma-separated list of allowed origins
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://frontend:3000",
    ]


settings = Settings()
