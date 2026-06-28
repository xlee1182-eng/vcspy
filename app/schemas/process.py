"""Process warp 요청 폼/DTO (Pydantic).

원본 ImportSqlForm, ExportSqlInfoDto 이식.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.base_form import BaseForm


class ImportSqlForm(BaseForm):
    """학습 데이터 가져오기 폼.

    data: SiteManageList + ForkliftLineList + SiteInitPointList 를 JSON 직렬화한 문자열.
    """
    data: str | None = None


class ClearAllDataForm(BaseForm):
    """전체 데이터 초기화 (warp/clearAllData). 필수값 없음."""


class IsSyncTaskSourceForm(BaseForm):
    """동기화 작업 출처 설정 폼."""
    syncTaskSource: str | None = None

    _validations = (("syncTaskSource", "syncTaskSource 는 비어있을 수 없습니다"),)


class ToPointSwitchSetForm(BaseForm):
    """회차점 복귀 스위치 설정 폼."""
    toPointSwitch: str | None = None

    _validations = (("toPointSwitch", "toPointSwitch 는 비어있을 수 없습니다"),)


class ToPointTimeSetForm(BaseForm):
    """무작업 회차점 복귀 시간 설정 폼."""
    toPointTime: int | None = None

    _validations = (("toPointTime", "toPointTime 은 비어있을 수 없습니다"),)


class SiteManageDto(BaseModel):
    """원본 SiteManageEntity (camelCase JSON 역직렬화용)."""
    manageId: str | None = None
    siteManageId: int | None = None
    siteManageName: str | None = None
    siteId: str | None = None
    deviceImei: int | None = None
    siteCode: int | None = None
    siteName: str | None = None
    siteType: str | None = None
    siteAttr: str | None = None
    createdBy: str | None = None
    createdDate: datetime | None = None
    updatedBy: str | None = None
    updatedDate: datetime | None = None
    siteX: int | None = None
    siteY: int | None = None
    siteFlag: str | None = None
    customerId: str | None = None
    areaId: str | None = None


class ForkliftLineDto(BaseModel):
    """원본 ForkliftLineEntity (camelCase JSON 역직렬화용)."""
    forkliftLineId: int | None = None
    lineName: str | None = None
    startSiteId: str | None = None
    startSiteName: str | None = None
    startSiteCode: int | None = None
    endSiteId: str | None = None
    endSiteName: str | None = None
    endSiteCode: int | None = None
    deviceImei: int | None = None
    stepNumber: int | None = None
    isBackingUp: int | None = None
    createdBy: str | None = None
    createdDate: datetime | None = None
    updatedBy: str | None = None
    updatedDate: datetime | None = None
    parentLineId: int | None = None
    startSiteX: int | None = None
    startSiteY: int | None = None
    endSiteX: int | None = None
    endSiteY: int | None = None
    lineAttr: str | None = None
    returnLineId: int | None = None
    returnParentId: int | None = None
    areaId: str | None = None
    isRadar: str | None = None
    lineItem: str | None = None
    isCorrectsLine: str | None = None
    customerId: str | None = None
    floor: int | None = None


class ExportSqlInfoDto(BaseModel):
    """원본 ExportSqlInfoDto (importSqlInfo data 필드 내부 구조)."""
    siteManageList: list[SiteManageDto] | None = None
    forkliftLineList: list[ForkliftLineDto] | None = None
    siteInitPointList: list[Any] | None = None
