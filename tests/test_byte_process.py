"""ByteProcess/CRC 프로토콜 유틸 검증.

원본 Java 의 정수/바이트 의미를 그대로 보존했는지, CRC 송신/검증이
왕복(round-trip)으로 일치하는지 확인한다.
실행: python tests/test_byte_process.py
"""
from __future__ import annotations

from app.tcp import byte_process as bp
from app.tcp import constants
from app.tcp.crc import crc_16_ccitt_false

ok = 0
fail = 0


def check(name: str, cond: bool) -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


# 1) hex <-> bytes 왕복
b = bp.hex_string_to_bytes("40BF807F")
check("hexStringToBytes(40BF807F)", b == constants.FRAME_HEAD)
check("printHexString 왕복", bp.print_hex_string(b) == "40BF807F")
check("공백 포함 hex 처리", bp.hex_string_to_bytes("40 BF 80 7F") == constants.FRAME_HEAD)

# 2) intToBytes / bytesToInt (빅엔디안)
check("intToBytes(258,2)=0102", bp.print_hex_string(bp.int_to_bytes(258, 2)) == "0102")
check("bytesToInt(0102)=258", bp.bytes_to_int(bp.hex_string_to_bytes("0102"), 2) == 258)
check("intToBytes(16777215,3)=FFFFFF", bp.int_to_hex(16777215, 3) == "FFFFFF")
check("bytesToInt 4byte 큰값", bp.bytes_to_int(bp.int_to_bytes(305419896, 4), 4) == 305419896)

# 3) printHexString 단일 바이트
check("printHexString(byte 0x0A)", bp.print_hex_string(0x0A) == "0A")

# 4) CRC-16/CCITT-FALSE 알려진 벡터 ("123456789" -> 0x29B1)
check("CRC '123456789' = 0x29B1", crc_16_ccitt_false(b"123456789") == 0x29B1)

# 5) 송신 프레임 생성 후 CRC 검증 왕복 (password 포함)
#    head + 본문(seq/imei/funcode/data) 구성 -> getCRCToSend -> checkedCrc 통과해야 함
body = "40BF807F" + "00000001" + "0012F78B" + "71" + "0007" + "00CDEF" + "00000001"
frame_hex = bp.get_crc_to_send(body, "123456789")
frame_bytes = bp.hex_string_to_bytes(frame_hex)
check("getCRCToSend -> 헤더 보존", frame_bytes[0:4] == constants.FRAME_HEAD)
check("getCRCToSend -> 종단 50AFA05F", frame_bytes[-4:] == constants.FRAME_END)
check("checkedCrc(생성프레임, pwd) 통과", bp.checked_crc(frame_bytes, "123456789") is True)
check("checkedCrc 잘못된 pwd 실패", bp.checked_crc(frame_bytes, "000000000") is False)

# 6) get_request_code 포맷
rc = bp.get_request_code(frame_hex)
check("getRequestCode 'imei:seq:fun'", rc.count(":") == 2)

print(f"\n결과: {ok} passed, {fail} failed")
if fail:
    raise SystemExit(1)
