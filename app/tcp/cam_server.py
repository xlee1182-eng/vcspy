"""카메라 TCP 서버.

원본 CamNettyServer + CamServerHandler + CamMsgProcessor.
전송 구조는 차량 서버와 동일(구분자 50AFA05FA0, 공유 채널매니저).
원본 빌드에서는 MainProcessServer 가 primary 만 기동하므로, 이 서버도 기본 비활성이다.
message_handler 로 카메라 상태 처리(CamMsgProcessor.messageProcess)를 주입한다.
"""
from __future__ import annotations

from app.tcp.frame_server import FrameTcpServer


class CamServer(FrameTcpServer):
    def __init__(self, port: int, message_handler=None) -> None:
        super().__init__(port, name="CamServer", message_handler=message_handler)


_server: CamServer | None = None


async def start_cam_server(port: int) -> CamServer:
    global _server
    _server = CamServer(port)
    await _server.start()
    return _server
