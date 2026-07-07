from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Sequence

class Settings(BaseSettings):
    PROJECT_NAME: str = "OCI Service"
    ALLOWED_ORIGINS: Sequence[str] = ['*']
    ENV: Literal["development", "stage", "production"]
    DATABASE_URL: str
    FMP_API_KEY: str

    # 캔들 수집 크론 시각 (UTC) — 기본 05:30.
    # 일봉의 기간은 미국 동부 자정(04:00~05:00 UTC)에 끝나므로, 그 직후에 돌아야
    # 전일 캔들이 '확정'으로 판정되어 저장됨 (미확정 캔들은 저장하지 않는 정책)
    COLLECT_CRON_HOUR: int = 5
    COLLECT_CRON_MINUTE: int = 30

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