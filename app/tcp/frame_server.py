"""제네릭 프레임 TCP 서버 (asyncio).

원본 PrimaryNettyServer/CamNettyServer/CallBoxNettyServer + 각 핸들러는
전송 구조가 동일하다(구분자 50AFA05FA0, 동일 디코더, 동일 dedup/saveChannel/receiveMsg).
이를 하나의 재사용 서버로 일반화한다. 도메인별 차이는 message_handler 콜백뿐.
"""
from __future__ import annotations

import asyncio
import logging

from app.tcp import byte_process as bp
from app.tcp.channel_manager import channel_manager
from app.tcp.frame_codec import FrameBuffer

LOGGER = logging.getLogger('app')


class FrameTcpServer:
    def __init__(self, port: int, name: str = "server", message_handler=None) -> None:
        self.port = port
        self.name = name
        self.message_handler = message_handler
        self._server: asyncio.AbstractServer | None = None
        self._doing: set[str] = set()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, host="0.0.0.0", port=self.port)
        LOGGER.info("%s Start, Port: %s", self.name, self.port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        ip = peer[0] if peer else ""
        peer_str = f"{peer[0]}:{peer[1]}" if peer else "unknown"
        LOGGER.info("%s client login port %s", peer_str, self.port)
        if self.message_handler is not None:
            self.message_handler(writer, bytes.fromhex("0F0F0F0F"))
        buf = FrameBuffer()
        imei_seen: int | None = None
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                for frame in buf.feed(data):
                    imei_seen = self._on_frame(frame, writer, ip) or imei_seen
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            channel_manager.delete_channel_by_imei(imei_seen)
            LOGGER.warning("Connection with client IP %s has timed out, connection removed from server %s", peer_str, self.port)
            writer.close()

    def _on_frame(self, frame: bytes, writer: asyncio.StreamWriter, ip: str) -> int | None:
        """원본 channelRead0: 1프레임 처리(dedup → saveChannel → processor → receiveMsg)."""
        try:
            msg_no = bp.bytes_to_int(bp.split_byte(frame, 4, 8), 4)
            imei = bp.bytes_to_int(bp.split_byte(frame, 8, 12), 4)
            fun = bp.print_hex_string(bp.split_byte(frame, 12, 13))
            flag = bp.print_hex_string(bp.split_byte(frame, 14, 15))
            start_code = bp.bytes_to_int(bp.split_byte(frame, 15, 18), 3) if fun == "00" else 0
            end_code = bp.bytes_to_int(bp.split_byte(frame, 18, 21), 3) if fun == "00" else 0
            key = f"{imei}:{fun}:{msg_no}"
            if key in self._doing:
                self._doing.discard(key)
                return imei
            self._doing.add(key)
            try:
                channel_manager.save_channel(writer, frame, ip)
                if self.message_handler is not None:
                    self.message_handler(writer, frame)
                
                LOGGER.warning(
                    # "imei【:%s】,fun:【%s】,flag:【%s】,msgNo:【%s】,line:【%s-->%s】,frame:%s",
                    "imei[%s] fun[%s] flag[%s] msgNo[%s] line[%s-->%s] frame[%s]",
                    imei, fun, flag, msg_no, start_code, end_code, bp.print_hex_string(frame),
                )
                if fun != "00":
                    channel_manager.receive_msg(frame, ip)
            finally:
                self._doing.discard(key)
            return imei
        except Exception:
            LOGGER.exception("프레임 처리 오류")
            return None
