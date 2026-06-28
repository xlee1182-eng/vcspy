"""UserTask WARP REST API.

원본 UserTaskWarpWebService(@RequestMapping /service/warp/userTask) 의
호출작업/점대점 엔드포인트.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.task import (
    TaskCallCancelForm,
    TaskCallForm,
    TaskCallGetForm,
    TaskCountForm,
    TaskDelForm,
    TaskInfoForm,
    TaskPointsForm,
)
from app.services.user_task import user_task_service

LOGGER = logging.getLogger('app')

# router = APIRouter(prefix="/service/warp/userTask", tags=["用户任务(warp)"])
router = APIRouter(prefix="/service/warp/userTask", tags=["사용자 작업(warp)"])


def _param_err(msg: JsonResult) -> JsonResult:
    return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")


@router.post("/callDeviceTask", response_model=JsonResult)
async def call_device_task(form: TaskCallForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await user_task_service.call_device_task(db, form)
    except Exception:
        # LOGGER.exception("呼叫设备任务接口出现异常！")
        LOGGER.exception("장치 호출 작업 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/sendPointsTask", response_model=JsonResult)
async def send_points_task(form: TaskPointsForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await user_task_service.send_points_task(db, form)
    except Exception:
        LOGGER.exception("점대점 작업 전송 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getUserTaskInfo", response_model=JsonResult)
async def get_user_task_info(form: TaskInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        return await user_task_service.get_user_task_info(db, form.sendFlag)
    except Exception:
        LOGGER.exception("작업 목록 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getCallDeviceTask", response_model=JsonResult)
async def get_call_device_task(form: TaskCallGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        return await user_task_service.get_call_device_task(db)
    except Exception:
        LOGGER.exception("호출 작업 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/cancelCallDeviceTask", response_model=JsonResult)
async def cancel_call_device_task(form: TaskCallCancelForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        return await user_task_service.cancel_call_device_task(db, form.userName)
    except Exception:
        LOGGER.exception("호출 작업 취소 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/delUserTask", response_model=JsonResult)
async def del_user_task(form: TaskDelForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await user_task_service.del_user_task(db, form.userTaskId)
    except Exception:
        LOGGER.exception("작업 삭제 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getCountTask", response_model=JsonResult)
async def get_count_task(form: TaskCountForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        return await user_task_service.get_count_task(db, form.type)
    except Exception:
        LOGGER.exception("작업 통계 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()
