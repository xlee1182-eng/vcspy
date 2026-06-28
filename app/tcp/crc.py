"""CRC 유틸.

원본 com.ygcloud.ygvcs.primaryserver.tcp.CrcUtil 이식.
핵심: CRC-16/CCITT-FALSE (init=0xFFFF, poly=0x1021), 바이트당 MSB first.
원본은 length 인자를 받지만 실제로는 전체 바이트를 순회한다(원본 동작 보존).
"""
from __future__ import annotations


def crc_16_ccitt_false(data: bytes, length: int = 2) -> int:
    """원본 crc_16_CCITT_False. length 인자는 원본대로 무시(전체 순회)."""
    crc = 0xFFFF
    polynomial = 0x1021
    for b in data:
        for i in range(8):
            bit = ((b >> (7 - i)) & 1) == 1
            c15 = ((crc >> 15) & 1) == 1
            crc = (crc << 1) & 0xFFFF
            if c15 ^ bit:
                crc ^= polynomial
    return crc & 0xFFFF


def is_pass_crc(src: bytes, length: int) -> bool:
    """원본 isPassCRC: 끝 2바이트가 본문 CRC와 일치하는지."""
    calc = _calc_crc(src, 0, len(src) - length)
    expect = bytes([(calc >> 8) & 0xFF, calc & 0xFF])
    actual = src[-2:]
    return expect[0] == actual[0] and expect[1] == actual[1]


def _calc_crc(buf: bytes, offset: int, crc_len: int) -> int:
    crc = 0xFFFF
    polynomial = 0x1021
    for index in range(offset, offset + crc_len):
        b = buf[index]
        for i in range(8):
            bit = ((b >> (7 - i)) & 1) == 1
            c15 = ((crc >> 15) & 1) == 1
            crc = (crc << 1) & 0xFFFF
            if c15 ^ bit:
                crc ^= polynomial
    return crc & 0xFFFF
