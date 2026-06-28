"""바이트/프레임 처리 유틸.

원본 com.ygcloud.ygvcs.primaryserver.tcp.ByteProcess 이식(핵심 함수).
Java signed byte 연산은 모두 0~255 마스킹(& 0xFF)으로 동일 의미를 보존한다.

참고: 원본 is0xFFOr0x00(응답 파서)은 app/tcp/response_parser.py 로 분리 이식됨.
"""
from __future__ import annotations

import struct

from app.tcp import constants
from app.tcp.crc import crc_16_ccitt_false

_HEX = "0123456789ABCDEF"


def hex_string_to_bytes(hex_string: str | None) -> bytes | None:
    """원본 hexStringToBytes. 공백 제거 후 대문자화하여 2자리씩 변환."""
    if hex_string is None or hex_string == "":
        return None
    if " " in hex_string:
        hex_string = hex_string.replace(" ", "")
    hex_string = hex_string.upper()
    length = len(hex_string) // 2
    out = bytearray(length)
    for i in range(length):
        pos = i * 2
        hi = _HEX.index(hex_string[pos])
        lo = _HEX.index(hex_string[pos + 1])
        out[i] = ((hi << 4) | lo) & 0xFF
    return bytes(out)


def print_hex_string(b: bytes | int | None) -> str | None:
    """원본 printHexString. 바이트열(또는 단일 바이트)을 대문자 HEX 문자열로."""
    if b is None:
        return None
    if isinstance(b, int):
        return f"{b & 0xFF:02X}"
    return "".join(f"{x & 0xFF:02X}" for x in b)


def int_to_bytes(value: int, size: int) -> bytes:
    """원본 intToBytes. 빅엔디안, size(1~4) 바이트."""
    value &= 0xFFFFFFFF
    if size == 1:
        return bytes([value & 0xFF])
    if size == 2:
        return bytes([(value >> 8) & 0xFF, value & 0xFF])
    if size == 3:
        return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])
    return bytes([(value >> 24) & 0xFF, (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])


def int_to_hex(value: int, size: int) -> str:
    return print_hex_string(int_to_bytes(value, size))


def bytes_to_int(b: bytes, length: int) -> int:
    """원본 bytesToInt. 빅엔디안. 길이 부족 시 원본과 동일하게 보정."""
    if b is None:
        return 0
    b = bytes(b)
    if len(b) < length:
        b1 = bytearray(length)
        for i in range(length):
            b1[length - i - 1] = b[i] if i <= len(b) - 1 else 0
        b = bytes(b1)
    if len(b) > 0 and len(b) == length:
        if length == 1:
            return b[0] & 0xFF
        if length == 2:
            return (b[1] & 0xFF) | ((b[0] & 0xFF) << 8)
        if length == 3:
            return (b[2] & 0xFF) | ((b[1] & 0xFF) << 8) | ((b[0] & 0xFF) << 16)
        if length == 4:
            return (b[3] & 0xFF) | ((b[2] & 0xFF) << 8) | ((b[1] & 0xFF) << 16) | ((b[0] & 0xFF) << 24)
        return 0
    return 0


def split_byte(reqb: bytes | None, start: int, end: int) -> bytes | None:
    """원본 splitByte(byte[]). 범위 밖이면 원본처럼 0 4바이트 반환."""
    try:
        if reqb is not None and len(reqb) >= 8:
            if len(reqb) < end:
                return int_to_bytes(0, 4)
            return bytes(reqb[start:end])
        return None
    except Exception:
        return int_to_bytes(0, 4)


def split_byte_hex(hex_str: str, start: int, end: int) -> bytes | None:
    return split_byte(hex_string_to_bytes(hex_str), start, end)


def checked_send_frame(reqb: bytes | None) -> bool:
    """원본 checkedSendFrame: 길이>9 이고 헤더가 FRAME_HEAD."""
    if reqb is None or len(reqb) <= 9:
        return False
    return reqb[0:4] == constants.FRAME_HEAD


def checked_recv_frame(reqb: bytes | None) -> bool:
    """원본 checkedRecvFrame: 헤더 FRAME_RECV_HEAD + 종단 FRAME_RECV_END."""
    if reqb is None or len(reqb) <= 9:
        return False
    if reqb[0:4] != constants.FRAME_RECV_HEAD:
        return False
    return reqb[-4:] == constants.FRAME_RECV_END


def get_crc_to_send(hex_str: str, pasd: str | None = None) -> str:
    """원본 getCRCToSend.

    pasd 가 있으면: head(8hex) 이후 본문 + 비밀번호 바이트로 CRC-16 계산.
    pasd 가 None 이면 단일 인자 오버로드(본문만으로 CRC).
    pasd 가 빈 문자열이면 원본처럼 "0000" 고정.
    """
    old = hex_str
    cleaned = hex_str.replace(" ", "").replace("\n", "") if " " in hex_str else hex_str

    if pasd is None:
        # getCRCToSend(String) 오버로드
        body = cleaned[8:]
        bs = hex_string_to_bytes(body) or b""
        crc = crc_16_ccitt_false(bs, 2)
        return old + " " + print_hex_string(int_to_bytes(crc, 2)) + " " + " 50AFA05F"

    if pasd == "":
        return old + "0000" + " 50AFA05F"

    body = cleaned[8:]
    bs = hex_string_to_bytes(body) or b""
    bs2 = pasd.encode("latin-1")
    crc = crc_16_ccitt_false(bs + bs2, 2)
    return old + "" + print_hex_string(int_to_bytes(crc, 2)) + " " + " 50AFA05F"


def checked_crc(reqb: bytes, password: str | None = None) -> bool:
    """원본 checkedCrc. 송/수신 프레임이면 끝 CRC 검증.

    password 가 있으면 본문+비밀번호로 CRC 계산하여 비교.
    """
    try:
        if checked_send_frame(reqb) or checked_recv_frame(reqb):
            crc_old = bytes_to_int(split_byte(reqb, len(reqb) - 6, len(reqb) - 4), 2)
            cont = split_byte(reqb, 4, len(reqb) - 6) or b""
            if password:
                cont = bytes(cont) + password.encode("latin-1")
            crc_new = crc_16_ccitt_false(bytes(cont), 2)
            return crc_old == crc_new
        return False
    except Exception:
        return False


def get_request_code(hex_str: str) -> str:
    """원본 getRequestCode: 'imei:seq:funCode'."""
    reqb = hex_string_to_bytes(hex_str)
    seq = bytes_to_int(split_byte(reqb, 4, 8), 4)
    imei = bytes_to_int(split_byte(reqb, 8, 12), 4)
    fun_code = print_hex_string(split_byte(reqb, 12, 13))
    return f"{imei}:{seq}:{fun_code}"


def bytes_to_binary(b: bytes) -> str:
    """원본 bytesToBinary: bytesToInt(b,4) 의 2진 문자열(선행 0 없음)."""
    return bin(bytes_to_int(b, 4))[2:]


def out_imei(msg: bytes) -> int:
    """원본 outImei: msg[3],msg[2] 를 2바이트 정수로."""
    return bytes_to_int(bytes([msg[3], msg[2]]), 2)


def byte_to_float(b: bytes) -> float:
    """원본 byteToFloat: 리틀엔디안 IEEE754."""
    return struct.unpack("<f", bytes(b[0:4]))[0]


def byte_to_float2(b: bytes) -> float:
    """원본 byteToFloat2: 빅엔디안 IEEE754."""
    return struct.unpack(">f", bytes(b[0:4]))[0]


def float_to_byte(f: float) -> bytes:
    """원본 floatToByte: 빅엔디안 비트 후 역순 -> 리틀엔디안."""
    return struct.pack("<f", f)
