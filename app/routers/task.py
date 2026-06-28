"""Task 템플릿 REST API.

원본 TaskWarpWebService(@RequestMapping /service/warp/task) 이식.
addTaskTemp/editTaskTemp/editTaskTempInfo/delTaskTemp/clearTaskTemp/
selectTaskTempList/selectTaskTempInfo.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.repositories.task import task_template_repository
from app.schemas.task import TaskAddForm, TaskClearTempForm, TaskEditForm, TaskEditInfoForm, TaskSelectListForm
from app.services.task import task_service
from app.utils import json_util

LOGGER = logging.getLogger('app')

# router = APIRouter(prefix="/service/warp/task", tags=["任务模板管理"])
router = APIRouter(prefix="/service/warp/task", tags=["작업 템플릿 관리"])


def _param_err(msg: JsonResult) -> JsonResult:
    return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")


@router.post("/addTaskTemp", response_model=JsonResult)
async def add_task_temp(form: TaskAddForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await task_service.add_task_temp(db, form)
    except Exception:
        # LOGGER.exception("新增任务模板接口出现异常！")
        LOGGER.exception("작업 템플릿 추가 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/editTaskTemp", response_model=JsonResult)
async def edit_task_temp(form: TaskEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await task_service.edit_task_temp(db, form)
    except Exception:
        # LOGGER.exception("修改任务模板接口出现异常！")
        LOGGER.exception("작업 템플릿 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/editTaskTempInfo", response_model=JsonResult)
async def edit_task_temp_info(form: TaskEditInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await task_service.edit_task_temp_info(db, form)
    except Exception:
        # LOGGER.exception("修改任务模板信息接口出现异常！")
        LOGGER.exception("작업 템플릿 정보 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/delTaskTemp", response_model=JsonResult)
async def del_task_temp(form: TaskEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await task_service.del_task_temp(db, form)
    except Exception:
        # LOGGER.exception("删除任务模板接口出现异常！")
        LOGGER.exception("작업 템플릿 삭제 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/clearTaskTemp", response_model=JsonResult)
async def clear_task_temp(form: TaskClearTempForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 clearTaskTemp: 전체 템플릿을 순회하며 삭제."""
    try:
        templates = await task_template_repository.select_all(db)
        msg = JsonResult.success()
        for t in templates:
            msg = await task_service.del_task_temp(db, TaskEditForm(taskTemplateId=t.task_template_id))
        return msg
    except Exception:
        LOGGER.exception("작업 템플릿 전체 초기화 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/selectTaskTempList", response_model=JsonResult)
async def select_task_temp_list(form: TaskSelectListForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 selectTaskTempList: 템플릿 목록 조회."""
    try:
        templates = await task_template_repository.select_all(db)
        msg = JsonResult.success()
        msg.data = [json_util.to_dict(t) for t in templates]
        return msg
    except Exception:
        LOGGER.exception("작업 템플릿 목록 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/selectTaskTempInfo", response_model=JsonResult)
async def select_task_temp_info(form: TaskEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await task_service.select_task_temp_info(db, form)
    except Exception:
        # LOGGER.exception("查询任务模板详情接口出现异常！")
        LOGGER.exception("작업 템플릿 상세 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()
