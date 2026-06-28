"""User REST API.

원본 UserWarpWebService (@RequestMapping /service/warp/user) 이식.
원본 엔드포인트: POST /userLogin, POST /editPassword.
원본은 진입/반환을 LOGGER.warn 으로 남기고, 예외는 JsonResult.syserr() 로 감싼다.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.user import UserEditForm, UserLoginForm
from app.services.user import user_service

LOGGER = logging.getLogger('app')

# router = APIRouter(prefix="/service/warp/user", tags=["用户管理"])
router = APIRouter(prefix="/service/warp/user", tags=["사용자 관리"])


@router.post("/userLogin", response_model=JsonResult)
async def user_login(form: UserLoginForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    # name = "用户登录接口"
    name = "사용자 로그인 인터페이스"
    try:
        # LOGGER.warning("%s入口,参数为：%s", name, form.param_to_string())
        LOGGER.warning("%s 진입, 파라미터: %s", name, form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
            return msg
        msg = await user_service.user_login(db, form)
        # LOGGER.warning("%s返回帧：%s", name, msg.model_dump())
        LOGGER.warning("%s 반환 프레임: %s", name, msg.model_dump())
        return msg
    except Exception:
        # LOGGER.exception("%s出现异常！", name)
        LOGGER.exception("%s 예외 발생!", name)
        return JsonResult.syserr()


@router.post("/editPassword", response_model=JsonResult)
async def edit_password(form: UserEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    # name = "修改密码接口"
    name = "비밀번호 수정 인터페이스"
    try:
        # LOGGER.warning("%s入口,参数为：%s", name, form.param_to_string())
        LOGGER.warning("%s 진입, 파라미터: %s", name, form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")
            return msg
        msg = await user_service.edit_password(db, form)
        # LOGGER.warning("%s返回帧：%s", name, msg.model_dump())
        LOGGER.warning("%s 반환 프레임: %s", name, msg.model_dump())
        return msg
    except Exception:
        # LOGGER.exception("%s出现异常！", name)
        LOGGER.exception("%s 예외 발생!", name)
        return JsonResult.syserr()
