"""Task 요청 폼/DTO (Pydantic).

원본 webservice.form.task.* 이식.
- warp 엔드포인트 폼 : BaseForm 상속 (공통 인증 필드 포함)
- web  엔드포인트 폼 : WebForm 상속 (인증 필드 없음)
"""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.base_form import BaseForm, WebForm


# ──────────────────────────────────────────────
# 공유 sub-모델
# ──────────────────────────────────────────────

class DeviceReg(BaseModel):
    """form.task.DeviceReg — 템플릿에 등록할 장비."""

    deviceImei: int | None = None
    deviceName: str | None = None


class SiteForm(BaseModel):
    """form.task.SiteForm — 시작/종료 사이트 + 예비위치(standbyList)."""

    siteCode: int = 0
    siteName: str | None = None
    storageId: str | None = None
    storageName: str | None = None
    orderNo: int | None = None
    standbyList: list["SiteForm"] | None = None


class TaskWayPointsForm(BaseModel):
    """form.task.TaskWayPointsForm — 경유점."""

    siteCode: int = 0
    siteHandel: str | None = "0"
    storageHeight: int | None = None
    isWait: str | None = "0"
    waitTime: int | None = 0


SiteForm.model_rebuild()


# ──────────────────────────────────────────────
# warp 엔드포인트 폼 (BaseForm — 인증 필드 포함)
# ──────────────────────────────────────────────

class TaskAddForm(BaseForm):
    """작업 템플릿 추가 (warp/addTaskTemp)."""

    taskName: str | None = None
    startSites: list[SiteForm] = []
    endSites: list[SiteForm] = []
    devices: list[DeviceReg] | None = None
    taskTemplateId: int | None = None

    _validations = (("taskName", "작업명은 비어있을 수 없습니다"),)


class TaskEditForm(BaseForm):
    """작업 템플릿 수정/삭제/조회 (warp/editTaskTemp·delTaskTemp·selectTaskTempInfo)."""

    taskTemplateId: int | None = None
    runStatus: str | None = None

    _validations = (("taskTemplateId", "템플릿 ID는 비어있을 수 없습니다"),)


class TaskEditInfoForm(BaseForm):
    """작업 템플릿 전체 수정 (warp/editTaskTempInfo)."""

    taskName: str | None = None
    taskTemplateId: int | None = None
    startSites: list[SiteForm] = []
    endSites: list[SiteForm] = []
    devices: list[DeviceReg] | None = None

    _validations = (
        ("taskName", "작업명은 비어있을 수 없습니다"),
        ("taskTemplateId", "작업 ID는 비어있을 수 없습니다"),
    )


class TaskClearTempForm(BaseForm):
    """작업 템플릿 전체 초기화 (warp/clearTaskTemp). 필수값 없음."""


class TaskSelectListForm(BaseForm):
    """작업 템플릿 목록 조회 (warp/selectTaskTempList)."""

    taskTemplateId: int | None = None


class TaskCallForm(BaseForm):
    """장비 호출 작업 (warp/callDeviceTask)."""

    deviceImei: str | None = None
    siteCode: int | None = None
    startHandel: str | None = None
    callType: str | None = None

    _validations = (
        ("siteCode", "호출 지점은 비어있을 수 없습니다"),
        ("callType", "차량 호출 유형은 비어있을 수 없습니다"),
    )


class TaskPointsForm(BaseForm):
    """점대점 작업 송신 (warp/sendPointsTask)."""

    deviceImei: int | None = None
    startSiteCode: int | None = None
    startSiteName: str | None = None
    endSiteCode: int | None = None
    endSiteName: str | None = None
    startStorageHeight: int | None = None
    endStorageHeight: int | None = None
    startHandel: str | None = None
    endHandel: str | None = None

    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("startSiteCode", "시작점은 비어있을 수 없습니다"),
    )


class TaskInfoForm(BaseForm):
    """작업 목록 조회 (warp/getUserTaskInfo). sendFlag 선택 필터."""

    sendFlag: str | None = None


class TaskCallGetForm(BaseForm):
    """호출 작업 조회 (warp/getCallDeviceTask). 필수값 없음."""


class TaskCallCancelForm(BaseForm):
    """호출 작업 취소 (warp/cancelCallDeviceTask). userName은 BaseForm 공유."""


class TaskDelForm(BaseForm):
    """작업 삭제 (warp/delUserTask)."""

    userTaskId: int | None = None

    _validations = (("userTaskId", "작업 ID는 비어있을 수 없습니다"),)


class TaskCountForm(BaseForm):
    """작업 통계 (warp/getCountTask). type 선택 필터."""

    type: str | None = None


# ──────────────────────────────────────────────
# web 엔드포인트 폼 (WebForm — 인증 필드 없음)
# ──────────────────────────────────────────────

class WebTaskAddForm(WebForm):
    """web/sendTask — 외부 작업 송신 폼 (원본 TaskAddForm)."""

    messageId: str | None = None
    deviceImei: int | None = None
    startSiteCode: int | None = None
    endSiteCode: int | None = None
    startHandel: str | None = None
    endHandel: str | None = None
    startStorageHeight: int | None = None
    endStorageHeight: int | None = None
    upDownHeight: int | None = None
    taskIsCancel: str | None = None
    taskWayPoints: list[TaskWayPointsForm] | None = None
    taskPriority: int | None = None


class TaskStateGetForm(WebForm):
    """작업 상태/취방화 상태 조회 (web/getTaskResult·getPickPlaceState)."""

    customerId: str | None = None
    messageId: str | None = None
    # deviceImei: int | None = None

    _validations = (("messageId", "메시지 ID는 비어있을 수 없습니다"),)


class TaskCancelForm(WebForm):
    """미실행 작업 취소 (web/cancelTask)."""

    # customerId: str | None = None
    deviceImei: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class TaskClearForm(WebForm):
    """전체 작업 초기화 (web/clearTask). 필수값 없음."""


class KeyboardLockSetForm(WebForm):
    """키보드 작업 잠금 설정 (web/setKeyboardLock)."""

    # customerId: str | None = None
    deviceImei: int | None = None
    lockState: int | None = None

    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("lockState", "잠금 상태는 비어있을 수 없습니다"),
    )


class TaskSetForm(WebForm):
    """작업 설정(시작/일시정지/종료) (web/setTask)."""

    # customerId: str | None = None
    messageId: str | None = None
    taskState: str | None = None
    # deviceImei: int | None = None

    _validations = (
        ("messageId", "메시지 ID는 비어있을 수 없습니다"),
        ("taskState", "작업 상태는 비어있을 수 없습니다"),
    )


class TaskRepeatSendForm(WebForm):
    """작업 반복 송신 (web/sendRepeatTask)."""

    messageId: str | None = None

    _validations = (("messageId", "메시지 ID는 비어있을 수 없습니다"),)


class TaskInfoGetForm(WebForm):
    """작업 정보 목록 조회 (web/getTaskInfo). messageIds 또는 deviceImeis 기반 필터."""

    messageIds: list[str] | None = None
    deviceImeis: list[int] | None = None


class TaskCodeGetForm(WebForm):
    """시작점 기준 최근 작업 조회 (web/getTaskByCode)."""

    siteCode: int | None = None


class TaskTreatGetForm(WebForm):
    """구분 작업 상태 조회 (web/getTaskTreatInfo)."""

    # customerId: str | None = None
    messageId: str | None = None

    _validations = (("messageId", "메시지 ID는 비어있을 수 없습니다"),)


class TaskPlanInfoGetForm(WebForm):
    """작업 경로 정보 조회 (web/getTaskPlanInfo). deviceImei 기반 Redis 조회."""

    deviceImei: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)
