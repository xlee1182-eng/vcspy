"""TCP 프로토콜 상수.

원본 com.ygcloud.ygvcs.primaryserver.tcp.TcpConstants (및 utils.TcpConstants) 이식.
바이트 배열은 Java signed byte 값을 부호 없는 0~255로 변환해 보관한다.
주의: 원본에 primaryserver/TcpConstants 와 utils/TcpConstants 두 벌이 있고
      FUN_CODES/FUN_LENTHS 일부가 미세하게 다르다. 송신 경로(initLocation 등)는
      primaryserver 판을 쓰므로 그쪽을 기본으로 채택한다.
"""
from __future__ import annotations

# 프레임 헤더/종단 (Java signed byte -> 부호없는 int)
FRAME_HEAD = bytes([64, 0xBF, 0x80, 127])         # 40 BF 80 7F
FRAME_END = bytes([0x50, 0xAF, 0xA0, 0x5F])       # 50 AF A0 5F
FRAME_END2 = bytes([0x50, 0xAF, 0xA0, 0x5F, 0xA0])
FRAME_RECV_HEAD = bytes([32, 0xBF, 64, 127])      # 20 BF 40 7F
FRAME_RECV_END = bytes([0x50, 0xAF, 0xA0, 0x5F])
FRAME_ELEVATOR_RECEIVED_HEAD_A = bytes([0xAA, 0xAA, 0xAA, 0xAA])
FRAME_ELEVATOR_SEND_HEAD_B = bytes([0xBB, 0xBB, 0xBB, 0xBB])
RESPONSE_DATA = bytes([0, 0, 0, 0])

FRAME_ELEVATOR_RECEIVED_HEAD = "AAAAAAAA"
FRAME_HEAD_HEX = "40BF807F"
FRAME_HEAD_HEX2 = "20BF407F"
FRAME_END_HEX = " 50AFA05F"
FRAME_ELEVATOR_SEND_HEAD = "BBBBBBBB"
MSG_NUM = "00 00 00 02 "

# 동작 모드
MODEL_FREE = "00"
MODEL_LEARN = "01"
MODEL_RUN = "02"
MODEL_SET = "03"
AUTO_LEARN_MODEL = "05"
MODEL_CALIB = "06"

CRC_FIXED_PWD = "EmJJ8y5*"
COMMUNICATION_KEY = "123456789"

MODEL_TYPE = ["00", "01", "02", "03", "04", "05"]
SEND_FLAG = ["0", "1", "2", "3", "4"]

# 기능 코드 테이블 (primaryserver.TcpConstants 판)
FUN_CODES = [
    "03", "04", "0D", "0E", "0B", "12", "06", "07", "05", "09", "08", "1E",
    "1A", "FE", "20", "21", "11", "23", "22", "24", "13", "28", "29", "30",
    "31", "32", "35", "0A", "36", "50", "51", "49", "1B", "1C", "52", "19",
    "56", "54", "55", "57", "58", "59", "60", "61", "1D", "1C", "1F", "62",
    "63", "64", "65", "66", "40", "41", "42", "43", "44", "45", "46", "47",
    "48", "53", "67", "68", "70", "71", "72", "73", "74", "A8", "A9", "76",
    "77", "78", "01", "79", "80", "81", "82", "83", "84", "85", "C0", "87",
    "C1", "C2", "C3", "86", "89", "90", "91", "95", "97", "B2", "B3",
    "B5", "9E", "C4",
]

FUN_LENTHS = [
    # "01", "06", "06", "00", "00", "07", "可变（0x（4n+5））", "09", "0F", "01",
    "01", "06", "06", "00", "00", "07", "가변（0x（4n+5））", "09", "0F", "01",
    "0xn", "0xn", "04", "01", "01", "01", "04", "01", "01", "01", "01", "23",
    "30", "35", "07", "0A", "35", "0D", "07", "0001", "5*n", "n", "n", "n",
    "00", "19", "00", "01", "04", "01", "01", "01", "01", "01", "04", "00",
    "02", "01", "00", "05", "00", "00", "01", "01", "01", "55", "56", "57",
    "58", "59", "60", "61", "62", "63", "64", "65", "66", "11", "00", "01",
    "00", "7*n", "00", "46", "01", "08", "00", "0A", "00", "00", "19", "0002",
    "05", "0003", "0001", "0001", "0001", "01", "01", "0D", "0001",
]
