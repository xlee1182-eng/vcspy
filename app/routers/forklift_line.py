"""ForkliftLine REST API.

원본 ForkliftLineWebService(@RequestMapping /service/web/forkliftLine) 이식.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.jsonresult import JsonResult
from app.schemas.base_form import WebForm
from app.services.forklift_line import forklift_line_service

LOGGER = logging.getLogger('app')

router = APIRouter(prefix="/service/web/forkliftLine", tags=["노선 관리"])


class ForkliftLineAllForm(WebForm):
    """전체 노선 조회(외부) — customerId 선택."""

    # customerId: str | None = None


@router.post("/getAllForkliftLine", response_model=JsonResult)
async def get_all_forklift_line(form: ForkliftLineAllForm) -> JsonResult:
    try:
        return await forklift_line_service.get_all_forklift_line()
    except Exception:
        LOGGER.exception("전체 노선 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()
