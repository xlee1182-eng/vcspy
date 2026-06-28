"""Site/Storage 요청 폼/DTO (Pydantic).

원본 webservice.form.site.* 이식.
- warp 엔드포인트 폼 : BaseForm 상속 (공통 인증 필드 포함)
- web  엔드포인트 폼 : WebForm 상속 (인증 필드 없음)
"""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.base_form import BaseForm, WebForm


# ──────────────────────────────────────────────
# warp 엔드포인트 폼 (BaseForm)
# ──────────────────────────────────────────────

class SiteInfoForm(BaseForm):
    """보관위치(사이트) 목록 조회 — 필수값 없음."""


class SiteEditForm(BaseForm):
    """보관위치 수정 (warp/editStorage)."""

    storageId: str | None = None
    siteName: str | None = None
    isEnable: str | None = None

    _validations = (("storageId", "보관위치 ID는 비어있을 수 없습니다"),)


class StorageInfo(BaseModel):
    """StorageDeviceAddForm 내 보관위치 항목."""

    siteCode: int | None = None
    siteName: str | None = None
    siteType: str | None = None
    orderNo: int | None = None


class StorageDeviceAddForm(BaseForm):
    """보관위치-장비 바인딩 (warp/editStorageDevice)."""

    deviceImei: str | None = None
    ipStr: str | None = None
    type: str | None = None
    deviceName: str | None = None
    storageInfos: list[StorageInfo] | None = None

    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("type", "장치 유형은 비어있을 수 없습니다"),
        ("deviceName", "장치 이름은 비어있을 수 없습니다"),
        ("storageInfos", "보관위치 정보는 비어있을 수 없습니다"),
    )


class StorageDeviceDelForm(BaseForm):
    """보관위치-장비 바인딩 해제 (warp/delStorageDevice)."""

    siteCode: int | None = None

    _validations = (("siteCode", "스테이션 코드는 비어있을 수 없습니다"),)


class StorageDeviceInfoForm(BaseForm):
    """장비별 바인딩된 보관위치 조회 (warp/getSiteByDevice)."""

    deviceImei: str | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class StorageStatusEditForm(BaseForm):
    """보관위치 상태 변경(수동) (warp/editStorageStatus)."""

    siteCode: int | None = None
    siteStatus: str | None = None
    actionType: str | None = None

    _validations = (
        ("siteCode", "스테이션 코드는 비어있을 수 없습니다"),
        ("siteStatus", "보관위치 상태는 비어있을 수 없습니다"),
        ("actionType", "작업 유형은 비어있을 수 없습니다"),
    )


class AreaStatusEditForm(BaseForm):
    """구역 일괄 상태 변경 (warp/editAreaStatus)."""

    taskTemplateId: int | None = None
    siteStatus: str | None = None
    type: str | None = None

    _validations = (
        ("taskTemplateId", "템플릿 ID는 비어있을 수 없습니다"),
        ("siteStatus", "보관위치 상태는 비어있을 수 없습니다"),
        ("type", "작업 구역은 비어있을 수 없습니다"),
    )


class StorageStatusScanEditForm(BaseForm):
    """보관위치 상태 변경(스캐너) (warp/editScanStorageStatus)."""

    deviceImei: str | None = None
    siteCode: int | None = None
    siteStatus: str | None = None
    deviceType: str | None = None
    actionType: str | None = None

    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("siteCode", "스테이션 코드는 비어있을 수 없습니다"),
        ("deviceType", "장치 유형은 비어있을 수 없습니다"),
    )


# ──────────────────────────────────────────────
# web 엔드포인트 폼 (WebForm — 인증 필드 없음)
# ──────────────────────────────────────────────

class SiteManageAllForm(WebForm):
    """전체 사이트 조회(외부) web/siteManage/getAllSite."""

    customerId: str | None = None


class SiteManageInfoForm(WebForm):
    """현재 사이트 정보 조회(외부) web/siteManage/getSiteInfo."""

    siteCode: int | None = None

    _validations = (("siteCode", "스테이션 코드는 비어있을 수 없습니다"),)


class StorageInfoDto(BaseModel):
    """StorageSkuSetForm 내 보관위치-SKU 항목 (원본 StorageInfoDto)."""

    siteCode: int | None = None
    # siteStatus: str | None = None
    skuCode: str | None = None


class StorageInfoGetForm(WebForm):
    """code 기준 보관위치 물자·공만 조회 (web/siteManage/getStorageInfo)."""

    siteCodes: list[int] | None = None


class StorageSkuSetForm(WebForm):
    """보관위치(열) SKU 바인딩 (web/siteManage/setStorageSkus)."""

    storageSkus: list[StorageInfoDto] | None = None


class StorageWebEditForm(WebForm):
    """보관위치 상태 변경(외부) (web/siteManage/editStorageStatus).

    actionType 은 폼에 존재하지만 실제 로직은 DB 조회로 결정한다.
    """

    siteCode: int | None = None
    siteStatus: str | None = None
    # actionType: str | None = None

    _validations = (
        ("siteCode", "스테이션 코드는 비어있을 수 없습니다"),
        ("siteStatus", "보관위치 상태는 비어있을 수 없습니다"),
    )
