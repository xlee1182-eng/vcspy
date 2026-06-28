"""웹 폼 공통 베이스.

원본 com.ygcloud.ygcommon.web.BaseUserWebForm 의 check() 대체.
- BaseForm  : warp 엔드포인트 공통 인증 필드(userName/userId/resourceId/...)를 포함.
- WebForm   : web(외부) 엔드포인트용 — 인증 필드 없음, check()/param_to_string() 만 제공.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.jsonresult import JsonResult


class BaseForm(BaseModel):
    """warp 엔드포인트 공통 인증 필드 (원본 BaseUserWebForm)."""

    userName: str | None = None
    userId: int | None = None
    resourceId: str | None = None
    userType: str | None = Field(default="3", description="사용자 유형: 1 슈퍼관리자, 2 제조사, 3 대리점, 4 기업")
    clientType: str | None = Field(default="1", description="클라이언트 유형: 1 모바일, 2 패드, 3 PC")
    appId: str | None = None
    agvFunVersion: int | None = None

    _validations: tuple[tuple[str, str], ...] = ()

    def check(self) -> JsonResult:
        for field, notes in self._validations:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return JsonResult.fail("1", notes)
        return JsonResult.success()

    def param_to_string(self) -> str:
        data = {k: v for k, v in self.model_dump().items() if v is not None}
        return f"{self.__class__.__name__}({data})"


class WebForm(BaseModel):
    """web(외부) 엔드포인트용 기본 폼 — 인증 필드 없음."""

    _validations: tuple[tuple[str, str], ...] = ()

    def check(self) -> JsonResult:
        for field, notes in self._validations:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return JsonResult.fail("1", notes)
        return JsonResult.success()

    def param_to_string(self) -> str:
        data = {k: v for k, v in self.model_dump().items() if v is not None}
        return f"{self.__class__.__name__}({data})"
