"""실시간 푸시 서버 (원본 wsServer).

원본 WsNettyServer 는 WebSocket 이 아니라 LineBasedFrameDecoder + StringDecoder 기반의
line TCP 서버다. 클라이언트가 접속/등록하면 서버가 상태 변화를 push 한다.
핵심: WsMsgProcessor.sendMsg(response, isAll) — 특정 imei 또는 전체 클라이언트로 전송.

원본 빌드에서 이 서버도 기본 비활성(MainProcessServer 가 primary 만 기동).
"""
from __future__ import annotations

import asyncio
import logging

from app.tcp import byte_process as bp

LOGGER = logging.getLogger('app')


class WsConnection:
    def __init__(self, writer: asyncio.StreamWriter, ip: str, port: str):
        self.writer = writer
        self.ip = ip
        self.port = port
        self.imei: int | None = None


class WsChannelManager:
    """원본 WsChannelManager + WsMsgProcessor.users/sendMsg."""

    def __init__(self) -> None:
        self._conns: set[WsConnection] = set()

    def add(self, conn: WsConnection) -> None:
        self._conns.add(conn)

    def remove(self, conn: WsConnection) -> None:
        self._conns.discard(conn)

    def is_online(self, imei: int) -> bool:
        return any(c.imei == imei for c in self._conns)

    def handle_message(self, conn: WsConnection, msg: bytes) -> None:
        """원본 WsMsgProcessor.messageHandler: 로그인 등록 + imei 설정."""
        if len(msg) == 4:
            LOGGER.warning("this client has logined system [%s:%s]", conn.ip, conn.port)
            return
        conn.imei = bp.bytes_to_int(bp.split_byte(msg, 8, 12), 4)

    def send_msg(self, response: bytes | str, is_all: bool = False) -> int:
        """원본 sendMsg: response[8:12] 의 imei 클라이언트(또는 전체)로 전송. 전송 건수 반환."""
        if isinstance(response, str):
            response = bp.hex_string_to_bytes(response.replace(" ", "")) or b""
        if not self._conns:
            return 0
        res_imei = bp.bytes_to_int(bp.split_byte(response, 8, 12), 4)
        sent = 0
        for conn in list(self._conns):
            if not is_all and conn.imei != res_imei:
                continue
            try:
                conn.writer.write(response)
                sent += 1
                if not is_all:
                    break
            except Exception:
                self.remove(conn)
        return sent


ws_channel_manager = WsChannelManager()


class WsServer:
    def __init__(self, port: int) -> None:
        self.port = port
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, host="0.0.0.0", port=self.port)
        LOGGER.warning("WsServer 시작, 포트: %s", self.port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        ip = peer[0] if peer else ""
        port = str(peer[1]) if peer else ""
        conn = WsConnection(writer, ip, port)
        ws_channel_manager.add(conn)
        try:
            while True:
                line = await reader.readline()  # 원본 LineBasedFrameDecoder
                if not line:
                    break
                ws_channel_manager.handle_message(conn, line.rstrip(b"\r\n"))
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            ws_channel_manager.remove(conn)
            writer.close()


_server: WsServer | None = None


async def start_ws_server(port: int) -> WsServer:
    global _server
    _server = WsServer(port)
    await _server.start()
    return _server
