"""ForkliftLine 리포지토리.

원본 ForkliftLineMapper 의 커스텀 SQL(addForkLineList, getLineToInit/2) 이식.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import ForkliftLine
from app.repositories.base import BaseRepository


class ForkliftLineRepository(BaseRepository[ForkliftLine]):
    def __init__(self) -> None:
        super().__init__(ForkliftLine)

    async def add_fork_line_list(self, db: AsyncSession, lines: Sequence[ForkliftLine]) -> int:
        """원본 addForkLineList: 일괄 insert. 반영 건수 반환."""
        db.add_all(list(lines))
        await db.flush()
        return len(lines)

    async def get_line_to_init(
        self, db: AsyncSession, device_imei: int, start_site_code: int, end_site_code: int
    ) -> list[dict]:
        """원본 getLineToInit: 시작/종료 코드 모두 일치하는 회차 라인."""
        stmt = (
            sa_select(ForkliftLine.return_line_id, ForkliftLine.return_parent_id)
            .where(ForkliftLine.device_imei == device_imei)
            .where(or_(ForkliftLine.return_line_id.isnot(None), ForkliftLine.return_parent_id.isnot(None)))
            .where(ForkliftLine.step_number > 1)
            .where(ForkliftLine.start_site_code == start_site_code)
            .where(ForkliftLine.end_site_code == end_site_code)
        )
        res = await db.execute(stmt)
        return [{"returnLineId": r[0], "returnParentId": r[1]} for r in res.all()]

    async def get_line_to_init2(self, db: AsyncSession, device_imei: int, site_code: int) -> list[dict]:
        """원본 getLineToInit2: 시작 또는 종료 코드가 site_code 인 회차 라인."""
        stmt = (
            sa_select(ForkliftLine.return_line_id, ForkliftLine.return_parent_id)
            .where(ForkliftLine.device_imei == device_imei)
            .where(or_(ForkliftLine.return_line_id.isnot(None), ForkliftLine.return_parent_id.isnot(None)))
            .where(ForkliftLine.step_number > 1)
            .where(or_(ForkliftLine.start_site_code == site_code, ForkliftLine.end_site_code == site_code))
        )
        res = await db.execute(stmt)
        return [{"returnLineId": r[0], "returnParentId": r[1]} for r in res.all()]


forklift_line_repository = ForkliftLineRepository()
