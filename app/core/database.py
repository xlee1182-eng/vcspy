"""SQLAlchemy 비동기 세션/엔진 설정.

원본: MyBatis + Druid 커넥션 풀 -> SQLAlchemy(async) + 내장 풀로 대체.
주의: 이 애플리케이션은 기존 운영 DB 스키마를 그대로 사용한다.
      테이블 생성/변경(DDL)을 수행하지 않는다 (create_all 호출 금지).

엔진은 지연 초기화한다. 모델 모듈을 단순 임포트할 때(예: 코드 생성/테스트)
DB 드라이버(asyncmy)가 설치돼 있지 않아도 되도록 하기 위함.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """모든 ORM 모델의 베이스."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.db_url,
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            pool_recycle=60,  # 원본 time-between-eviction-runs-millis 60000
            pool_pre_ping=True,  # 원본 test-while-idle/keep-alive 대응
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성: 요청 단위 세션."""
    async with get_sessionmaker()() as session:
        yield session
