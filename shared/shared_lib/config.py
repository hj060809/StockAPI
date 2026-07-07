from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Sequence

class Settings(BaseSettings):
    PROJECT_NAME: str = "OCI Service"
    ALLOWED_ORIGINS: Sequence[str] = ['*']
    ENV: Literal["development", "stage", "production"]
    DATABASE_URL: str
    FMP_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def API_KEY_PREFIX(self) -> str:
        prefix_map = {
            'development': 'sk-dev-',
            'stage': 'sk-stg-',
            'production': 'sk-prd-'
        }
        return prefix_map[self.ENV]

settings = Settings()