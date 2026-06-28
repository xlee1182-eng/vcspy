"""AGV 요청/응답 상관(correlation) 매니저.

원본 com.ygcloud.ygvcs.common.future.AgvChannelFuture(Manager) 이식.
키: imei + fun + msgNo (문자열 결합). 송신 시 future 생성, 수신 시 완료.
원본 타임아웃 10초, 미응답 시 JsonMsg.fail.
asyncio.Future 로 동기 대기를 비동기 대기로 대체한다.
"""
from __future__ import annotations

import asyncio

from app.tcp.json_msg import JsonMsg

REQUEST_TIMEOUT = 10.0  # 원본 get() 기본 10000ms


class AgvChannelFutureManager:
    def __init__(self) -> None:
        self._futures: dict[str, asyncio.Future[JsonMsg]] = {}

    @staticmethod
    def _key(imei: int, fun: str, msg_no: str) -> str:
        return f"{imei}{fun}{msg_no}"

    def create(self, imei: int, fun: str, msg_no: str) -> asyncio.Future[JsonMsg]:
        """원본 create: future 등록."""
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[JsonMsg] = loop.create_future()
        self._futures[self._key(imei, fun, msg_no)] = fut
        return fut

    def delete(self, imei: int, fun: str, msg_no: str) -> asyncio.Future[JsonMsg] | None:
        return self._futures.pop(self._key(imei, fun, msg_no), None)

    def get(self, imei: int, fun: str, msg_no: str) -> asyncio.Future[JsonMsg] | None:
        return self._futures.get(self._key(imei, fun, msg_no))

    def future_complete(self, imei: int, fun: str, msg_no: str, state: bool, msg: bytes) -> None:
        """원본 futureComplete: 해당 future 를 완료. 응답바이트는 otherData 로."""
        fut = self.delete(imei, fun, msg_no)
        if fut is None or fut.done():
            return
        result = JsonMsg(status=state, otherData=msg) if state else JsonMsg.fail()
        fut.set_result(result)

    async def wait(self, fut: asyncio.Future[JsonMsg], timeout: float = REQUEST_TIMEOUT) -> JsonMsg:
        """원본 get(timeout): 타임아웃 시 실패 메시지."""
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            # return JsonMsg.fail("网络延迟，请稍后重试！")
            return JsonMsg.fail("네트워크 지연, 잠시 후 다시 시도해 주세요!")


future_manager = AgvChannelFutureManager()
