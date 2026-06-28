"""애플리케이션 설정.

원본 application.yml(yg-vcs)의 값을 환경변수/기본값으로 옮긴 것.
민감정보(DB 비밀번호 등)는 .env 또는 환경변수로 주입한다.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py 위치(app/core/) 기준으로 프로젝트 루트의 .env 를 절대경로로 지정
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_prefix="YGVCS_", extra="ignore")

    # --- 웹 서버 ---
    app_name: str
    host: str
    port: int
    context_path: str

    # --- MySQL ---
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_pool_size: int
    db_pool_min: int
    db_echo: bool

    # --- Redis ---
    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int
    redis_timeout: int

    # --- TCP 통신 서버 ---
    primary_server_enabled: bool
    primary_server_port: int
    communication_key: str
    server_version: str

    cam_server_enabled: bool
    cam_server_port: int
    callbox_server_enabled: bool
    callbox_server_port: int
    ws_server_enabled: bool
    ws_server_port: int

    # --- 스케줄러 ---
    scheduler_enabled: bool

    @property
    def db_url(self) -> str:
        """SQLAlchemy async DSN (aiomysql 드라이버, 순수 파이썬)."""
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def db_url_sync(self) -> str:
        """동기 DSN (PyMySQL) — 스크립트/테스트용."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
