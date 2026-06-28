"""Traffic 서비스 (연합 교통관제).

원본 TrafficWebService 의 비즈니스 로직 이식.
DB 접근 없이 Redis 키만 조작한다.
"""
from __future__ import annotations

from app.core import redis_constants as rc
from app.core.jsonresult import JsonResult
from app.utils.redis_util import redis_util


class TrafficService:
    async def is_site_pass(self, form) -> JsonResult:
        """원본 isSitePass: 통행 가능 사이트 목록을 Redis에 저장하거나 삭제."""
        if not form.siteList:
            await redis_util.delete_by_key(rc.PASS_SITE_ID)
        else:
            await redis_util.set_to_str(rc.PASS_SITE_ID, form.siteList)
        return JsonResult.success()

    async def set_traffic_point(self, form) -> JsonResult:
        """원본 setTrafficPoint: 교통관제 포인트 목록을 Redis에 저장하거나 삭제."""
        if not form.siteList:
            await redis_util.delete_by_key(rc.TRAFFIC_POINT)
        else:
            await redis_util.set_to_str(rc.TRAFFIC_POINT, form.siteList)
        return JsonResult.success()


traffic_service = TrafficService()
