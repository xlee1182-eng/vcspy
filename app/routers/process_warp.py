"""Process WARP REST API.

원본 ProcessWarpWebService(@RequestMapping /service/warp/process) 이식.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core import redis_constants as rc
from app.core.config import settings
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.base_form import BaseForm
from app.schemas.process import (
    ClearAllDataForm,
    ImportSqlForm,
    IsSyncTaskSourceForm,
    ToPointSwitchSetForm,
    ToPointTimeSetForm,
)
from app.services.process_service import process_service
from app.utils.redis_util import redis_util

LOGGER = logging.getLogger('app')

router = APIRouter(prefix="/service/warp/process", tags=["프로세스(warp)"])


def _param_err(msg: JsonResult) -> JsonResult:
    return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")


@router.post("/importSqlInfo", response_model=JsonResult)
async def import_sql_info(form: ImportSqlForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await process_service.import_sql_info(db, form)
    except Exception:
        LOGGER.exception("학습 데이터 가져오기 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getServerVersion", response_model=JsonResult)
async def get_server_version(form: BaseForm) -> JsonResult:
    try:
        return JsonResult.success(settings.server_version)
    except Exception:
        LOGGER.exception("서버 버전 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/isSyncTaskSource", response_model=JsonResult)
async def is_sync_task_source(form: IsSyncTaskSourceForm) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        await redis_util.set_to_str(rc.IS_SYNC_TASK_SOURCE, form.syncTaskSource)
        return JsonResult.success()
    except Exception:
        LOGGER.exception("동기화 작업 출처 설정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getIsSyncTaskSource", response_model=JsonResult)
async def get_is_sync_task_source(form: BaseForm) -> JsonResult:
    try:
        val = await redis_util.get_str_to_object(rc.IS_SYNC_TASK_SOURCE, str)
        sync_val = val.strip('"') if val and val.strip('"') else "0"
        return JsonResult.success({"syncTaskSource": sync_val})
    except Exception:
        LOGGER.exception("동기화 작업 출처 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/setToPointSwitch", response_model=JsonResult)
async def set_to_point_switch(form: ToPointSwitchSetForm) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        await redis_util.set_to_str(rc.TO_POINT_SWITCH, form.toPointSwitch)
        return JsonResult.success()
    except Exception:
        LOGGER.exception("회차점 스위치 설정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getToPointSwitch", response_model=JsonResult)
async def get_to_point_switch(form: BaseForm) -> JsonResult:
    try:
        val = await redis_util.get_str_to_object(rc.TO_POINT_SWITCH, str)
        switch_val = val.strip('"') if val and val.strip('"') else "0"
        return JsonResult.success({"toPointSwitch": switch_val})
    except Exception:
        LOGGER.exception("회차점 스위치 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/setToPointTime", response_model=JsonResult)
async def set_to_point_time(form: ToPointTimeSetForm) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        await redis_util.set_to_str(rc.DEVICE_NOT_TASK_TO_WAIT_POINT_TIME, form.toPointTime)
        return JsonResult.success()
    except Exception:
        LOGGER.exception("회차점 대기 시간 설정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getToPointTime", response_model=JsonResult)
async def get_to_point_time(form: BaseForm) -> JsonResult:
    try:
        val = await redis_util.get_str_to_object(rc.DEVICE_NOT_TASK_TO_WAIT_POINT_TIME, str)
        time_val = int(val.strip('"')) if val and val.strip('"').lstrip("-").isdigit() else 15
        return JsonResult.success({"toPointTime": time_val})
    except Exception:
        LOGGER.exception("회차점 대기 시간 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/clearAllData", response_model=JsonResult)
async def clear_all_data(form: ClearAllDataForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        return await process_service.clear_all_data(db)
    except Exception:
        LOGGER.exception("전체 데이터 삭제 인터페이스 예외 발생!")
        return JsonResult.syserr()
