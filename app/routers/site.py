"""Site/Storage REST API.

원본 SiteWarpWebService(/service/warp/site),
     StroageDeviceWarpWebService(/service/warp/storageDevice) 이식.
작업생성 의존 엔드포인트(editStorageStatus/editAreaStatus/editScanStorageStatus)는
Task 도메인 이식 후 추가한다.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.site import (
    AreaStatusEditForm,
    SiteEditForm,
    SiteInfoForm,
    SiteManageAllForm,
    SiteManageInfoForm,
    StorageDeviceAddForm,
    StorageDeviceDelForm,
    StorageDeviceInfoForm,
    StorageInfoGetForm,
    StorageSkuSetForm,
    StorageStatusEditForm,
    StorageStatusScanEditForm,
    StorageWebEditForm,
)
from app.services.storage import storage_device_relation_service, storage_service

LOGGER = logging.getLogger('app')

# site_router = APIRouter(prefix="/service/warp/site", tags=["站点管理"])
site_router = APIRouter(prefix="/service/warp/site", tags=["스테이션 관리"])
# storage_device_router = APIRouter(prefix="/service/warp/storageDevice", tags=["库位设备管理"])
storage_device_router = APIRouter(prefix="/service/warp/storageDevice", tags=["보관위치 장치 관리"])
# site_manage_router = APIRouter(prefix="/service/web/siteManage", tags=["对外站点管理"])
site_manage_router = APIRouter(prefix="/service/web/siteManage", tags=["사이트 관리(web)"])


def _param_err(msg: JsonResult) -> JsonResult:
    return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")


@site_router.post("/getSiteInfo", response_model=JsonResult)
async def get_site_info(form: SiteInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.get_site_info(db, form)
    except Exception:
        # LOGGER.exception("获取站点列表接口出现异常！")
        LOGGER.exception("스테이션 목록 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/getSiteByDevice", response_model=JsonResult)
async def get_site_by_device(form: StorageDeviceInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.get_site_by_device(db, form)
    except Exception:
        # LOGGER.exception("根据设备获取已绑定的库位接口出现异常！")
        LOGGER.exception("장치 기준 바인딩된 보관위치 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editStorage", response_model=JsonResult)
async def edit_storage(form: SiteEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_storage(db, form)
    except Exception:
        # LOGGER.exception("修改库位接口出现异常！")
        LOGGER.exception("보관위치 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@storage_device_router.post("/editStorageDevice", response_model=JsonResult)
async def edit_storage_device(form: StorageDeviceAddForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_device_relation_service.edit_storage_device(db, form)
    except Exception:
        # LOGGER.exception("绑定库位设备接口出现异常！")
        LOGGER.exception("보관위치 장치 바인딩 인터페이스 예외 발생!")
        return JsonResult.syserr()


@storage_device_router.post("/delStorageDevice", response_model=JsonResult)
async def del_storage_device(form: StorageDeviceDelForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_device_relation_service.del_storage_device(db, form)
    except Exception:
        # LOGGER.exception("解绑库位设备接口出现异常！")
        LOGGER.exception("보관위치 장치 바인딩 해제 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editStorageStatus", response_model=JsonResult)
async def edit_storage_status(form: StorageStatusEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 editStorageStatus: 수동 상태변경 (deviceImei="0")."""
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_storage_status(
            db, "0", "0", form.siteCode, form.siteStatus, form.actionType
        )
    except Exception:
        # LOGGER.exception("修改库位状态接口出现异常！")
        LOGGER.exception("보관위치 상태 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editScanStorageStatus", response_model=JsonResult)
async def edit_scan_storage_status(form: StorageStatusScanEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 editScanStorageStatus: 스캐너 상태변경."""
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_scan_storage_status(db, form)
    except Exception:
        # LOGGER.exception("扫码修改库位状态接口出现异常！")
        LOGGER.exception("바코드 스캔 보관위치 상태 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editAreaStatus", response_model=JsonResult)
async def edit_area_status(form: AreaStatusEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 editAreaStatus: 구역 일괄 상태변경(일괄 창고 정리)."""
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_area_status(db, form)
    except Exception:
        # LOGGER.exception("一键清满库接口出现异常！")
        LOGGER.exception("일괄 창고 정리 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_manage_router.post("/getAllSite", response_model=JsonResult)
async def get_all_site(form: SiteManageAllForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 SiteManageWebService.getAllSite: 전체 사이트 조회(외부)."""
    try:
        LOGGER.info("전체 사이트 조회(외부) 인터페이스 진입, 파라미터: %s", form.param_to_string())
        return await storage_service.get_all_site(db, form.customerId)
    except Exception:
        LOGGER.exception("전체 사이트 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_manage_router.post("/getSiteInfo", response_model=JsonResult)
async def get_site_manage_info(form: SiteManageInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 SiteManageWebService.getSiteInfo: 현재 사이트 정보 조회(외부)."""
    try:
        LOGGER.info("사이트 정보 조회(외부) 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.get_site_manage_info(db, form.siteCode)
    except Exception:
        LOGGER.exception("사이트 정보 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_manage_router.post("/getStorageInfo", response_model=JsonResult)
async def get_storage_info(form: StorageInfoGetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 SiteManageWebService.getStorageInfo: siteCode 기준 보관위치 물자·공만 조회(외부)."""
    try:
        LOGGER.warning("getStorageInfo ->: %s", form.model_dump_json())
        result = await storage_service.get_storage_info(db, form.siteCodes)
        LOGGER.warning("getStorageInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("보관위치 물자 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_manage_router.post("/setStorageSkus", response_model=JsonResult)
async def set_storage_skus(form: StorageSkuSetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 SiteManageWebService.setStorageSkus: 보관위치(열) SKU 바인딩(외부)."""
    try:
        LOGGER.warning("setStorageSkus ->: %s", form.model_dump_json())
        result = await storage_service.set_storage_skus(db, form)
        LOGGER.warning("setStorageSkus <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("보관위치 SKU 바인딩(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_manage_router.post("/editStorageStatus", response_model=JsonResult)
async def edit_storage_status_web(form: StorageWebEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 SiteManageWebService.editStorageStatus: TaskTempSite 조회로 actionType 자동 결정(외부)."""
    try:
        LOGGER.warning("siteManage/editStorageStatus ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        result = await storage_service.edit_storage_status_web(db, form.siteCode, form.siteStatus)
        LOGGER.warning("siteManage/editStorageStatus <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("보관위치 상태 변경(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()
