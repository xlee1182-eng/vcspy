"""User 요청 폼 (Pydantic).

원본 webservice.form.user.UserLoginForm / UserEditForm 의 대체.
공통 인증 필드(userName/userId/resourceId/...)는 BaseForm 에서 상속.
"""
from __future__ import annotations

from pydantic import Field

from app.core.jsonresult import JsonResult
from app.schemas.base_form import BaseForm


class UserLoginForm(BaseForm):
    """사용자 로그인 (用户登录)."""

    password: str | None = Field(default=None, description="비밀번호")

    def check(self) -> JsonResult:
        if not self.userName:
            return JsonResult.fail("1", "사용자명은 비어있을 수 없습니다")
        if not self.password:
            return JsonResult.fail("1", "비밀번호는 비어있을 수 없습니다")
        return JsonResult.success()

    def param_to_string(self) -> str:
        return f"UserLoginForm(userName={self.userName})"


class UserEditForm(BaseForm):
    """비밀번호 수정 (修改密码)."""

    password: str | None = Field(default=None, description="기존 비밀번호")
    newPassword: str | None = Field(default=None, description="새 비밀번호")

    def check(self) -> JsonResult:
        if not self.userName:
            return JsonResult.fail("1", "사용자명은 비어있을 수 없습니다")
        if not self.password:
            return JsonResult.fail("1", "기존 비밀번호는 비어있을 수 없습니다")
        if not self.newPassword:
            return JsonResult.fail("1", "새 비밀번호는 비어있을 수 없습니다")
        return JsonResult.success()

    def param_to_string(self) -> str:
        return f"UserEditForm(userName={self.userName})"
