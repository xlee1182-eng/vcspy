"""TCP 통신 결과 메시지.

원본 com.ygcloud.ygvcs.utils.JsonMsg 의 대체.
필드: status(성공여부), msg(메시지/플래그), otherData(원시 응답 등).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JsonMsg(BaseModel):
    status: bool = False
    msg: str | None = None
    otherData: Any | None = None

    @classmethod
    def ok(cls, msg: str | None = None) -> "JsonMsg":
        return cls(status=True, msg=msg)

    @classmethod
    def fail(cls, msg: str | None = None) -> "JsonMsg":
        return cls(status=False, msg=msg)
