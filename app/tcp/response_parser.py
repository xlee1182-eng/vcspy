"""AGV 응답 프레임 해석.

원본 com.ygcloud.ygvcs.primaryserver.tcp.ByteProcess.is0xFFOr0x00 이식.
응답 HEX 문자열에서 플래그(FF=성공)를 읽고, 실패 시 funcode 별 FLAG_* 배열로
사람이 읽을 메시지를 매핑한다.
"""
from __future__ import annotations

from app.tcp import byte_process as bp
from app.tcp import constants as K
from app.tcp import flags as F
from app.tcp.json_msg import JsonMsg

_FC = K.FUN_CODES

# 응답 funcode(resp[24:26]) → FLAG 배열 (원본 elif 체인)
_FLAG_MAP = {
    _FC[0]: F.FLAG_03,
    _FC[72]: F.FLAG_72,
    _FC[6]: F.FLAG_06,
    _FC[7]: F.FLAG_07,
    _FC[8]: F.FLAG_08,
    _FC[27]: F.FLAG_0A,
    _FC[16]: F.FLAG_11,
    _FC[5]: F.FLAG_12,
    _FC[18]: F.FLAG_22,
    _FC[17]: F.FLAG_23,
    _FC[21]: F.FLAG_28,
    _FC[22]: F.FLAG_29,
    _FC[23]: F.FLAG_30,
    _FC[24]: F.FLAG_31,
    _FC[26]: F.FLAG_35,
    _FC[28]: F.FLAG_36,
    _FC[31]: F.FLAG_49,
    _FC[30]: F.FLAG_51,
    _FC[61]: F.FLAG_53,
    _FC[37]: F.FLAG_54,
    _FC[40]: F.FLAG_58,
    _FC[41]: F.FLAG_59,
    _FC[42]: F.FLAG_60,
    _FC[43]: F.FLAG_61,
    _FC[67]: F.FLAG_73,
    _FC[89]: F.FLAG_90,
}

# 응답 플래그를 resp[30:32] 에서 읽는 특수 funcode(task.funCode 기준)
_FLAG_AT_30 = {_FC[28], _FC[29], _FC[90], _FC[91], _FC[92], _FC[93], _FC[94]}

# _FAIL_DEFAULT = "指令执行失败，请检查叉车是否在对应的指令模式下！"
_FAIL_DEFAULT = "명령 실행 실패, 지게차가 해당 명령 모드에 있는지 확인해 주세요!"


def is_0xff_or_0x00(task) -> JsonMsg:
    """원본 is0xFFOr0x00(task). task: funCode, responseMsg 보유."""
    msg = JsonMsg.fail()
    msg.otherData = task.responseMsg
    resp = task.responseMsg
    if not resp or len(resp) <= 30:
        return msg

    # 특수: funCode == FUN_CODES[2] ("0D")
    if task.funCode == _FC[2]:
        flag = resp[28:30]
        if flag != "FF":
            msg.msg = _FAIL_DEFAULT if flag == "00" else flag
        else:
            msg.status = True
            msg.msg = flag
        return msg

    fun_code = resp[24:26]
    flag = resp[28:30]

    if task.funCode == _FC[75] and flag == "03":
        msg.status = True
        # msg.msg = "操作成功！"
        msg.msg = "작업 성공!"
        return msg

    if task.funCode in _FLAG_AT_30:
        flag = resp[30:32]

    if flag == "FF":
        msg.status = True
        # msg.msg = "操作成功！"
        msg.msg = "작업 성공!"
        return msg

    msg.status = False
    idx = bp.bytes_to_int(bp.hex_string_to_bytes(flag), 1)

    if fun_code in (_FC[93], _FC[94]):  # B2/B3: 인덱스 숫자 그대로
        msg.msg = str(idx)
        return msg

    arr = _FLAG_MAP.get(fun_code)
    if arr is not None:
        msg.msg = arr[idx] if idx <= len(arr) - 1 else flag
    else:
        msg.msg = _FAIL_DEFAULT
        if flag == "01":
            msg.msg = "01"
    return msg
