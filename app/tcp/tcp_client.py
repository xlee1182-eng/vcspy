"""차량(AGV) TCP 클라이언트.

원본 com.ygcloud.ygvcs.primaryserver.client.TcpClient 이식.
sendTcpMsg(task): 채널로 프레임 송신 후 응답을 (비동기) 대기하고,
성공 시 응답바이트를 HEX 문자열로 setMsg 한다.
"""
from __future__ import annotations

import logging

from app.tcp import byte_process as bp
from app.tcp.channel_manager import channel_manager
from app.tcp.future_manager import future_manager
from app.tcp.json_msg import JsonMsg

LOGGER = logging.getLogger('app')


class TaskModel:
    """원본 form.process.TaskModel 의 최소 대체 (송신 프레임/응답 보관)."""

    def __init__(self) -> None:
        self.requestMsg: str | None = None
        self.responseMsg: str | None = None
        self.funCode: str | None = None
        self.deviceImei: int | None = None


async def send_tcp_msg(task: TaskModel) -> JsonMsg:
    """원본 TcpClient.sendTcpMsg: 동기송신 → 응답 HEX 반환."""
    try:
        fut = channel_manager.send_msg_sync(task.requestMsg)
        msg = await future_manager.wait(fut)
        if not msg.status:
            return msg
        # 성공: otherData(응답 바이트) → HEX 문자열
        msg.msg = bp.print_hex_string(msg.otherData) if isinstance(msg.otherData, (bytes, bytearray)) else msg.otherData
        return msg
    except Exception:
        LOGGER.exception("sendTcpMsg 오류")
        return JsonMsg.fail()


def send_task_queen(task: TaskModel, is_read: bool = False) -> JsonMsg:
    """원본 sendTaskQueen: 응답 대기 없이 송신만."""
    ok = channel_manager.send_msg(task.requestMsg)
    return JsonMsg.ok() if ok else JsonMsg.fail()
