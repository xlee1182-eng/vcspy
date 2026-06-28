"""표준 응답 래퍼.

원본 com.ygcloud.ygcommon.web.JsonResult 의 대체.
원본 필드/메서드: resultCode, resultMsg, data, isSuccess().
원본 코드 규약(관찰): 성공 코드 "0", 실패 코드는 호출부가 지정("1" 등),
시스템 오류는 sys_err 메시지. 필드명은 원본 JSON 키와 호환되도록 유지한다.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.core import messages

SUCCESS_CODE = "0"


class JsonResult(BaseModel):
    resultCode: str = SUCCESS_CODE
    resultMsg: str = ""
    data: Any | None = None

    # --- 팩토리 (원본 정적 메서드 대응) ---
    @classmethod
    def success(cls, data: Any | None = None) -> "JsonResult":
        return cls(resultCode=SUCCESS_CODE, resultMsg=messages.get_msg("success"), data=data)

    @classmethod
    def fail(cls, code: str = "1", msg: str | None = None) -> "JsonResult":
        return cls(resultCode=code, resultMsg=msg if msg is not None else messages.get_msg("fail"))

    @classmethod
    def syserr(cls) -> "JsonResult":
        return cls(resultCode="1", resultMsg=messages.get_msg("sys_err"))

    # --- 동작 (원본 메서드 대응) ---
    def is_success(self) -> bool:
        return self.resultCode == SUCCESS_CODE

    def set_result_msg(self, msg: str) -> "JsonResult":
        self.resultMsg = msg
        return self
