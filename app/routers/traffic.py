"""Traffic REST API (연합 교통관제).

원본 TrafficWebService(@RequestMapping /service/web/traffic) 이식.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.jsonresult import JsonResult
from app.schemas.traffic import TrafficPointSetForm, TrafficSitePassForm
from app.services.traffic import traffic_service

LOGGER = logging.getLogger('app')

router = APIRouter(prefix="/service/web/traffic", tags=["교통관제(web)"])


@router.post("/isSitePass", response_model=JsonResult)
async def is_site_pass(form: TrafficSitePassForm) -> JsonResult:
    """원본 isSitePass: 연합 교통관제 통행 가능 사이트 설정."""
    try:
        LOGGER.warning("isSitePass ->: %s", form.model_dump_json())
        result = await traffic_service.is_site_pass(form)
        LOGGER.warning("isSitePass <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("연합 교통관제 통행 가능 사이트(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/setTrafficPoint", response_model=JsonResult)
async def set_traffic_point(form: TrafficPointSetForm) -> JsonResult:
    """원본 setTrafficPoint: 교통관제 포인트 설정."""
    try:
        LOGGER.warning("setTrafficPoint ->: %s", form.model_dump_json())
        result = await traffic_service.set_traffic_point(form)
        LOGGER.warning("setTrafficPoint <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("교통관제 포인트 설정(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()
