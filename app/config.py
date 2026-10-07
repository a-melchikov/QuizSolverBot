import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    TOKEN: str = ""
    SQLITE_DB_PATH: str = "data/database.db"
    ADMINS: list[int] = []
    LOG_FILE: str = "app.log"
    WEBAPP_HOST: str = "0.0.0.0"
    WEBAPP_PORT: int = 8000
    WEBAPP_URL: str = ""
    WEBHOOK_URL: str = ""
    WEBHOOK_PATH: str = "/webhook/telegram"
    WEBHOOK_SECRET: str = ""

    @field_validator("ADMINS", mode="before")
    @classmethod
    def split_admins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            return [
                int(admin_id.strip())
                for admin_id in value.split(",")
                if admin_id.strip()
            ]
        elif isinstance(value, int):
            return [value]
        elif value is None:
            return []
        return value

    def get_db_url(self) -> str:
        db_path = Path(self.SQLITE_DB_PATH)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
        os.makedirs(db_path.parent, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"


settings = Settings()
