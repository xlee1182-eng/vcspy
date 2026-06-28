"""Device 요청 폼/DTO (Pydantic).

원본 webservice.form.device.* 및 dto.device.* 이식.
- warp 엔드포인트 폼 : BaseForm 상속 (공통 인증 필드 포함)
- web  엔드포인트 폼 : WebForm 상속 (인증 필드 없음)
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.base_form import BaseForm, WebForm


# ──────────────────────────────────────────────
# warp 엔드포인트 폼 (BaseForm — 인증 필드 포함)
# ──────────────────────────────────────────────

class DeviceInfoForm(WebForm):
    """장비 목록/심박 조회 — 필수값 없음 (warp·web 공용, 인증 필드 제외)."""


class DeviceAddForm(BaseForm):
    """장비 추가 (warp/addDevice)."""

    deviceImei: str | None = None
    ipStr: str | None = None
    deviceName: str | None = None
    type: str | None = None
    isEnable: str | None = None
    codeAct: str | None = None
    action: str | None = None

    _validations = (
        ("deviceImei", "IMEI는 비어있을 수 없습니다"),
        ("deviceName", "이름은 비어있을 수 없습니다"),
        ("type", "장치 유형은 비어있을 수 없습니다"),
        ("isEnable", "활성화 여부는 비어있을 수 없습니다"),
    )


class DeviceEditForm(BaseForm):
    """장비 수정 (warp/editDevice)."""

    deviceImei: str | None = None
    deviceName: str | None = None
    isEnable: str | None = None
    codeAct: str | None = None
    action: str | None = None

    _validations = (("deviceImei", "IMEI는 비어있을 수 없습니다"),)


class DeviceDelForm(BaseForm):
    """장비 삭제 (warp/delDevice)."""

    deviceImei: str | None = None

    _validations = (("deviceImei", "IMEI는 비어있을 수 없습니다"),)


class DeviceTrafficInfoForm(BaseForm):
    """전체 장치 트래픽 정보 조회 (warp/getAllDeviceTrafficInfo)."""

    deviceImei: int | None = None
    floor: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


# ──────────────────────────────────────────────
# web 엔드포인트 폼 (WebForm — 인증 필드 없음)
# ──────────────────────────────────────────────

class DeviceInitForm(WebForm):
    """위치 초기화 (web/initLocation). deviceImei + siteCode 필수."""

    deviceImei: int | None = None
    siteCode: int | None = None

    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("siteCode", "스테이션 위치는 비어있을 수 없습니다"),
    )


class DeviceTerminateForm(WebForm):
    """작업 종료 (web/terminateTask). deviceImei 필수."""

    deviceImei: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceWifiInitForm(WebForm):
    """wifi 재시작 임계값 설정 (web/setWifiRestartValue)."""

    deviceImei: int | None = None
    wifiRestartValue: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceParamsSetForm(WebForm):
    """포크리프트 파라미터 설정 (web/setDeviceParams)."""

    deviceImei: int | None = None
    palletWidth: float | None = None
    noCargoHeight: float | None = None
    liftHeight: float | None = None
    haveCargoHeight: float | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceWebInfoForm(WebForm):
    """장치 상태 조회(외부) web/device/getDeviceInfo."""

    deviceImei: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class InitPointsSetForm(WebForm):
    """다중 시작점 설정 (web/setInitPoints)."""

    deviceImei: int | None = None
    sites: list[int] | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceWifiGetForm(WebForm):
    """WiFi 신호 강도 조회 (web/getWifiStrength)."""

    deviceImei: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DevicePauseAndStartForm(WebForm):
    """일시정지/재시작 (web/setPauseAndStart). status: 1=일시정지, 2=재시작."""

    deviceImei: int | None = None
    status: str | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceTreatInfoForm(WebForm):
    """구분 상태 장치 정보 조회 (web/getDeviceTreatInfo)."""

    deviceImei: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceDataForm(BaseForm):
    """장치 운행 데이터 조회 (warp/getTimeAndData)."""

    deviceImei: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


# ──────────────────────────────────────────────
# DTO
# ──────────────────────────────────────────────

class DeviceHeartBeat(BaseModel):
    """dto.device.DeviceHeartBeat."""

    deviceImei: int | None = None
    command: str | None = None


class DeviceInfoDto(BaseModel):
    """dto.device.DeviceInfoDto — 타입별 장비 목록."""

    deviceAGV: list[dict[str, Any]] | None = None
    deviceCamera: list[dict[str, Any]] | None = None
    deviceCall: list[dict[str, Any]] | None = None
    deviceScan: list[dict[str, Any]] | None = None
