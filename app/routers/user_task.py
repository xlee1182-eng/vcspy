"""UserTask REST API (실작업 조회/취소/초기화).

원본 UserTaskWebService(@RequestMapping /service/web/userTask) 의 DB 기반 엔드포인트.
sendTask/setTask/setKeyboardLock/sendRepeatTask 등 TCP 송신 의존부는 후속.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.task import (
    KeyboardLockSetForm,
    TaskCancelForm,
    TaskClearForm,
    TaskCodeGetForm,
    TaskInfoGetForm,
    TaskPlanInfoGetForm,
    TaskRepeatSendForm,
    TaskSetForm,
    TaskStateGetForm,
    TaskTreatGetForm,
    WebTaskAddForm,
)
from app.services.user_task import user_task_service

LOGGER = logging.getLogger('app')

# router = APIRouter(prefix="/service/web/userTask", tags=["用户任务(web)"])
router = APIRouter(prefix="/service/web/userTask", tags=["사용자 작업(web)"])


@router.post("/sendTask", response_model=JsonResult)
async def send_task(form: WebTaskAddForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 sendTask: 외부 작업 송신(addTask)."""
    try:
        LOGGER.warning("작업 전송(외부) 인터페이스, AGV【%s】 작업 하달 메서드 진입!", form.deviceImei)
        msg = form.check()
        if not msg.is_success():
            from app.core import messages
            return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
        LOGGER.warning("작업 전송(외부) 인터페이스 입력 파라미터: %s", form.model_dump_json())
        result = await user_task_service.add_task(db, form)
        LOGGER.warning("작업 전송(외부) 인터페이스 반환 데이터: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("发送任务(对外)接口出现异常！")
        LOGGER.exception("작업 전송(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getTaskResult", response_model=JsonResult)
async def get_task_result(form: TaskStateGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("getTaskResult ->: %s", form.model_dump_json())
        result = await user_task_service.get_task_result(db, form.customerId, form.messageId)
        LOGGER.warning("getTaskResult <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("获取任务状态(对外)接口出现异常！")
        LOGGER.exception("작업 상태 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getPickPlaceState", response_model=JsonResult)
async def get_pick_place_state(form: TaskStateGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("getPickPlaceState ->: %s", form.model_dump_json())
        result = await user_task_service.get_pick_place_state(db, form.customerId, form.messageId)
        LOGGER.warning("getPickPlaceState <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("查询取放货状态(对外)接口出现异常！")
        LOGGER.exception("화물 취득/적재 상태 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/cancelTask", response_model=JsonResult)
async def cancel_task(form: TaskCancelForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("cancelTask ->: %s", form.model_dump_json())
        result = await user_task_service.cancel_task(db, form.deviceImei)
        LOGGER.warning("cancelTask <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("取消所有未执行的任务(对外)接口出现异常！")
        LOGGER.exception("미실행 전체 작업 취소(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/clearTask", response_model=JsonResult)
async def clear_task(form: TaskClearForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("clearTask ->: %s", form.model_dump_json())
        result = await user_task_service.clear_task(db)
        LOGGER.warning("clearTask <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("清空所有任务(对外)接口出现异常！")
        LOGGER.exception("전체 작업 초기화(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/setKeyboardLock", response_model=JsonResult)
async def set_keyboard_lock(form: KeyboardLockSetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("setKeyboardLock ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            from app.core import messages
            return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
        result = await user_task_service.set_keyboard_lock(db, form)
        LOGGER.warning("setKeyboardLock <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("设置键盘任务锁(对外)接口出现异常！")
        LOGGER.exception("키보드 작업 잠금 설정(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/setTask", response_model=JsonResult)
async def set_task(form: TaskSetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("setTask ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            from app.core import messages
            return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
        result = await user_task_service.set_task(db, form)
        LOGGER.warning("setTask <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("设置任务(对外)接口出现异常！")
        LOGGER.exception("작업 설정(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getTaskInfo", response_model=JsonResult)
async def get_task_info(form: TaskInfoGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 getTaskInfo: messageIds/deviceImeis 기반 작업 목록 조회."""
    try:
        LOGGER.warning("getTaskInfo ->: %s", form.model_dump_json())
        result = await user_task_service.get_task_info_list(db, form)
        LOGGER.warning("getTaskInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("작업 정보 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/sendRepeatTask", response_model=JsonResult)
async def send_repeat_task(form: TaskRepeatSendForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("sendRepeatTask ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            from app.core import messages
            return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
        result = await user_task_service.send_repeat_task(db, form)
        LOGGER.warning("sendRepeatTask <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("重复发送任务(对外)接口出现异常！")
        LOGGER.exception("작업 반복 전송(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getTaskByCode", response_model=JsonResult)
async def get_task_by_code(form: TaskCodeGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 getTaskByCode: 시작점 기준 최근 작업 1건 조회."""
    try:
        LOGGER.warning("getTaskByCode ->: %s", form.model_dump_json())
        result = await user_task_service.get_task_by_code(db, form.siteCode)
        LOGGER.warning("getTaskByCode <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("시작점 기준 최근 작업 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getTaskTreatInfo", response_model=JsonResult)
async def get_task_treat_info(form: TaskTreatGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 getTaskTreatInfo: messageId 기준 구분 작업 상태 조회."""
    try:
        LOGGER.warning("getTaskTreatInfo ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            from app.core import messages
            return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
        result = await user_task_service.get_task_treat_info(db, form.messageId)
        LOGGER.warning("getTaskTreatInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("구분 작업 상태 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getTaskPlanInfo", response_model=JsonResult)
async def get_task_plan_info(form: TaskPlanInfoGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 getTaskPlanInfo: deviceImei 기준 작업 경로(siteCodes/forkLines) 조회."""
    try:
        LOGGER.warning("getTaskPlanInfo ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            from app.core import messages
            return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
        result = await user_task_service.get_task_plan_info(db, form.deviceImei)
        LOGGER.warning("getTaskPlanInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("작업 경로 정보 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()
