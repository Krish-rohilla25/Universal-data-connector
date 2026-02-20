"""
Application configuration loaded from environment variables or .env file.
We use pydantic-settings so every setting is typed and validated on startup.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Universal Data Connector"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # How many records to return by default before voice rules kick in
    MAX_RESULTS: int = 10
    # Stricter cap used when the caller signals voice mode
    MAX_VOICE_RESULTS: int = 5

    # Where the JSON fixture files live (relative to the working directory)
    DATA_DIR: str = "data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single module-level instance – import this everywhere instead of re-creating
settings = Settings()
