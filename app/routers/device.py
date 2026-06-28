"""Device REST API.

원본 DeviceWarpWebService(@RequestMapping /service/warp/device) 이식.
엔드포인트: getDeviceInfo, addDevice, editDevice, delDevice, getAgvHeartList.
공통 패턴: 진입 로그 → form.check() → 서비스 호출 → 예외 시 syserr().
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.device import (
    DeviceAddForm,
    DeviceDataForm,
    DeviceDelForm,
    DeviceEditForm,
    DeviceInfoForm,
    DeviceInitForm,
    DeviceParamsSetForm,
    DevicePauseAndStartForm,
    DeviceTerminateForm,
    DeviceTrafficInfoForm,
    DeviceTreatInfoForm,
    DeviceWebInfoForm,
    DeviceWifiGetForm,
    DeviceWifiInitForm,
    InitPointsSetForm,
)
from app.services.device import device_service

LOGGER = logging.getLogger('app')

# router = APIRouter(prefix="/service/warp/device", tags=["设备管理"])
router = APIRouter(prefix="/service/warp/device", tags=["장치 관리"])
# web_router = APIRouter(prefix="/service/web/device", tags=["设备管理(web)"])
web_router = APIRouter(prefix="/service/web/device", tags=["장치 관리(web)"])


def _param_err(msg: JsonResult) -> JsonResult:
    return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")


@router.post("/getDeviceInfo", response_model=JsonResult)
async def get_device_info(form: DeviceInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("getDeviceInfo ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("getDeviceInfo <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.get_device_info(db, form)
        LOGGER.warning("getDeviceInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("获取设备列表接口出现异常！")
        LOGGER.exception("장치 목록 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/addDevice", response_model=JsonResult)
async def add_device(form: DeviceAddForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("addDevice ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("addDevice <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.add_device(db, form)
        LOGGER.warning("addDevice <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("新增设备接口出现异常！")
        LOGGER.exception("장치 추가 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/editDevice", response_model=JsonResult)
async def edit_device(form: DeviceEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("editDevice ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("editDevice <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.edit_device(db, form)
        LOGGER.warning("editDevice <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("修改设备接口出现异常！")
        LOGGER.exception("장치 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/delDevice", response_model=JsonResult)
async def del_device(form: DeviceDelForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        LOGGER.warning("delDevice ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("delDevice <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.del_device(db, form)
        LOGGER.warning("delDevice <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("删除设备接口出现异常！")
        LOGGER.exception("장치 삭제 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getAllDeviceTrafficInfo", response_model=JsonResult)
async def get_all_device_traffic_info(form: DeviceTrafficInfoForm) -> JsonResult:
    try:
        LOGGER.warning("getAllDeviceTrafficInfo ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("getAllDeviceTrafficInfo <-: %s", msg.model_dump_json())
            return _param_err(msg)
        from app.services.device_memory_table import get_all_device_traffic_info
        data = await get_all_device_traffic_info(form.deviceImei, form.floor or 0)
        result = JsonResult.success(data)
        LOGGER.warning("getAllDeviceTrafficInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("전체 장치 트래픽 정보 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getAgvHeartList", response_model=JsonResult)
async def get_agv_heart_list(form: DeviceInfoForm) -> JsonResult:
    try:
        LOGGER.warning("getAgvHeartList ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("getAgvHeartList <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.get_agv_heart_list(form)
        LOGGER.warning("getAgvHeartList <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("获取所有设备心跳接口出现异常！")
        LOGGER.exception("전체 장치 하트비트 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/initLocation", response_model=JsonResult)
async def init_location(form: DeviceInitForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 DeviceWebService.initLocation."""
    try:
        LOGGER.warning("initLocation ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("initLocation <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.init_location(db, form)
        LOGGER.warning("initLocation <-: %s", result.model_dump_json())
        return result
    except Exception:
        # LOGGER.exception("初始化位置(对外)接口出现异常！")
        LOGGER.exception("위치 초기화(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/terminateTask", response_model=JsonResult)
async def terminate_task(form: DeviceTerminateForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 DeviceWebService.terminateTask."""
    try:
        LOGGER.warning("terminateTask ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("terminateTask <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.terminate_task(db, form)
        LOGGER.warning("terminateTask <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("작업 종료(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/setWifiRestartValue", response_model=JsonResult)
async def set_wifi_restart_value(form: DeviceWifiInitForm) -> JsonResult:
    """원본 DeviceWebService.setWifiRestartValue."""
    try:
        LOGGER.warning("setWifiRestartValue ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("setWifiRestartValue <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.set_wifi_restart_value(form)
        LOGGER.warning("setWifiRestartValue <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("wifi 재시작 임계값 설정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/getDeviceInfo", response_model=JsonResult)
async def web_get_device_info(form: DeviceWebInfoForm) -> JsonResult:
    """원본 DeviceWebService.getDeviceInfo: 장치 상태 조회(외부)."""
    try:
        LOGGER.warning("web/getDeviceInfo ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("web/getDeviceInfo <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.get_web_device_info(form.deviceImei)
        LOGGER.warning("web/getDeviceInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("장치 상태 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/getDeviceList", response_model=JsonResult)
async def web_get_device_list(form: DeviceInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 DeviceWebService.getDeviceList: 장치 목록 조회(외부)."""
    try:
        LOGGER.warning("getDeviceList ->: %s", form.model_dump_json())
        result = await device_service.get_web_device_list(db)
        LOGGER.warning("getDeviceList <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("장치 목록 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/setDeviceParams", response_model=JsonResult)
async def set_device_params(form: DeviceParamsSetForm) -> JsonResult:
    """원본 DeviceWebService.setDeviceParams."""
    try:
        LOGGER.warning("setDeviceParams ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("setDeviceParams <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.set_device_params(form)
        LOGGER.warning("setDeviceParams <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("장치 파라미터 설정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/setInitPoints", response_model=JsonResult)
async def set_init_points(form: InitPointsSetForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 DeviceWebService.setInitPoints: 다중 시작점 초기화(외부)."""
    try:
        LOGGER.warning("setInitPoints ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("setInitPoints <-: %s", msg.model_dump_json())
            return _param_err(msg)
        if not form.sites:
            return JsonResult.fail("1", messages.get_msg("device.initLocation.siteCodeBotNull"))
        if len(form.sites) > 10:
            return JsonResult.fail("1", messages.get_msg("device.setInitPoints.sitesOverLength"))
        result = await device_service.set_init_points(db, form)
        LOGGER.warning("setInitPoints <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("다중 시작점 초기화(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/getWifiStrength", response_model=JsonResult)
async def get_wifi_strength(form: DeviceWifiGetForm) -> JsonResult:
    """원본 DeviceWebService.getWifiStrength: WiFi 신호 강도 조회(외부)."""
    try:
        LOGGER.warning("getWifiStrength ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("getWifiStrength <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.get_wifi_strength(form)
        LOGGER.warning("getWifiStrength <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("WiFi 신호 강도 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/setPauseAndStart", response_model=JsonResult)
async def set_pause_and_start(form: DevicePauseAndStartForm) -> JsonResult:
    """원본 DeviceWebService.setPauseAndStart: 일시정지/재시작(외부)."""
    try:
        LOGGER.warning("setPauseAndStart ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("setPauseAndStart <-: %s", msg.model_dump_json())
            return _param_err(msg)
        if not form.status or not form.status.strip():
            return JsonResult.fail("1", messages.get_msg("api.paramNotEmpty") + "【status】")
        if form.status not in ("1", "2"):
            return JsonResult.fail("1", messages.get_msg("api.paramError") + "【status】")
        result = await device_service.set_pause_and_start(form.deviceImei, form.status)
        LOGGER.warning("setPauseAndStart <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("일시정지/재시작(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/getDeviceTreatInfo", response_model=JsonResult)
async def get_device_treat_info(form: DeviceTreatInfoForm) -> JsonResult:
    """원본 DeviceWebService.getDeviceTreatInfo: 구분 상태 장치 정보 조회(외부)."""
    try:
        LOGGER.warning("getDeviceTreatInfo ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("getDeviceTreatInfo <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.get_device_treat_info(form.deviceImei)
        LOGGER.warning("getDeviceTreatInfo <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("구분 상태 장치 정보 조회(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getTimeAndData", response_model=JsonResult)
async def get_time_and_data(form: DeviceDataForm) -> JsonResult:
    """원본 DeviceWarpWebService.getTimeAndData: 장치 총 주행 거리 조회(warp)."""
    try:
        LOGGER.warning("getTimeAndData ->: %s", form.model_dump_json())
        msg = form.check()
        if not msg.is_success():
            LOGGER.warning("getTimeAndData <-: %s", msg.model_dump_json())
            return _param_err(msg)
        result = await device_service.get_time_and_data(form)
        LOGGER.warning("getTimeAndData <-: %s", result.model_dump_json())
        return result
    except Exception:
        LOGGER.exception("장치 운행 데이터 조회(warp) 인터페이스 예외 발생!")
        return JsonResult.syserr()
