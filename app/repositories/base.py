"""제네릭 리포지토리.

원본 lh.mybatis.web.service.BaseService<T> 의 핵심 메서드(select/updateByPK 등)를
SQLAlchemy(async)로 대체한다. 원본 select(entity)는 "예시 객체(non-null 필드)"를
AND 조건으로 변환하는 query-by-example 방식이다.
"""
from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import inspect, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T]):
        self.model = model

    def _pk_columns(self) -> list[str]:
        return [c.name for c in inspect(self.model).primary_key]

    async def select(self, db: AsyncSession, example: dict[str, Any] | None = None) -> Sequence[T]:
        """query-by-example: example의 non-None 값들을 AND 조건으로 조회."""
        stmt = sa_select(self.model)
        for key, value in (example or {}).items():
            if value is None:
                continue
            stmt = stmt.where(getattr(self.model, key) == value)
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_all(self, db: AsyncSession) -> Sequence[T]:
        """원본 selectAll: 전체 조회."""
        res = await db.execute(sa_select(self.model))
        return res.scalars().all()

    async def delete(self, db: AsyncSession, example: dict[str, Any]) -> int:
        """원본 delete(entity): 예시 객체(non-None 필드)를 조건으로 삭제."""
        stmt = sa_delete(self.model)
        for key, value in example.items():
            if value is None:
                continue
            stmt = stmt.where(getattr(self.model, key) == value)
        res = await db.execute(stmt)
        return res.rowcount or 0

    async def update_by_example(
        self, db: AsyncSession, values: dict[str, Any], where: dict[str, Any]
    ) -> int:
        """원본 updateByConditionSelective: where 조건에 values 를 부분 갱신."""
        from sqlalchemy import update as sa_update

        stmt = sa_update(self.model)
        for key, value in where.items():
            if value is None:
                continue
            stmt = stmt.where(getattr(self.model, key) == value)
        stmt = stmt.values(**{k: v for k, v in values.items() if v is not None})
        res = await db.execute(stmt)
        return res.rowcount or 0

    async def select_one(self, db: AsyncSession, example: dict[str, Any] | None = None) -> T | None:
        rows = await self.select(db, example)
        return rows[0] if rows else None

    async def select_by_pk(self, db: AsyncSession, pk: Any) -> T | None:
        return await db.get(self.model, pk)

    async def insert(self, db: AsyncSession, entity: T) -> T:
        db.add(entity)
        await db.flush()
        return entity

    async def update_by_pk(self, db: AsyncSession, entity: T) -> T:
        """원본 updateByPK: PK 기준 머지 후 반영."""
        merged = await db.merge(entity)
        await db.flush()
        return merged

    async def delete_by_pk(self, db: AsyncSession, pk: Any) -> int:
        pk_cols = self._pk_columns()
        col = getattr(self.model, pk_cols[0])
        res = await db.execute(sa_delete(self.model).where(col == pk))
        return res.rowcount or 0
