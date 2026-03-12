from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Get the directory where this config.py is located
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DATABASE_URL: str

    # Point directly to the .env in the root folder, no matter where we start the server!
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

# Instantiate the settings
settings = Settings() # type: ignore
