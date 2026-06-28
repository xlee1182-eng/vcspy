"""프레임 디코더 (스트림 → 완전한 프레임).

원본 DelimiterFrameDecoder 의 기능적 대체.
원본 Netty 파이프라인은 구분자 "50AFA05FA0"(FRAME_END + A0) 로 프레임을 자르고,
stripDelimiter=true 로 구분자를 제거한다(원본은 종단 5바이트 중 마지막 A0만 skip하여
FRAME_END 4바이트는 프레임에 남는다 → length 계산은 eol-readerIndex).

여기서는 누적 버퍼에서 구분자 "50AFA05FA0" 를 찾아, 그 직전까지(FRAME_END 포함)를
하나의 프레임으로 산출한다. 최소 길이 16 미만 프레임은 원본처럼 버린다.
"""
from __future__ import annotations

from app.tcp import constants

# 원본 server 파이프라인 구분자: 50 AF A0 5F A0
DELIMITER = bytes([0x50, 0xAF, 0xA0, 0x5F, 0xA0])
MIN_LENGTH = 16
MAX_LENGTH = 51200000


class FrameBuffer:
    """수신 바이트를 누적하고 완전한 프레임 단위로 분리."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        """바이트를 추가하고, 완성된 프레임 목록을 반환."""
        self._buf.extend(data)
        frames: list[bytes] = []
        while True:
            idx = self._buf.find(DELIMITER)
            if idx == -1:
                break
            # 원본: stripDelimiter=true → 마지막 A0만 제거, FRAME_END(4바이트)는 프레임에 포함.
            # 즉 프레임 = 시작 ~ (구분자 시작 + 4) = FRAME_END 까지.
            frame = bytes(self._buf[: idx + 4])
            del self._buf[: idx + len(DELIMITER)]
            if MIN_LENGTH <= len(frame) < MAX_LENGTH:
                frames.append(frame)
            # 길이 미달 프레임은 원본처럼 폐기
        return frames

    def pending(self) -> int:
        return len(self._buf)
