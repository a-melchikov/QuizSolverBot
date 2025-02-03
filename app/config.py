from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.logger_setup import get_logger

BASE_DIR = Path(__file__).parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"
logger = get_logger(__name__)

logger.info(f"Base directory: {BASE_DIR}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    TOKEN: str
    SQLITE_DB_PATH: str
    ADMINS: list[int]

    @field_validator("ADMINS", mode="before")
    @classmethod
    def split_admins(cls, value):
        if isinstance(value, str):
            return [int(admin_id.strip()) for admin_id in value.split(",")]
        elif isinstance(value, int):
            return [value]
        return value

    def get_db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"


settings = Settings()

if __name__ == "__main__":
    print(ENV_FILE_PATH)
    print(settings.model_dump())
    print(settings.get_db_url())
