"""호출박스(콜박스) TCP 서버.

원본 CallBoxNettyServer + CallBoxServerHandler + CallBoxMsgProcessor.
전송 구조는 차량 서버와 동일. 원본 빌드에서 기본 비활성(primary 만 기동).
"""
from __future__ import annotations

from app.tcp.frame_server import FrameTcpServer


class CallBoxServer(FrameTcpServer):
    def __init__(self, port: int, message_handler=None) -> None:
        super().__init__(port, name="CallBoxServer", message_handler=message_handler)


_server: CallBoxServer | None = None


async def start_callbox_server(port: int) -> CallBoxServer:
    global _server
    _server = CallBoxServer(port)
    await _server.start()
    return _server
