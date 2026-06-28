"""ForkliftLine 서비스.

원본 ForkliftLineServiceImpl + ForkliftLineWebService.getAllForkliftLine 이식.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis_constants as rc
from app.core.jsonresult import JsonResult
from app.models.tables import ForkliftLine
from app.repositories.forklift_line import forklift_line_repository
from app.utils.redis_util import redis_util


class ForkliftLineService:
    async def add_fork_line_list(self, db: AsyncSession, lines: Sequence[ForkliftLine]) -> JsonResult:
        """원본 addForkLineList: 일괄 추가, 0건이면 실패."""
        n = await forklift_line_repository.add_fork_line_list(db, lines)
        if n > 0:
            await db.commit()
            return JsonResult.success()
        # return JsonResult.fail("1", "添加失败！")
        return JsonResult.fail("1", "추가 실패!")

    async def get_line_to_init(
        self,
        db: AsyncSession,
        device_imei: int,
        start_site_code: int | None = None,
        end_site_code: int | None = None,
        site_code: int | None = None,
    ) -> list[dict]:
        """원본 getLineToInit: 시작/종료 둘 다 있으면 정밀 매칭, 아니면 site_code 매칭."""
        if start_site_code is not None and end_site_code is not None:
            return await forklift_line_repository.get_line_to_init(
                db, device_imei, start_site_code, end_site_code
            )
        return await forklift_line_repository.get_line_to_init2(db, device_imei, site_code)

    async def get_all_forklift_line(self) -> JsonResult:
        """원본 getAllForkliftLine: Redis 'forklift_all' 리스트 반환."""
        msg = JsonResult.success()
        msg.data = await redis_util.get_list(rc.FORKLIFT_ALL)
        return msg


forklift_line_service = ForkliftLineService()
