"""도메인 코드값 상수.

근거: 운영 DB 스키마(schema.sql)의 컬럼 COMMENT + 디컴파일된 원본 로직.
원본은 문자열/문자 코드값을 직접 비교하므로, 값은 원본과 동일한 문자열로 유지한다.
"""
from __future__ import annotations

from enum import StrEnum


class SendFlag(StrEnum):
    """yg_user_task.send_flag — 작업 송신/진행 상태."""

    CREATED = "1"        # 신규 생성
    EXECUTING = "2"      # 실행 중
    COMPLETED = "3"      # 완료
    EXEC_FAILED = "4"    # 실행 실패
    SENT = "5"           # 전송됨
    SEND_FAILED = "6"    # 전송 실패
    CANCELLED = "7"      # 취소됨


class TaskType(StrEnum):
    """yg_user_task.task_type — 작업 유형."""

    ASSIGNED = "1"       # 지정 차량
    UNASSIGNED = "2"     # 미지정 차량
    MULTI = "3"          # 다중 차량
    CALL_DEVICE = "4"    # 호출 장비


class DeviceType(StrEnum):
    """device_type / yg_device.type — 장비 유형."""

    MANUAL = "0"         # 수동
    AGV = "1"            # AGV
    CAMERA = "2"         # 카메라
    CALL_BOX = "3"       # 호출박스
    SCANNER = "4"        # 스캐너


class PickPlaceState(StrEnum):
    """yg_user_task.pick_place_state — 취/방화 상태."""

    NONE = "0"           # 무동작
    PICKED = "1"         # 취화 완료
    PLACED = "2"         # 방화 완료


class DeviceModel(StrEnum):
    """yg_device_memory_table.model — 장비 동작 모드.

    원본 TcpConstants: MODEL_FREE/LEARN/RUN/CALIB/SET 와 대응.
    """

    FREE = "0"           # 공회전/대기
    LEARN = "1"          # 경로 학습
    RUN = "2"            # 주행/작업
    CONFIG = "3"         # 설정


# 작업 상태 전이(추정 — 디컴파일 로직으로 확정 예정)
#  CREATED(1) -> SENT(5) -> EXECUTING(2) -> COMPLETED(3)
#                       \-> SEND_FAILED(6)
#                            EXECUTING(2)  -> EXEC_FAILED(4)
#  any active            -> CANCELLED(7)
# 원본 com.ygcloud.ygvcs.utils.Constants 배열 (TaskOpService 등에서 인덱스로 참조)
CODE_ACT = ["0", "1", "2", "3", "4"]
SITE_TYPE = ["0", "1", "2"]
SITE_STATUS = ["0", "1", "2", "3"]
TASK_TYPE = ["1", "2", "3"]
HANDLES = ["0", "1", "2"]
TASK_IS_CANCEL = ["0", "1", "2"]
SEND_FLAG_ARR = ["0", "1", "2", "3", "4", "5", "6", "7"]


ACTIVE_SEND_FLAGS = {SendFlag.CREATED, SendFlag.EXECUTING, SendFlag.SENT}
FINISHED_SEND_FLAGS = {
    SendFlag.COMPLETED,
    SendFlag.EXEC_FAILED,
    SendFlag.SEND_FAILED,
    SendFlag.CANCELLED,
}
