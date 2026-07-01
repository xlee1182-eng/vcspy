"""애플리케이션 설정.

원본 application.yml(yg-vcs)의 값을 환경변수/기본값으로 옮긴 것.
민감정보(DB 비밀번호 등)는 .env 또는 환경변수로 주입한다.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="YGVCS_", extra="ignore")

    # --- 웹 서버 (원본: server.port 8188, context-path /ygvcs) ---
    app_name: str = "yg-vcs"
    host: str = "0.0.0.0"
    port: int = 8188
    context_path: str = "/ygvcs"

    # --- MySQL (원본 datasource) ---
    db_host: str = "localhost"
    db_port: int = 3307
    db_name: str = "yg_vcs_cloud"
    db_user: str = "root"
    db_password: str = "root"
    db_pool_size: int = 10  # 원본 druid max-active
    db_pool_min: int = 5
    db_echo: bool = False

    # --- Redis (원본 spring.redis, database index 2) ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    # redis_password: str | None = None
    redis_password: str = "admin"
    redis_db: int = 2
    redis_timeout: int = 5

    # --- TCP 통신 서버 (원본: serverPort, communicationKey) ---
    primary_server_enabled: bool = True
    primary_server_port: int = 9112
    communication_key: str = "123456789"
    server_version: str = "1.4.19"

    # 원본 빌드에서 MainProcessServer 는 primary 만 기동(cam/callBox/ws 는 정의만).
    # 동일하게 기본 비활성. 필요 시 환경변수로 활성화.
    cam_server_enabled: bool = False
    cam_server_port: int = 9113
    callbox_server_enabled: bool = False
    callbox_server_port: int = 9114
    ws_server_enabled: bool = False
    ws_server_port: int = 9115

    # 스케줄러(RecordHeartJob 등)
    scheduler_enabled: bool = True

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
