"""차량(AGV) TCP 서버.

원본 PrimaryNettyServer + PrimaryServerHandler 의 대체.
전송 구조는 FrameTcpServer 로 일반화돼 있으며, 여기서는 차량용 인스턴스를 제공한다.
"""
from __future__ import annotations

from app.tcp.frame_server import FrameTcpServer


class PrimaryServer(FrameTcpServer):
    def __init__(self, port: int, message_handler=None) -> None:
        super().__init__(port, name="PrimaryServer", message_handler=message_handler)


_server: PrimaryServer | None = None


async def start_primary_server(port: int) -> PrimaryServer:
    global _server
    from app.tcp.heartbeat_processor import message_handler

    _server = PrimaryServer(port, message_handler=message_handler)
    await _server.start()
    return _server
