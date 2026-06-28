"""AGV 채널 관리.

원본 com.ygcloud.ygvcs.primaryserver.handler.AgvChannelManager 이식.
- imei -> 연결(StreamWriter) 매핑
- 프레임에서 imei/fun/msgNo 추출 규칙(원본과 동일):
    msgNo = printHexString(bytes[4:8])
    imei  = bytesToInt(bytes[8:12], 4)
    fun   = printHexString(bytes[12:13])
- sendMsgSync: future 생성 후 송신 → 응답 대기는 호출측에서 wait().
"""
from __future__ import annotations

import asyncio
import logging

from app.tcp import byte_process as bp
from app.tcp.future_manager import future_manager
from app.tcp.json_msg import JsonMsg
from app.jobs.record_heart_job import RecordHeart

LOGGER = logging.getLogger('app')


class AgvChannelManager:
    def __init__(self) -> None:
        # imei -> StreamWriter
        self._channels: dict[int, asyncio.StreamWriter] = {}

    # --- 프레임 필드 추출 (원본 규칙) ---
    @staticmethod
    def msg_no(msg: bytes) -> str:
        return bp.print_hex_string(bp.split_byte(msg, 4, 8))

    @staticmethod
    def imei_of(msg: bytes) -> int:
        return bp.bytes_to_int(bp.split_byte(msg, 8, 12), 4)

    @staticmethod
    def fun_of(msg: bytes) -> str:
        return bp.print_hex_string(bp.split_byte(msg, 12, 13))

    def is_online(self, imei: int) -> bool:
        return imei in self._channels

    def save_channel(self, writer: asyncio.StreamWriter, msg: bytes, ip: str = "") -> None:
        """원본 saveChannel: 비로컬 + imei 존재 시 채널 등록(최초 1회)."""
        imei = self.imei_of(msg)
        # 원본은 127.0.0.1 접속을 무시했으나, 로컬 에뮬레이터 테스트를 위해 허용.
        # if "127.0.0.1" in ip:
        #     return
        if imei and imei not in self._channels:
            self._channels[imei] = writer
            LOGGER.info("클라이언트 imei=【%s】, ip=【%s】 서버에 연결됐습니다!", imei, ip)

    def delete_channel_by_imei(self, imei: int | None) -> None:
        """원본 deleteChannel: 연결 종료 시 매핑 제거."""
        if imei is not None:
            self._channels.pop(imei, None)
            LOGGER.warning("클라이언트 imei=【%s】 연결이 끊어졌습니다!", imei)

    def send_msg(self, msg: str | bytes) -> bool:
        """원본 sendMsg: imei 채널로 프레임 전송."""
        if isinstance(msg, str):
            msg = bp.hex_string_to_bytes(msg.replace(" ", "").replace("\n", ""))
        imei = self.imei_of(msg)
        writer = self._channels.get(imei)
        if writer is None:
            LOGGER.warning("imei=%s 대응 채널이 존재하지 않습니다!", imei)
            return False
        writer.write(msg)
        if RecordHeart.record_heart:
            fun = self.fun_of(msg)
            LOGGER.warning("imei=【%s】,fun=【%s】,frame=%s", imei, fun, bp.print_hex_string(msg))
        return True

    def send_msg_sync(self, msg: str | bytes):
        """원본 sendMsgSync: future 생성 후 송신. future 반환."""
        if isinstance(msg, str):
            msg = bp.hex_string_to_bytes(msg.replace(" ", "").replace("\n", ""))
        imei = self.imei_of(msg)
        fun = self.fun_of(msg)
        msg_no = self.msg_no(msg)
        fut = future_manager.create(imei, fun, msg_no)
        self.send_msg(msg)
        return fut

    def receive_msg(self, msg: bytes, ip: str = "") -> None:
        """원본 receiveMsg: 비로컬 + fun!=00 이면 해당 요청 future 완료."""
        imei = self.imei_of(msg)
        fun = self.fun_of(msg)
        # 로컬 에뮬레이터 테스트를 위해 127.0.0.1 제한 해제.
        # if "127.0.0.1" in ip:
        #     return
        if imei and fun.lower() != "00":
            msg_no = self.msg_no(msg)
            future_manager.future_complete(imei, fun, msg_no, True, msg)


channel_manager = AgvChannelManager()
