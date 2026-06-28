"""시퀀스 채번 서비스.

원본 SequenceServiceImpl + MySQL 저장함수 nextval(name, code) 의 대체.
nextval: sequence 테이블의 (name, code) 행 current_value 를 increment 만큼 증가시키고
반환한다. 행이 없으면 1 부터 시작(저장함수 동작 근사).
usertaskSeq: code="usertask", name="usertask".
"""
from __future__ import annotations

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Sequence
from app.utils.id_utils import next_id_long

USERTASK_CODE = "usertask"
USERTASK_NAME = "usertask"


class SequenceService:
    async def next_val(self, db: AsyncSession, name: str, code: str) -> int:
        """원본 nextval(name, code): 행 증가 후 새 값. 없으면 생성(1)."""
        stmt = sa_select(Sequence).where(Sequence.name == name).where(Sequence.code == code)
        row = (await db.execute(stmt)).scalars().first()
        if row is None:
            row = Sequence(
                id=next_id_long(), code=code, name=name,
                # current_value=1, increment=1, remark="站点序列",
                current_value=1, increment=1, remark="스테이션 시퀀스",
            )
            db.add(row)
            await db.flush()
            return 1
        row.current_value = (row.current_value or 0) + (row.increment or 1)
        await db.flush()
        return row.current_value

    async def add_and_get_user_task_id(self, db: AsyncSession) -> int:
        """원본 addAndGetUserTaskId."""
        return await self.next_val(db, USERTASK_NAME, USERTASK_CODE)


sequence_service = SequenceService()
